"""Configure only the dedicated authenticated clinic CI controller; never the existing8080."""

import argparse
import json
import os
import secrets
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".ci-local"
SETTINGS = ROOT / ".env.ci"
URL = "http://127.0.0.1:18090"
FOLDER = "an-uyen"
JOB = "clinic-pipeline"
OWNER = "Managed by scripts/bootstrap-ci.py for vxxngw/DevOps"


def read_settings():
    return dict(
        line.split("=", 1)
        for line in SETTINGS.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith("#")
    )


def write_settings(values):
    SETTINGS.write_text(
        "\n".join(key + "=" + value for key, value in values.items()) + "\n", encoding="utf-8"
    )
    if os.name != "nt":
        SETTINGS.chmod(0o600)


def init():
    LOCAL.mkdir(exist_ok=True, mode=0o700)
    if SETTINGS.exists():
        print("Existing .env.ci retained")
        return
    write_settings(
        {
            "CLINIC_JENKINS_ADMIN_PASSWORD": secrets.token_urlsafe(36),
            "CLINIC_JENKINS_AGENT_SECRET": "",
        }
    )
    print("Created local-only .env.ci; admin is clinic-admin; password is not printed")


class Controller:
    def __init__(self):
        password = read_settings()["CLINIC_JENKINS_ADMIN_PASSWORD"]
        self.client = httpx.Client(
            base_url=URL,
            auth=("clinic-admin", password),
            timeout=30,
            follow_redirects=True,
            trust_env=False,
        )
        anonymous = httpx.get(URL + "/api/json", timeout=10, trust_env=False)
        if anonymous.status_code == 200:
            raise RuntimeError(
                "Refusing to install credentials into an anonymously readable controller"
            )
        metadata = self.client.get("/api/json?tree=useSecurity").raise_for_status().json()
        if metadata.get("useSecurity") is not True:
            raise RuntimeError("The dedicated controller must have security enabled")
        crumb = self.client.get("/crumbIssuer/api/json").raise_for_status().json()
        self.client.headers[crumb["crumbRequestField"]] = crumb["crumb"]

    def request(self, method, path, **kwargs):
        response = self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"Jenkins HTTP{response.status_code} at{path}; response withheld")
        return response

    def owned_item(self, path, xml):
        exists = self.client.get(path + "/config.xml")
        if exists.status_code == 200:
            if OWNER not in exists.text:
                raise RuntimeError("Refusing to overwrite an item not owned by this project")
            self.request(
                "POST",
                path + "/config.xml",
                content=xml,
                headers={"Content-Type": "application/xml"},
            )
        elif exists.status_code == 404:
            parent, name = path.rsplit("/job/", 1)
            self.request(
                "POST",
                (parent or "") + "/createItem",
                params={"name": name},
                content=xml,
                headers={"Content-Type": "application/xml"},
            )
        else:
            raise RuntimeError("Cannot inspect Jenkins item")

    def credential(self, identifier, username, password):
        path = f"/job/{FOLDER}/credentials/store/folder/domain/_"
        payload = {
            "": "0",
            "credentials": {
                "scope": "GLOBAL",
                "id": identifier,
                "description": OWNER,
                "username": username,
                "password": password,
                "$class": "com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl",
            },
        }
        existing = self.request("GET", path + "/api/json?tree=credentials[id]").json()
        if any(item["id"] == identifier for item in existing.get("credentials", [])):
            print("Existing project credential retained:", identifier)
            return
        self.request("POST", path + "/createCredentials", data={"json": json.dumps(payload)})
        stored = self.request("GET", path + "/api/json?tree=credentials[id]").json()
        if not any(item["id"] == identifier for item in stored.get("credentials", [])):
            raise RuntimeError("Jenkins did not persist the credential")
        print("Stored encrypted project credential:", identifier)


def github_credential():
    if os.environ.get("CLINIC_GITHUB_TOKEN"):
        return os.environ.get("CLINIC_GITHUB_USER", "vxxngw"), os.environ["CLINIC_GITHUB_TOKEN"]
    return None


def job_xml(authenticated=False):
    root = ET.Element("flow-definition", plugin="workflow-job")
    ET.SubElement(root, "description").text = OWNER
    properties = ET.SubElement(root, "properties")
    definitions = ET.SubElement(
        ET.SubElement(properties, "hudson.model.ParametersDefinitionProperty"),
        "parameterDefinitions",
    )
    for name, value in {
        "SOURCE_REF": os.environ.get("CLINIC_SOURCE_REF", "codex/milestone-4"),
        "SOURCE_BRANCH": os.environ.get("CLINIC_SOURCE_BRANCH", "codex/milestone-4"),
        "CLUSTER_SERVER_URL": "https://192.168.150.11:6443",
        "STAGING_URL": "https://staging.anuyen.test",
        "PRODUCTION_URL": "https://hospital.anuyen.test",
        "SECURITY_DEMO": "none",
        "PRODUCTION_APPROVERS": "clinic-admin",
        "REGISTRY_NAMESPACE": os.environ.get("CLINIC_REGISTRY", "ghcr.io/vxxngw"),
    }.items():
        field = ET.SubElement(definitions, "hudson.model.StringParameterDefinition")
        ET.SubElement(field, "name").text = name
        ET.SubElement(field, "defaultValue").text = value
    for name in ["IS_PR", "PUBLISH_IMAGES", "DEPLOY"]:
        field = ET.SubElement(definitions, "hudson.model.BooleanParameterDefinition")
        ET.SubElement(field, "name").text = name
        ET.SubElement(field, "defaultValue").text = "false"
    definition = ET.SubElement(
        root,
        "definition",
        {
            "class": "org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition",
            "plugin": "workflow-cps",
        },
    )
    scm = ET.SubElement(definition, "scm", {"class": "hudson.plugins.git.GitSCM", "plugin": "git"})
    ET.SubElement(scm, "configVersion").text = "2"
    remote = ET.SubElement(
        ET.SubElement(scm, "userRemoteConfigs"), "hudson.plugins.git.UserRemoteConfig"
    )
    ET.SubElement(remote, "url").text = os.environ.get(
        "CLINIC_REPO_URL", "https://github.com/vxxngw/DevOps.git"
    )
    if authenticated:
        ET.SubElement(remote, "credentialsId").text = "clinic-github"
    ET.SubElement(
        remote, "refspec"
    ).text = "+refs/heads/*:refs/remotes/origin/* +refs/pull/*/head:refs/remotes/origin/pr/*"
    ET.SubElement(
        ET.SubElement(ET.SubElement(scm, "branches"), "hudson.plugins.git.BranchSpec"), "name"
    ).text = "${SOURCE_REF}"
    ET.SubElement(scm, "doGenerateSubmoduleConfigurations").text = "false"
    ET.SubElement(scm, "extensions")
    ET.SubElement(definition, "scriptPath").text = "Jenkinsfile"
    ET.SubElement(definition, "lightweight").text = "false"
    ET.SubElement(root, "disabled").text = "false"
    return ET.tostring(root, encoding="utf-8")


def configure():
    controller = Controller()
    folder_xml = f'<com.cloudbees.hudson.plugins.folder.Folder plugin="cloudbees-folder"><description>{OWNER}</description><properties/></com.cloudbees.hudson.plugins.folder.Folder>'.encode()
    controller.owned_item("/job/" + FOLDER, folder_xml)
    scm_credential = github_credential()
    if scm_credential:
        controller.credential("clinic-github", *scm_credential)
    registry_token = ROOT / ".registry-token"
    if registry_token.is_file() and registry_token.read_text(encoding="utf-8-sig").strip():
        controller.credential(
            "clinic-ghcr",
            os.environ.get("CLINIC_REGISTRY_USER", "vxxngw"),
            registry_token.read_text(encoding="utf-8-sig").strip(),
        )
    else:
        print("GHCR credential not available yet; publish remains blocked")
    script = """
import jenkins.model.Jenkins
import hudson.model.Node
import hudson.slaves.DumbSlave
import hudson.slaves.JNLPLauncher
def j=Jenkins.get()
def n=j.getNode('clinic-ci-linux')
if(n==null){
  def launcher=new JNLPLauncher()
  launcher.setWebSocket(true)
  n=new DumbSlave('clinic-ci-linux','/home/jenkins/agent',launcher)
  n.setNumExecutors(1)
  n.setMode(Node.Mode.EXCLUSIVE)
  n.setLabelString('clinic-ci-linux')
  j.addNode(n)
}
println(j.getComputer('clinic-ci-linux').getJnlpMac())
"""
    secret = controller.request("POST", "/scriptText", data={"script": script}).text.strip()
    if (
        not secret
        or len(secret) < 32
        or any(character not in "0123456789abcdef" for character in secret)
    ):
        raise RuntimeError("Agent setup failed; secret not printed")
    values = read_settings()
    values["CLINIC_JENKINS_AGENT_SECRET"] = secret
    write_settings(values)
    controller.owned_item(f"/job/{FOLDER}/job/{JOB}", job_xml(authenticated=bool(scm_credential)))
    print(
        "Configured dedicated authenticated controller, project folder, SCM credential, agent and pipeline"
    )


def validate():
    controller = Controller()
    response = controller.request(
        "POST",
        "/pipeline-model-converter/validate",
        data={"jenkinsfile": (ROOT / "Jenkinsfile").read_text(encoding="utf-8")},
    )
    if "Jenkinsfile successfully validated" not in response.text:
        raise RuntimeError("Declarative validation failed: " + response.text[:2000])
    print("Jenkinsfile successfully validated by Jenkins")


def configure_webhook():
    controller = Controller()
    directory = LOCAL / "webhook"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    secret_file = directory / "webhook-secret"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32), encoding="utf-8")
    configuration = directory / "webhook-config.json"
    if configuration.exists():
        print("Existing private webhook configuration retained")
        return
    # The relay's API token has READ/BUILD permissions only, via security.groovy.
    script = """
import jenkins.model.Jenkins
import hudson.model.User
import jenkins.security.ApiTokenProperty
def user=User.getById('clinic-webhook', false)
if(user==null){
  Jenkins.get().getSecurityRealm().createAccount('clinic-webhook', java.util.UUID.randomUUID().toString())
  user=User.getById('clinic-webhook', false)
}
def property=user.getProperty(ApiTokenProperty.class)
def token=property.tokenStore.generateNewToken('clinic-webhook-relay')
user.save()
println(token.plainValue)
"""
    token = controller.request("POST", "/scriptText", data={"script": script}).text.strip()
    if len(token) < 32 or not all(character in "0123456789abcdef" for character in token):
        raise RuntimeError("Webhook API token setup failed; response withheld")
    configuration.write_text(
        json.dumps(
            {
                "jenkins_url": "http://controller:8080",
                "username": "clinic-webhook",
                "api_token": token,
            }
        ),
        encoding="utf-8",
    )
    if os.name != "nt":
        # The relay container runs as UID10001. Directory is only mounted in that service.
        directory.chmod(0o755)
        secret_file.chmod(0o644)
        configuration.chmod(0o644)
    print("Created local-only webhook HMAC and restricted Jenkins token; values withheld")


def github_webhook(public_url):
    from urllib.parse import urlparse

    parsed = urlparse(public_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Webhook requires a public HTTPS URL without credentials/query/fragment")
    secret_file = LOCAL / "webhook/webhook-secret"
    secret = secret_file.read_text(encoding="utf-8").strip()
    if len(secret) < 32:
        raise ValueError("Missing local webhook secret; run configure-webhook first")
    credential = github_credential()
    if credential is None:
        raise RuntimeError("GitHub webhook management requires an explicit CLINIC_GITHUB_TOKEN")
    username, token = credential
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    base = "https://api.github.com/repos/vxxngw/DevOps"
    endpoint = public_url.rstrip("/") + "/github"
    with httpx.Client(auth=(username, token), headers=headers, timeout=30) as client:
        hooks = client.get(base + "/hooks").raise_for_status().json()
        existing = [hook for hook in hooks if hook.get("config", {}).get("url") == endpoint]
        payload = {
            "name": "web",
            "active": True,
            "events": ["push", "pull_request"],
            "config": {
                "url": endpoint,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0",
            },
        }
        if existing:
            response = client.patch(base + "/hooks/" + str(existing[0]["id"]), json=payload)
        else:
            response = client.post(base + "/hooks", json=payload)
        response.raise_for_status()
        hook = response.json()
    print(
        "Configured GitHub webhook",
        hook["id"],
        "with TLS verification; actual delivery/build still requires verification",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["init", "configure", "validate", "configure-webhook", "github-webhook"]
    )
    parser.add_argument("--public-url")
    args = parser.parse_args()
    if args.action == "github-webhook":
        if not args.public_url:
            parser.error(
                "github-webhook requires --public-url pointing to the relay, never the controller"
            )
        github_webhook(args.public_url)
    else:
        {
            "init": init,
            "configure": configure,
            "validate": validate,
            "configure-webhook": configure_webhook,
        }[args.action]()


if __name__ == "__main__":
    main()

import importlib.util
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ci_bootstrap", ROOT / "scripts/bootstrap-ci.py")
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def test_public_source_never_queries_local_credentials(monkeypatch):
    monkeypatch.delenv("CLINIC_GITHUB_TOKEN", raising=False)

    def refuse(*args, **kwargs):
        raise AssertionError("Public SCM must not read credential helpers")

    monkeypatch.setattr(subprocess, "run", refuse)
    assert bootstrap.github_credential() is None
    root = ET.fromstring(bootstrap.job_xml())
    assert root.find(".//credentialsId") is None


def test_explicit_source_token_remains_supported(monkeypatch):
    monkeypatch.setenv("CLINIC_GITHUB_TOKEN", "unit-test-only-not-a-deployment-token")
    monkeypatch.setenv("CLINIC_GITHUB_USER", "unit-user")
    assert bootstrap.github_credential() == ("unit-user", "unit-test-only-not-a-deployment-token")
    assert ET.fromstring(bootstrap.job_xml(True)).findtext(".//credentialsId") == "clinic-github"


def test_registry_namespace_is_configurable(monkeypatch):
    monkeypatch.setenv("CLINIC_REGISTRY", "ghcr.io/baolong205")
    root = ET.fromstring(bootstrap.job_xml())
    parameters = {
        field.findtext("name"): field.findtext("defaultValue")
        for field in root.findall(".//hudson.model.StringParameterDefinition")
    }
    assert parameters["REGISTRY_NAMESPACE"] == "ghcr.io/baolong205"


def test_webhook_management_still_requires_explicit_token(monkeypatch, tmp_path):
    monkeypatch.delenv("CLINIC_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(bootstrap, "LOCAL", tmp_path)
    directory = tmp_path / "webhook"
    directory.mkdir()
    (directory / "webhook-secret").write_text("unit-test-only-" * 4)
    with pytest.raises(RuntimeError, match="explicit CLINIC_GITHUB_TOKEN"):
        bootstrap.github_webhook("https://relay.example.test")


def test_deployment_uses_fork_and_exact_revision(monkeypatch):
    monkeypatch.setenv("CLINIC_REPO_URL", "https://github.com/baolong205/DevOps.git")
    monkeypatch.setenv("CLINIC_SOURCE_REF", "a" * 40)
    monkeypatch.setenv("CLINIC_SOURCE_BRANCH", "deploy/baolong205-jenkins")
    root = ET.fromstring(bootstrap.job_xml())
    assert root.findtext(".//userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url") == (
        "https://github.com/baolong205/DevOps.git"
    )
    parameters = {
        field.findtext("name"): field.findtext("defaultValue")
        for field in root.findall(".//hudson.model.StringParameterDefinition")
    }
    assert parameters["SOURCE_REF"] == "a" * 40
    assert parameters["SOURCE_BRANCH"] == "deploy/baolong205-jenkins"

# Jenkins deployment review: baolong205

This branch starts from local commit
`5cac55cd32b0a4466d6a6eb05236c517fd3c7101`, which already contains the
controller, engine, agent and Ansible provisioning files. It does not start from
the current origin HEAD, which lacks `scripts/bootstrap-ci.py`.

Scope:

- Public source checkout without an SCM credential or credential-helper lookup.
- Optional explicit SCM token remains supported for private source.
- GHCR account and pipeline namespace configurable; private inventory selects
  `baolong205` / `ghcr.io/baolong205`.
- Explicit token still required for GitHub webhook management (not public clone).
- Unit tests cover anonymous checkout and registry namespace propagation.

Existing observability files and pipeline stage are retained. Unrelated local
deletions, infrastructure work and evidence are not copied into this branch.
No Vault, key, state or private inventory belongs in this branch.

Before deployment:

1. Review this branch's diff and choose a repository where the operator can push.
2. Commit and push only after approval; record the exact remote commit in private
   inventory as `clinic_repo_revision` and set `clinic_repo_url` accordingly.
3. Select a source ref containing these changes when configuring/running the
   Jenkins pipeline; inherited milestone branch defaults are not acceptance proof.
4. Supply the encrypted deployment Vault interactively, never via chat or logs.
5. Run the CI play and verify controller/agent health plus a second-run recap.

This review preparation does not install Jenkins or establish runtime acceptance.

The public fork `baolong205/DevOps` was verified accessible. Provisioning now
passes the inventory repository URL and exact deployment revision into job XML,
so the initial pipeline checkout does not fall back to the upstream milestone
branch. GitHub webhook management remains outside this provisioning scope.
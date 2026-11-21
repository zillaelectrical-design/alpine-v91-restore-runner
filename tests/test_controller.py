import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ".github/workflows/recovery-control.yml"
workflow = (ROOT / WORKFLOW_PATH).read_text(encoding="utf-8")
sha = "1" * 40


def run_fragment(name, env):
    source = workflow.split(f"          # {name}\n", 1)[1]
    source = source.split(f"          # end {name}\n", 1)[0]
    script = "\n".join(line.removeprefix(" " * 10) for line in source.splitlines())
    return subprocess.run(["bash", "-c", script], env=env, capture_output=True)


def verify_workflow_digest(body):
    manifest = (ROOT / "SHA256SUMS").read_text(encoding="utf-8")
    digest, path = next(line.split("  ", 1) for line in manifest.splitlines()
                        if line.endswith(f"  {WORKFLOW_PATH}"))
    assert path == WORKFLOW_PATH
    return hashlib.sha256(body).hexdigest() == digest


assert "permissions:\n  contents: read\n" in workflow
assert "    needs: authorize\n" in workflow
assert "needs.authorize.result == 'success'" in workflow
assert "    environment: alpine-v91-restore\n" in workflow
assert workflow.count("github.ref == 'refs/heads/main'") == 3
assert "workflow_dispatch:" in workflow
assert not re.search(r"pull_request_target|workflow_run|secrets\.|id-token:", workflow)
assert verify_workflow_digest(workflow.encode())
assert not verify_workflow_digest(workflow.replace("exit 66", "exit 0").encode())
print("PASS modified workflow rejected against the trusted manifest")

valid = {"confirm": "CHECK_DISABLED_CONTROLLER", "reviewed_sha": sha}
with tempfile.TemporaryDirectory() as temp:
    payload = Path(temp, "event.json")
    payload.write_text(json.dumps({"inputs": valid}), encoding="utf-8")
    env = {
        "PATH": os.defpath,
        "GITHUB_EVENT_PATH": str(payload),
        "GITHUB_REPOSITORY": "zillaelectrical-design/alpine-v91-restore-runner",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_SHA": sha,
        "GITHUB_WORKFLOW_SHA": sha,
        "APPROVED_SHA": sha,
    }
    assert run_fragment("dispatch guard", env).returncode == 0
    for key, bad in {
        "GITHUB_REPOSITORY": "example/other",
        "GITHUB_REF": "refs/heads/unreviewed",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_SHA": "2" * 40,
        "GITHUB_WORKFLOW_SHA": "2" * 40,
        "APPROVED_SHA": "",
    }.items():
        assert run_fragment("dispatch guard", env | {key: bad}).returncode != 0, key
    for inputs in ({}, valid | {"extra": "x"}, valid | {"confirm": "RESTORE"},
                   valid | {"reviewed_sha": "2" * 40}):
        payload.write_text(json.dumps({"inputs": inputs}), encoding="utf-8")
        assert run_fragment("dispatch guard", env).returncode != 0, inputs
    print("PASS unexpected repo, branch, event, commit and input rejected")
    assert run_fragment("recovery barrier", env).returncode == 66
    print("PASS disabled recovery exits 66")

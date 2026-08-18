"""Mentrix Coding Agent production missions A–G — real disposable git, no fake PASS."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.services.coding_engine.lifecycle import (
    approve_git,
    approve_plan,
    cancel_mission,
    repair_and_retry,
    resume_mission,
    start_mission,
)
from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.services.mentrix.org_policy import ensure_companion_rules
from app.services.mentrix.permission_broker import check_tool_permission


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return (out.stdout or "").strip()


def _init_repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "zect-ca@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT CA"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


def _bare_origin(tmp: Path, name: str) -> Path:
    bare = tmp / f"{name}.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True, text=True)
    return bare


def _add_origin(repo: Path, bare: Path) -> None:
    subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=repo, check=True, capture_output=True)


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("MENTRIX_PR_DRY_RUN", "0")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return tmp_path


def test_git_commit_always_needs_approval(ws):
    repo = _init_repo(ws / "r", {"a.txt": "x\n"})
    (repo / "a.txt").write_text("y\n", encoding="utf-8")
    root = resolve_workspace(str(repo))
    out = execute_tool("git_commit", {"message": "x"}, workspace=root, auto_approve_edits=True)
    assert out.get("needs_approval") is True
    out2 = execute_tool(
        "git_commit",
        {"message": "x", "_approved": True},
        workspace=root,
        auto_approve_edits=True,
    )
    assert out2.get("ok") is True


def test_permission_broker_git_write_is_always_confirm():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    ensure_companion_rules(db)
    r = check_tool_permission(db, "git_commit", user_confirmed=False)
    assert r["needs_confirm"] is True or r["result"] in ("pending_approval", "denied")
    r2 = check_tool_permission(db, "git_push", user_confirmed=False)
    assert r2["needs_confirm"] is True or r2["result"] in ("pending_approval", "denied")


def test_mission_a_backend_defect(ws):
    repo = _init_repo(
        ws / "backend",
        {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        },
    )
    bare = _bare_origin(ws, "backend")
    _add_origin(repo, bare)
    m = start_mission(
        goal="Fix add() so 2+3 is 5",
        roots=[{"id": 1, "label": "backend", "path": str(repo)}],
        patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
        workspace_parent=str(ws / "wt"),
    )
    assert m["phase"] == "awaiting_plan_approval"
    m = approve_plan(m["id"])
    assert m["phase"] == "awaiting_git_approval"
    assert m["tests"]["1"] == "pass"
    m = approve_git(m["id"])
    assert m["phase"] == "ready_to_merge"
    assert m["no_auto_merge"] is True
    sha = m["repos"][0]["committed_shas"][-1]
    again = approve_git(m["id"])
    assert again["repos"][0]["committed_shas"][-1] == sha


def test_mission_b_frontend_defect(ws):
    repo = _init_repo(
        ws / "web",
        {
            "web/greet.js": 'export function greet(name) { return "Hello"; }\n',
            "tests/test_greet.py": (
                "from pathlib import Path\n\n"
                "def test_greet_uses_name():\n"
                "    text = Path('web/greet.js').read_text(encoding='utf-8')\n"
                "    assert 'Hello, ' in text\n"
            ),
        },
    )
    m = start_mission(
        goal="Greet must include the name",
        roots=[{"id": 2, "label": "web", "path": str(repo)}],
        patches_by_repo={
            "2": [{"path": "web/greet.js", "old": 'return "Hello"', "new": 'return "Hello, " + name'}]
        },
        workspace_parent=str(ws / "wt"),
    )
    m = approve_plan(m["id"])
    assert m["phase"] == "awaiting_git_approval"
    m = approve_git(m["id"], push=True)
    assert m["ready_to_merge"] is True
    assert m["repos"][0]["push"].get("skipped") == "no_origin"


def test_mission_c_fullstack_feature(ws):
    repo = _init_repo(
        ws / "full",
        {
            "api.py": "PRICE = 10\n",
            "web/client.js": "export const PRICE = 10;\n",
            "tests/test_price.py": (
                "from pathlib import Path\nimport api\n\n"
                "def test_price():\n"
                "    assert api.PRICE == 12\n"
                "    assert '12' in Path('web/client.js').read_text(encoding='utf-8')\n"
            ),
        },
    )
    m = start_mission(
        goal="Raise price to 12 in API and client",
        roots=[{"id": 3, "label": "full", "path": str(repo)}],
        patches_by_repo={
            "3": [
                {"path": "api.py", "old": "PRICE = 10", "new": "PRICE = 12"},
                {"path": "web/client.js", "old": "PRICE = 10", "new": "PRICE = 12"},
            ]
        },
        workspace_parent=str(ws / "wt"),
    )
    m = approve_git(approve_plan(m["id"])["id"], push=False)
    assert m["phase"] == "ready_to_merge"


def test_mission_d_security_defect(ws):
    repo = _init_repo(
        ws / "sec",
        {
            "config.py": 'API_KEY = "sk-live-secret-value"\n',
            "tests/test_config.py": (
                "from pathlib import Path\n\n"
                "def test_no_hardcoded_key():\n"
                "    text = Path('config.py').read_text(encoding='utf-8')\n"
                "    assert 'sk-live' not in text\n"
            ),
        },
    )
    m = start_mission(
        goal="Remove hardcoded API key",
        roots=[{"id": 4, "label": "sec", "path": str(repo)}],
        patches_by_repo={
            "4": [
                {
                    "path": "config.py",
                    "old": 'API_KEY = "sk-live-secret-value"',
                    "new": "import os\nAPI_KEY = os.environ.get('API_KEY', '')",
                }
            ]
        },
        workspace_parent=str(ws / "wt"),
    )
    planned = approve_plan(m["id"])
    assert planned["phase"] == "awaiting_git_approval", planned.get("review")
    m = approve_git(planned["id"], push=False)
    assert m["phase"] == "ready_to_merge"


def test_mission_e_review_blocks_then_remediates(ws):
    repo = _init_repo(
        ws / "rev",
        {
            "unsafe.py": "def run(q):\n    return eval(q)\n",
            "tests/test_ok.py": "def test_ok():\n    assert True\n",
        },
    )
    blocked = start_mission(
        goal="Stop using eval",
        roots=[{"id": 5, "label": "rev", "path": str(repo)}],
        patches_by_repo={"5": []},
        workspace_parent=str(ws / "wt-block"),
    )
    blocked = approve_plan(blocked["id"])
    assert blocked["phase"] == "blocked"
    assert blocked["review"]["critical_findings"] >= 1

    fixed = start_mission(
        goal="Stop using eval",
        roots=[{"id": 5, "label": "rev", "path": str(repo)}],
        patches_by_repo={
            "5": [{"path": "unsafe.py", "old": "return eval(q)", "new": "return str(q)"}]
        },
        workspace_parent=str(ws / "wt-fix"),
    )
    fixed = approve_git(approve_plan(fixed["id"])["id"], push=False)
    assert fixed["phase"] == "ready_to_merge"


def test_mission_f_sibling_failure_blocks_then_repair(ws):
    a = _init_repo(
        ws / "alpha",
        {
            "protocol.py": "PROTOCOL = 1\n",
            "tests/test_a.py": "import protocol\n\ndef test_proto():\n    assert protocol.PROTOCOL == 2\n",
        },
    )
    b = _init_repo(
        ws / "beta",
        {
            "protocol.py": "PROTOCOL = 1\n",
            "tests/test_b.py": "import protocol\n\ndef test_proto():\n    assert protocol.PROTOCOL == 2\n",
        },
    )
    m = start_mission(
        goal="Bump protocol to 2 in both roots",
        roots=[
            {"id": 10, "label": "alpha", "path": str(a)},
            {"id": 11, "label": "beta", "path": str(b)},
        ],
        patches_by_repo={"10": [{"path": "protocol.py", "old": "PROTOCOL = 1", "new": "PROTOCOL = 2"}]},
        workspace_parent=str(ws / "wt"),
    )
    m = approve_plan(m["id"])
    assert m["phase"] == "blocked"
    assert m["sibling"]["blocked"] is True
    with pytest.raises(ValueError):
        approve_git(m["id"])
    m = repair_and_retry(
        m["id"],
        {"11": [{"path": "protocol.py", "old": "PROTOCOL = 1", "new": "PROTOCOL = 2"}]},
    )
    assert m["phase"] == "awaiting_git_approval"
    m = approve_git(m["id"], push=False)
    assert m["phase"] == "ready_to_merge"
    assert all(r["test_ok"] for r in m["repos"])


def test_mission_g_cancel_resume_no_duplicate_commits(ws):
    repo = _init_repo(
        ws / "g",
        {
            "n.py": "N = 1\n",
            "tests/test_n.py": "import n\n\ndef test_n():\n    assert n.N == 2\n",
        },
    )
    m = start_mission(
        goal="Set N=2",
        roots=[{"id": 7, "label": "g", "path": str(repo)}],
        patches_by_repo={"7": [{"path": "n.py", "old": "N = 1", "new": "N = 2"}]},
        workspace_parent=str(ws / "wt"),
    )
    m = approve_plan(m["id"])
    assert m["phase"] == "awaiting_git_approval", (m.get("phase"), m.get("review"), m.get("tests"), m.get("blockers"))
    m = cancel_mission(m["id"])
    assert m["phase"] == "cancelled"
    m = resume_mission(m["id"])
    assert m["phase"] == "awaiting_git_approval"
    m = approve_git(m["id"], push=False)
    shas = list(m["repos"][0]["committed_shas"])
    m = approve_git(m["id"], push=False)
    assert m["repos"][0]["committed_shas"] == shas
    head_main = _git(repo, "rev-parse", "HEAD")
    assert head_main not in shas
    assert (repo / "n.py").read_text(encoding="utf-8") == "N = 1\n"


def test_github_push_blocked_external_without_token(ws):
    repo = _init_repo(
        ws / "gh",
        {
            "z.py": "Z = 1\n",
            "tests/test_z.py": "import z\n\ndef test_z():\n    assert z.Z == 2\n",
        },
    )
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/example/zect-ca.git"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    m = start_mission(
        goal="Set Z=2",
        roots=[{"id": 8, "label": "gh", "path": str(repo)}],
        patches_by_repo={"8": [{"path": "z.py", "old": "Z = 1", "new": "Z = 2"}]},
        workspace_parent=str(ws / "wt"),
    )
    planned = approve_plan(m["id"])
    assert planned["phase"] == "awaiting_git_approval", planned.get("review")
    m = approve_git(planned["id"], push=True)
    assert m["repos"][0]["push"].get("blocked_external") is True
    assert m["phase"] == "ready_to_merge"
    assert m["ci"]["status"] == "BLOCKED_EXTERNAL"


def test_missions_require_auth(client):
    r = client.post("/api/coding-agent/missions", json={"goal": "x", "roots": [{"id": 1, "path": "/tmp"}]})
    assert r.status_code in (401, 403)


def test_mission_http_lifecycle(ws, authed_client):
    repo = _init_repo(
        ws / "http",
        {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        },
    )
    created = authed_client.post(
        "/api/coding-agent/missions",
        json={
            "goal": "Fix add()",
            "roots": [{"id": 91, "label": "http", "path": str(repo)}],
            "patches_by_repo": {"91": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            "workspace_parent": str(ws / "wt-http"),
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["phase"] == "awaiting_plan_approval"
    assert body["no_auto_merge"] is True
    mid = body["id"]
    planned = authed_client.post(f"/api/coding-agent/missions/{mid}/approve-plan")
    assert planned.status_code == 200, planned.text
    assert planned.json()["phase"] == "awaiting_git_approval"
    cancelled = authed_client.post(f"/api/coding-agent/missions/{mid}/cancel")
    assert cancelled.json()["phase"] == "cancelled"
    resumed = authed_client.post(f"/api/coding-agent/missions/{mid}/resume")
    assert resumed.json()["phase"] == "awaiting_git_approval"
    git = authed_client.post(f"/api/coding-agent/missions/{mid}/approve-git")
    assert git.status_code == 200, git.text
    out = git.json()
    assert out["phase"] == "ready_to_merge"
    assert out["no_auto_merge"] is True
    got = authed_client.get(f"/api/coding-agent/missions/{mid}")
    assert got.json()["phase"] == "ready_to_merge"


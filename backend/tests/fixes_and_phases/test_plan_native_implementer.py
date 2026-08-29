"""PLAN → native implementer, pull-intent (no mission), discovered JS tests, jailed git."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.services.coding_engine.lifecycle import (
    approve_plan,
    isolate_worktree,
    run_repo_tests,
    start_mission,
)
from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace
from app.services.coding_engine.sync_pull import is_pull_sync_intent, sync_authorized_roots


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "zect-ca@example.com")
    _git(root, "config", "user.name", "ZECT CA")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "init")
    return root


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    return tmp_path


def test_pull_sync_intent_does_not_match_code_change():
    assert is_pull_sync_intent("pull latest ZOAS and ZAF")
    assert is_pull_sync_intent("git pull the authorized clones")
    assert is_pull_sync_intent("sync clones")
    assert not is_pull_sync_intent("Fix add() so 2+3 is 5")
    assert not is_pull_sync_intent("Approve the PLAN and implement the overlay")


def test_sync_authorized_roots_never_creates_a_mission(ws, monkeypatch):
    repo = _init_repo(ws / "zoas", {"README.md": "ok\n"})
    monkeypatch.setattr(
        "app.services.coding_engine.sync_pull.ff_pull_root",
        lambda path, remote="origin": {
            "ok": True,
            "path": path,
            "exit_code": 0,
            "stdout": "Already up to date.",
            "stderr": "",
            "lattice_stale": True,
        },
    )
    out = sync_authorized_roots([{"id": 1, "label": "zoas", "path": str(repo)}])
    assert out["mission_created"] is False
    assert out["phase"] == "synced"
    assert out["lattice_stale"] is True
    assert out["no_auto_merge"] is True
    assert out["roots"][0]["ok"] is True


def test_approve_plan_empty_propose_uses_native_smoke(ws, monkeypatch):
    repo = _init_repo(ws / "app", {"hello.py": "print('hi')\n"})
    src_hello = (repo / "hello.py").read_text(encoding="utf-8")
    monkeypatch.setenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE", "1")
    monkeypatch.setattr(
        "app.services.coding_engine.propose_patches.propose_from_plan",
        lambda mission: {},
    )
    m = start_mission(
        goal="Add a smoke marker from PLAN",
        roots=[{"id": 9, "label": "app", "path": str(repo)}],
        plan="# PLAN\n\nWrite the smoke marker.\n",
        workspace_parent=str(ws / "wt"),
        propose_if_empty=True,
    )
    m = approve_plan(m["id"])
    native = m["repos"][0].get("native_build") or {}
    assert native.get("ok") is True or native.get("files_written")
    wt = Path(m["repos"][0]["worktree_path"])
    assert (wt / "mentrix_p0_smoke_marker.py").is_file()
    assert (repo / "hello.py").read_text(encoding="utf-8") == src_hello
    assert not (repo / "mentrix_p0_smoke_marker.py").exists()


def test_run_repo_tests_discovers_npm_script(ws):
    repo = _init_repo(
        ws / "web",
        {
            "package.json": json.dumps({"scripts": {"test": "node -e \"process.exit(0)\""}}),
        },
    )
    iso = isolate_worktree(repo, branch="zect-ca-js", dest=ws / "wt" / "web")
    assert iso.get("ok"), iso
    out = run_repo_tests(Path(iso["worktree_path"]))
    if not out.get("ok") and "npm" not in str(out.get("kind") or "") and out.get("kind") in ("none", None):
        pytest.skip("node/npm not available in this environment")
    assert out["ok"] or out.get("kind") == "none", out


def test_git_checkout_refused_on_live_clone(ws):
    repo = _init_repo(ws / "live", {"a.txt": "1\n"})
    root = resolve_workspace(str(repo))
    out = execute_tool("git_checkout", {"branch": "other"}, workspace=root, auto_approve_edits=True)
    assert out.get("ok") is False
    assert out.get("error") == "refused_live_clone_checkout"


def test_git_pull_tool_is_ff_only(ws, monkeypatch):
    repo = _init_repo(ws / "live", {"a.txt": "1\n"})
    root = resolve_workspace(str(repo))
    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(list(argv) if isinstance(argv, (list, tuple)) else [str(argv)])

        class R:
            returncode = 0
            stdout = "Already up to date."
            stderr = ""

        return R()

    monkeypatch.setattr("app.services.coding_engine.sync_pull.subprocess.run", fake_run)
    out = execute_tool("git_pull", {"remote": "origin"}, workspace=root, auto_approve_edits=True)
    assert out.get("ok") is True
    joined = " ".join(" ".join(cmd) for cmd in seen)
    assert "--ff-only" in joined

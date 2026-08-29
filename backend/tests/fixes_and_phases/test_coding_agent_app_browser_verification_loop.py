"""_run_app_and_browser_verification wired into the real mission loop:
edit -> test pass -> start/verify in a real browser -> failure -> diagnose ->
retry -> final evidence. Uses a mocked native-agent-loop call (as the
diagnose-and-retry tests do) so this is deterministic, but everything around
it -- recipe discovery, the mission phase machine, process cleanup -- is real."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.domains.workspace.app_runner import list_owned_processes_in_workspace
from app.services.coding_engine.lifecycle import approve_plan, start_mission


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


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    monkeypatch.setenv("MENTRIX_PR_DRY_RUN", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def _app_repo_with_passing_patch(ws) -> Path:
    """A repo with both a passing unit test AND a package.json -- so
    runtime_discovery finds a recipe and browser verification actually runs."""
    return _init_repo(
        ws / "webapp",
        {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            "package.json": json.dumps({"scripts": {"dev": "echo unused-in-mocked-test"}}),
        },
    )


class TestAppAndBrowserVerificationInTheRealLoop:
    def test_verification_runs_and_passes_reaches_awaiting_git_approval(self, ws, monkeypatch):
        repo = _app_repo_with_passing_patch(ws)
        m = start_mission(
            goal="Fix add()",
            roots=[{"id": 1, "label": "webapp", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            workspace_parent=str(ws / "wt"),
        )

        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
            return_value={"ok": True, "status": "completed", "files_written": [], "summary": "verified in browser"},
        ) as mocked:
            m = approve_plan(m["id"])

        assert mocked.called, "browser verification must actually invoke the native agent loop, not skip it"
        assert m["phase"] == "awaiting_git_approval", m
        verify = m["repos"][0]["browser_verification"]
        assert verify["ran"] is True
        assert verify["verified"] is True
        events = [e["event"] for e in m["events"]]
        assert "browser_verify_attempt" in events
        assert "browser_verify_result" in events

    def test_verification_failure_blocks_with_evidence_of_every_attempt(self, ws, monkeypatch):
        monkeypatch.setenv("MENTRIX_CODING_AGENT_BROWSER_VERIFY_MAX", "2")
        monkeypatch.setenv("MENTRIX_CODING_AGENT_AUTO_REPAIR_MAX", "1")
        repo = _app_repo_with_passing_patch(ws)
        m = start_mission(
            goal="Fix add()",
            roots=[{"id": 1, "label": "webapp", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            workspace_parent=str(ws / "wt"),
        )

        # The mocked "agent" never actually fixes anything and the retest
        # inside the diagnose loop it triggers still fails -- proving a
        # genuinely unverifiable app still reaches blocked, not a false pass.
        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
            return_value={"ok": False, "status": "no_browser_available", "files_written": [], "summary": "could not verify"},
        ):
            m = approve_plan(m["id"])

        assert m["phase"] == "blocked", m
        repo_out = m["repos"][0]
        assert "browser_verification_failed" in repo_out["blocker"]
        assert repo_out["browser_verification"]["attempts"] == 2

    def test_no_runnable_app_is_a_noop_not_a_failure(self, ws):
        """The existing diagnose-and-retry fixture repo has no package.json/
        requirements.txt -- confirms verification silently skips rather than
        blocking a mission that has nothing browsable."""
        repo = _init_repo(
            ws / "lib",
            {
                "calc.py": "def add(a, b):\n    return a - b\n",
                "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            },
        )
        m = start_mission(
            goal="Fix add()",
            roots=[{"id": 1, "label": "lib", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            workspace_parent=str(ws / "wt"),
        )
        with patch("app.services.coding_engine.mentrix_native_build.run_mentrix_native_build") as mocked:
            m = approve_plan(m["id"])
        assert not mocked.called, "no recipe was discoverable -- must not invent a browser-verification turn"
        assert m["phase"] == "awaiting_git_approval"
        assert m["repos"][0]["browser_verification"]["ran"] is False

    def test_no_lingering_owned_process_after_verification(self, ws):
        """stop_owned_processes_in_workspace must run even when verification
        passes -- a mission must never leave a server running behind it."""
        repo = _app_repo_with_passing_patch(ws)
        m = start_mission(
            goal="Fix add()",
            roots=[{"id": 1, "label": "webapp", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            workspace_parent=str(ws / "wt"),
        )
        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
            return_value={"ok": True, "status": "completed", "files_written": []},
        ):
            m = approve_plan(m["id"])
        wt = m["repos"][0]["worktree_path"]
        owned = [p for p in list_owned_processes_in_workspace(wt) if p["running"]]
        assert owned == []

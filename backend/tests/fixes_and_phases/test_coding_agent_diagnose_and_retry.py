"""Coding Agent: on test failure, diagnose-and-repair via the same native agent
loop before giving up, bounded so a persistently-broken repo still reaches
`blocked` rather than looping forever or being silently reported as passing.

Closes the gap identified in the Developer Workspace reconciliation: previously
a test failure just set phase="blocked" with no attempt to fix it, and
retry/resume re-ran the identical unchanged patch (guaranteed to fail again)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

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


def _broken_mission(ws):
    """A patch that still leaves the test failing -- add() stays subtraction."""
    repo = _init_repo(
        ws / "backend",
        {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        },
    )
    return start_mission(
        goal="Fix add() so 2+3 is 5",
        roots=[{"id": 1, "label": "backend", "path": str(repo)}],
        patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a - b  # unchanged"}]},
        workspace_parent=str(ws / "wt"),
    )


class TestDiagnoseAndRepair:
    def test_bounded_retries_still_block_when_repair_cannot_fix_it(self, ws, monkeypatch):
        monkeypatch.setenv("MENTRIX_CODING_AGENT_AUTO_REPAIR_MAX", "2")
        m = _broken_mission(ws)
        m = approve_plan(m["id"])

        assert m["phase"] == "blocked"
        repo = m["repos"][0]
        assert repo["auto_repair_attempts"] == 2, "must exhaust the bounded budget, not skip or loop forever"
        assert "tests_fail_after_2_repair_attempt(s)" in repo["blocker"]
        attempt_events = [e for e in m["events"] if e["event"] in ("diagnose_attempt", "diagnose_result")]
        assert len(attempt_events) == 4, "2 attempts x (attempt + result) = 4 evidence events, not hidden"

    def test_successful_repair_unblocks_the_mission(self, ws, monkeypatch):
        monkeypatch.setenv("MENTRIX_CODING_AGENT_AUTO_REPAIR_MAX", "2")

        def fake_repair(*, workspace, **_kwargs):
            target = Path(workspace) / "calc.py"
            target.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            return {"ok": True, "status": "completed", "files_written": ["calc.py"], "run_id": "fake"}

        m = _broken_mission(ws)
        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
            side_effect=fake_repair,
        ):
            m = approve_plan(m["id"])

        assert m["phase"] == "awaiting_git_approval", m
        repo = m["repos"][0]
        assert repo["test_ok"] is True
        assert repo["auto_repair_attempts"] == 1, "should stop as soon as tests pass, not spend the whole budget"
        assert repo["blocker"] == ""
        result_events = [e for e in m["events"] if e["event"] == "diagnose_result"]
        assert result_events and result_events[-1]["data"]["ok"] is True

    def test_passing_tests_never_invoke_repair(self, ws):
        """No regression: a correct patch takes the exact same path as before."""
        repo = _init_repo(
            ws / "backend",
            {
                "calc.py": "def add(a, b):\n    return a - b\n",
                "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            },
        )
        m = start_mission(
            goal="Fix add()",
            roots=[{"id": 1, "label": "backend", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            workspace_parent=str(ws / "wt"),
        )
        m = approve_plan(m["id"])
        assert m["phase"] == "awaiting_git_approval"
        assert m["repos"][0].get("auto_repair_attempts", 0) == 0
        assert not [e for e in m["events"] if e["event"].startswith("diagnose_")]

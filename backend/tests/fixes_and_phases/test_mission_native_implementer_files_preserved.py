"""_run_edit_test_review() must not wipe repo["files"] that the native
implementer (Explore/Coder, taken whenever there are no JSON patches --
i.e. any goal-only submission, including the legacy Agent Mode redirect and
Developer Workspace's own PLAN.md-only Approve & Build flow) already
recorded before this function runs. Previously it unconditionally set
repo["files"] = list(applied.get("files") or []) from _apply_patches's
(empty, since there are no JSON patches on this path) result, silently
discarding real evidence of what the agent actually wrote."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.coding_engine.lifecycle import approve_plan, start_mission


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8"
    )
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def test_native_implementer_files_survive_into_the_final_mission(ws):
    repo = _init_repo(ws / "backend")

    def fake_build(*, workspace, **_kwargs):
        Path(workspace, "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        return {"ok": True, "status": "completed", "files_written": ["calc.py"], "run_id": "fake"}

    m = start_mission(
        goal="Fix add() (goal-only, no JSON patches)",
        roots=[{"id": 1, "label": "backend", "path": str(repo)}],
        propose_if_empty=True,
        workspace_parent=str(ws / "wt"),
    )
    with (
        patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
        patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
            side_effect=fake_build,
        ),
    ):
        m = approve_plan(m["id"])

    assert m["phase"] == "awaiting_git_approval", m
    assert "calc.py" in m["repos"][0]["files"], "native-implementer files must not be wiped by the JSON-patch step"
    assert "calc.py" in m["files"]

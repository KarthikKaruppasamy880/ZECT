"""Mission PLAN approval must bind an immutable revision/hash, per the master
spec's Plan-mode requirement ("Approval stores immutable revision/hash").
Previously the coding-agent mission's own plan_approved field was a bare
boolean with no content binding -- a separate WorkItem-level plan_hash
system existed, but it was unconnected to lifecycle.py's mission approval."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from app.services.coding_engine.lifecycle import _lookup, approve_plan, start_mission


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
    monkeypatch.setenv("MENTRIX_PR_DRY_RUN", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def _start(ws, repo, plan_text):
    return start_mission(
        goal="Fix add()",
        plan=plan_text,
        roots=[{"id": 1, "label": "backend", "path": str(repo)}],
        patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
        workspace_parent=str(ws / "wt"),
    )


class TestPlanHashBinding:
    def test_plan_hash_computed_at_creation(self, ws):
        repo = _init_repo(ws / "backend")
        plan_text = "# PLAN\n\nDo the fix.\n"
        m = _start(ws, repo, plan_text)
        # start_mission() stores plan.strip() -- hash must match the stored text, not the raw input.
        assert m["plan_hash"] == hashlib.sha256(plan_text.strip().encode("utf-8")).hexdigest()
        assert m["plan_approved_hash"] == ""

    def test_approval_binds_the_exact_approved_revision(self, ws):
        repo = _init_repo(ws / "backend")
        plan_text = "# PLAN\n\nDo the fix.\n"
        m = _start(ws, repo, plan_text)
        expected_hash = hashlib.sha256(plan_text.strip().encode("utf-8")).hexdigest()
        m = approve_plan(m["id"])
        assert m["plan_approved_hash"] == expected_hash
        assert m["plan_hash"] == expected_hash
        approved_events = [e for e in m["events"] if e["event"] == "plan_approved"]
        assert approved_events and expected_hash[:12] in approved_events[-1]["message"]
        assert not [e for e in m["events"] if e["event"] == "plan_hash_drift"]

    def test_plan_mutated_after_creation_is_detected_and_rehashed_at_approval(self, ws):
        """Defense in depth: if anything ever mutates mission['plan'] between
        creation and approval, approval must bind the CONTENT actually being
        approved, and must not silently pretend the original hash still applies."""
        repo = _init_repo(ws / "backend")
        m = _start(ws, repo, "# PLAN\n\noriginal\n")
        internal = _lookup(m["id"])
        internal["plan"] = "# PLAN\n\nmutated before approval\n"
        m = approve_plan(m["id"])
        expected_hash = hashlib.sha256(internal["plan"].encode("utf-8")).hexdigest()
        assert m["plan_approved_hash"] == expected_hash
        assert m["plan_hash"] == expected_hash
        drift_events = [e for e in m["events"] if e["event"] == "plan_hash_drift"]
        assert drift_events, "must record that the approved content differed from what was originally hashed"

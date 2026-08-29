"""Phase D — orchestrator's upgrade-mode build stage used to hardcode
step_index=0, so a multi-phase plan (inventory, port module 1, port module 2,
tests, review, approve) only ever built its FIRST step no matter how many
steps the plan had. This verifies run_mentrix(mode="upgrade") now builds every
plan step, aggregates files_written across all of them, and that critical/high
Rules Engine violations on generated code get flagged as rejected files.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register all models incl. Rule, MentrixRun
from app.infrastructure.database import Base
from app.services.forge_loop import orchestrator

FAKE_PLAN = {
    "plan": "# Upgrade plan\n\n## Inventory\n## Port module 1\n## Port module 2\n## Tests",
    "phases": ["Inventory", "Port module 1", "Port module 2", "Tests"],
    "steps": [
        {"step": 1, "title": "Inventory", "action": "Inventory", "files": []},
        {"step": 2, "title": "Port module 1", "action": "Port module 1", "files": []},
        {"step": 3, "title": "Port module 2", "action": "Port module 2", "files": []},
        {"step": 4, "title": "Tests", "action": "Tests", "files": []},
    ],
    "model": "offline",
    "tokens_used": 0,
    "offline": True,
}


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _fake_ask(*a, **kw):
    return {"answer": "clarified", "model": "offline", "offline": True}


def _fake_ultra_review(*a, **kw):
    return {"score": 90, "critical_findings": 0, "summary": "ok"}


def _run_and_confirm(db, **kwargs):
    """Upgrade mode now stops at awaiting_plan_confirm after the plan stage
    (human-in-the-loop plan review) — resume past it the same way the real
    POST /runs/{id}/confirm-plan endpoint does."""
    run = orchestrator.run_mentrix(db, **kwargs)
    if run.status == "awaiting_plan_confirm":
        run = orchestrator.continue_mentrix_after_plan(db, run)
    return run


def _make_fake_builder(calls, *, clean=True):
    def fake_run_build_from_plan(full_plan, *, step_index=0, **kw):
        calls.append(step_index)
        code = "def handler():\n    return True\n" if clean else "password = 'hardcoded123'\n"
        return {
            "file_path": f"module_{step_index}.py",
            "generated_code": code,
            "language": "python",
            "model": "offline",
            "files_written": [f"module_{step_index}.py"],
            "files_expected": [f"module_{step_index}.py"],
            "finish_reason": "stop",
            "continuations": 0,
            "structure_ok": True,
        }

    return fake_run_build_from_plan


class TestBuildLoopCoversEveryPlanStep:
    def test_builds_all_steps_not_just_step_zero(self):
        db = _session()
        calls: list[int] = []
        fake_builder = _make_fake_builder(calls)

        with patch("app.services.forge_loop.orchestrator.run_ask", side_effect=_fake_ask), \
             patch("app.services.forge_loop.orchestrator.run_plan", return_value=FAKE_PLAN), \
             patch("app.services.forge_loop.orchestrator.run_ultra_review", side_effect=_fake_ultra_review), \
             patch("app.services.phases.build_phase_svc.run_build_from_plan", side_effect=fake_builder):
            _run_and_confirm(
                db, goal="Upgrade this repo to FastAPI", mode="upgrade", project_key="", workspace="", repo_id=None,
            )

        assert calls[:4] == [0, 1, 2, 3]

    def test_aggregates_files_written_across_all_steps(self):
        db = _session()
        calls: list[int] = []
        fake_builder = _make_fake_builder(calls)

        with patch("app.services.forge_loop.orchestrator.run_ask", side_effect=_fake_ask), \
             patch("app.services.forge_loop.orchestrator.run_plan", return_value=FAKE_PLAN), \
             patch("app.services.forge_loop.orchestrator.run_ultra_review", side_effect=_fake_ultra_review), \
             patch("app.services.phases.build_phase_svc.run_build_from_plan", side_effect=fake_builder):
            run = _run_and_confirm(
                db, goal="Upgrade this repo to FastAPI", mode="upgrade", project_key="", workspace="", repo_id=None,
            )

        import json

        events = json.loads(run.events_json)
        build_msgs = [e["message"] for e in events if e.get("agent") == "builder" and "wrote" in e.get("message", "")]
        assert build_msgs, "expected a 'Build wrote N file(s)' event"
        assert "4 file(s)" in build_msgs[-1]

    def test_critical_rule_violation_flags_rejected_file(self):
        db = _session()
        from app.models import Rule

        db.add(Rule(
            name="no-hardcoded-secrets",
            rule_type="security",
            condition="password",
            action="block",
            severity="critical",
            is_active=True,
        ))
        db.commit()

        calls: list[int] = []
        fake_builder = _make_fake_builder(calls, clean=False)

        with patch("app.services.forge_loop.orchestrator.run_ask", side_effect=_fake_ask), \
             patch("app.services.forge_loop.orchestrator.run_plan", return_value=FAKE_PLAN), \
             patch("app.services.forge_loop.orchestrator.run_ultra_review", side_effect=_fake_ultra_review), \
             patch("app.services.phases.build_phase_svc.run_build_from_plan", side_effect=fake_builder), \
             patch(
                 "app.services.build_intel.file_ops.check_rule_violations",
                 return_value=[{"rule_name": "no-hardcoded-secrets", "severity": "critical", "matched": True}],
             ):
            run = _run_and_confirm(
                db, goal="Upgrade this repo to FastAPI", mode="upgrade", project_key="", workspace="", repo_id=None,
            )

        import json

        events = json.loads(run.events_json)
        rule_events = [e for e in events if e.get("event") == "rule_violations"]
        assert rule_events, "expected a rule_violations event to be pushed"

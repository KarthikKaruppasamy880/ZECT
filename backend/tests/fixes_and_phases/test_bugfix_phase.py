"""Bugfix orchestrator mode — the closest prior mode ("review_only") was just
["reviewer", "fixer"], with no reproduce/trace/root-cause stages at all.
This covers the new run_root_cause_analysis() service and the orchestrator's
reproduce -> trace_impacted -> root_cause -> build chain."""

from __future__ import annotations

from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.services.forge_loop import orchestrator
from app.services.phases.bugfix_phase import run_root_cause_analysis

FAKE_ANALYSIS = (
    "## Root Cause\nThe login handler swallows the auth exception silently.\n\n"
    "## Affected Components\n- auth.py :: login\n\n"
    "## Fix Plan\n1. Re-raise the caught exception with context\n2. Add a regression test for the swallowed case"
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestRunRootCauseAnalysis:
    def test_parses_analysis_and_fix_steps(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            lambda client, **kw: {"content": FAKE_ANALYSIS, "tokens_used": 50, "prompt_tokens": 40, "completion_tokens": 10},
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = run_root_cause_analysis(
            goal="Login fails silently",
            reproduction={"attempted": True, "command": "pytest -q", "success": False, "output": "AssertionError"},
            trace={"nodes": [{"kind": "function", "name": "login", "path": "auth.py"}]},
            blueprint={"prompt": "structural summary"},
        )

        assert "swallows the auth exception" in result["analysis"]
        assert len(result["fix_steps"]) == 2
        assert "Re-raise" in result["fix_steps"][0]
        assert result["tokens_used"] == 50

    def test_falls_back_to_generic_step_when_no_fix_plan_parsed(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            lambda client, **kw: {"content": "## Root Cause\nUnclear.", "tokens_used": 10, "prompt_tokens": 8, "completion_tokens": 2},
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = run_root_cause_analysis(
            goal="Something is broken", reproduction={}, trace={}, blueprint={},
        )

        assert result["fix_steps"] == ["Fix the reported issue based on the root-cause analysis above"]

    def test_routes_to_anthropic_when_configured(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        captured = {}

        def fake_complete(client, **kw):
            captured["model"] = kw.get("model")
            captured["create_fn"] = kw.get("create_fn")
            return {"content": FAKE_ANALYSIS, "tokens_used": 20, "prompt_tokens": 15, "completion_tokens": 5}

        monkeypatch.setattr("app.services.quality.truncation.complete_with_continuations", fake_complete)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        run_root_cause_analysis(goal="bug", reproduction={}, trace={}, blueprint={})

        assert captured["model"] == "claude-sonnet-5"
        assert captured["create_fn"] is not None


class TestBugfixOrchestratorStages:
    def _fake_ask(self, *a, **kw):
        return {"answer": "n/a", "model": "offline", "offline": True}

    def _fake_ultra_review(self, *a, **kw):
        return {"score": 90, "critical_findings": 0, "summary": "ok"}

    def test_reproduce_runs_detected_test_command(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        db = _session()
        fake_run_result = {"success": False, "stdout": "", "stderr": "AssertionError: boom", "exit_code": 1}

        def fake_build(full_plan, *, step_index=0, **kw):
            return {
                "file_path": f"fix_{step_index}.py", "generated_code": "x = 1\n", "language": "python",
                "model": "offline", "files_written": [f"fix_{step_index}.py"], "files_expected": [f"fix_{step_index}.py"],
                "finish_reason": "stop", "continuations": 0, "structure_ok": True,
            }

        # _run_command backs both the "reproduce" stage directly and, via
        # run_and_fix, the later "sandbox"/regression-test stage — mock
        # run_and_fix separately so the two don't collide on the same
        # always-failing result.
        with patch("app.routers.autofix._run_command", return_value=fake_run_result) as mock_run, \
             patch("app.routers.autofix.run_and_fix", return_value=Mock(success=True, total_attempts=1, final_output="ok")), \
             patch("app.services.forge_loop.orchestrator.run_ask", side_effect=self._fake_ask), \
             patch("app.services.forge_loop.orchestrator.run_ultra_review", side_effect=self._fake_ultra_review), \
             patch(
                 "app.services.phases.bugfix_phase.run_root_cause_analysis",
                 return_value={
                     "analysis": "root cause", "fix_plan_text": "## Fix Plan\n1. Fix it",
                     "fix_steps": ["Fix it"], "model": "gpt-4o-mini", "tokens_used": 10,
                 },
             ), \
             patch("app.services.phases.build_phase_svc.run_build_from_plan", side_effect=fake_build):
            run = orchestrator.run_mentrix(
                db, goal="Fix the login bug", mode="bugfix", project_key="", workspace=str(tmp_path), repo_id=None,
            )

        mock_run.assert_called_once()
        assert mock_run.call_args.args[0] == "pytest -q"
        import json

        events = json.loads(run.events_json)
        repro_events = [e for e in events if "confirmed failing" in e.get("message", "")]
        assert repro_events

    def test_root_cause_populates_plan_for_build_stage(self, tmp_path):
        db = _session()
        calls = []

        def fake_build(full_plan, *, step_index=0, **kw):
            calls.append((full_plan, step_index))
            return {
                "file_path": f"fix_{step_index}.py", "generated_code": "x = 1\n", "language": "python",
                "model": "offline", "files_written": [f"fix_{step_index}.py"], "files_expected": [f"fix_{step_index}.py"],
                "finish_reason": "stop", "continuations": 0, "structure_ok": True,
            }

        with patch("app.services.forge_loop.orchestrator.run_ask", side_effect=self._fake_ask), \
             patch("app.services.forge_loop.orchestrator.run_ultra_review", side_effect=self._fake_ultra_review), \
             patch(
                 "app.services.phases.bugfix_phase.run_root_cause_analysis",
                 return_value={
                     "analysis": "root cause found",
                     "fix_plan_text": "## Fix Plan\n1. Patch the handler\n2. Add a test",
                     "fix_steps": ["Patch the handler", "Add a test"],
                     "model": "gpt-4o-mini",
                     "tokens_used": 30,
                 },
             ), \
             patch("app.services.phases.build_phase_svc.run_build_from_plan", side_effect=fake_build):
            orchestrator.run_mentrix(
                db, goal="Fix the login bug", mode="bugfix", project_key="", workspace=str(tmp_path), repo_id=None,
            )

        assert len(calls) == 2
        assert calls[0][1] == 0 and calls[1][1] == 1

    def test_bugfix_pipeline_registered(self):
        assert "bugfix" in orchestrator.MODE_PIPELINE
        pipeline = orchestrator.MODE_PIPELINE["bugfix"]
        for stage in ("reproduce", "trace_impacted", "root_cause", "build", "sandbox", "ultra_review", "integrator"):
            assert stage in pipeline
        assert pipeline.index("reproduce") < pipeline.index("root_cause") < pipeline.index("build")

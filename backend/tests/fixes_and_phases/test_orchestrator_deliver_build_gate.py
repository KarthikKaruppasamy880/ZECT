"""Two orchestrator gaps found while tracing why Build came back empty for a
plain chat/voice "build this" request:

1. mode="deliver" with no workspace/repo_id used to skip the real LLM builder
   entirely and fall to _run_builder() — a hardcoded stub that never calls an
   LLM and returns a "Builder guidance ready..." note with no generated_code.
   Both companion.py's start_delivery tool and assistant_phase.py's deliver
   kickoff never pass a workspace/repo_id, so a normal ad-hoc "build this" hit
   this stub every time. run_build_from_plan already gates writing to disk on
   workspace/repo_id being set — the orchestrator's own gate was redundant and
   wrong. This verifies deliver mode now always calls the real builder.

2. The integrator's Jira/Confluence "suggested_actions" were always
   fabricated placeholders, never executed — unlike Slack/email/Datadog,
   which do fire for real via the MCP hub when the goal text matches a
   keyword heuristic. This verifies Jira/Confluence now execute for real too.
"""

from __future__ import annotations

from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register all models incl. Rule, MentrixRun
from app.database import Base
from app.services.forge_loop import orchestrator

FAKE_PLAN = {
    "plan": "# Delivery plan\n\n## Implement",
    "phases": ["Implement"],
    "steps": [{"step": 1, "title": "Implement", "action": "Implement", "files": []}],
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
    run = orchestrator.run_mentrix(db, **kwargs)
    if run.status == "awaiting_plan_confirm":
        run = orchestrator.continue_mentrix_after_plan(db, run)
    return run


class TestDeliverModeAlwaysCallsRealBuilder:
    def test_deliver_with_no_workspace_still_calls_real_builder(self):
        db = _session()
        calls: list[int] = []

        def fake_run_build_from_plan(full_plan, *, step_index=0, **kw):
            calls.append(step_index)
            return {
                "file_path": "module.py",
                "generated_code": "def handler():\n    return True\n",
                "language": "python",
                "model": "offline",
                "files_written": [],  # write_to_repo is False with no workspace/repo_id
                "files_expected": ["module.py"],
                "finish_reason": "stop",
                "continuations": 0,
                "structure_ok": True,
            }

        with patch("app.services.forge_loop.orchestrator.run_ask", side_effect=_fake_ask), \
             patch("app.services.forge_loop.orchestrator.run_plan", return_value=FAKE_PLAN), \
             patch("app.services.forge_loop.orchestrator.run_ultra_review", side_effect=_fake_ultra_review), \
             patch("app.services.phases.build_phase_svc.run_build_from_plan", side_effect=fake_run_build_from_plan):
            run = _run_and_confirm(
                db, goal="build a small helper", mode="deliver", project_key="", workspace="", repo_id=None,
            )

        # Old behavior: calls stays empty because _run_builder() (the stub) ran
        # instead, and result["builder"] would have a "note" key with no
        # generated_code. New behavior: the real builder mock actually ran.
        # (deliver mode's plan comes from the internal _run_planner template,
        # not the mocked run_plan, hence >1 step — the step count isn't the
        # point here, that the real builder ran at all is.)
        assert calls
        import json

        result = json.loads(run.result_json)
        assert result["builder"].get("code_chars")

    def test_upgrade_mode_unaffected_still_calls_real_builder(self):
        """Guardrail: the gate simplification must not change upgrade/bugfix,
        which already always called the real builder."""
        db = _session()
        calls: list[int] = []

        def fake_run_build_from_plan(full_plan, *, step_index=0, **kw):
            calls.append(step_index)
            return {
                "file_path": "module.py",
                "generated_code": "def handler():\n    return True\n",
                "language": "python",
                "model": "offline",
                "files_written": ["module.py"],
                "files_expected": ["module.py"],
                "finish_reason": "stop",
                "continuations": 0,
                "structure_ok": True,
            }

        with patch("app.services.forge_loop.orchestrator.run_ask", side_effect=_fake_ask), \
             patch("app.services.forge_loop.orchestrator.run_plan", return_value=FAKE_PLAN), \
             patch("app.services.forge_loop.orchestrator.run_ultra_review", side_effect=_fake_ultra_review), \
             patch("app.services.phases.build_phase_svc.run_build_from_plan", side_effect=fake_run_build_from_plan):
            _run_and_confirm(
                db, goal="upgrade this repo", mode="upgrade", project_key="", workspace="", repo_id=None,
            )

        assert calls == [0]


class TestIntegratorExecutesJiraConfluence:
    def test_jira_keyword_executes_search_issues(self):
        db = _session()
        with patch("app.services.mcp.hub.execute_tool", return_value={"status": "ok", "result": {}}) as mock_exec:
            out = orchestrator._run_integrator(
                db, "file a jira ticket for this bug", [], {"lint_ok": True, "sandbox_ready": True, "review_ok": True},
            )

        assert mock_exec.call_args.kwargs["server_id"] == "jira"
        assert mock_exec.call_args.kwargs["tool_name"] == "search_issues"
        assert out["executed"]

    def test_confluence_keyword_executes_search(self):
        db = _session()
        with patch("app.services.mcp.hub.execute_tool", return_value={"status": "ok", "result": {}}) as mock_exec:
            out = orchestrator._run_integrator(
                db, "update the confluence page with this", [], {"lint_ok": True, "sandbox_ready": True, "review_ok": True},
            )

        assert mock_exec.call_args.kwargs["server_id"] == "confluence"
        assert mock_exec.call_args.kwargs["tool_name"] == "search"
        assert out["executed"]

    def test_goal_with_no_mcp_keywords_executes_nothing(self):
        db = _session()
        with patch("app.services.mcp.hub.execute_tool") as mock_exec:
            out = orchestrator._run_integrator(
                db, "just refactor this function", [], {"lint_ok": True, "sandbox_ready": True, "review_ok": True},
            )

        mock_exec.assert_not_called()
        assert out["executed"] == []
        # Suggested/preview actions still surface even when nothing executed.
        assert out["suggested_actions"]

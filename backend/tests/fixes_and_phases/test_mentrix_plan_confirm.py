"""Mentrix Delivery plan-confirm gate + context pack preflight."""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models import MentrixRun
from app.services.forge_loop import orchestrator as orch
from app.services.quality.gates_policy import gates_allow_approve, gates_allow_create_pr


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestContextPack:
    def test_missing_workspace_and_key(self):
        errs = orch.validate_context_pack(workspace="", project_key="", mode="bugfix")
        assert any("project_key" in e for e in errs)

    def test_chat_skips_pack(self):
        assert orch.validate_context_pack(workspace="", project_key="", mode="chat") == []

    def test_indexed_ok(self, monkeypatch):
        monkeypatch.setenv("LATTICE_ENABLED", "true")
        monkeypatch.setattr(
            "app.services.lattice.indexer.get_graph",
            lambda pk: Mock(files_indexed=1),
        )
        assert (
            orch.validate_context_pack(workspace="C:/ws", project_key="zoas", mode="upgrade") == []
        )

    def test_engage_rejects_missing_pack(self, monkeypatch):
        from app.routers.mentrix import StartRunRequest, start_run

        monkeypatch.setattr(orch, "validate_context_pack", lambda **kw: ["project_key required"])
        # re-import path uses validate from mentrix router
        import app.routers.mentrix as mr

        monkeypatch.setattr(mr, "validate_context_pack", lambda **kw: ["project_key required"])
        with pytest.raises(HTTPException) as exc:
            start_run(
                StartRunRequest(goal="fix bug", mode="bugfix"),
                db=_session(),
                user=Mock(email="a@b.c", user_id=1),
            )
        assert exc.value.status_code == 400


class TestPlanConfirmGate:
    def test_bugfix_pauses_for_plan(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_REQUIRE_PLAN_CONFIRM", "1")
        monkeypatch.setenv("LATTICE_ENABLED", "false")
        monkeypatch.setattr(orch, "_ensure_lattice_ingest", lambda *a, **k: None)
        monkeypatch.setattr(orch, "_run_scout", lambda *a, **k: {"graph_hits": [], "rag_hits": []})
        monkeypatch.setattr(
            orch,
            "run_blueprint",
            lambda *a, **k: {"prompt": "bp", "design_contract": {"acceptance_criteria": []}},
        )

        def fake_root_cause(**kw):
            return {
                "analysis": "## Root Cause\nbad null",
                "fix_steps": ["Add null check in foo.py", "Add test"],
                "fix_plan_text": "Add null check",
                "model": "test",
                "tokens_used": 1,
            }

        monkeypatch.setattr(
            "app.services.phases.bugfix_phase.run_root_cause_analysis",
            fake_root_cause,
        )
        # skip reproduce/trace heavy work via empty returns already

        db = _session()
        run = orch.run_mentrix(
            db,
            goal="Null crash in foo",
            mode="bugfix",
            project_key="zoas",
            workspace="C:/ws/zoas",
            created_by="t@t.com",
        )
        assert run.status == "awaiting_plan_confirm"
        result = json.loads(run.result_json or "{}")
        assert result.get("plan", {}).get("steps")
        gates = json.loads(run.gates_json or "{}")
        assert gates.get("plan_confirmed") is False

    def test_confirm_sets_plan_confirmed_and_resumes(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_REQUIRE_PLAN_CONFIRM", "1")
        monkeypatch.setenv("LATTICE_ENABLED", "false")
        monkeypatch.setattr(orch, "_ensure_lattice_ingest", lambda *a, **k: None)
        monkeypatch.setattr(orch, "_run_scout", lambda *a, **k: {"graph_hits": [], "rag_hits": []})
        monkeypatch.setattr(
            orch,
            "run_blueprint",
            lambda *a, **k: {"prompt": "bp", "design_contract": {"acceptance_criteria": []}},
        )
        monkeypatch.setattr(
            "app.services.phases.bugfix_phase.run_root_cause_analysis",
            lambda **kw: {
                "analysis": "cause",
                "fix_steps": ["fix it"],
                "fix_plan_text": "fix it",
                "model": "t",
                "tokens_used": 0,
            },
        )

        # After resume, stub build and remaining stages to finish quickly
        def fake_build(*a, **k):
            return {
                "file_path": "foo.py",
                "language": "python",
                "generated_code": "x=1\n",
                "files_written": ["foo.py"],
                "files_expected": ["foo.py"],
            }

        monkeypatch.setattr(
            "app.services.phases.build_phase_svc.run_build_from_plan",
            fake_build,
        )
        monkeypatch.setattr(orch, "_run_lint_gate", lambda *a, **k: {"ok": True})
        monkeypatch.setattr(
            orch,
            "_run_sandbox_check",
            lambda *a, **k: {"ready": True, "blockers": []},
        )
        monkeypatch.setattr(
            orch,
            "run_ultra_review",
            lambda *a, **k: {
                "passed": True,
                "score": 90,
                "critical_findings": 0,
                "findings": [],
                "summary": "ok",
            },
        )

        db = _session()
        run = orch.run_mentrix(
            db,
            goal="fix",
            mode="bugfix",
            project_key="zoas",
            workspace="C:/ws",
        )
        assert run.status == "awaiting_plan_confirm"

        # Stub remaining pipeline agents that might call real tools
        monkeypatch.setattr(
            orch,
            "_detect_test_command",
            lambda *a, **k: None,
        )

        continued = orch.continue_mentrix_after_plan(
            db, run, plan_patch={"summary": "edited plan"}, confirmed_by="ops@zect"
        )
        gates = json.loads(continued.gates_json or "{}")
        assert gates.get("plan_confirmed") is True
        assert continued.status != "awaiting_plan_confirm"

    def test_gates_block_unconfirmed_plan(self):
        ok, blockers = gates_allow_approve({"plan_confirmed": False, "lint_ok": True})
        assert not ok
        assert any("plan_confirmed" in b for b in blockers)

    def test_sast_blocks_create_pr(self):
        ok, blockers = gates_allow_create_pr(
            {
                "plan_confirmed": True,
                "lint_ok": True,
                "sandbox_ready": True,
                "review_ok": True,
                "incomplete_ok": True,
                "api_eval_ok": True,
                "grounding_ok": True,
                "contract_ok": True,
                "acceptance_ok": True,
                "sast_required": True,
                "sast_checked": True,
                "sast_ok": False,
            }
        )
        assert not ok
        assert any("sast" in b for b in blockers)

    def test_sast_not_checked_does_not_block(self):
        ok, blockers = gates_allow_create_pr(
            {
                "plan_confirmed": True,
                "lint_ok": True,
                "sandbox_ready": True,
                "review_ok": True,
                "incomplete_ok": True,
                "api_eval_ok": True,
                "grounding_ok": True,
                "contract_ok": True,
                "acceptance_ok": True,
                "sast_required": True,
                "sast_checked": False,
                "sast_ok": False,
            }
        )
        assert ok
        assert not any("sast" in b for b in blockers)


class TestSastChecksOk:
    def test_semgrep_success_match(self, monkeypatch):
        from app import github_service as gs

        monkeypatch.setattr(gs, "sast_required", lambda: True)
        monkeypatch.setattr(
            gs,
            "list_check_runs",
            lambda owner, repo, ref: [
                {
                    "id": 1,
                    "name": "Semgrep",
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://github.com/example/checks/1",
                    "app": "semgrep",
                }
            ],
        )
        out = gs.sast_checks_ok("acme", "zoas", "abc123")
        assert out["ok"] is True
        assert out["required"] is True
        assert len(out["matched"]) == 1
        assert "Semgrep" in out["note"] or out["ok"]


class TestDesktopDeleteNever:
    def test_delete_file_seed_is_never(self):
        from app.routers.permissions import DEFAULT_RULES
        from app.services.mentrix.org_policy import COMPANION_SEED_RULES

        delete = next(r for r in DEFAULT_RULES if r["action_pattern"] == "delete_file")
        assert delete["permission_level"] == "never"
        desk = next(
            r for r in DEFAULT_RULES if r["action_pattern"] == "companion_desktop_delete"
        )
        assert desk["permission_level"] == "never"
        org_desk = next(
            r for r in COMPANION_SEED_RULES if r["action_pattern"] == "companion_desktop_delete"
        )
        assert org_desk["permission_level"] == "never"

    def test_companion_refuses_delete_tool(self):
        from app.services.mentrix.companion import _exec_tool

        out = _exec_tool(Mock(), "desktop_delete", {"path": "C:/Users/x/Desktop/a.txt"})
        assert out["ok"] is False
        assert out["error"] == "delete_never_allowed"

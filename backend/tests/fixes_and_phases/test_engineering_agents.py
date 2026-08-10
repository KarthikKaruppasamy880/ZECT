"""Mentrix Engineering Agents — role boundaries, loops, budgets, evidence gates."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_01_planner_cannot_edit_production_code(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, planner_may_write_path

    assert planner_may_write_path("backend/app/main.py") is False
    assert planner_may_write_path("frontend/src/pages/Mentrix.tsx") is False
    p = MentrixPlanner(db)
    refused = p.refuse_production_edit("backend/app/services/foo.py")
    assert refused["ok"] is False
    assert refused["error"] == "planner_cannot_edit_production_code"


def test_02_planner_cannot_ready_to_ship(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, role_may_declare_ready_to_ship, ROLE_PLANNER

    assert role_may_declare_ready_to_ship(ROLE_PLANNER) is False
    out = MentrixPlanner(db).refuse_ready_to_ship()
    assert out["may_ready_to_ship"] is False


def test_03_coder_cannot_ready_to_ship(db: Session):
    from app.services.mentrix.engineering_agents import MentrixCodingAgentRole, role_may_declare_ready_to_ship, ROLE_CODER

    assert role_may_declare_ready_to_ship(ROLE_CODER) is False
    assert MentrixCodingAgentRole(db).refuse_ready_to_ship()["may_ready_to_ship"] is False


def test_04_coder_only_approved_manifest_ops(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, MentrixCodingAgentRole

    plan = MentrixPlanner(db).plan(goal="Approved ops only", approve=True)
    wi = plan["work_item_id"]
    coder = MentrixCodingAgentRole(db)
    bad = coder.execute_approved_ops(work_item_id=wi, dry_run=True, operation_ids=["OP-NOT-IN-MANIFEST"])
    assert bad["ok"] is False
    assert bad["error"] == "unapproved_operations"
    good = coder.execute_approved_ops(work_item_id=wi, dry_run=True, operation_ids=["OP-1"])
    assert good["ok"] is True
    assert "OP-1" in (good.get("operations_simulated") or [])
    assert good.get("operations_completed") == []


def test_05_test_failure_routes_back_to_coder(db: Session):
    from app.services.mentrix.engineering_agents import EngineeringLoopRunner

    out = EngineeringLoopRunner(db).run(
        loop_key="engineering_delivery",
        goal="Test fail routes",
        auto_approve_plan=True,
        dry_run=True,
        inject_test={"ok": False, "passed": 0, "failed": 1},
        autonomy="L2",
    )
    assert out.get("ready_to_ship") is not True
    assert out.get("status") == "NEEDS_HUMAN_DECISION" or out.get("ok") is False
    phases = [p["phase"] for p in out.get("phases") or []]
    assert "coding_agent" in phases
    assert "test_agent" in phases
    assert any(p.get("route_back") for p in out.get("phases") or [] if p.get("phase") == "test_agent")


def test_06_verified_blocking_review_routes_to_coder(db: Session):
    from app.services.mentrix.engineering_agents import EngineeringLoopRunner

    findings = [
        {
            "id": "f1",
            "severity": "high",
            "category": "security",
            "verification_status": "verified",
            "claim": "auth bypass",
        }
    ]
    out = EngineeringLoopRunner(db).run(
        loop_key="pr_review_fix",
        goal="Review routes",
        auto_approve_plan=True,
        dry_run=True,
        inject_test={"ok": True, "passed": 1, "failed": 0},
        inject_review=findings,
        autonomy="L2",
    )
    review_phases = [p for p in out.get("phases") or [] if p.get("phase") == "review_agent"]
    assert review_phases
    assert any(p.get("route_back") for p in review_phases)


def test_07_unverified_review_does_not_route_edits(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, MentrixReviewAgent

    plan = MentrixPlanner(db).plan(goal="Unverified review", approve=True)
    wi = plan["work_item_id"]
    rev = MentrixReviewAgent(db, wi).review(
        inject_findings=[
            {
                "id": "u1",
                "severity": "high",
                "category": "security",
                "verification_status": "unverified",
                "claim": "maybe bad",
            }
        ]
    )
    assert rev["route_back_to_coder"] is False
    assert rev["may_edit_from_unverified"] is False
    assert rev["clean"] is True


def test_08_incomplete_requirement_blocks_acceptance(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, AcceptanceVerifier
    from app.services.work_items.artifact_store import ArtifactStore

    plan = MentrixPlanner(db).plan(goal="Missing req", approve=True)
    wi = plan["work_item_id"]
    store = ArtifactStore(wi)
    man = store.read_json("EXECUTION_MANIFEST.json")
    man["requirement_ids"] = ["REQ-1", "REQ-MISSING"]
    store.write_json("EXECUTION_MANIFEST.json", man)
    store.write_json("TEST_RESULTS.json", {"ok": True})
    store.write_json("REVIEW.json", {"clean": True, "blocking": []})
    out = AcceptanceVerifier(db, wi).verify(ship=False)
    assert out["ok"] is False
    assert "REQ-MISSING" in (out.get("missing_requirements") or [])


def test_09_incomplete_acceptance_blocks(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, AcceptanceVerifier
    from app.services.work_items.artifact_store import ArtifactStore

    plan = MentrixPlanner(db).plan(goal="Missing AC", approve=True)
    wi = plan["work_item_id"]
    store = ArtifactStore(wi)
    man = store.read_json("EXECUTION_MANIFEST.json")
    man["acceptance_ids"] = ["AC-1", "AC-MISSING"]
    store.write_json("EXECUTION_MANIFEST.json", man)
    store.write_json("TEST_RESULTS.json", {"ok": True})
    store.write_json("REVIEW.json", {"clean": True, "blocking": []})
    out = AcceptanceVerifier(db, wi).verify(ship=False)
    assert out["ok"] is False
    assert "AC-MISSING" in (out.get("missing_acceptance") or [])


def test_10_hundred_ops_cannot_finish_at_99(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, AcceptanceVerifier
    from app.services.work_items.artifact_store import ArtifactStore

    plan = MentrixPlanner(db).plan(goal="100 ops", approve=True)
    wi = plan["work_item_id"]
    store = ArtifactStore(wi)
    ops = [{"id": f"OP-{i}", "mandatory": True, "status": "completed"} for i in range(1, 101)]
    ops[-1]["status"] = "pending"
    man = {
        "operations": ops,
        "mandatory_operation_ids": [o["id"] for o in ops],
        "requirement_ids": ["REQ-1"],
        "acceptance_ids": ["AC-1"],
    }
    store.write_json("EXECUTION_MANIFEST.json", man)
    evidence = [
        {
            "id": f"e-{i}",
            "type": "FILE_CHANGED",
            "operation_id": f"OP-{i}",
            "requirement_ids": ["REQ-1"],
            "acceptance_ids": ["AC-1"],
            "llm_claim": False,
        }
        for i in range(1, 100)
    ]
    store.write_json("TEST_RESULTS.json", {"ok": True})
    store.write_json("REVIEW.json", {"clean": True, "blocking": []})
    out = AcceptanceVerifier(db, wi).verify(evidence=evidence, ship=False)
    assert out["ok"] is False
    assert out["ready_to_ship"] is False
    assert "OP-100" in (out.get("missing_operations") or []) or "incomplete_manifest_operations" in (
        out.get("errors") or []
    )


def test_11_circuit_breaker_on_repeated_failures(db: Session):
    from app.services.mentrix.automation_loops.types import LoopBudget
    from app.services.mentrix.engineering_agents import EngineeringLoopRunner

    budget = LoopBudget(max_coder_test_cycles=10, max_same_failure=3, no_progress_threshold=99, max_actions=50)
    out = EngineeringLoopRunner(db).run(
        loop_key="bug_fix",
        goal="Breaker",
        auto_approve_plan=True,
        dry_run=True,
        inject_test={"ok": False, "passed": 0, "failed": 1},
        autonomy="L2",
        budget_override=budget,
    )
    assert out.get("circuit_breaker_tripped") is True or out.get("error") == "circuit_breaker_test_failure"
    assert out.get("status") == "NEEDS_HUMAN_DECISION"


def test_12_no_progress_escalates(db: Session):
    from app.services.mentrix.automation_loops.types import LoopBudget
    from app.services.mentrix.engineering_agents import EngineeringLoopRunner

    budget = LoopBudget(max_coder_test_cycles=10, max_same_failure=99, no_progress_threshold=2, max_actions=50)
    out = EngineeringLoopRunner(db).run(
        loop_key="ci_fix",
        goal="No progress",
        auto_approve_plan=True,
        dry_run=True,
        inject_test={"ok": False, "passed": 0, "failed": 1},
        autonomy="L2",
        budget_override=budget,
    )
    assert out.get("error") == "no_progress_threshold"
    assert out.get("needs_human") is True


def test_13_resume_from_checkpoint(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, EngineeringLoopRunner
    from app.services.work_items.checkpoints import record_checkpoint, load_execution_state
    from app.services.work_items.artifact_store import ArtifactStore

    plan = MentrixPlanner(db).plan(goal="Resume me", approve=True)
    wi = plan["work_item_id"]
    store = ArtifactStore(wi)
    record_checkpoint(store, checkpoint_type="completion", operation_id="OP-1", payload={"note": "mid"})
    state = load_execution_state(store)
    assert state.get("resume_operation") == "OP-1"
    out = EngineeringLoopRunner(db).run(
        loop_key="engineering_delivery",
        goal="Resume me",
        work_item_id=wi,
        resume=True,
        auto_approve_plan=True,
        dry_run=True,
        inject_test={"ok": True, "passed": 1, "failed": 0},
        autonomy="L2",
    )
    assert any(p.get("phase") == "resume" for p in out.get("phases") or [])
    assert out.get("work_item_id") == wi


def test_14_l3_obeys_permissions(db: Session):
    from app.services.mentrix.engineering_agents import EngineeringLoopRunner, evaluate_high_risk_action

    risk = evaluate_high_risk_action("secret_access", autonomy="L3")
    assert risk["denied"] is True
    assert risk["l3_bypasses_permissions"] is False
    out = EngineeringLoopRunner(db).run(
        loop_key="engineering_delivery",
        goal="Secret",
        autonomy="L3",
        force_high_risk="secret_access",
        auto_approve_plan=True,
    )
    assert out.get("ok") is False
    assert out.get("error") == "permission_or_policy_blocked"


def test_15_l3_obeys_data_classification(db: Session):
    from app.services.mentrix.engineering_agents import evaluate_high_risk_action

    risk = evaluate_high_risk_action(
        "external_message", autonomy="L3", data_classification="confidential"
    )
    assert risk["denied"] is True
    assert risk["allowed"] is False


def test_16_budgets_enforced(db: Session):
    from app.services.mentrix.automation_loops.types import LoopBudget
    from app.services.mentrix.engineering_agents import EngineeringLoopRunner

    budget = LoopBudget(max_tokens=10, max_cost_usd=0.01, max_actions=40)
    out = EngineeringLoopRunner(db).run(
        loop_key="engineering_delivery",
        goal="Budget",
        auto_approve_plan=True,
        dry_run=True,
        autonomy="L2",
        budget_override=budget,
        tokens_delta=99999,
    )
    assert out.get("error") == "budget_tokens_exhausted"
    out2 = EngineeringLoopRunner(db).run(
        loop_key="engineering_delivery",
        goal="Budget cost",
        auto_approve_plan=True,
        dry_run=True,
        autonomy="L2",
        budget_override=budget,
        cost_delta=9.0,
    )
    assert out2.get("error") == "budget_cost_exhausted"


def test_17_coding_agent_native_path(db: Session, monkeypatch):
    from app.adapters.coding_runtime import selected_coding_engine
    from app.services.mentrix.engineering_agents import MentrixPlanner, MentrixCodingAgentRole

    monkeypatch.setenv("ZECT_CODING_ENGINE", "mentrix_native")
    plan = MentrixPlanner(db).plan(goal="Native path", approve=True)
    out = MentrixCodingAgentRole(db).execute_approved_ops(work_item_id=plan["work_item_id"], dry_run=True)
    assert out.get("engine") == selected_coding_engine()
    assert out.get("engine") in ("mentrix_native", "native")
    assert "native_ok" in out


def test_18_full_flow_ready_to_ship_with_evidence(db: Session):
    from app.services.mentrix.engineering_agents import EngineeringLoopRunner
    from app.services.work_items.artifact_store import ArtifactStore

    # Dry-run cannot READY_TO_SHIP (simulated ops). Prove gate refuses fabrication.
    out = EngineeringLoopRunner(db).run(
        loop_key="engineering_delivery",
        goal="Ship with evidence",
        auto_approve_plan=True,
        dry_run=True,
        inject_test={"ok": True, "passed": 1, "failed": 0},
        inject_review=[],
        autonomy="L3",
        ship=True,
    )
    assert out.get("acceptance", {}).get("ready_to_ship") is not True
    phase_names = [p["phase"] for p in out.get("phases") or []]
    for required in ("planner", "coding_agent", "test_agent", "review_agent", "acceptance_verifier"):
        assert required in phase_names

    # Real completion path: mark ops completed + agent artifacts → READY_TO_SHIP
    from app.services.mentrix.engineering_agents import AcceptanceVerifier

    wi = out["work_item_id"]
    store = ArtifactStore(wi)
    man = store.read_json("EXECUTION_MANIFEST.json")
    for op in man.get("operations") or []:
        op["status"] = "completed"
    store.write_json("EXECUTION_MANIFEST.json", man)
    store.write_json("TEST_RESULTS.json", {"ok": True, "passed": 1, "failed": 0, "role": "test_agent"})
    store.write_json("REVIEW.json", {"clean": True, "blocking": [], "role": "review_agent"})
    acc = AcceptanceVerifier(db, wi).verify(ship=True, actor="test")
    assert acc.get("ready_to_ship") is True


def test_19_failed_tests_prevent_ready_to_ship(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, AcceptanceVerifier
    from app.services.work_items.artifact_store import ArtifactStore

    plan = MentrixPlanner(db).plan(goal="Fail tests", approve=True)
    wi = plan["work_item_id"]
    store = ArtifactStore(wi)
    store.write_json("TEST_RESULTS.json", {"ok": False, "failed": 2})
    store.write_json("REVIEW.json", {"clean": True, "blocking": []})
    out = AcceptanceVerifier(db, wi).verify(ship=False)
    assert out["ready_to_ship"] is False
    assert "tests_failed_block_ready_to_ship" in (out.get("errors") or [])


def test_20_blocking_review_prevents_ready_to_ship(db: Session):
    from app.services.mentrix.engineering_agents import MentrixPlanner, AcceptanceVerifier
    from app.services.work_items.artifact_store import ArtifactStore

    plan = MentrixPlanner(db).plan(goal="Block review", approve=True)
    wi = plan["work_item_id"]
    store = ArtifactStore(wi)
    store.write_json("TEST_RESULTS.json", {"ok": True})
    store.write_json(
        "REVIEW.json",
        {"clean": False, "blocking": [{"id": "b1", "severity": "high", "verification_status": "verified"}]},
    )
    out = AcceptanceVerifier(db, wi).verify(ship=False)
    assert out["ready_to_ship"] is False
    assert "blocking_review_findings" in (out.get("errors") or [])


def test_engineering_loops_registered():
    from app.services.mentrix.automation_loops.definitions import BUILTIN_LOOPS, is_engineering_loop

    for key in ("engineering_delivery", "bug_fix", "jira_delivery", "ci_fix", "pr_review_fix"):
        assert key in BUILTIN_LOOPS
        assert is_engineering_loop(key)
        assert BUILTIN_LOOPS[key]["default_autonomy"] in ("L0", "L1")


def test_engineering_delivery_via_automation_loop(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    r = client.post(
        "/api/mentrix/automation-loops/run",
        headers=auth_headers,
        json={"loop_key": "engineering_delivery", "autonomy": "L1", "prompt": "Implement small safe change"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("loop_key") == "engineering_delivery"
    eng = (body.get("result") or {}).get("engineering") or {}
    assert eng.get("work_item_id")
    assert eng.get("status") in (
        "AWAITING_PLAN_APPROVAL",
        "READY_FOR_HUMAN_SHIP_GATE",
        "ACCEPTED",
        "NEEDS_EVIDENCE",
        "READY_TO_SHIP",
    )

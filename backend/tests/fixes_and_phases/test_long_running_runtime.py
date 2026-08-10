"""Long-running Mentrix engineering runtime — lease, restart, 100+ ops, budgets."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import Base, SessionLocal, engine
from app.services.mentrix.automation_loops.types import LoopBudget
from app.services.mentrix.long_running_runtime import (
    STATUS_NEEDS_HUMAN,
    STATUS_PAUSED,
    STATUS_READY_TO_SHIP,
    STATUS_RUNNING,
    LongRunningAgentRuntime,
    build_synthetic_operations,
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _wi(db: Session, title: str = "LRR") -> int:
    from app.domains.work_items import service as wi_svc

    wi = wi_svc.create_work_item(db, title=title, repository_ref="main", base_commit_sha="base01")
    return int(wi.id)


def test_pause_resume(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db)
    started = rt.start(work_item_id=wi, operations=build_synthetic_operations(10), synthetic=True)
    run_id = started["run_id"]
    rt.tick(run_id, worker_id="w1", max_ops=3)
    paused = rt.pause(run_id)
    assert paused["status"] == STATUS_PAUSED
    # ticks while paused must fail
    blocked = rt.tick(run_id, worker_id="w1", max_ops=1)
    assert blocked.get("ok") is False
    resumed = rt.resume(run_id, verify_worktree=False)
    assert resumed["status"] == STATUS_RUNNING
    assert resumed["resume_operation"] == "OP-004"
    again = rt.tick(run_id, worker_id="w2", max_ops=2)
    assert again.get("ok") is True
    assert again["operations_completed"] == 5


def test_backend_restart_recovery(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "restart")
    started = rt.start(work_item_id=wi, operations=build_synthetic_operations(20))
    run_id = started["run_id"]
    rt.tick(run_id, worker_id="worker-a", max_ops=7)
    before = rt.serialize(rt.get(run_id))
    assert before["operations_completed"] == 7
    assert before["resume_operation"] == "OP-008"
    # Simulate backend death: worker gone, leases cleared
    recovered = rt.recover_after_restart()
    assert recovered["ok"] is True
    row = rt.get(run_id)
    assert row.worker_id == ""
    assert row.lease_expires_at is None
    assert row.current_operation_id == "OP-008"
    # New worker resumes without redoing completed ops
    after = rt.tick(run_id, worker_id="worker-b", max_ops=3)
    assert after["operations_completed"] == 10
    assert "OP-001" not in (after.get("processed") or [])
    assert after["processed"][0] == "OP-008"


def test_worker_lease_prevents_double_execution(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "lease")
    run_id = rt.start(work_item_id=wi, operations=build_synthetic_operations(5))["run_id"]
    c1 = rt.claim(run_id, worker_id="alpha", lease_seconds=60)
    assert c1["ok"] is True
    c2 = rt.claim(run_id, worker_id="beta", lease_seconds=60)
    assert c2["ok"] is False
    assert c2["error"] == "lease_held"
    # Expired lease can be reclaimed
    row = rt.get(run_id)
    row.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    c3 = rt.claim(run_id, worker_id="beta", lease_seconds=60)
    assert c3["ok"] is True
    assert c3["worker_id"] == "beta"


def test_stale_worktree_detected(db: Session, tmp_path: Path):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "wt")
    wt = tmp_path / "worktree"
    wt.mkdir()
    (wt / ".zect_lrr_base_sha").write_text("base01", encoding="utf-8")
    run_id = rt.start(
        work_item_id=wi,
        operations=build_synthetic_operations(3),
        worktree_path=str(wt),
        base_commit_sha="base01",
    )["run_id"]
    # External dirty marker
    (wt / ".zect_lrr_external_dirty").write_text("1", encoding="utf-8")
    out = rt.resume(run_id, verify_worktree=True)
    assert out.get("ok") is False
    assert out.get("error") == "worktree_externally_modified"
    assert out["status"] == STATUS_NEEDS_HUMAN


def test_hundred_plus_ops_ready_to_ship(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "100ops")
    ops = build_synthetic_operations(100)
    run_id = rt.start(
        work_item_id=wi,
        operations=ops,
        budget=LoopBudget(max_actions=250, max_runtime_seconds=3600),
    )["run_id"]
    # Partial progress
    rt.tick(run_id, worker_id="w", max_ops=40)
    mid = rt.serialize(rt.get(run_id))
    assert mid["operations_completed"] == 40
    assert mid["resume_operation"] == "OP-041"
    # Finish remaining
    done = rt.tick(run_id, worker_id="w", max_ops=60)
    assert done["status"] == STATUS_READY_TO_SHIP
    assert done["operations_completed"] == 100
    assert done.get("acceptance", {}).get("ready_to_ship") is True


def test_99_of_100_blocks_completion(db: Session):
    from app.services.mentrix.engineering_agents import AcceptanceVerifier
    from app.services.work_items.artifact_store import ArtifactStore

    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "99")
    run_id = rt.start(work_item_id=wi, operations=build_synthetic_operations(100))["run_id"]
    rt.tick(run_id, worker_id="w", max_ops=99)
    store = ArtifactStore(wi)
    man = store.read_json("EXECUTION_MANIFEST.json")
    pending = [o for o in man["operations"] if o["status"] != "completed"]
    assert len(pending) == 1
    store.write_json("TEST_RESULTS.json", {"ok": True})
    store.write_json("REVIEW.json", {"clean": True, "blocking": []})
    # LLM says done — EvidenceVerifier must reject
    out = AcceptanceVerifier(db, wi).verify(ship=False)
    assert out["ready_to_ship"] is False
    assert out["ok"] is False


def test_token_cost_runtime_budgets(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "budget")
    run_id = rt.start(
        work_item_id=wi,
        operations=build_synthetic_operations(5),
        budget=LoopBudget(max_tokens=10, max_cost_usd=0.01, max_runtime_seconds=5),
    )["run_id"]
    t = rt.tick(run_id, worker_id="w", max_ops=1, tokens_delta=999)
    assert t.get("error") == "budget_tokens_exhausted"
    run_id2 = rt.start(
        work_item_id=_wi(db, "budget2"),
        operations=build_synthetic_operations(5),
        budget=LoopBudget(max_tokens=1_000_000, max_cost_usd=0.01, max_runtime_seconds=5),
    )["run_id"]
    c = rt.tick(run_id2, worker_id="w", max_ops=1, cost_delta=9)
    assert c.get("error") == "budget_cost_exhausted"
    run_id3 = rt.start(
        work_item_id=_wi(db, "budget3"),
        operations=build_synthetic_operations(5),
        budget=LoopBudget(max_tokens=1_000_000, max_cost_usd=100, max_runtime_seconds=5),
    )["run_id"]
    r = rt.tick(run_id3, worker_id="w", max_ops=1, runtime_delta_seconds=99)
    assert r.get("error") == "budget_runtime_exhausted"


def test_model_switch_logged_and_policy(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "model")
    run_id = rt.start(work_item_id=wi, operations=build_synthetic_operations(4), model_profile="QUALITY")["run_id"]
    denied = rt.tick(run_id, worker_id="w", max_ops=1, switch_model="model-b", allow_model_switch=False)
    assert denied.get("error") == "model_switch_denied_by_policy"
    run_id2 = rt.start(work_item_id=_wi(db, "model2"), operations=build_synthetic_operations(4), model_profile="QUALITY")[
        "run_id"
    ]
    ok = rt.tick(run_id2, worker_id="w", max_ops=1, switch_model="model-b", allow_model_switch=True)
    assert ok.get("ok") is True
    switches = ok["state"].get("model_switches") or []
    assert switches and switches[0]["to"] == "model-b"
    assert any(t.get("operation_id") for t in ok.get("telemetry") or [])


def test_l3_permission_and_restricted_model(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "l3")
    run_id = rt.start(work_item_id=wi, operations=build_synthetic_operations(3), autonomy="L3")["run_id"]
    denied = rt.tick(run_id, worker_id="w", max_ops=1, force_high_risk="secret_access")
    assert denied.get("error") == "permission_or_policy_blocked"
    run_id2 = rt.start(
        work_item_id=_wi(db, "restricted"),
        operations=build_synthetic_operations(3),
        model_profile="RESTRICTED",
    )["run_id"]
    denied2 = rt.tick(run_id2, worker_id="w", max_ops=1, switch_model="gpt-4o", allow_model_switch=True)
    assert denied2.get("error") in ("restricted_cloud_fallback_denied", "model_switch_denied_by_policy")


def test_circuit_breaker_on_repeated_failure(db: Session):
    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "breaker")
    run_id = rt.start(
        work_item_id=wi,
        operations=build_synthetic_operations(5),
        budget=LoopBudget(max_same_failure=3, max_actions=20),
    )["run_id"]
    out = None
    for _ in range(3):
        out = rt.tick(run_id, worker_id="w", max_ops=1, inject_failure="compiler_error_X")
    assert out is not None
    assert out.get("circuit_breaker_tripped") is True
    assert out["status"] == STATUS_NEEDS_HUMAN


def test_idempotent_op_completion_on_resume(db: Session):
    from app.services.work_items.artifact_store import ArtifactStore

    rt = LongRunningAgentRuntime(db)
    wi = _wi(db, "idem")
    run_id = rt.start(work_item_id=wi, operations=build_synthetic_operations(5))["run_id"]
    rt.tick(run_id, worker_id="w", max_ops=2)
    store = ArtifactStore(wi)
    man = store.read_json("EXECUTION_MANIFEST.json")
    # Force current pointer back but leave ops completed — tick must not duplicate
    completed_before = [o["id"] for o in man["operations"] if o["status"] == "completed"]
    assert completed_before == ["OP-001", "OP-002"]
    rt.recover_after_restart()
    rt.tick(run_id, worker_id="w2", max_ops=1)
    man2 = store.read_json("EXECUTION_MANIFEST.json")
    completed = [o["id"] for o in man2["operations"] if o["status"] == "completed"]
    assert completed == ["OP-001", "OP-002", "OP-003"]


def test_pr_ci_cannot_bypass_evidence(db: Session):
    """READY_TO_SHIP only via AcceptanceVerifier+EvidenceVerifier allow_gate."""
    from app.domains.work_items.status import GATE_STATUSES, STATUS_READY_TO_SHIP
    from app.services.mentrix.engineering_agents.roles import ROLE_CODER, role_may_declare_ready_to_ship

    assert STATUS_READY_TO_SHIP in GATE_STATUSES
    assert role_may_declare_ready_to_ship(ROLE_CODER) is False

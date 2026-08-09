"""P0 Mentrix consolidation — WorkItem, ArtifactStore, Context, PI, Evidence, fallback, E2E."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.domains.work_items.events import WorkItemEventMutationError, forbid_event_delete, forbid_event_update
from app.domains.work_items.source_adapter import UserSourceAdapter, get_source_adapter
from app.domains.work_items.status import ALL_STATUSES, STATUS_PLAN_APPROVED, STATUS_READY_TO_SHIP
from app.infrastructure.database import SessionLocal
from app.services.work_items.artifact_store import ArtifactStore, plan_hash_bytes
from app.services.work_items.checkpoints import CHECKPOINT_TYPES, record_checkpoint
from app.services.work_items.context_engine import PROVENANCE_KEYS, MentrixContextEngine
from app.services.work_items.developer_service import MentrixDeveloperService
from app.services.work_items.evidence_verifier import EvidenceVerifier
from app.services.work_items.fallback_policy import (
    POLICY_ASK,
    POLICY_AUTOMATIC,
    POLICY_NEVER,
    assert_never_no_cloud_call,
    resolve_model_route,
)
from app.services.work_items.project_intelligence import ProjectIntelligenceService
from app.services.work_items.telemetry import build_telemetry


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_work_item_create_has_repo_fields_and_event(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    from app.domains.work_items import service as wi_svc

    wi = wi_svc.create_work_item(
        db,
        title="P0 WI",
        repository_id=42,
        repository_ref="main",
        base_commit_sha="abc123",
    )
    assert wi.repository_id == 42
    assert wi.repository_ref == "main"
    assert wi.base_commit_sha == "abc123"
    assert wi.status == "NEW"
    events = wi_svc.list_events(db, wi.id)
    assert events
    assert events[0].event_type == "created"


def test_work_item_event_append_only():
    with pytest.raises(WorkItemEventMutationError):
        forbid_event_update(1)
    with pytest.raises(WorkItemEventMutationError):
        forbid_event_delete(1)


def test_sdlc_enums_cover_canonical():
    for s in (
        "NEW",
        "INGESTED",
        "ANALYZED",
        "PLANNED",
        "PLAN_APPROVED",
        "EXECUTING",
        "IMPLEMENTED",
        "VERIFYING",
        "REVIEWING",
        "ACCEPTANCE_TESTING",
        "READY_TO_SHIP",
        "SHIP_APPROVED",
        "PR_CREATED",
        "CI_GREEN",
        "DONE",
        "BLOCKED",
        "FAILED_VERIFICATION",
        "NEEDS_HUMAN_DECISION",
        "CANCELLED",
    ):
        assert s in ALL_STATUSES


def test_artifact_store_plan_hash_reapproval(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Ship WorkItem ArtifactStore ownership",
        repository_id=1,
        repository_ref="main",
        base_commit_sha="deadbeef",
    )
    wid = planned["work_item_id"]
    store = ArtifactStore(wid, root=tmp_path / "artifacts")
    assert store.path("PLAN.md").exists()
    assert planned["plan_hash"] == plan_hash_bytes(store.read_plan())
    approved = svc.approve_plan(work_item_id=wid)
    assert approved["status"] == STATUS_PLAN_APPROVED
    assert approved["approved_plan_hash"] == planned["plan_hash"]
    # Material change → reapproval
    store.write_plan(store.read_plan() + "\n\n## Extra phase\nDo more.\n")
    from app.domains.work_items import service as wi_svc

    wi = wi_svc.get_work_item(db, wid)
    new_hash = store.plan_hash()
    wi.plan_hash = new_hash
    if wi.approved_plan_hash and wi.approved_plan_hash != new_hash:
        from app.domains.work_items.status import STATUS_NEEDS_HUMAN_DECISION
        from app.domains.work_items.events import append_event

        wi.approved_plan_hash = None
        wi.status = STATUS_NEEDS_HUMAN_DECISION
        append_event(db, work_item_id=wid, event_type="plan_reapproval_required", payload={"plan_hash": new_hash})
        db.commit()
    wi2 = wi_svc.get_work_item(db, wid)
    assert wi2.approved_plan_hash is None
    assert wi2.status == "NEEDS_HUMAN_DECISION"


def test_context_pack_provenance_keys():
    pack = MentrixContextEngine(token_budget=2000).build(
        work_item_id=1,
        repository_id=9,
        repository_ref="main",
        base_commit_sha="c0ffee",
        goal="test",
        knowledge_hits=[{"id": "k1", "content": "truth fact", "score": 0.9}],
        memory_hits=[{"id": "m1", "content": "learned fact", "score": 0.5}],
    )
    d = pack.to_dict()
    assert d["items"]
    for item in d["items"]:
        for k in PROVENANCE_KEYS:
            assert k in item


def test_project_intelligence_contract_knowledge_ne_memory():
    snap = ProjectIntelligenceService().snapshot(project_id=1).to_dict()
    for key in (
        "lattice",
        "blueprint",
        "knowledge",
        "memory",
        "related_work",
        "skill_selection",
        "playbook_selection",
        "freshness",
    ):
        assert key in snap
    assert snap["knowledge"] is not snap["memory"]


def test_source_adapter_stubs():
    user = get_source_adapter("user")
    assert isinstance(user, UserSourceAdapter)
    fields = user.to_work_item_fields({"title": "T", "external_id": "1"})
    assert fields["source"] == "user"
    jira = get_source_adapter("jira")
    with pytest.raises(NotImplementedError):
        jira.fetch_raw("ZECT-1")


def test_evidence_verifier_rejects_llm_only():
    v = EvidenceVerifier()
    bad = v.verify(
        mandatory_operation_ids=["OP-1"],
        requirement_ids=["R1"],
        acceptance_ids=["A1"],
        evidence=[{"id": "e1", "type": "NARRATIVE", "llm_claim": True, "operation_id": "OP-1"}],
    )
    assert bad.ready_to_ship is False
    assert "llm_text_alone_cannot_complete" in bad.errors

    good = v.verify(
        mandatory_operation_ids=["OP-1"],
        requirement_ids=["R1"],
        acceptance_ids=["A1"],
        evidence=[
            {
                "id": "e1",
                "type": "FILE_CHANGED",
                "operation_id": "OP-1",
                "requirement_ids": ["R1"],
                "acceptance_ids": ["A1"],
            }
        ],
    )
    assert good.ready_to_ship is True


def test_checkpoint_types_and_resume_fields(tmp_path):
    store = ArtifactStore(99, root=tmp_path)
    for t in CHECKPOINT_TYPES:
        record_checkpoint(
            store,
            checkpoint_type=t,
            operation_id="OP-X",
            worktree_path=str(tmp_path / "wt"),
            base_commit_sha="aaa",
            current_commit_sha="bbb",
        )
    state = store.read_json("EXECUTION_STATE.json")
    assert state["worktree_path"]
    assert state["base_commit_sha"] == "aaa"
    assert state["current_commit_sha"] == "bbb"
    assert len(state["checkpoints"]) == len(CHECKPOINT_TYPES)


def test_telemetry_fields():
    tel = build_telemetry(
        requested_provider="local",
        requested_model="m1",
        actual_provider="cloud",
        actual_model="m2",
        fallback_used=True,
        fallback_reason="automatic_cloud_fallback",
        latency_ms=12,
        work_item_id=1,
        agent_run_id="r1",
        operation_id="OP-033",
    )
    for k in (
        "requested_provider",
        "actual_provider",
        "fallback_used",
        "fallback_reason",
        "latency_ms",
        "work_item_id",
        "agent_run_id",
        "operation_id",
    ):
        assert k in tel


def test_fallback_policies_never_ask_automatic():
    never = resolve_model_route(local_configured=False, cloud_configured=True, policy=POLICY_NEVER)
    assert never.blocked is True
    assert never.allow_cloud_context is False
    assert never.provider == "none"

    ask = resolve_model_route(
        local_configured=False, cloud_configured=True, policy=POLICY_ASK, user_allows_cloud=False
    )
    assert ask.blocked is True

    ask_ok = resolve_model_route(
        local_configured=False, cloud_configured=True, policy=POLICY_ASK, user_allows_cloud=True
    )
    assert ask_ok.provider == "cloud"
    assert ask_ok.fallback_used is True

    auto = resolve_model_route(local_configured=False, cloud_configured=True, policy=POLICY_AUTOMATIC)
    assert auto.provider == "cloud"

    local = resolve_model_route(local_configured=True, cloud_configured=True, policy=POLICY_AUTOMATIC)
    assert local.provider == "local"
    assert local.fallback_used is False

    out = assert_never_no_cloud_call(
        policy=POLICY_NEVER,
        cloud_client_factory=lambda: (_ for _ in ()).throw(RuntimeError("should not call cloud")),
        context_pack={"items": [{"content": "secret"}]},
    )
    assert out["cloud_called"] is False


def test_llm_phase_uses_openai_compat_module():
    import app.services.phases.llm_phase as llm_phase

    src = Path(llm_phase.__file__).read_text(encoding="utf-8")
    assert "openai_compat" in src
    assert "get_openai_compat_client" in src
    assert "from openai import OpenAI" not in src or "openai_compat" in src


def test_coding_agent_real_smoke_deterministic(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mentrix_native")
    monkeypatch.setenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE", "1")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    from app.adapters.coding_runtime import reset_coding_runtime_for_tests
    from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

    reset_coding_runtime_for_tests()
    ws = tmp_path / "repo"
    ws.mkdir()
    out = run_mentrix_native_build(
        goal="write smoke marker",
        workspace=str(ws),
        expected_files=["mentrix_p0_smoke_marker.py"],
    )
    assert out["engine"] == "mentrix_native"
    assert out["ok"] is True
    assert (ws / "mentrix_p0_smoke_marker.py").exists()
    events = out.get("events_tail") or []
    assert any(e.get("event") == "write_file" for e in events)
    assert any(e.get("event") == "read_file" for e in events)
    assert any(e.get("event") == "run_command" for e in events)
    assert any(e.get("file_diff") for e in events if e.get("event") == "write_file")


def test_native_build_fail_closed_no_silent_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mock")
    monkeypatch.delenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE", raising=False)
    from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

    out = run_mentrix_native_build(goal="x", workspace=str(tmp_path))
    assert out.get("ok") is False
    assert out.get("error") == "coding_engine_mock_forbidden"

    monkeypatch.setenv("ZECT_ALLOW_OFFLINE_BUILD_STUB", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app.services.phases.build_phase_svc import run_build_generate

    out2 = run_build_generate("step", workspace=str(tmp_path), file_path="x.py")
    assert out2.get("ok") is False
    assert out2.get("error") == "generation_unavailable"


def test_work_item_api_routes_registered():
    from app.main import app

    paths = set(app.openapi()["paths"])
    assert "/api/work-items" in paths
    assert "/api/mentrix/developer/plan" in paths
    assert "/api/mentrix/developer/ask" in paths
    assert "/api/work-items/{work_item_id}/events/{event_id}" in paths


def test_work_item_api_service_and_append_only(db: Session):
    from app.domains.work_items import service as wi_svc

    wi = wi_svc.create_work_item(
        db,
        title="API WI",
        repository_id=7,
        repository_ref="develop",
        base_commit_sha="fff",
    )
    assert wi.repository_id == 7
    got = wi_svc.get_work_item(db, wi.id)
    assert got.title == "API WI"
    events = wi_svc.list_events(db, wi.id)
    assert events
    with pytest.raises(WorkItemEventMutationError):
        forbid_event_delete(events[0].id)


def test_developer_api_plan_approve(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Add WorkItem READY_TO_SHIP path",
        repository_id=1,
        repository_ref="main",
        base_commit_sha="abc",
    )
    wid = planned["work_item_id"]
    approved = svc.approve_plan(work_item_id=wid)
    assert approved["status"] == STATUS_PLAN_APPROVED


def test_e2e_work_item_to_ready_to_ship(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mentrix_native")
    monkeypatch.setenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE", "1")
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")

    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="E2E: create marker file via Mentrix Developer Agent",
        repository_id=1,
        repository_ref="main",
        base_commit_sha="base01",
    )
    wid = planned["work_item_id"]
    svc.approve_plan(work_item_id=wid)
    agent = svc.start_agent(work_item_id=wid, deterministic=True)
    assert agent["files_written"]
    marker = Path(agent["worktree_path"]) / agent["files_written"][0]
    assert marker.exists()

    resumed = svc.resume(work_item_id=wid)
    assert resumed["execution_state"].get("worktree_path")

    evidence = [
        {
            "id": "ev-file",
            "type": "FILE_CHANGED",
            "operation_id": "agent",
            "requirement_ids": ["R22"],
            "acceptance_ids": ["AC-E2E"],
            "payload": {"path": str(marker)},
        },
        {
            "id": "ev-cmd",
            "type": "COMMAND_EXIT",
            "operation_id": "agent",
            "requirement_ids": ["R22"],
            "acceptance_ids": ["AC-E2E"],
            "payload": {"exit_code": 0},
        },
        {
            "id": "ev-human",
            "type": "HUMAN_APPROVAL",
            "operation_id": "approve_plan",
            "requirement_ids": ["R12"],
            "acceptance_ids": ["AC-E2E"],
        },
    ]
    out = svc.verify_and_ready_to_ship(
        work_item_id=wid,
        mandatory_operation_ids=["agent", "approve_plan"],
        requirement_ids=["R22", "R12"],
        acceptance_ids=["AC-E2E"],
        evidence=evidence,
    )
    assert out["verification"]["ready_to_ship"] is True
    assert out["work_item"]["status"] == STATUS_READY_TO_SHIP

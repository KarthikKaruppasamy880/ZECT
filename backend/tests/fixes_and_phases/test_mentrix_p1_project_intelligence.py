"""P1 Mentrix Project Intelligence + SDLC connectivity."""

from __future__ import annotations

import json
import os

import pytest
from sqlalchemy.orm import Session

from app.domains.work_items.ingest import ingest_work_item
from app.domains.work_items.source_adapter import CamundaSourceAdapter, JiraSourceAdapter, get_source_adapter
from app.domains.work_items.status import (
    STATUS_INGESTED,
    STATUS_NEEDS_HUMAN_DECISION,
    STATUS_PLAN_APPROVED,
    STATUS_READY_TO_SHIP,
)
from app.infrastructure.database import SessionLocal
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.close_loop import close_external_loop
from app.services.work_items.developer_service import MentrixDeveloperService
from app.services.work_items.ownership import (
    assert_artifact_store_owns_plan,
    assert_forgeloop_mentrix_native_path,
)
from app.services.work_items.project_intelligence import ProjectIntelligenceService
from app.services.work_items.ultra_review_context import build_ultrareview_work_item_context


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_ti001_pytest_flag_preserves_auth_env():
    """TI-001: under ZECT_PYTEST, dotenv must not permanently own auth keys."""
    assert os.environ.get("ZECT_PYTEST") == "1"
    assert os.environ.get("ZECT_USERNAME") == "test@zect.local"
    assert os.environ.get("ZECT_PASSWORD") == "test-pass-1234"


def test_jira_and_camunda_adapters_registered():
    assert get_source_adapter("jira").source_name == "jira"
    assert get_source_adapter("camunda").source_name == "camunda"
    assert isinstance(JiraSourceAdapter(), JiraSourceAdapter)
    assert isinstance(CamundaSourceAdapter(), CamundaSourceAdapter)


def test_jira_ingest_fixture_binds_repo(db: Session, monkeypatch, tmp_path):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    raw = {
        "key": "ZECT-P1-1",
        "fields": {"summary": "P1 Jira ingest", "description": "desc", "labels": []},
        "project_id": 7,
        "repository_id": 99,
        "repository_ref": "main",
        "base_commit_sha": "abc1234",
    }
    monkeypatch.setenv("ZECT_JIRA_INGEST_FIXTURE_JSON", json.dumps(raw))
    out = ingest_work_item(db, source="jira", external_id="ZECT-P1-1", require_repo=True)
    wi = out["work_item"]
    assert wi["source"] == "jira"
    assert wi["external_id"] == "ZECT-P1-1"
    assert wi["repository_id"] == 99
    assert wi["status"] == STATUS_INGESTED
    assert out["needs_human"] is False


def test_ingest_missing_repo_needs_human(db: Session, monkeypatch, tmp_path):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    raw = {
        "key": "ZECT-P1-2",
        "fields": {"summary": "No repo", "description": ""},
    }
    out = ingest_work_item(
        db,
        source="jira",
        external_id="ZECT-P1-2",
        raw=raw,
        require_repo=True,
    )
    assert out["needs_human"] is True
    assert out["work_item"]["status"] == STATUS_NEEDS_HUMAN_DECISION


def test_camunda_ingest_fixture(db: Session, monkeypatch, tmp_path):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    raw = {
        "id": "task-77",
        "name": "Camunda review task",
        "description": "do it",
        "project_id": 1,
        "repository_id": 2,
        "repository_ref": "develop",
        "base_commit_sha": "deadbeef",
    }
    monkeypatch.setenv("ZECT_CAMUNDA_INGEST_FIXTURE_JSON", json.dumps(raw))
    out = ingest_work_item(db, source="camunda", external_id="task-77", require_repo=True)
    assert out["work_item"]["source"] == "camunda"
    assert out["work_item"]["external_id"] == "task-77"
    assert out["work_item"]["status"] == STATUS_INGESTED


def test_project_intelligence_knowledge_memory_distinct(db: Session):
    snap = ProjectIntelligenceService().snapshot(db=db, query="test", project_key="demo")
    d = snap.to_dict()
    assert "knowledge" in d and "memory" in d
    assert "skill_selection" in d and "playbook_selection" in d
    assert "freshness" in d and "related_work" in d
    assert d["knowledge"] is not d["memory"]


def test_developer_ask_uses_live_pi(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    svc = MentrixDeveloperService(db)
    out = svc.ask(
        question="What is the WorkItem spine?",
        repository_id=1,
        repository_ref="main",
        base_commit_sha="cafebabe",
    )
    assert "project_intelligence" in out or "context_pack" in out or "answer" in out
    pi = out.get("project_intelligence") or out.get("pi") or {}
    if pi:
        assert "knowledge" in pi and "memory" in pi
    pack = out.get("context_pack") or out.get("pack") or {}
    if pack:
        assert isinstance(pack, dict)


def test_fabric_handoff_requires_approved_plan(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    from app.services.work_items.fabric_handoff import fabric_handoff_from_work_item

    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="P1 fabric handoff",
        repository_id=1,
        repository_ref="main",
        base_commit_sha="abcdef0",
    )
    wid = planned["work_item_id"]
    refused = fabric_handoff_from_work_item(db, work_item_id=wid, workspace=str(tmp_path))
    assert refused["ok"] is False

    approved = svc.approve_plan(work_item_id=wid)
    assert approved["status"] == STATUS_PLAN_APPROVED
    result = fabric_handoff_from_work_item(db, work_item_id=wid, workspace=str(tmp_path))
    assert "ok" in result
    assert result.get("error") != "plan_not_approved"


def test_forgeloop_ownership_mentrix_native_and_artifact_store(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    fl = assert_forgeloop_mentrix_native_path()
    assert fl["ok"] is True
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Ownership PLAN.md",
        repository_id=1,
        repository_ref="main",
        base_commit_sha="11223344",
    )
    own = assert_artifact_store_owns_plan(planned["work_item_id"], root=tmp_path / "artifacts")
    assert own["owner"] == "ArtifactStore"
    assert own["exists"] is True


def test_ultrareview_consumes_work_item_context(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Ultra review context",
        repository_id=3,
        repository_ref="main",
        base_commit_sha="99887766",
    )
    ctx = build_ultrareview_work_item_context(db, work_item_id=planned["work_item_id"])
    assert ctx["engine"] == "review_service"
    assert "context_pack" in ctx
    assert "project_intelligence" in ctx
    assert ctx["work_item"]["id"] == planned["work_item_id"]


def test_evidence_ready_to_ship_triggers_close_loop_dry_run(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    raw = {
        "key": "ZECT-P1-CLOSE",
        "fields": {"summary": "Close loop", "description": ""},
        "repository_id": 1,
        "repository_ref": "main",
        "base_commit_sha": "aabbccdd",
    }
    ingested = ingest_work_item(db, source="jira", external_id="ZECT-P1-CLOSE", raw=raw)
    wid = ingested["work_item"]["id"]
    svc = MentrixDeveloperService(db)
    out = svc.verify_and_ready_to_ship(
        work_item_id=wid,
        mandatory_operation_ids=[],
        requirement_ids=[],
        acceptance_ids=[],
        evidence=[{"type": "TEST_RESULT", "id": "e1", "summary": "ok"}],
        actor="test",
    )
    assert out["work_item"]["status"] == STATUS_READY_TO_SHIP
    assert "close_loop" in out
    assert out["close_loop"]["ok"] is True
    assert out["close_loop"]["dry_run"] is True

    closed = close_external_loop(db, work_item_id=wid, pr_url="https://example.com/pr/1", dry_run=True)
    assert closed["ok"] is True
    types = [a["type"] for a in closed["actions"]]
    assert "pr_url" in types
    assert "jira_comment" in types


def test_connectivity_spine_smoke(db: Session, tmp_path, monkeypatch):
    """OP-050: Jira → PI → Plan → UltraReview context → Evidence → close_loop."""
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    raw = {
        "key": "ZECT-P1-SPINE",
        "fields": {"summary": "Spine smoke", "description": "end to end"},
        "repository_id": 5,
        "repository_ref": "develop",
        "base_commit_sha": "f00dcafe",
        "project_id": None,
    }
    ing = ingest_work_item(db, source="jira", external_id="ZECT-P1-SPINE", raw=raw)
    wid = ing["work_item"]["id"]
    pi = ProjectIntelligenceService().snapshot(db=db, query="spine", repository_id=5)
    assert "knowledge" in pi.to_dict()
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Spine plan",
        work_item_id=wid,
        repository_id=5,
        repository_ref="develop",
        base_commit_sha="f00dcafe",
    )
    assert planned["work_item_id"] == wid
    store = ArtifactStore(wid, root=tmp_path / "artifacts")
    assert store.path("PLAN.md").exists()
    svc.approve_plan(work_item_id=wid)
    ctx = build_ultrareview_work_item_context(db, work_item_id=wid)
    assert ctx["context_pack"]
    verified = svc.verify_and_ready_to_ship(
        work_item_id=wid,
        mandatory_operation_ids=[],
        requirement_ids=[],
        acceptance_ids=[],
        evidence=[{"type": "TEST_RESULT", "id": "spine", "summary": "pass"}],
    )
    assert verified["work_item"]["status"] == STATUS_READY_TO_SHIP

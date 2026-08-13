"""Multi-repo Developer ASK/PLAN aggregation (R3)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.mentrix.engineering_agents.acceptance_verifier import AcceptanceVerifier
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.developer_service import MentrixDeveloperService
from app.services.work_items.multi_repo_context import (
    build_affected_repos_manifest,
    resolve_authorized_repository_ids,
)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_project_with_repos(db: Session) -> tuple[Project, Repo, Repo]:
    p = Project(name="multi-r3", description="test", status="active")
    db.add(p)
    db.flush()
    r1 = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main")
    r2 = Repo(project_id=p.id, owner="acme", repo_name="beta", default_branch="main")
    db.add_all([r1, r2])
    db.commit()
    db.refresh(p)
    db.refresh(r1)
    db.refresh(r2)
    return p, r1, r2


def test_resolve_authorized_filters_foreign_repo(db: Session):
    p, r1, r2 = _seed_project_with_repos(db)
    other = Repo(project_id=p.id, owner="acme", repo_name="gamma", default_branch="main")
    db.add(other)
    db.commit()
    foreign = Repo(project_id=99999, owner="x", repo_name="foreign", default_branch="main")
    db.add(foreign)
    db.commit()
    ids = resolve_authorized_repository_ids(
        db,
        project_id=p.id,
        repository_ids=[r1.id, r2.id, foreign.id],
        repository_id=None,
    )
    assert r1.id in ids and r2.id in ids
    assert foreign.id not in ids


def test_ask_multi_repo_context_by_repository(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r1, r2 = _seed_project_with_repos(db)
    svc = MentrixDeveloperService(db)
    out = svc.ask(
        question="Cross-repo impact?",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    assert out.get("context_by_repository")
    assert len(out["context_by_repository"]) == 2
    assert len(out.get("affected_repos") or []) == 2
    assert "context_pack" in out


def test_plan_writes_execution_manifest_with_affected_repos(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r1, r2 = _seed_project_with_repos(db)
    svc = MentrixDeveloperService(db)
    out = svc.plan(
        goal="Ship cross-repo feature",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    assert "Affected repositories" in (out.get("plan") or "")
    assert len(out.get("affected_repos") or []) == 2
    manifest = out.get("execution_manifest") or {}
    assert len(manifest.get("operations") or []) == 2
    store = ArtifactStore(out["work_item_id"])
    on_disk = store.read_json("EXECUTION_MANIFEST.json", default={})
    assert len(on_disk.get("affected_repos") or []) == 2


def test_acceptance_verifier_blocks_mandatory_failed_repo_op(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    wid = 42
    manifest = build_affected_repos_manifest(
        [
            {"repository_id": 1, "mandatory": True, "status": "ready"},
            {"repository_id": 2, "mandatory": True, "status": "failed"},
        ]
    )
    manifest["operations"][1]["status"] = "failed"
    store = ArtifactStore(wid)
    store.write_json("EXECUTION_MANIFEST.json", manifest)
    store.write_json("EVIDENCE.json", [])
    av = AcceptanceVerifier(db, wid)
    out = av.verify(ship=False)
    assert out["ready_to_ship"] is False
    assert any("mandatory_repo" in e for e in out.get("errors") or [])

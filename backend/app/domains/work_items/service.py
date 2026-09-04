"""WorkItem CRUD + status transitions with append-only events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.work_items.events import append_event
from app.domains.work_items.status import ALL_STATUSES, GATE_STATUSES, STATUS_NEW
from app.models import WorkItem, WorkItemEvent


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_work_item(
    db: Session,
    *,
    title: str,
    description: str = "",
    source: str = "user",
    external_id: str = "",
    project_id: int | None = None,
    repository_id: int | None = None,
    repository_ref: str = "",
    base_commit_sha: str = "",
    requirements: list[Any] | None = None,
    acceptance: list[Any] | None = None,
    created_by: str = "",
    is_test_fixture: bool = False,
    test_run_id: str = "",
) -> WorkItem:
    wi = WorkItem(
        title=title,
        description=description or "",
        source=source or "user",
        external_id=external_id or "",
        project_id=project_id,
        repository_id=repository_id,
        repository_ref=repository_ref or "",
        base_commit_sha=base_commit_sha or "",
        status=STATUS_NEW,
        requirements_json=json.dumps(requirements or [], default=str),
        acceptance_json=json.dumps(acceptance or [], default=str),
        created_by=created_by or "",
        is_test_fixture=bool(is_test_fixture),
        test_run_id=(test_run_id or "").strip(),
    )
    db.add(wi)
    db.flush()
    append_event(
        db,
        work_item_id=wi.id,
        event_type="created",
        payload={
            "status": wi.status,
            "title": wi.title,
            "repository_id": wi.repository_id,
            "repository_ref": wi.repository_ref,
            "base_commit_sha": wi.base_commit_sha,
        },
    )
    db.commit()
    db.refresh(wi)
    return wi


def get_work_item(db: Session, work_item_id: int) -> WorkItem:
    wi = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not wi:
        raise HTTPException(status_code=404, detail="work_item_not_found")
    return wi


def list_work_items(
    db: Session,
    *,
    project_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    include_fixtures: bool = False,
) -> list[WorkItem]:
    q = db.query(WorkItem).order_by(WorkItem.id.desc())
    if project_id is not None:
        q = q.filter(WorkItem.project_id == project_id)
    if status:
        q = q.filter(WorkItem.status == status)
    if not include_fixtures:
        q = q.filter((WorkItem.is_test_fixture.is_(False)) | (WorkItem.is_test_fixture.is_(None)))
    return q.limit(min(limit, 500)).all()


def list_events(db: Session, work_item_id: int) -> list[WorkItemEvent]:
    get_work_item(db, work_item_id)
    return (
        db.query(WorkItemEvent)
        .filter(WorkItemEvent.work_item_id == work_item_id)
        .order_by(WorkItemEvent.id.asc())
        .all()
    )


def transition_status(
    db: Session,
    work_item_id: int,
    new_status: str,
    *,
    reason: str = "",
    allow_gate: bool = False,
    actor: str = "system",
) -> WorkItem:
    wi = get_work_item(db, work_item_id)
    status = (new_status or "").strip().upper()
    if status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid_status:{status}")
    if status in GATE_STATUSES and not allow_gate:
        raise HTTPException(
            status_code=403,
            detail="READY_TO_SHIP/DONE require EvidenceVerifier (allow_gate=True)",
        )
    old = wi.status
    wi.status = status
    wi.updated_at = _now()
    append_event(
        db,
        work_item_id=wi.id,
        event_type="status_changed",
        payload={"from": old, "to": status, "reason": reason, "actor": actor},
    )
    db.commit()
    db.refresh(wi)
    return wi


def serialize_work_item(wi: WorkItem) -> dict[str, Any]:
    return {
        "id": wi.id,
        "source": wi.source,
        "external_id": wi.external_id,
        "project_id": wi.project_id,
        "repository_id": wi.repository_id,
        "repository_ref": wi.repository_ref,
        "base_commit_sha": wi.base_commit_sha,
        "title": wi.title,
        "description": wi.description,
        "status": wi.status,
        "requirements": json.loads(wi.requirements_json or "[]"),
        "acceptance": json.loads(wi.acceptance_json or "[]"),
        "context_snapshot": json.loads(wi.context_snapshot_json or "{}"),
        "plan_version": wi.plan_version,
        "plan_hash": wi.plan_hash,
        "approved_plan_hash": wi.approved_plan_hash,
        "mentrix_run_id": wi.mentrix_run_id,
        "coding_mission_id": str(getattr(wi, "coding_mission_id", None) or ""),
        "worktree_path": wi.worktree_path,
        "current_commit_sha": wi.current_commit_sha,
        "created_by": wi.created_by,
        "is_test_fixture": bool(getattr(wi, "is_test_fixture", False)),
        "test_run_id": str(getattr(wi, "test_run_id", None) or ""),
        "created_at": wi.created_at.isoformat() if wi.created_at else None,
        "updated_at": wi.updated_at.isoformat() if wi.updated_at else None,
    }


def serialize_event(ev: WorkItemEvent) -> dict[str, Any]:
    try:
        payload = json.loads(ev.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {
        "id": ev.id,
        "work_item_id": ev.work_item_id,
        "event_type": ev.event_type,
        "payload": payload,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }

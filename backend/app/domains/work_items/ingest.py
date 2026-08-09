"""Ingest external sources into WorkItems with project/repo binding."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.domains.work_items.events import append_event
from app.domains.work_items.source_adapter import get_source_adapter
from app.domains.work_items.status import STATUS_INGESTED, STATUS_NEEDS_HUMAN_DECISION
from app.models import WorkItem


def ingest_work_item(
    db: Session,
    *,
    source: str,
    external_id: str,
    raw: dict[str, Any] | None = None,
    project_id: int | None = None,
    repository_id: int | None = None,
    repository_ref: str = "",
    base_commit_sha: str = "",
    created_by: str = "",
    require_repo: bool = True,
) -> dict[str, Any]:
    adapter = get_source_adapter(source)
    payload = dict(raw) if raw else adapter.fetch_raw(external_id)
    # Allow caller overrides for binding
    if project_id is not None:
        payload["project_id"] = project_id
    if repository_id is not None:
        payload["repository_id"] = repository_id
    if repository_ref:
        payload["repository_ref"] = repository_ref
    if base_commit_sha:
        payload["base_commit_sha"] = base_commit_sha

    fields = adapter.to_work_item_fields(payload)
    # Upsert by source+external_id
    existing = (
        db.query(WorkItem)
        .filter(WorkItem.source == fields["source"], WorkItem.external_id == fields["external_id"])
        .first()
    )
    missing_repo = not fields.get("repository_id") and not (
        fields.get("repository_ref") and fields.get("base_commit_sha")
    )
    if existing:
        for k in (
            "title",
            "description",
            "project_id",
            "repository_id",
            "repository_ref",
            "base_commit_sha",
        ):
            if fields.get(k) is not None and fields.get(k) != "":
                setattr(existing, k, fields[k])
        if require_repo and missing_repo:
            existing.status = STATUS_NEEDS_HUMAN_DECISION
        else:
            existing.status = STATUS_INGESTED
        append_event(
            db,
            work_item_id=existing.id,
            event_type="ingested",
            payload={"source": fields["source"], "external_id": fields["external_id"], "updated": True},
        )
        db.commit()
        db.refresh(existing)
        wi = existing
    else:
        wi = wi_svc.create_work_item(
            db,
            title=fields["title"],
            description=fields.get("description") or "",
            source=fields["source"],
            external_id=fields.get("external_id") or "",
            project_id=fields.get("project_id"),
            repository_id=fields.get("repository_id"),
            repository_ref=fields.get("repository_ref") or "",
            base_commit_sha=fields.get("base_commit_sha") or "",
            requirements=fields.get("requirements"),
            acceptance=fields.get("acceptance"),
            created_by=created_by,
        )
        if require_repo and missing_repo:
            wi = wi_svc.transition_status(
                db,
                wi.id,
                STATUS_NEEDS_HUMAN_DECISION,
                reason="repository_identity_missing",
                actor="ingest",
            )
        else:
            wi = wi_svc.transition_status(
                db,
                wi.id,
                STATUS_INGESTED,
                reason="ingested_from_source",
                actor="ingest",
            )

    return {
        "work_item": wi_svc.serialize_work_item(wi),
        "needs_human": wi.status == STATUS_NEEDS_HUMAN_DECISION,
        "missing_repository_identity": bool(require_repo and missing_repo),
    }

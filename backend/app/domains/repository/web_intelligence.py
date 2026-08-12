"""ZECT Web Intelligence API — attach/fetch/retrieve external content with provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.scopes import PROJECT_SHARED, USER_PRIVATE
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication
from app.infrastructure.database import get_db
from app.models import ExternalContentArtifact, ExternalContentChunk, ExternalContentVersion, KnowledgeEntry
from app.services.mentrix.permission_broker import check_tool_permission
from app.services.web_intelligence.service import (
    UNTRUSTED_TAG,
    get_accessible_artifact,
    ingest_external,
    retrieve_web_context,
    serialize_artifact,
)
from app.services.web_intelligence.ssrf import SsrfBlocked
from app.services.work_items.context_engine import MentrixContextEngine

router = APIRouter(prefix="/api/web", tags=["web-intelligence"])


def _uid(user: CurrentUser) -> int:
    uid = getattr(user, "user_id", None)
    if uid is None:
        raise HTTPException(401, "user_required")
    return int(uid)


class AttachIn(BaseModel):
    url: str
    project_id: Optional[int] = None
    scope: str = USER_PRIVATE
    sensitivity: str = "INTERNAL"
    adapter: Optional[str] = None
    confirmed_browser: bool = False
    replace_artifact_id: Optional[int] = None


@router.post("/attach")
@require_authentication
def attach_url(
    body: AttachIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    tool = "web_browser_snapshot" if (body.adapter or "").lower() == "browser" else "web_fetch"
    perm = check_tool_permission(db, tool, user_id=uid, project_id=body.project_id)
    if not perm.get("allowed") and perm.get("level") == "never":
        raise HTTPException(403, detail={"error": "permission_denied", **perm})
    if tool == "web_browser_snapshot" and not body.confirmed_browser:
        raise HTTPException(400, detail="browser_snapshot_requires_confirmation")
    try:
        out = ingest_external(
            db,
            user_id=uid,
            url=body.url,
            project_id=body.project_id,
            scope=body.scope,
            sensitivity=body.sensitivity,
            adapter=body.adapter,
            confirmed_browser=body.confirmed_browser,
            replace_artifact_id=body.replace_artifact_id,
        )
    except SsrfBlocked as e:
        raise HTTPException(400, detail={"error": "ssrf_blocked", "message": str(e)}) from e
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e
    return {"ok": True, "artifact": out, "permission": perm, "tag": UNTRUSTED_TAG}


@router.get("")
@require_authentication
def list_web(
    project_id: Optional[int] = None,
    scope: Optional[str] = None,
    current_only: bool = True,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    from sqlalchemy import and_, or_

    if project_id is None:
        q = db.query(ExternalContentArtifact).filter(
            ExternalContentArtifact.scope == USER_PRIVATE,
            ExternalContentArtifact.user_id == uid,
        )
    else:
        q = db.query(ExternalContentArtifact).filter(
            or_(
                and_(ExternalContentArtifact.scope == USER_PRIVATE, ExternalContentArtifact.user_id == uid),
                and_(
                    ExternalContentArtifact.scope == PROJECT_SHARED,
                    ExternalContentArtifact.project_id == project_id,
                ),
            )
        )
    if current_only:
        q = q.filter(ExternalContentArtifact.is_current == True)  # noqa: E712
    if scope:
        q = q.filter(ExternalContentArtifact.scope == scope.upper())
    rows = q.order_by(ExternalContentArtifact.id.desc()).limit(100).all()
    version_ids = [a.content_version_id for a in rows if a.content_version_id]
    versions = {}
    if version_ids:
        for cv in db.query(ExternalContentVersion).filter(ExternalContentVersion.id.in_(version_ids)).all():
            versions[cv.id] = cv
    return {
        "documents": [
            serialize_artifact(a, content_version=versions.get(a.content_version_id)) for a in rows
        ],
        "tag": UNTRUSTED_TAG,
    }


@router.get("/{artifact_id}")
@require_authentication
def get_web(
    artifact_id: int,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    art = get_accessible_artifact(db, artifact_id, uid, project_id=project_id)
    if not art:
        raise HTTPException(404, "web_artifact_not_found")
    cv = None
    if art.content_version_id:
        cv = db.query(ExternalContentVersion).filter(ExternalContentVersion.id == art.content_version_id).first()
    out = serialize_artifact(art, content_version=cv)
    try:
        out["source_map"] = json.loads(art.source_map_json or "[]")
    except Exception:
        out["source_map"] = []
    return out


@router.get("/{artifact_id}/markdown")
@require_authentication
def get_markdown(
    artifact_id: int,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    art = get_accessible_artifact(db, artifact_id, uid, project_id=project_id)
    if not art:
        raise HTTPException(404, "web_artifact_not_found")
    cv = db.query(ExternalContentVersion).filter(ExternalContentVersion.id == art.content_version_id).first()
    md = ""
    if cv and cv.markdown_path and Path(cv.markdown_path).is_file():
        md = Path(cv.markdown_path).read_text(encoding="utf-8", errors="replace")
    return {
        "artifact_id": art.id,
        "content_version_id": art.content_version_id,
        "content_sha256": art.content_sha256,
        "source_url": art.source_url,
        "is_current": art.is_current,
        "freshness": "current" if art.is_current else "stale",
        "markdown": md,
        "tag": UNTRUSTED_TAG,
    }


class RetrieveIn(BaseModel):
    query: str = ""
    project_id: Optional[int] = None
    artifact_ids: list[int] = Field(default_factory=list)
    max_tokens: int = 1200
    build_context_pack: bool = True


@router.post("/retrieve")
@require_authentication
def retrieve_for_context(
    body: RetrieveIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    perm = check_tool_permission(db, "web_retrieve", user_id=uid, project_id=body.project_id)
    if not perm.get("allowed") and perm.get("level") == "never":
        raise HTTPException(403, detail={"error": "permission_denied", **perm})
    items, meta = retrieve_web_context(
        db,
        user_id=uid,
        query=body.query,
        project_id=body.project_id,
        artifact_ids=body.artifact_ids or None,
        max_tokens=body.max_tokens,
    )
    pack = None
    if body.build_context_pack:
        engine = MentrixContextEngine(token_budget=max(2000, body.max_tokens + 500))
        pack = engine.build(goal=body.query or "web context", extra_items=items).to_dict()
        pack["items"] = [
            i
            for i in pack.get("items") or []
            if i.get("freshness") == "current" or i.get("source_type") == "goal"
        ]
    return {
        "ok": True,
        "meta": meta,
        "items": [i.to_dict() for i in items],
        "context_pack": pack,
        "permission": perm,
        "tag": UNTRUSTED_TAG,
    }


@router.delete("/{artifact_id}")
@require_authentication
def remove_web(
    artifact_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    perm = check_tool_permission(db, "web_delete", user_id=uid, project_id=None)
    if not perm.get("allowed") and perm.get("level") == "never":
        raise HTTPException(403, detail={"error": "permission_denied", **perm})
    art = (
        db.query(ExternalContentArtifact)
        .filter(ExternalContentArtifact.id == artifact_id, ExternalContentArtifact.user_id == uid)
        .first()
    )
    if not art:
        raise HTTPException(404, "web_artifact_not_found")
    art.is_current = False
    art.status = "SUPERSEDED"
    db.query(ExternalContentChunk).filter(
        ExternalContentChunk.external_artifact_id == art.id
    ).update({"freshness": "stale"})
    if art.knowledge_entry_id:
        ke = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == art.knowledge_entry_id).first()
        if ke:
            ke.is_active = False
    db.commit()
    return {"ok": True, "id": artifact_id, "status": "SUPERSEDED", "permission": perm}

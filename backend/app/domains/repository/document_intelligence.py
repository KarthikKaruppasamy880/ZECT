"""ZECT Document Intelligence API — upload/parse/retrieve with provenance."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.scopes import PROJECT_SHARED, USER_PRIVATE
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication
from app.infrastructure.database import get_db
from app.models import DocumentArtifact, DocumentChunk, DocumentContentVersion
from app.services.document_intelligence.service import (
    get_accessible_artifact,
    ingest_document,
    ingest_image,
    link_artifact_to_work_item,
    list_work_item_attachments,
    read_image_data_url,
    retrieve_document_context,
    serialize_artifact,
)
from app.services.mentrix.permission_broker import check_tool_permission
from app.services.work_items.context_engine import MentrixContextEngine

router = APIRouter(prefix="/api/documents", tags=["document-intelligence"])


def _uid(user: CurrentUser) -> int:
    uid = getattr(user, "user_id", None)
    if uid is None:
        raise HTTPException(401, "user_required")
    return int(uid)


@router.post("/upload", response_model=None)
@require_authentication
async def upload_document(
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(None),
    scope: str = Form(USER_PRIVATE),
    sensitivity: str = Form("INTERNAL"),
    replace_artifact_id: Optional[int] = Form(None),
    work_item_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    perm = check_tool_permission(db, "document_upload", user_id=uid, project_id=project_id)
    if not perm.get("allowed") and perm.get("level") == "never":
        raise HTTPException(403, detail={"error": "permission_denied", **perm})

    # Reject oversized uploads before buffering when Content-Length is present.
    from app.services.document_intelligence.service import MAX_UPLOAD_BYTES

    cl = file.headers.get("content-length") if getattr(file, "headers", None) else None
    if cl:
        try:
            if int(cl) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, detail="file_too_large")
        except ValueError:
            pass

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail="file_too_large")
    try:
        out = ingest_document(
            db,
            user_id=uid,
            filename=file.filename or "upload.bin",
            data=data,
            project_id=project_id,
            scope=scope,
            mime_type=file.content_type or "",
            sensitivity=sensitivity,
            replace_artifact_id=replace_artifact_id,
            work_item_id=work_item_id,
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e
    return {"ok": True, "artifact": out, "permission": perm}


@router.post("/upload-image", response_model=None)
@require_authentication
async def upload_image_attachment(
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(None),
    work_item_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """A pasted/attached screenshot -- durable, not just an in-memory data
    URL, so it survives a refresh and is visible to PLAN/AGENT without the
    user re-pasting it."""
    uid = _uid(current_user)
    perm = check_tool_permission(db, "document_upload", user_id=uid, project_id=project_id)
    if not perm.get("allowed") and perm.get("level") == "never":
        raise HTTPException(403, detail={"error": "permission_denied", **perm})

    from app.services.document_intelligence.service import MAX_UPLOAD_BYTES

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail="file_too_large")
    try:
        out = ingest_image(
            db,
            user_id=uid,
            filename=file.filename or "screenshot.png",
            data=data,
            mime_type=file.content_type or "",
            project_id=project_id,
            work_item_id=work_item_id,
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e
    return {"ok": True, "artifact": out}


@router.get("/{artifact_id}/raw")
@require_authentication
def get_raw_image(
    artifact_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    try:
        return {"ok": True, **read_image_data_url(db, artifact_id=artifact_id, user_id=uid)}
    except ValueError as e:
        raise HTTPException(404, detail=str(e)) from e


class LinkAttachmentIn(BaseModel):
    work_item_id: int


@router.post("/{artifact_id}/link")
@require_authentication
def link_attachment(
    artifact_id: int,
    body: LinkAttachmentIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retroactively attach an artifact (usually uploaded before a WorkItem
    existed, e.g. the first ASK turn) to a WorkItem, once one is known."""
    uid = _uid(current_user)
    try:
        out = link_artifact_to_work_item(db, artifact_id=artifact_id, user_id=uid, work_item_id=body.work_item_id)
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e
    return {"ok": True, "artifact": out}


@router.get("")
@require_authentication
def list_documents(
    project_id: Optional[int] = None,
    scope: Optional[str] = None,
    current_only: bool = True,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    from sqlalchemy import and_, or_

    # Without project_id: USER_PRIVATE only (never dump all PROJECT_SHARED).
    if project_id is None:
        q = db.query(DocumentArtifact).filter(
            DocumentArtifact.scope == USER_PRIVATE,
            DocumentArtifact.user_id == uid,
        )
    else:
        q = db.query(DocumentArtifact).filter(
            or_(
                and_(DocumentArtifact.scope == USER_PRIVATE, DocumentArtifact.user_id == uid),
                and_(
                    DocumentArtifact.scope == PROJECT_SHARED,
                    DocumentArtifact.project_id == project_id,
                ),
            )
        )
    if current_only:
        q = q.filter(DocumentArtifact.is_current == True)  # noqa: E712
    if scope:
        q = q.filter(DocumentArtifact.scope == scope.upper())
    rows = q.order_by(DocumentArtifact.id.desc()).limit(100).all()
    version_ids = [a.content_version_id for a in rows if a.content_version_id]
    versions = {}
    if version_ids:
        for cv in db.query(DocumentContentVersion).filter(DocumentContentVersion.id.in_(version_ids)).all():
            versions[cv.id] = cv
    return {
        "documents": [
            serialize_artifact(a, content_version=versions.get(a.content_version_id)) for a in rows
        ]
    }


@router.get("/{artifact_id}")
@require_authentication
def get_document(
    artifact_id: int,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    art = get_accessible_artifact(db, artifact_id, uid, project_id=project_id)
    if not art:
        raise HTTPException(404, "document_not_found")
    cv = None
    if art.content_version_id:
        cv = db.query(DocumentContentVersion).filter(DocumentContentVersion.id == art.content_version_id).first()
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
        raise HTTPException(404, "document_not_found")
    cv = db.query(DocumentContentVersion).filter(DocumentContentVersion.id == art.content_version_id).first()
    md = ""
    if cv and cv.markdown_path and Path(cv.markdown_path).is_file():
        md = Path(cv.markdown_path).read_text(encoding="utf-8", errors="replace")
    return {
        "artifact_id": art.id,
        "content_version_id": art.content_version_id,
        "content_sha256": art.content_sha256,
        "is_current": art.is_current,
        "freshness": "current" if art.is_current else "stale",
        "markdown": md,
        "tag": "UNTRUSTED_DOCUMENT_CONTEXT",
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
    perm = check_tool_permission(db, "document_retrieve", user_id=uid, project_id=body.project_id)
    if not perm.get("allowed") and perm.get("level") == "never":
        raise HTTPException(403, detail={"error": "permission_denied", **perm})

    items, meta = retrieve_document_context(
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
        pack = engine.build(goal=body.query or "document context", extra_items=items).to_dict()
        # Ensure no stale freshness slipped in
        pack["items"] = [i for i in pack.get("items") or [] if i.get("freshness") == "current" or i.get("source_type") == "goal"]
    return {
        "ok": True,
        "meta": meta,
        "items": [i.to_dict() for i in items],
        "context_pack": pack,
        "permission": perm,
    }


@router.delete("/{artifact_id}")
@require_authentication
def remove_document(
    artifact_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = _uid(current_user)
    perm = check_tool_permission(db, "document_delete", user_id=uid, project_id=None)
    if not perm.get("allowed") and perm.get("level") == "never":
        raise HTTPException(403, detail={"error": "permission_denied", **perm})
    art = db.query(DocumentArtifact).filter(DocumentArtifact.id == artifact_id, DocumentArtifact.user_id == uid).first()
    if not art:
        raise HTTPException(404, "document_not_found")
    art.is_current = False
    art.status = "SUPERSEDED"
    db.query(DocumentChunk).filter(DocumentChunk.document_artifact_id == art.id).update({"freshness": "stale"})
    if art.knowledge_entry_id:
        from app.models import KnowledgeEntry

        ke = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == art.knowledge_entry_id).first()
        if ke:
            ke.is_active = False
    db.commit()
    return {"ok": True, "id": artifact_id, "status": "SUPERSEDED", "permission": perm}

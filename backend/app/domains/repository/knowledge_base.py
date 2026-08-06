"""Knowledge Base — persistent tips, instructions, project notes."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import KnowledgeEntry

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeCreate(BaseModel):
    title: str
    content: str
    category: str = "general"
    tags: list = []
    source: str = "manual"
    project_id: Optional[int] = None


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list] = None
    is_active: Optional[bool] = None


class KnowledgeSearchBody(BaseModel):
    query: str
    category: Optional[str] = None
    project_id: Optional[int] = None
    limit: int = 20


class KnowledgeContextBody(BaseModel):
    query: str = ""
    project_id: Optional[int] = None
    category: Optional[str] = None
    tags: Optional[list] = None
    max_tokens: int = 800
    limit: int = 5


def retrieve_knowledge_for_context(
    db: Session,
    *,
    query: str = "",
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    tags: Optional[list] = None,
    max_tokens: int = 800,
    limit: int = 5,
) -> tuple[str, dict]:
    """Return a short Knowledge block and metadata (entries used, chars, est tokens)."""
    max_chars = max(200, int(max_tokens) * 4)
    q = db.query(KnowledgeEntry).filter(KnowledgeEntry.is_active == True)  # noqa: E712
    if project_id is not None:
        q = q.filter(
            (KnowledgeEntry.project_id == project_id) | (KnowledgeEntry.project_id == None)  # noqa: E711
        )
    if category:
        q = q.filter(KnowledgeEntry.category == category)
    q_text = (query or "").strip()
    if q_text:
        matched = q.filter(
            KnowledgeEntry.title.ilike(f"%{q_text}%")
            | KnowledgeEntry.content.ilike(f"%{q_text}%")
        ).order_by(KnowledgeEntry.usage_count.desc()).limit(limit).all()
        items = matched or q.order_by(KnowledgeEntry.updated_at.desc()).limit(limit).all()
    else:
        items = q.order_by(KnowledgeEntry.updated_at.desc()).limit(limit).all()

    if tags:
        tag_set = {str(t).lower() for t in tags}
        filtered = []
        for e in items:
            etags = {str(t).lower() for t in (e.tags or [])}
            if etags & tag_set:
                filtered.append(e)
        if filtered:
            items = filtered

    parts: list[str] = []
    used_ids: list[int] = []
    total_chars = 0
    now = datetime.now(timezone.utc)
    for e in items:
        snippet = f"- {e.title}: {(e.content or '').strip()[:600]}"
        if total_chars + len(snippet) > max_chars:
            remain = max_chars - total_chars
            if remain > 80:
                parts.append(snippet[:remain] + "…")
                used_ids.append(e.id)
            break
        parts.append(snippet)
        used_ids.append(e.id)
        total_chars += len(snippet) + 1
        e.usage_count = (e.usage_count or 0) + 1
        e.last_used_at = now
    if used_ids:
        try:
            db.commit()
        except Exception:
            db.rollback()

    block = ""
    if parts:
        block = "Knowledge Base (prefer these conventions over guessing):\n" + "\n".join(parts)
    est_tokens = max(0, len(block) // 4)
    return block, {
        "entry_ids": used_ids,
        "entry_count": len(used_ids),
        "chars": len(block),
        "tokens_estimated": est_tokens,
        "max_tokens": max_tokens,
    }


def _to_dict(e: KnowledgeEntry) -> dict:
    return {
        "id": e.id,
        "user_id": e.user_id,
        "project_id": e.project_id,
        "title": e.title,
        "content": e.content,
        "category": e.category,
        "tags": e.tags or [],
        "source": e.source,
        "is_active": e.is_active,
        "usage_count": e.usage_count,
        "last_used_at": e.last_used_at.isoformat() if e.last_used_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


@router.get("")
def list_entries(
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List knowledge entries with filters."""
    try:
        q = db.query(KnowledgeEntry).filter(KnowledgeEntry.is_active == is_active)
        if category:
            q = q.filter(KnowledgeEntry.category == category)
        if project_id:
            q = q.filter(KnowledgeEntry.project_id == project_id)
        if search:
            q = q.filter(
                KnowledgeEntry.title.ilike(f"%{search}%")
                | KnowledgeEntry.content.ilike(f"%{search}%")
            )
        total = q.count()
        items = q.order_by(KnowledgeEntry.updated_at.desc()).offset(skip).limit(limit).all()
        return {"items": [_to_dict(e) for e in items], "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_entry(data: KnowledgeCreate, db: Session = Depends(get_db)):
    """Create a new knowledge entry."""
    try:
        entry = KnowledgeEntry(
            title=data.title,
            content=data.content,
            category=data.category,
            tags=data.tags,
            source=data.source,
            project_id=data.project_id,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _to_dict(entry)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """Get all used categories with counts."""
    try:
        from sqlalchemy import func
        rows = db.query(
            KnowledgeEntry.category, func.count(KnowledgeEntry.id)
        ).filter(KnowledgeEntry.is_active == True).group_by(KnowledgeEntry.category).all()  # noqa: E712
        return [{"category": r[0], "count": r[1]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
def search_entries(body: KnowledgeSearchBody, db: Session = Depends(get_db)):
    """Full-text search across knowledge entries."""
    try:
        q_text = (body.query or "").strip()
        if not q_text:
            return []
        q = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.is_active == True,  # noqa: E712
            KnowledgeEntry.title.ilike(f"%{q_text}%")
            | KnowledgeEntry.content.ilike(f"%{q_text}%"),
        )
        if body.category:
            q = q.filter(KnowledgeEntry.category == body.category)
        if body.project_id is not None:
            q = q.filter(
                (KnowledgeEntry.project_id == body.project_id) | (KnowledgeEntry.project_id == None)  # noqa: E711
            )
        items = q.order_by(KnowledgeEntry.usage_count.desc()).limit(body.limit).all()
        return [_to_dict(e) for e in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context")
def knowledge_for_context(body: KnowledgeContextBody, db: Session = Depends(get_db)):
    """Token-capped knowledge snippets for Mentrix / Ask prompt injection."""
    try:
        block, meta = retrieve_knowledge_for_context(
            db,
            query=body.query,
            project_id=body.project_id,
            category=body.category,
            tags=body.tags,
            max_tokens=body.max_tokens,
            limit=body.limit,
        )
        return {"context": block, **meta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}")
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    """Get a single knowledge entry."""
    try:
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")
        entry.usage_count = (entry.usage_count or 0) + 1
        entry.last_used_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(entry)
        return _to_dict(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{entry_id}")
def update_entry(entry_id: int, data: KnowledgeUpdate, db: Session = Depends(get_db)):
    """Update a knowledge entry."""
    try:
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")
        if data.title is not None:
            entry.title = data.title
        if data.content is not None:
            entry.content = data.content
        if data.category is not None:
            entry.category = data.category
        if data.tags is not None:
            entry.tags = data.tags
        if data.is_active is not None:
            entry.is_active = data.is_active
        db.commit()
        db.refresh(entry)
        return _to_dict(entry)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a knowledge entry."""
    try:
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")
        db.delete(entry)
        db.commit()
        return {"status": "deleted", "id": entry_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

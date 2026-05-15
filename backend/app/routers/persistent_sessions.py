"""Persistent Sessions API — maintain AI context across pages/stages.

Sessions track all AI interactions and inject history into subsequent
prompts so context is never lost when navigating between pages.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PersistentSession, SessionMessage

router = APIRouter(prefix="/api/persistent-sessions", tags=["persistent-sessions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CreateSessionRequest(BaseModel):
    project_id: int | None = None
    repo_id: int | None = None
    title: str = ""


class AddMessageRequest(BaseModel):
    role: str  # user, assistant, system
    content: str
    page: str = ""  # ask, plan, build, review, deploy
    model: str = ""
    tokens_used: int = 0
    metadata: dict | None = None


class SessionContextResponse(BaseModel):
    session_id: int
    title: str
    messages_count: int
    context_summary: str
    recent_messages: list[dict]


@router.post("/create")
def create_session(req: CreateSessionRequest, db: Session = Depends(get_db)):
    """Create a new persistent session."""
    session = PersistentSession(
        project_id=req.project_id,
        repo_id=req.repo_id,
        title=req.title or f"Session {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _format_session(session, db)


@router.get("/active")
def get_active_session(project_id: int | None = None, db: Session = Depends(get_db)):
    """Get the active session for a project, or the most recent active session."""
    query = db.query(PersistentSession).filter(PersistentSession.status == "active")
    if project_id:
        query = query.filter(PersistentSession.project_id == project_id)
    session = query.order_by(PersistentSession.last_activity.desc()).first()
    if not session:
        return {"session": None}
    return _format_session(session, db)


@router.get("/list")
def list_sessions(limit: int = 20, offset: int = 0, status: str | None = None, db: Session = Depends(get_db)):
    """List all sessions."""
    query = db.query(PersistentSession)
    if status:
        query = query.filter(PersistentSession.status == status)
    sessions = query.order_by(PersistentSession.last_activity.desc()).offset(offset).limit(limit).all()
    total = query.count()
    return {
        "sessions": [_format_session(s, db) for s in sessions],
        "total": total,
    }


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a session with all messages."""
    session = db.query(PersistentSession).filter(PersistentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _format_session(session, db, include_all_messages=True)


@router.post("/{session_id}/message")
def add_message(session_id: int, req: AddMessageRequest, db: Session = Depends(get_db)):
    """Add a message to a session."""
    session = db.query(PersistentSession).filter(PersistentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg = SessionMessage(
        session_id=session_id,
        role=req.role,
        content=req.content,
        page=req.page,
        model=req.model,
        tokens_used=req.tokens_used,
        metadata_json=json.dumps(req.metadata) if req.metadata else None,
    )
    db.add(msg)

    session.messages_count = (session.messages_count or 0) + 1
    session.total_tokens = (session.total_tokens or 0) + req.tokens_used
    session.last_activity = datetime.now(timezone.utc)
    if req.page and req.page not in (session.pages_visited or ""):
        session.pages_visited = f"{session.pages_visited or ''},{req.page}".strip(",")
    db.commit()
    db.refresh(msg)

    return {"id": msg.id, "role": msg.role, "content": msg.content[:200], "page": msg.page}


@router.get("/{session_id}/context")
def get_session_context(session_id: int, page: str = "", max_messages: int = 10, db: Session = Depends(get_db)):
    """Get session context for injection into AI prompts.

    Returns a summary of the session + recent messages, formatted
    for injection into LLM system prompts.
    """
    session = db.query(PersistentSession).filter(PersistentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    query = db.query(SessionMessage).filter(SessionMessage.session_id == session_id)
    if page:
        query = query.filter(SessionMessage.page == page)

    recent = query.order_by(SessionMessage.created_at.desc()).limit(max_messages).all()
    recent.reverse()

    context_parts = []
    if session.title:
        context_parts.append(f"Session: {session.title}")
    if session.pages_visited:
        context_parts.append(f"Pages visited: {session.pages_visited}")

    for msg in recent:
        role_label = msg.role.capitalize()
        page_label = f" [{msg.page}]" if msg.page else ""
        context_parts.append(f"{role_label}{page_label}: {msg.content[:500]}")

    context_summary = "\n".join(context_parts)

    return SessionContextResponse(
        session_id=session_id,
        title=session.title or "",
        messages_count=session.messages_count or 0,
        context_summary=context_summary,
        recent_messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "page": m.page,
                "model": m.model,
                "tokens_used": m.tokens_used,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in recent
        ],
    )


@router.patch("/{session_id}/close")
def close_session(session_id: int, db: Session = Depends(get_db)):
    """Close a session."""
    session = db.query(PersistentSession).filter(PersistentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "completed"
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "completed", "session_id": session_id}


@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a session and all its messages."""
    session = db.query(PersistentSession).filter(PersistentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(SessionMessage).filter(SessionMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"deleted": True, "session_id": session_id}


def _format_session(session: PersistentSession, db: Session, include_all_messages: bool = False) -> dict:
    result = {
        "id": session.id,
        "project_id": session.project_id,
        "repo_id": session.repo_id,
        "title": session.title,
        "status": session.status,
        "messages_count": session.messages_count or 0,
        "total_tokens": session.total_tokens or 0,
        "pages_visited": session.pages_visited or "",
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_activity": session.last_activity.isoformat() if session.last_activity else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }

    if include_all_messages:
        messages = db.query(SessionMessage).filter(
            SessionMessage.session_id == session.id
        ).order_by(SessionMessage.created_at).all()
        result["messages"] = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "page": m.page,
                "model": m.model,
                "tokens_used": m.tokens_used,
                "metadata": json.loads(m.metadata_json) if m.metadata_json else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]

    return result

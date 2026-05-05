"""User Sessions — Track user work sessions, context files, and activity."""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import UserSession, ContextFile

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    user_id: int = 1
    project_id: int | None = None
    session_type: str = "general"
    title: str = ""


class SessionOut(BaseModel):
    id: int
    user_id: int
    project_id: int | None
    session_type: str
    title: str
    status: str
    total_tokens_used: int
    total_cost_usd: float
    models_used: str
    messages_count: int
    started_at: str
    ended_at: str | None
    last_activity: str


class ContextFileCreate(BaseModel):
    name: str
    file_type: str = "file"  # file, repo, snippet
    content: str = ""


class ContextFileOut(BaseModel):
    id: int
    session_id: int
    name: str
    file_type: str
    char_count: int
    token_estimate: int
    created_at: str


# ---------------------------------------------------------------------------
# Session Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[SessionOut])
@router.get("/", response_model=list[SessionOut])
def list_sessions(
    status: str | None = None,
    user_id: int | None = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """List user sessions."""
    query = db.query(UserSession)
    if status:
        query = query.filter(UserSession.status == status)
    if user_id:
        query = query.filter(UserSession.user_id == user_id)
    sessions = query.order_by(UserSession.last_activity.desc()).limit(limit).all()
    return [_session_out(s) for s in sessions]


@router.post("", response_model=SessionOut)
@router.post("/", response_model=SessionOut)
def create_session(req: SessionCreate, db: Session = Depends(get_db)):
    """Create a new work session."""
    session = UserSession(
        user_id=req.user_id,
        project_id=req.project_id,
        session_type=req.session_type,
        title=req.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get session details."""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_out(session)


@router.post("/{session_id}/end", response_model=SessionOut)
def end_session(session_id: int, db: Session = Depends(get_db)):
    """End a session."""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "completed"
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return _session_out(session)


# ---------------------------------------------------------------------------
# Context File Endpoints
# ---------------------------------------------------------------------------

@router.get("/{session_id}/context", response_model=list[ContextFileOut])
def list_context_files(session_id: int, db: Session = Depends(get_db)):
    """List context files for a session."""
    files = db.query(ContextFile).filter(ContextFile.session_id == session_id).all()
    return [
        ContextFileOut(
            id=f.id, session_id=f.session_id, name=f.name,
            file_type=f.file_type, char_count=f.char_count,
            token_estimate=f.token_estimate,
            created_at=f.created_at.isoformat() if f.created_at else "",
        )
        for f in files
    ]


@router.post("/{session_id}/context", response_model=ContextFileOut)
def add_context_file(session_id: int, req: ContextFileCreate, db: Session = Depends(get_db)):
    """Add a context file to a session."""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    char_count = len(req.content)
    token_estimate = char_count // 4  # rough estimate

    cf = ContextFile(
        session_id=session_id,
        name=req.name,
        file_type=req.file_type,
        content=req.content,
        char_count=char_count,
        token_estimate=token_estimate,
    )
    db.add(cf)
    session.last_activity = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cf)
    return ContextFileOut(
        id=cf.id, session_id=cf.session_id, name=cf.name,
        file_type=cf.file_type, char_count=cf.char_count,
        token_estimate=cf.token_estimate,
        created_at=cf.created_at.isoformat() if cf.created_at else "",
    )


@router.delete("/{session_id}/context/{file_id}")
def remove_context_file(session_id: int, file_id: int, db: Session = Depends(get_db)):
    """Remove a context file from a session."""
    cf = db.query(ContextFile).filter(ContextFile.id == file_id, ContextFile.session_id == session_id).first()
    if not cf:
        raise HTTPException(status_code=404, detail="Context file not found")
    db.delete(cf)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_out(s: UserSession) -> SessionOut:
    return SessionOut(
        id=s.id, user_id=s.user_id, project_id=s.project_id,
        session_type=s.session_type, title=s.title or "",
        status=s.status, total_tokens_used=s.total_tokens_used,
        total_cost_usd=s.total_cost_usd, models_used=s.models_used or "",
        messages_count=s.messages_count,
        started_at=s.started_at.isoformat() if s.started_at else "",
        ended_at=s.ended_at.isoformat() if s.ended_at else None,
        last_activity=s.last_activity.isoformat() if s.last_activity else "",
    )

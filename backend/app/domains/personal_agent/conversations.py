"""Conversation History — persistent chat threads across sessions."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import Conversation, ConversationMessage

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ---- Pydantic schemas ----

class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    mode: str = "ask"
    project_id: Optional[int] = None
    model_used: str = ""

class MessageCreate(BaseModel):
    role: str  # user, assistant, system
    content: str
    model: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    attachments: list = []
    metadata_extra: dict = {}

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


# ---- Endpoints ----

@router.get("")
def list_conversations(
    mode: Optional[str] = None,
    project_id: Optional[int] = None,
    is_archived: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List conversations with optional filters."""
    try:
        q = db.query(Conversation).filter(Conversation.is_archived == is_archived)
        if mode:
            q = q.filter(Conversation.mode == mode)
        if project_id:
            q = q.filter(Conversation.project_id == project_id)
        total = q.count()
        items = q.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
        return {
            "items": [_conv_to_dict(c) for c in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversation thread."""
    try:
        conv = Conversation(
            title=data.title,
            mode=data.mode,
            project_id=data.project_id,
            model_used=data.model_used,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return _conv_to_dict(conv)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Get a conversation with all messages."""
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        result = _conv_to_dict(conv)
        result["messages"] = [_msg_to_dict(m) for m in conv.messages]
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conversation_id}")
def update_conversation(conversation_id: int, data: ConversationUpdate, db: Session = Depends(get_db)):
    """Update conversation metadata (title, pin, archive)."""
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if data.title is not None:
            conv.title = data.title
        if data.is_pinned is not None:
            conv.is_pinned = data.is_pinned
        if data.is_archived is not None:
            conv.is_archived = data.is_archived
        db.commit()
        db.refresh(conv)
        return _conv_to_dict(conv)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        db.delete(conv)
        db.commit()
        return {"status": "deleted", "id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/messages")
def add_message(conversation_id: int, data: MessageCreate, db: Session = Depends(get_db)):
    """Add a message to a conversation."""
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=data.role,
            content=data.content,
            model=data.model,
            tokens_used=data.tokens_used,
            cost_usd=data.cost_usd,
            attachments=data.attachments,
            metadata_extra=data.metadata_extra,
        )
        db.add(msg)
        conv.message_count = (conv.message_count or 0) + 1
        conv.total_tokens = (conv.total_tokens or 0) + data.tokens_used
        conv.total_cost_usd = (conv.total_cost_usd or 0) + data.cost_usd
        if data.model:
            conv.model_used = data.model
        db.commit()
        db.refresh(msg)
        return _msg_to_dict(msg)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List messages in a conversation."""
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        q = db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation_id
        ).order_by(ConversationMessage.created_at.asc())
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return {
            "items": [_msg_to_dict(m) for m in items],
            "total": total,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Helpers ----

def _conv_to_dict(c: Conversation) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "project_id": c.project_id,
        "title": c.title,
        "mode": c.mode,
        "model_used": c.model_used,
        "total_tokens": c.total_tokens,
        "total_cost_usd": c.total_cost_usd,
        "message_count": c.message_count,
        "is_pinned": c.is_pinned,
        "is_archived": c.is_archived,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }

def _msg_to_dict(m: ConversationMessage) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "model": m.model,
        "tokens_used": m.tokens_used,
        "cost_usd": m.cost_usd,
        "attachments": m.attachments or [],
        "metadata_extra": m.metadata_extra or {},
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }

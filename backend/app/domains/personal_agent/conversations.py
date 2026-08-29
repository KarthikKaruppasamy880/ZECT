"""Conversation History — persistent chat threads (USER_PRIVATE, auth required)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.scopes import PERSONAL_DEFAULT_SCOPE, USER_PRIVATE
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication
from app.infrastructure.database import get_db
from app.models import Conversation, ConversationMessage

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


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


def _uid(user: CurrentUser) -> int | None:
    return getattr(user, "user_id", None)


def _owned_conv(db: Session, conversation_id: int, user: CurrentUser) -> Conversation:
    uid = _uid(user)
    q = db.query(Conversation).filter(Conversation.id == conversation_id)
    if uid is not None:
        q = q.filter(Conversation.user_id == uid)
    conv = q.first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("")
@require_authentication
def list_conversations(
    mode: Optional[str] = None,
    project_id: Optional[int] = None,
    is_archived: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List conversations owned by the current user only."""
    try:
        uid = _uid(current_user)
        q = db.query(Conversation).filter(Conversation.is_archived == is_archived)
        if uid is not None:
            q = q.filter(Conversation.user_id == uid)
        else:
            q = q.filter(Conversation.id == -1)  # no anonymous listing
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
            "scope": USER_PRIVATE,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
@require_authentication
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new conversation thread for the current user."""
    try:
        conv = Conversation(
            title=data.title,
            mode=data.mode,
            project_id=data.project_id,
            model_used=data.model_used,
            user_id=_uid(current_user),
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        out = _conv_to_dict(conv)
        out["scope"] = PERSONAL_DEFAULT_SCOPE
        return out
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}")
@require_authentication
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a conversation with all messages (owner only)."""
    try:
        conv = _owned_conv(db, conversation_id, current_user)
        result = _conv_to_dict(conv)
        result["messages"] = [_msg_to_dict(m) for m in conv.messages]
        result["scope"] = USER_PRIVATE
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conversation_id}")
@require_authentication
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update conversation metadata (title, pin, archive)."""
    try:
        conv = _owned_conv(db, conversation_id, current_user)
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
@require_authentication
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete a conversation and all its messages (owner only)."""
    try:
        conv = _owned_conv(db, conversation_id, current_user)
        db.delete(conv)
        db.commit()
        return {"status": "deleted", "id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/messages")
@require_authentication
def add_message(
    conversation_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Add a message to an owned conversation."""
    try:
        conv = _owned_conv(db, conversation_id, current_user)
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
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)
        return _msg_to_dict(msg)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}/messages")
@require_authentication
def list_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List messages in an owned conversation."""
    try:
        _owned_conv(db, conversation_id, current_user)
        q = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return {
            "items": [_msg_to_dict(m) for m in items],
            "total": total,
            "scope": USER_PRIVATE,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        "scope": USER_PRIVATE,
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

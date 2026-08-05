"""Phase 8 Stage A — outbound draft-before-send for Slack/email."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import OutboundDraft


def create_outbound_draft(
    db: Session,
    *,
    channel: str,
    payload: dict[str, Any],
    user_id: int | None = None,
    project_id: int | None = None,
) -> OutboundDraft:
    row = OutboundDraft(
        channel=channel,
        status="draft",
        payload_json=payload,
        user_id=user_id,
        project_id=project_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_draft(db: Session, draft_id: int) -> OutboundDraft | None:
    return db.query(OutboundDraft).filter(OutboundDraft.id == draft_id).first()


def mark_sent(db: Session, draft: OutboundDraft, provider_id: str = "") -> OutboundDraft:
    draft.status = "sent"
    draft.provider_message_id = provider_id or ""
    draft.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)
    return draft


def serialize_draft(d: OutboundDraft) -> dict[str, Any]:
    return {
        "id": d.id,
        "channel": d.channel,
        "status": d.status,
        "payload": d.payload_json or {},
        "provider_message_id": d.provider_message_id or "",
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "sent_at": d.sent_at.isoformat() if d.sent_at else None,
    }

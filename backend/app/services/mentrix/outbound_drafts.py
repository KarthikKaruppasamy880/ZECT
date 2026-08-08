"""PA-3 outbound draft approval — immutable preview hash, expiry, anti-dupe."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import OutboundDraft

DEFAULT_APPROVAL_TTL_MINUTES = 30


def _canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)


def preview_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload(payload).encode("utf-8")).hexdigest()


def create_outbound_draft(
    db: Session,
    *,
    channel: str,
    payload: dict[str, Any],
    user_id: int | None = None,
    project_id: int | None = None,
    citations: list[dict[str, Any]] | None = None,
    dictation: str = "",
    ttl_minutes: int | None = None,
    correlation_id: str = "",
) -> OutboundDraft:
    ttl = ttl_minutes if ttl_minutes is not None else int(
        __import__("os").getenv("MENTRIX_DRAFT_TTL_MINUTES", str(DEFAULT_APPROVAL_TTL_MINUTES)) or DEFAULT_APPROVAL_TTL_MINUTES
    )
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=max(1, ttl))
    body = dict(payload or {})
    body["_pa3"] = {
        "preview_hash": preview_hash(payload),
        "expires_at": expires.isoformat(),
        "citations": citations or [],
        "dictation": (dictation or "")[:4000],
        "correlation_id": correlation_id or "",
        "created_at": now.isoformat(),
    }
    row = OutboundDraft(
        channel=channel,
        status="draft",
        payload_json=body,
        user_id=user_id,
        project_id=project_id,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_draft(db: Session, draft_id: int) -> OutboundDraft | None:
    return db.query(OutboundDraft).filter(OutboundDraft.id == draft_id).first()


def _pa3(draft: OutboundDraft) -> dict[str, Any]:
    payload = draft.payload_json or {}
    meta = payload.get("_pa3") if isinstance(payload, dict) else None
    return meta if isinstance(meta, dict) else {}


def is_expired(draft: OutboundDraft) -> bool:
    meta = _pa3(draft)
    raw = meta.get("expires_at") or ""
    if not raw:
        return False
    try:
        exp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp
    except ValueError:
        return False


def verify_approval(
    draft: OutboundDraft,
    *,
    expected_hash: str | None = None,
    payload_override: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Return (ok, reason). Enforces status, expiry, and immutable preview hash."""
    if draft.status == "sent":
        return False, "already_sent"
    if draft.status == "cancelled":
        return False, "cancelled"
    if draft.status != "draft":
        return False, f"invalid_status:{draft.status}"
    if is_expired(draft):
        return False, "approval_expired"
    meta = _pa3(draft)
    stored = str(meta.get("preview_hash") or "")
    if not stored:
        # Legacy drafts without PA-3 meta — allow once, then prefer hash path
        return True, "legacy_no_hash"
    if expected_hash:
        if expected_hash != stored:
            return False, "preview_hash_mismatch"
    if payload_override is not None:
        # Strip _pa3 before hashing comparison of user-visible content
        clean = {k: v for k, v in payload_override.items() if k != "_pa3"}
        original = {k: v for k, v in (draft.payload_json or {}).items() if k != "_pa3"}
        if preview_hash(clean) != preview_hash(original):
            return False, "payload_mutated"
    return True, "ok"


def mark_sent(db: Session, draft: OutboundDraft, provider_id: str = "") -> OutboundDraft:
    if draft.status == "sent":
        # Anti-dupe: idempotent — do not re-send
        return draft
    draft.status = "sent"
    draft.provider_message_id = provider_id or draft.provider_message_id or ""
    draft.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)
    return draft


def mark_cancelled(db: Session, draft: OutboundDraft) -> OutboundDraft:
    if draft.status == "sent":
        return draft
    draft.status = "cancelled"
    db.commit()
    db.refresh(draft)
    return draft


def serialize_draft(d: OutboundDraft) -> dict[str, Any]:
    payload = dict(d.payload_json or {})
    meta = payload.pop("_pa3", None) if isinstance(payload, dict) else None
    out: dict[str, Any] = {
        "id": d.id,
        "channel": d.channel,
        "status": d.status,
        "payload": payload,
        "provider_message_id": d.provider_message_id or "",
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "sent_at": d.sent_at.isoformat() if d.sent_at else None,
        "expired": is_expired(d),
    }
    if isinstance(meta, dict):
        out["preview_hash"] = meta.get("preview_hash")
        out["expires_at"] = meta.get("expires_at")
        out["citations"] = meta.get("citations") or []
        out["dictation"] = meta.get("dictation") or ""
        out["correlation_id"] = meta.get("correlation_id") or ""
    return out


def public_payload(draft: OutboundDraft) -> dict[str, Any]:
    """User-visible payload without internal _pa3 envelope."""
    payload = dict(draft.payload_json or {})
    payload.pop("_pa3", None)
    return payload

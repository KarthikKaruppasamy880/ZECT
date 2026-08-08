"""PA gap-close — Calendar API (read + draft; never delete)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication, log_audit
from app.infrastructure.database import get_db
from app.services.mentrix.outbound_drafts import create_outbound_draft, serialize_draft
from app.services.mentrix.providers import get_calendar_provider

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class DraftEventRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    start_iso: str = ""
    end_iso: str = ""
    attendees: list[str] = Field(default_factory=list)
    body: str = ""


@router.get("/upcoming")
@require_authentication
def upcoming(
    limit: int = 10,
    current_user: CurrentUser = Depends(get_current_user),
):
    items = get_calendar_provider().upcoming(limit=max(1, min(limit, 50)))
    return {
        "ok": True,
        "meetings": [
            {
                "id": m.id,
                "title": m.title,
                "when": m.when,
                "body": m.body,
                "source": m.source,
                "meta": m.meta,
            }
            for m in items
        ],
        "policy": {"delete": "never", "write": "draft_with_approval"},
    }


@router.post("/draft-event")
@require_authentication
def draft_event(
    req: DraftEventRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an outbound calendar draft — never creates the event until PA-3 approve send."""
    drafted = get_calendar_provider().draft_event(
        title=req.title,
        start_iso=req.start_iso,
        end_iso=req.end_iso,
        attendees=req.attendees,
        body=req.body,
    )
    draft = create_outbound_draft(
        db,
        channel="calendar",
        payload={
            "title": req.title,
            "start": req.start_iso,
            "end": req.end_iso,
            "attendees": req.attendees,
            "body": req.body,
        },
        user_id=getattr(current_user, "user_id", None) or getattr(current_user, "id", None),
        citations=[{"kind": "calendar", "ref": "draft_event", "excerpt": req.title[:200]}],
    )
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="calendar_draft_event",
        resource_type="outbound_draft",
        details={"draft_id": draft.id, "title": req.title[:120]},
    )
    return {
        "ok": True,
        "draft": serialize_draft(draft),
        "provider_preview": drafted,
        "needs_write_approval": True,
        "note": "Calendar events are never auto-created or deleted.",
    }

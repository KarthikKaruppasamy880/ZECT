"""PA-8 meeting assistant — briefs from calendar + email + Slack (no auto-send)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.mentrix.providers import (
    DraftCitation,
    get_calendar_provider,
    get_email_provider,
    get_slack_provider,
)


def build_meeting_brief(
    db: Session,
    *,
    limit_meetings: int = 5,
    include_email: bool = True,
    include_slack: bool = True,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Compose a pre-meeting brief. Never sends; drafts only via outbound_drafts if requested."""
    cal = get_calendar_provider()
    meetings = cal.upcoming(limit=limit_meetings)
    citations: list[DraftCitation] = []
    email_bits: list[dict[str, Any]] = []
    slack_bits: dict[str, Any] = {}

    if include_email:
        email = get_email_provider().digest(limit=5)
        if email.get("ok"):
            for m in (email.get("messages") or email.get("items") or [])[:5]:
                email_bits.append(
                    {
                        "from": m.get("from") or m.get("address"),
                        "subject": m.get("subject") or m.get("title"),
                    }
                )
                citations.append(
                    DraftCitation(
                        kind="email",
                        ref=str(m.get("id") or m.get("subject") or "")[:200],
                        excerpt=str(m.get("subject") or "")[:200],
                    )
                )

    if include_slack:
        slack_bits = get_slack_provider().digest(limit=10)
        if slack_bits.get("ok"):
            citations.append(
                DraftCitation(
                    kind="slack",
                    ref=str(slack_bits.get("channel") or "general"),
                    excerpt="channel digest",
                )
            )

    for mtg in meetings:
        citations.append(
            DraftCitation(kind="calendar", ref=mtg.id, excerpt=mtg.title[:200])
        )

    lines = [
        f"# Meeting brief — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Upcoming",
    ]
    if not meetings:
        lines.append("_No calendar events (configure MENTRIX_CALENDAR_ICS_URL or MENTRIX_CALENDAR_DEMO=1)._")
    for mtg in meetings:
        lines.append(f"- **{mtg.title}** — {mtg.when or 'time TBD'} (`{mtg.id}`)")
        if mtg.body:
            lines.append(f"  - {mtg.body[:200]}")

    if email_bits:
        lines.append("")
        lines.append("## Related email (recent)")
        for e in email_bits:
            lines.append(f"- {e.get('subject') or '(no subject)'} — {e.get('from') or '?'}")

    if slack_bits.get("ok"):
        lines.append("")
        lines.append(f"## Slack context (#{slack_bits.get('channel')})")
        lines.append("_Digest loaded — see Mentrix board for details._")

    lines.append("")
    lines.append("## Policy")
    lines.append("- No auto-send of email/Slack follow-ups.")
    lines.append("- Recording requires explicit session consent (not started by this brief).")
    lines.append("- Calendar create/update requires approval.")

    body = "\n".join(lines)
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
            for m in meetings
        ],
        "email_context": email_bits,
        "slack_ok": bool(slack_bits.get("ok")),
        "citations": [
            {"kind": c.kind, "ref": c.ref, "excerpt": c.excerpt} for c in citations
        ],
        "board": {
            "type": "markdown",
            "title": "Meeting brief",
            "body": body,
        },
        "spoken_summary": (
            f"{len(meetings)} upcoming meeting(s)."
            if meetings
            else "No upcoming meetings on the calendar."
        ),
        "user_id": user_id,
    }


def draft_followups_from_brief(
    db: Session,
    brief: dict[str, Any],
    *,
    channel: str = "email",
    to: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """Create an outbound draft follow-up from a brief — never sends."""
    from app.services.mentrix.outbound_drafts import create_outbound_draft, serialize_draft

    meetings = brief.get("meetings") or []
    titles = ", ".join(m.get("title") or "" for m in meetings[:3]) or "meetings"
    if channel == "slack":
        draft = create_outbound_draft(
            db,
            channel="slack",
            payload={
                "channel": "general",
                "text": f"Follow-ups from: {titles}\n\n(Draft only — approve to send.)",
            },
            user_id=user_id,
            citations=brief.get("citations") or [],
        )
    else:
        draft = create_outbound_draft(
            db,
            channel="email",
            payload={
                "to": to,
                "subject": f"Follow-up: {titles}"[:200],
                "body": (
                    f"Hi,\n\nFollow-ups from our recent meetings ({titles}).\n\n"
                    "Best regards\n"
                ),
            },
            user_id=user_id,
            citations=brief.get("citations") or [],
        )
    return {
        "ok": True,
        "draft": serialize_draft(draft),
        "needs_send_approval": True,
        "spoken_summary": f"Follow-up draft #{draft.id} ready. Approve to send.",
    }

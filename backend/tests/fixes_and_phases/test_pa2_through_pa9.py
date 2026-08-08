"""PA-2 through PA-9 personal-agent spine tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.adapters.playwright_adapter import execute as pw_execute
from app.services.mentrix.meeting_assistant import build_meeting_brief
from app.services.mentrix.outbound_drafts import (
    create_outbound_draft,
    mark_sent,
    preview_hash,
    serialize_draft,
    verify_approval,
)
from app.services.mentrix.providers import MentrixCalendarProvider, allowlist_permits
from app.services.mentrix.skill_governance import (
    normalize_manifest,
    schedule_grants_from_config,
    schedule_tool_permitted,
    tool_allowed,
    validate_manifest,
)


def test_preview_hash_stable():
    a = preview_hash({"to": "a@b.com", "body": "hi"})
    b = preview_hash({"body": "hi", "to": "a@b.com"})
    assert a == b


def test_verify_approval_hash_and_antiduape(monkeypatch):
    from app.models import OutboundDraft

    payload = {"channel": "general", "text": "hello"}
    ph = preview_hash(payload)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    row = OutboundDraft(
        id=1,
        channel="slack",
        status="draft",
        payload_json={**payload, "_pa3": {"preview_hash": ph, "expires_at": expires}},
    )
    ok, reason = verify_approval(row, expected_hash=ph)
    assert ok and reason == "ok"
    bad, reason2 = verify_approval(row, expected_hash="deadbeef")
    assert not bad and reason2 == "preview_hash_mismatch"
    row.status = "sent"
    ok3, reason3 = verify_approval(row)
    assert not ok3 and reason3 == "already_sent"


def test_password_fill_refused():
    out = pw_execute(
        "fill",
        {"selector": "input[type=password]", "value": "secret"},
        config={},
        enabled=True,
    )
    assert out.get("error") == "password_scrape_forbidden" or out.get("status") in (
        "error",
        "not_configured",
        "disabled",
    )


def test_calendar_demo(monkeypatch):
    monkeypatch.setenv("MENTRIX_CALENDAR_DEMO", "1")
    monkeypatch.delenv("MENTRIX_CALENDAR_ICS_URL", raising=False)
    items = MentrixCalendarProvider().upcoming(limit=3)
    assert len(items) >= 1
    assert items[0].source == "calendar_demo"


def test_meeting_brief_demo(monkeypatch):
    monkeypatch.setenv("MENTRIX_CALENDAR_DEMO", "1")
    db = MagicMock()
    out = build_meeting_brief(db, include_email=False, include_slack=False)
    assert out["ok"] is True
    assert out.get("board", {}).get("type") == "markdown"


def test_skill_manifest_must_prohibit_delete():
    m = normalize_manifest({"allowed_tools": ["navigate"], "approval_points": []})
    errs = validate_manifest(m)
    assert not any(e.startswith("must_prohibit:") for e in errs)
    ok, reason = tool_allowed(m, "desktop_delete")
    assert ok is False


def test_schedule_grants():
    g = schedule_grants_from_config({"grants": {"allowed_tools": ["delivery_status"]}})
    ok, _ = schedule_tool_permitted(g, "delivery_status")
    assert ok is True
    bad, reason = schedule_tool_permitted(g, "slack_send")
    assert bad is False
    assert "not_granted" in reason


def test_allowlist_permits():
    assert allowlist_permits("github.com", ["github.com"]) is True
    assert allowlist_permits("evil.com", ["github.com"]) is False

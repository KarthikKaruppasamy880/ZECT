"""Gap-close coverage: calendar API + unverified click refuse."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.mentrix.companion import _exec_tool


def test_unverified_coordinate_click_refused():
    db = MagicMock()
    out = _exec_tool(db, "computer_click", {"x": 100, "y": 100})
    assert out["ok"] is False
    assert out["error"] == "unverified_coordinate_click"


def test_click_allowed_with_flag():
    db = MagicMock()
    out = _exec_tool(db, "computer_click", {"x": 100, "y": 100, "allow_unverified": True})
    assert out["ok"] is True


def test_calendar_upcoming_demo(monkeypatch):
    monkeypatch.setenv("MENTRIX_CALENDAR_DEMO", "1")
    from app.services.mentrix.providers import get_calendar_provider

    items = get_calendar_provider().upcoming(limit=2)
    assert len(items) >= 1

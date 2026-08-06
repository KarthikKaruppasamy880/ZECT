"""Preferred name + browser allowlist + MCP stubs."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.adapters import gmail_adapter, notion_adapter
from app.services.browser.allowlist import host_allowed
from app.services.mentrix.preferred_name import preferred_name_from_email, resolve_preferred_name
from app.services.mentrix import desktop_bridge as bridge


def test_preferred_name_from_email():
    assert preferred_name_from_email("karthik.karuppasamy@zinnia.com") == "Karthik"
    assert preferred_name_from_email("") == ""


def test_resolve_preferred_name_from_pref():
    db = MagicMock()
    pref = MagicMock()
    pref.communication = {"preferred_name": "Karthik"}
    db.query.return_value.filter.return_value.first.return_value = pref
    assert resolve_preferred_name(db, user_id=1, email="x@y.com") == "Karthik"


def test_browser_allowlist_star(monkeypatch):
    monkeypatch.setenv("MENTRIX_BROWSER_ALLOWLIST", "*")
    ok, _ = host_allowed("https://example.com/path")
    assert ok is True


def test_browser_allowlist_hosts(monkeypatch):
    monkeypatch.setenv("MENTRIX_BROWSER_ALLOWLIST", "example.com,github.com")
    ok, _ = host_allowed("https://docs.github.com")
    assert ok is True
    bad, reason = host_allowed("https://evil.example")
    assert bad is False
    assert "allowlist" in reason.lower() or "not in" in reason.lower()


def test_notion_stub_not_configured(monkeypatch):
    monkeypatch.delenv("NOTION_API_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    out = notion_adapter.execute("search", {"query": "x"}, config={}, enabled=True)
    assert out["status"] == "not_configured"


def test_gmail_fallback_message(monkeypatch):
    monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)
    out = gmail_adapter.execute("send_email", {"to": "a@b.com"}, config={}, enabled=True)
    assert out["status"] == "not_configured"
    assert out.get("fallback") == "email"


def test_desktop_bridge_offline_enqueue():
    bridge._QUEUES.clear()
    bridge._AGENTS.clear()
    out = bridge.enqueue("user@example.com", {"action": "write_note"})
    assert out["ok"] is False
    assert out["error"] == "desktop_offline"


def test_desktop_bridge_online_roundtrip():
    bridge._QUEUES.clear()
    bridge._AGENTS.clear()
    bridge.heartbeat("user@example.com")
    enq = bridge.enqueue("user@example.com", {"action": "write_note"})
    assert enq["ok"] is True
    polled = bridge.poll("user@example.com")
    assert len(polled["items"]) >= 1
    ack = bridge.ack("user@example.com", enq["id"], result={"ok": True})
    assert ack["ok"] is True

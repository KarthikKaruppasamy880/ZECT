"""Mentrix Companion — permission broker + turn intents."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.services.mentrix.companion import run_companion_turn
from app.services.mentrix.org_policy import ensure_companion_rules, export_org_policy, import_org_policy
from app.services.mentrix.permission_broker import check_tool_permission


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_permission_broker_navigate_allowed():
    db = _db()
    ensure_companion_rules(db)
    r = check_tool_permission(db, "navigate", user_confirmed=False)
    assert r["result"] in ("granted", "pending_approval")
    assert r["action"] == "companion_navigate"


def test_permission_broker_slack_send_needs_confirm():
    db = _db()
    ensure_companion_rules(db)
    r = check_tool_permission(db, "slack_send", user_confirmed=False)
    assert r["needs_confirm"] is True or r["result"] == "pending_approval"
    r2 = check_tool_permission(db, "slack_send", user_confirmed=True)
    assert r2["result"] == "granted"


def test_companion_turn_navigate_and_status():
    db = _db()
    ensure_companion_rules(db)
    out = run_companion_turn(db, "Open Lattice and what's my delivery status?")
    assert out["reply"]
    assert out.get("navigate") in ("/lattice", None) or out.get("tools")
    tools = [t["tool"] for t in out.get("tools") or []]
    assert "navigate" in tools or "delivery_status" in tools or out.get("pending_confirmations") is not None


def test_org_policy_export_import():
    db = _db()
    ensure_companion_rules(db)
    pack = export_org_policy(db)
    assert pack["agent"] == "Mentrix"
    assert pack["rules"]
    res = import_org_policy(db, pack, replace=False)
    assert res["imported_rules"] >= 1


def test_companion_send_pending_without_confirm():
    db = _db()
    ensure_companion_rules(db)
    out = run_companion_turn(db, "Slack send a message saying hello")
    pending = out.get("pending_confirmations") or []
    assert any(p["tool"] == "slack_send" for p in pending)
    assert out["avatar_state"] == "needs_permission"


def test_desktop_read_blocks_secrets():
    db = _db()
    from app.services.mentrix.companion import _exec_tool

    blocked = _exec_tool(db, "desktop_read", {"path": "C:/Users/me/.env"})
    assert blocked.get("ok") is False
    assert "blocked" in (blocked.get("error") or "")

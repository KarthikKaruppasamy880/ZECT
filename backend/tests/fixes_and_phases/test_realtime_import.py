"""Smoke: mentrix realtime module must import (syntax + tool registry)."""

from __future__ import annotations


def test_realtime_module_imports():
    from app.services.mentrix import realtime

    assert callable(realtime.run_realtime_tool)
    assert callable(realtime.mint_realtime_session)
    tools = realtime.realtime_tool_schemas()
    names = {t["name"] for t in tools}
    assert "calendar_upcoming" in names
    assert "meeting_brief" in names
    assert "connector_architecture" in names
    assert "slack_digest" in names
    assert "email_digest" in names
    assert "note_add" in names


def test_connector_architecture_exec():
    from app.services.mentrix.companion import _exec_tool

    class _DummyDB:
        def query(self, *_a, **_k):
            raise RuntimeError("unused")

    out = _exec_tool(_DummyDB(), "connector_architecture", {}, project_key="", created_by="test")
    assert out.get("ok") is True
    board = out.get("board") or {}
    extra = out.get("board_extra") or {}
    assert board.get("type") == "markdown"
    assert extra.get("type") == "mermaid"
    assert "MentrixOrchestrator" in (extra.get("body") or "")

"""/api/slack/notify used to always return sent=True with a "Simulated" note
— it never called Slack. Verifies it now routes through the real MCP slack
adapter (execute_tool) and surfaces a real failure instead of faking success
when Slack isn't actually configured/reachable.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.models import SlackConfig
from app.domains.integration.slack_integration import SlackNotification, send_notification
from fastapi import HTTPException
import pytest


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _configured_db():
    db = _session()
    db.add(SlackConfig(bot_token_encrypted="irrelevant", default_channel="#zect", is_active=True))
    db.commit()
    return db


class TestSendNotificationCallsRealAdapter:
    def test_success_calls_execute_tool_and_returns_sent(self, monkeypatch):
        db = _configured_db()
        captured = {}

        def fake_execute_tool(db_, *, server_id, tool_name, arguments):
            captured["server_id"] = server_id
            captured["tool_name"] = tool_name
            captured["arguments"] = arguments
            return {"status": "success", "result": {"ok": True}}

        monkeypatch.setattr("app.services.mcp.hub.execute_tool", fake_execute_tool)

        result = send_notification(SlackNotification(message="hello"), db=db)

        assert result["sent"] is True
        assert captured["server_id"] == "slack"
        assert captured["tool_name"] == "send_message"
        assert captured["arguments"] == {"channel": "#zect", "text": "hello"}
        assert "note" not in result  # no more "Simulated" placeholder text

    def test_not_configured_raises_instead_of_faking_success(self, monkeypatch):
        db = _configured_db()
        monkeypatch.setattr(
            "app.services.mcp.hub.execute_tool",
            lambda db_, **kw: {"status": "error", "result": {"status": "not_configured", "message": "Set SLACK_BOT_TOKEN"}},
        )

        with pytest.raises(HTTPException) as exc_info:
            send_notification(SlackNotification(message="hello"), db=db)

        assert exc_info.value.status_code == 502

    def test_slack_api_error_raises_instead_of_faking_success(self, monkeypatch):
        db = _configured_db()
        monkeypatch.setattr(
            "app.services.mcp.hub.execute_tool",
            lambda db_, **kw: {"status": "error", "result": {"error": "channel_not_found"}},
        )

        with pytest.raises(HTTPException) as exc_info:
            send_notification(SlackNotification(message="hello"), db=db)

        assert exc_info.value.status_code == 502

    def test_no_config_raises_400(self):
        db = _session()

        with pytest.raises(HTTPException) as exc_info:
            send_notification(SlackNotification(message="hello"), db=db)

        assert exc_info.value.status_code == 400

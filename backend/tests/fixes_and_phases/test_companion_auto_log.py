"""Personal-assistant auto-logging — Companion used to only write a note
when the user said a trigger phrase like "remember" or "note that"
(note_add's fast-intent regex). This verifies every completed exchange now
gets logged automatically (text path via _auto_log_exchange inside
iter_companion_events, voice path via the new /companion/log-exchange
endpoint), while incomplete/pending turns are skipped.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.services.mentrix import companion


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestAutoLogExchangeHelper:
    def test_logs_a_completed_exchange(self):
        with patch("app.services.mentrix.notes.add_note") as mock_add:
            companion._auto_log_exchange("what's the weather", "Sunny in Austin.")

        mock_add.assert_called_once()
        text, kwargs = mock_add.call_args.args[0], mock_add.call_args.kwargs
        assert "what's the weather" in text
        assert "Sunny in Austin." in text
        assert kwargs["tags"] == ["mentrix", "auto-log"]

    def test_skips_pending_turns(self):
        with patch("app.services.mentrix.notes.add_note") as mock_add:
            companion._auto_log_exchange("send this to slack", "", pending=True)

        mock_add.assert_not_called()

    def test_skips_empty_message_or_reply(self):
        with patch("app.services.mentrix.notes.add_note") as mock_add:
            companion._auto_log_exchange("", "some reply")
            companion._auto_log_exchange("some message", "")

        mock_add.assert_not_called()

    def test_note_write_failure_never_raises(self):
        with patch("app.services.mentrix.notes.add_note", side_effect=OSError("disk full")):
            companion._auto_log_exchange("hi", "hello")  # must not raise


class TestIterCompanionEventsAutoLogs:
    def test_completed_turn_triggers_auto_log(self, monkeypatch):
        db = _session()
        monkeypatch.setattr(companion, "_merge_intents", lambda message: [])
        monkeypatch.setattr(companion, "build_agent_context", lambda db, **kw: "")
        monkeypatch.setattr(companion, "_fast_tool_reply", lambda *a, **kw: "Delivery status: green.")

        with patch("app.services.mentrix.companion._auto_log_exchange") as mock_log:
            list(companion.iter_companion_events(db, "delivery status"))

        mock_log.assert_called_once()
        call_args = mock_log.call_args.args
        assert call_args[0] == "delivery status"
        assert "Delivery status: green." in call_args[1]

    def test_pending_confirmation_does_not_auto_log_yet(self, monkeypatch):
        db = _session()
        monkeypatch.setattr(
            companion,
            "_merge_intents",
            lambda message: [{"name": "slack_send", "args": {"text": "hi"}}],
        )
        monkeypatch.setattr(companion, "build_agent_context", lambda db, **kw: "")
        monkeypatch.setattr(
            companion,
            "check_tool_permission",
            lambda *a, **kw: {"result": "pending_approval", "needs_confirm": True, "audit_id": 1},
        )

        with patch("app.services.mentrix.companion._auto_log_exchange") as mock_log:
            list(companion.iter_companion_events(db, "send hi to slack"))

        assert mock_log.call_args.kwargs.get("pending") is True or mock_log.call_args.args[-1] is True


class TestLogExchangeEndpoint:
    def test_endpoint_delegates_to_auto_log_exchange(self):
        from app.domains.agent_run.mentrix import LogExchangeRequest, companion_log_exchange

        with patch("app.services.mentrix.companion._auto_log_exchange") as mock_log:
            result = companion_log_exchange(
                LogExchangeRequest(user_message="what's on my calendar", assistant_reply="Nothing scheduled."),
                _user=Mock(user_id=1),
            )

        mock_log.assert_called_once_with("what's on my calendar", "Nothing scheduled.")
        assert result == {"ok": True}

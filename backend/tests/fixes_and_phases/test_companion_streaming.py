"""Companion response timing — the LLM path used to compute the entire reply
first, then fake-stream it as ~4 instantly-fired chunks with no pacing
(explains "text response is too fast" relative to how long the real wait
was). This verifies the LLM path now streams real deltas as they're
generated, and that fixed/already-known replies (pending/denied/fast-tool)
get a paced reveal instead of an instant dump.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.services.mentrix import companion


def _mock_stream_chunks(*texts):
    chunks = []
    for t in texts:
        chunk = Mock()
        chunk.choices = [Mock(delta=Mock(content=t))]
        chunks.append(chunk)
    return chunks


class TestLlmAnswerStream:
    def test_no_api_key_yields_single_fallback_and_stops(self, monkeypatch):
        monkeypatch.setattr(companion, "_ensure_llm_ready", lambda: False)

        result = list(companion._llm_answer_stream("hello"))

        assert len(result) == 1
        assert "ready" in result[0].lower()

    def test_yields_deltas_as_they_arrive(self, monkeypatch):
        monkeypatch.setattr(companion, "_ensure_llm_ready", lambda: True)
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = _mock_stream_chunks("Hel", "lo ", "world")
        monkeypatch.setattr(
            companion, "get_openai_compat_client", lambda timeout=None: mock_client
        )

        result = list(companion._llm_answer_stream("hi"))

        assert result == ["Hel", "lo ", "world"]

    def test_skips_empty_deltas(self, monkeypatch):
        monkeypatch.setattr(companion, "_ensure_llm_ready", lambda: True)
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = _mock_stream_chunks("Hi", None, "", "there")
        monkeypatch.setattr(
            companion, "get_openai_compat_client", lambda timeout=None: mock_client
        )

        result = list(companion._llm_answer_stream("hi"))

        assert result == ["Hi", "there"]

    def test_exception_before_any_delta_yields_fallback(self, monkeypatch):
        monkeypatch.setattr(companion, "_ensure_llm_ready", lambda: True)
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        monkeypatch.setattr(
            companion, "get_openai_compat_client", lambda timeout=None: mock_client
        )

        result = list(companion._llm_answer_stream("hi", context="some context"))

        assert len(result) == 1
        assert "some context" in result[0] or "ready" in result[0].lower()

    def test_exception_after_partial_delta_keeps_what_was_yielded(self, monkeypatch):
        monkeypatch.setattr(companion, "_ensure_llm_ready", lambda: True)

        def broken_stream():
            yield _mock_stream_chunks("partial")[0]
            raise RuntimeError("connection dropped")

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = broken_stream()
        monkeypatch.setattr(
            companion, "get_openai_compat_client", lambda timeout=None: mock_client
        )

        result = list(companion._llm_answer_stream("hi"))

        assert result == ["partial"]  # no duplicate fallback appended after real content


class TestIterCompanionEventsStreamingPath:
    def test_llm_path_emits_token_per_delta_not_four_fixed_chunks(self, monkeypatch, db_session=None):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        import app.models  # noqa: F401
        from app.infrastructure.database import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()

        monkeypatch.setattr(companion, "_merge_intents", lambda message: [])
        monkeypatch.setattr(companion, "build_agent_context", lambda db, **kw: "")
        monkeypatch.setattr(companion, "_fast_tool_reply", lambda *a, **kw: None)
        monkeypatch.setattr(
            companion,
            "_llm_answer_stream",
            lambda q, c="", preferred_name="": iter(["Sun", "ny ", "in Austin."]),
        )
        monkeypatch.setattr(companion, "time", __import__("time"))  # keep real time.time() for latency_ms

        events = list(companion.iter_companion_events(db, "what's the weather"))

        token_events = [e for e in events if e["event"] == "token"]
        assert [t["data"]["text"] for t in token_events] == ["Sun", "ny ", "in Austin."]
        done = [e for e in events if e["event"] == "done"][0]
        assert done["data"]["reply"] == "Sunny in Austin."

    def test_fast_tool_reply_still_pages_through_token_events(self, monkeypatch):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from unittest.mock import Mock

        import app.models  # noqa: F401
        from app.infrastructure.database import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()

        monkeypatch.setattr(companion, "_merge_intents", lambda message: [])
        monkeypatch.setattr(companion, "build_agent_context", lambda db, **kw: "")
        monkeypatch.setattr(companion, "_fast_tool_reply", lambda *a, **kw: "Delivery status: green.")
        stream_spy = Mock()
        monkeypatch.setattr(companion, "_llm_answer_stream", stream_spy)

        events = list(companion.iter_companion_events(db, "delivery status"))

        stream_spy.assert_not_called()
        token_events = [e for e in events if e["event"] == "token"]
        assert "".join(t["data"]["text"] for t in token_events) == "Delivery status: green."
        assert len(token_events) >= 1

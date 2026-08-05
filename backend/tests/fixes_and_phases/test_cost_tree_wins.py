"""LLM Cost Tree — 3 low-effort levers implemented this round:
#8 structured JSON output (response_format json_schema, strict), #11
Anthropic prompt-prefix caching (covered in test_anthropic_client.py), and
#10 exact-match response caching for the review engine (covered here,
alongside the response_cache helper itself).
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register LLMResponseCache
from app.infrastructure.database import Base
from app.services.llm.response_cache import cache_key_for, get_cached, store_cached


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestResponseCacheHelper:
    def test_same_inputs_produce_same_key(self):
        assert cache_key_for("review_snippet", "python", "x = 1") == cache_key_for("review_snippet", "python", "x = 1")

    def test_different_inputs_produce_different_keys(self):
        assert cache_key_for("review_snippet", "python", "x = 1") != cache_key_for("review_snippet", "python", "x = 2")

    def test_get_cached_returns_none_when_absent(self):
        db = _session()
        assert get_cached(db, "nonexistent") is None

    def test_store_then_get_roundtrips(self):
        db = _session()
        store_cached(db, "key1", {"summary": "ok", "quality_score": 90}, model="gpt-4o-mini", tokens_used=100)

        result = get_cached(db, "key1")

        assert result == {"summary": "ok", "quality_score": 90}

    def test_store_upserts_existing_key(self):
        db = _session()
        store_cached(db, "key1", {"summary": "v1"}, tokens_used=100)
        store_cached(db, "key1", {"summary": "v2"}, tokens_used=50)

        assert get_cached(db, "key1") == {"summary": "v2"}

    def test_get_cached_returns_none_for_db_error(self):
        db = Mock()
        db.query.side_effect = RuntimeError("db down")
        assert get_cached(db, "key1") is None

    def test_store_cached_swallows_db_error(self):
        db = Mock()
        db.query.side_effect = RuntimeError("db down")
        store_cached(db, "key1", {"summary": "ok"})  # must not raise
        db.rollback.assert_called_once()

    def test_none_db_is_always_a_miss_and_noop_store(self):
        assert get_cached(None, "key1") is None
        store_cached(None, "key1", {"summary": "ok"})  # must not raise


class TestReviewCodeSnippetCaching:
    def test_cache_hit_skips_api_call(self, monkeypatch):
        from app.review_service import review_code_snippet

        db = _session()
        cache_key = cache_key_for("review_snippet", "python", "x = 1")
        store_cached(db, cache_key, {"summary": "cached review", "quality_score": 80, "findings": []}, tokens_used=0)

        client_called = []
        monkeypatch.setattr("app.review_service._get_client", lambda: client_called.append(True))

        result = review_code_snippet(code="x = 1", language="python", db=db)

        assert not client_called, "cached path must not call the OpenAI client"
        assert result["summary"] == "cached review"
        assert result["review_session_id"] is not None

    def test_cache_miss_calls_api_and_stores(self, monkeypatch):
        from app.review_service import review_code_snippet

        db = _session()
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(content='{"summary": "fresh review", "quality_score": 70, "findings": []}'))]
        mock_resp.usage = Mock(total_tokens=42, prompt_tokens=30, completion_tokens=12)
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_resp
        monkeypatch.setattr("app.review_service._get_client", lambda: mock_client)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = review_code_snippet(code="y = 2", language="python", db=db)

        assert result["summary"] == "fresh review"
        cache_key = cache_key_for("review_snippet", "python", "y = 2")
        assert get_cached(db, cache_key)["summary"] == "fresh review"

    def test_different_code_is_a_different_cache_entry(self, monkeypatch):
        from app.review_service import review_code_snippet

        db = _session()
        store_cached(db, cache_key_for("review_snippet", "python", "x = 1"), {"summary": "cached for x", "findings": []})

        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(content='{"summary": "fresh for y", "findings": []}'))]
        mock_resp.usage = Mock(total_tokens=10, prompt_tokens=5, completion_tokens=5)
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_resp
        monkeypatch.setattr("app.review_service._get_client", lambda: mock_client)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = review_code_snippet(code="y = 2", language="python", db=db)

        assert result["summary"] == "fresh for y"
        mock_client.chat.completions.create.assert_called_once()


class TestReviewStructuredOutputSchema:
    def test_review_calls_use_strict_json_schema_response_format(self):
        from app.review_service import REVIEW_RESPONSE_FORMAT

        assert REVIEW_RESPONSE_FORMAT["type"] == "json_schema"
        assert REVIEW_RESPONSE_FORMAT["json_schema"]["strict"] is True
        schema = REVIEW_RESPONSE_FORMAT["json_schema"]["schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == {
            "summary", "quality_score", "total_issues", "categories", "findings", "strengths", "recommendations",
        }

    def test_finding_schema_enumerates_severity_and_category(self):
        from app.review_service import REVIEW_RESPONSE_FORMAT

        finding_schema = REVIEW_RESPONSE_FORMAT["json_schema"]["schema"]["properties"]["findings"]["items"]
        assert set(finding_schema["properties"]["severity"]["enum"]) == {"critical", "high", "medium", "low", "info"}
        assert finding_schema["additionalProperties"] is False

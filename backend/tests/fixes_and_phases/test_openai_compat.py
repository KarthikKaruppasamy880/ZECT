"""Tests for Mentrix OpenAI-compatible LLM factory."""

import os
from unittest.mock import MagicMock, patch

from app.adapters.llm.openai_compat import (
    get_openai_compat_client,
    mentrix_local_llm_configured,
    mentrix_llm_chat_model,
    probe_mentrix_local_llm,
)


def test_mentrix_local_configured_when_base_url_set(monkeypatch):
    monkeypatch.setenv("ZECT_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    assert mentrix_local_llm_configured() is True


def test_mentrix_local_not_configured_without_base(monkeypatch):
    monkeypatch.delenv("ZECT_LLM_BASE_URL", raising=False)
    assert mentrix_local_llm_configured() is False


def test_chat_model_prefers_zect_env(monkeypatch):
    monkeypatch.setenv("ZECT_LLM_CHAT_MODEL", "qwen2.5:7b")
    monkeypatch.delenv("MENTRIX_COMPANION_MODEL", raising=False)
    assert mentrix_llm_chat_model() == "qwen2.5:7b"


def test_get_client_uses_base_url(monkeypatch):
    monkeypatch.setenv("ZECT_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("ZECT_LLM_API_KEY", "local")
    with patch("app.adapters.llm.openai_compat.OpenAI") as mock_openai:
        mock_openai.return_value = MagicMock()
        get_openai_compat_client()
        kwargs = mock_openai.call_args.kwargs
        assert kwargs["base_url"] == "http://127.0.0.1:11434/v1"
        assert kwargs["api_key"] == "local"


def test_probe_offline_when_unreachable(monkeypatch):
    monkeypatch.setenv("ZECT_LLM_BASE_URL", "http://127.0.0.1:1/v1")
    result = probe_mentrix_local_llm(timeout=0.2)
    assert result["configured"] is True
    assert result["online"] is False
    assert "Mentrix Local LLM" in result["label"]


def test_progressive_skill_inject_without_trigger(monkeypatch):
    from app.services.mentrix.companion import build_agent_context

    class FakeSkill:
        id = 1
        name = "Incident Pack"
        description = "Short tip"
        manifest = {
            "triggers": ["incident"],
            "template": "FULL_BODY_SHOULD_NOT_APPEAR",
        }

    class FakeQuery:
        def filter(self, *_a, **_k):
            return self

        def first(self):
            return FakeSkill()

    class FakeDb:
        def query(self, *_a, **_k):
            return FakeQuery()

    text = build_agent_context(FakeDb(), skill_id=1, query="hello weather")
    assert "Incident Pack" in text
    assert "FULL_BODY_SHOULD_NOT_APPEAR" not in text


def test_progressive_skill_inject_with_trigger():
    from app.services.mentrix.companion import build_agent_context

    class FakeSkill:
        id = 1
        name = "Incident Pack"
        description = "Short tip"
        manifest = {
            "triggers": ["incident"],
            "template": "FULL_BODY_LOADED",
        }

    class FakeQuery:
        def filter(self, *_a, **_k):
            return self

        def first(self):
            return FakeSkill()

    class FakeDb:
        def query(self, *_a, **_k):
            return FakeQuery()

    text = build_agent_context(FakeDb(), skill_id=1, query="open the incident runbook")
    assert "FULL_BODY_LOADED" in text

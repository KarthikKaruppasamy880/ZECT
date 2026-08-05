"""Unit tests for the real Anthropic client shim and Build's model routing.

Mocks anthropic.Anthropic entirely — no real API calls. The point of these
tests is the shape-adaptation logic (system message extraction, stop_reason
mapping, token field renaming) that complete_with_continuations depends on,
since that's exactly what the previous broken model_selection.py attempt got
wrong by treating Anthropic as OpenAI-compatible.
"""

from unittest.mock import Mock, patch

import pytest

from app.adapters.llm.anthropic_client import (
    DEFAULT_MODEL,
    _split_system,
    anthropic_available,
    create_fn,
    resolve_generation_model,
)


class TestAnthropicAvailability:
    def test_unavailable_without_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert anthropic_available() is False

    def test_available_with_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        assert anthropic_available() is True

    def test_available_false_for_blank_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
        assert anthropic_available() is False


class TestSplitSystem:
    """Anthropic takes system prompt as a top-level param, not a role="system"
    message — this is the exact thing the old broken attempt got wrong."""

    def test_extracts_system_message(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        system, rest = _split_system(messages)
        assert system == "You are helpful."
        assert rest == [{"role": "user", "content": "Hello"}]

    def test_no_system_message_returns_empty_string(self):
        messages = [{"role": "user", "content": "Hello"}]
        system, rest = _split_system(messages)
        assert system == ""
        assert rest == messages

    def test_only_first_system_message_extracted(self):
        messages = [
            {"role": "system", "content": "First"},
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "Second (should stay in rest, not silently dropped)"},
        ]
        system, rest = _split_system(messages)
        assert system == "First"
        assert len(rest) == 2  # the second "system" message isn't lost


class TestCreateFnShape:
    """The shim response must satisfy exactly what complete_with_continuations reads:
    .choices[0].message.content, .choices[0].finish_reason, .usage.*_tokens"""

    def _mock_anthropic_response(self, text="print('hi')", stop_reason="end_turn", input_tokens=10, output_tokens=5):
        block = Mock()
        block.type = "text"
        block.text = text
        resp = Mock()
        resp.content = [block]
        resp.stop_reason = stop_reason
        resp.usage = Mock(input_tokens=input_tokens, output_tokens=output_tokens)
        return resp

    def test_maps_content_and_token_fields(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        mock_client = Mock()
        mock_client.messages.create.return_value = self._mock_anthropic_response()

        with patch("app.adapters.llm.anthropic_client._get_client", return_value=mock_client):
            resp = create_fn(messages=[{"role": "user", "content": "write hello world"}])

        assert resp.choices[0].message.content == "print('hi')"
        assert resp.usage.prompt_tokens == 10
        assert resp.usage.completion_tokens == 5
        assert resp.usage.total_tokens == 15

    def test_max_tokens_stop_reason_maps_to_length(self, monkeypatch):
        """This is the mapping that makes complete_with_continuations's
        truncation-continuation loop work unchanged for Anthropic."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        mock_client = Mock()
        mock_client.messages.create.return_value = self._mock_anthropic_response(stop_reason="max_tokens")

        with patch("app.adapters.llm.anthropic_client._get_client", return_value=mock_client):
            resp = create_fn(messages=[{"role": "user", "content": "x"}])

        assert resp.choices[0].finish_reason == "length"

    def test_end_turn_maps_to_stop(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        mock_client = Mock()
        mock_client.messages.create.return_value = self._mock_anthropic_response(stop_reason="end_turn")

        with patch("app.adapters.llm.anthropic_client._get_client", return_value=mock_client):
            resp = create_fn(messages=[{"role": "user", "content": "x"}])

        assert resp.choices[0].finish_reason == "stop"

    def test_system_message_passed_as_top_level_param_not_in_messages(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        mock_client = Mock()
        mock_client.messages.create.return_value = self._mock_anthropic_response()

        with patch("app.adapters.llm.anthropic_client._get_client", return_value=mock_client):
            create_fn(messages=[
                {"role": "system", "content": "You are a build agent."},
                {"role": "user", "content": "generate code"},
            ])

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == [
            {"type": "text", "text": "You are a build agent.", "cache_control": {"type": "ephemeral"}}
        ]
        assert call_kwargs["messages"] == [{"role": "user", "content": "generate code"}]

    def test_system_prompt_marked_cacheable(self, monkeypatch):
        """Cost-tree lever #11 — the same system prompt is sent on every
        Build/review call; marking it cacheable avoids reprocessing it fresh
        each time within Anthropic's cache TTL."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        mock_client = Mock()
        mock_client.messages.create.return_value = self._mock_anthropic_response()

        with patch("app.adapters.llm.anthropic_client._get_client", return_value=mock_client):
            create_fn(messages=[
                {"role": "system", "content": "You are ZECT Build Agent."},
                {"role": "user", "content": "generate code"},
            ])

        system_param = mock_client.messages.create.call_args.kwargs["system"]
        assert system_param[0]["cache_control"] == {"type": "ephemeral"}

    def test_no_system_message_passes_none(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        mock_client = Mock()
        mock_client.messages.create.return_value = self._mock_anthropic_response()

        with patch("app.adapters.llm.anthropic_client._get_client", return_value=mock_client):
            create_fn(messages=[{"role": "user", "content": "generate code"}])

        assert mock_client.messages.create.call_args.kwargs["system"] is None

    def test_multiple_text_blocks_are_concatenated(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        block1, block2 = Mock(), Mock()
        block1.type, block1.text = "text", "hello "
        block2.type, block2.text = "text", "world"
        resp = Mock(content=[block1, block2], stop_reason="end_turn",
                    usage=Mock(input_tokens=1, output_tokens=1))
        mock_client = Mock()
        mock_client.messages.create.return_value = resp

        with patch("app.adapters.llm.anthropic_client._get_client", return_value=mock_client):
            result = create_fn(messages=[{"role": "user", "content": "x"}])

        assert result.choices[0].message.content == "hello world"

    def test_default_model_is_claude_sonnet_5(self):
        assert DEFAULT_MODEL == "claude-sonnet-5"


class TestBuildRoutingUsesAnthropicWhenConfigured:
    """Integration: build_phase_svc._generate_core picks Claude when
    ANTHROPIC_API_KEY is set, and OpenAI when it isn't — both paths, no crash."""

    def test_routes_to_anthropic_when_key_present(self, monkeypatch):
        from app.services.phases import build_phase_svc
        from unittest.mock import Mock as M
        from sqlalchemy.orm import Session

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=6, user_id=None: [],
        )
        monkeypatch.setattr(
            "app.routers.llm._build_repo_context",
            lambda db, repo_id, max_chars=4000: "",
        )
        monkeypatch.setattr("app.services.context_store.load", lambda db, user_id, page, keys=None: {})
        captured = {}

        def fake_complete(client, messages, **kwargs):
            captured["model"] = kwargs.get("model")
            captured["create_fn_is_anthropic"] = kwargs.get("create_fn") is not None
            return {"content": "FILE_PATH: x.py\nLANGUAGE: python\nEXPLANATION: ok\n```python\npass\n```",
                    "tokens_used": 3, "prompt_tokens": 2, "completion_tokens": 1,
                    "finish_reason": "stop", "structure_ok": True}

        monkeypatch.setattr("app.services.quality.truncation.complete_with_continuations", fake_complete)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        class Req:
            plan_step = "add feature"
            project_context = None
            tech_stack = ""
            repo_id = None
            file_path = "x.py"
            write_to_repo = False

        result = build_phase_svc._generate_core(Req(), db=M(spec=Session), workspace="")

        assert captured["model"] == "claude-sonnet-5"
        assert captured["create_fn_is_anthropic"] is True
        assert result["model"] == "claude-sonnet-5"

    def test_routes_to_openai_when_no_anthropic_key(self, monkeypatch):
        from app.services.phases import build_phase_svc
        from unittest.mock import Mock as M
        from sqlalchemy.orm import Session

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=6, user_id=None: [],
        )
        monkeypatch.setattr("app.services.context_store.load", lambda db, user_id, page, keys=None: {})
        captured = {}

        def fake_complete(client, messages, **kwargs):
            captured["model"] = kwargs.get("model")
            captured["create_fn"] = kwargs.get("create_fn")
            return {"content": "FILE_PATH: x.py\nLANGUAGE: python\nEXPLANATION: ok\n```python\npass\n```",
                    "tokens_used": 3, "prompt_tokens": 2, "completion_tokens": 1,
                    "finish_reason": "stop", "structure_ok": True}

        monkeypatch.setattr("app.services.quality.truncation.complete_with_continuations", fake_complete)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        class Req:
            plan_step = "add feature"
            project_context = None
            tech_stack = ""
            repo_id = None
            file_path = "x.py"
            write_to_repo = False

        result = build_phase_svc._generate_core(Req(), db=M(spec=Session), workspace="")

        assert captured["model"] == "gpt-4o-mini"
        assert captured["create_fn"] is None
        assert result["model"] == "gpt-4o-mini"


class TestResolveGenerationModel:
    """Build/HLD/Bugfix all called the same 3-line use_anthropic/model_name
    pattern independently — centralized here, plus the new CODEGEN_MODEL
    override (e.g. to force gpt-5.4) that none of them had before."""

    def test_prefers_anthropic_when_configured(self, monkeypatch):
        monkeypatch.delenv("CODEGEN_MODEL", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        use_anthropic, model_name = resolve_generation_model()

        assert use_anthropic is True
        assert model_name == "claude-sonnet-5"

    def test_falls_back_to_openai_default_without_anthropic_key(self, monkeypatch):
        monkeypatch.delenv("CODEGEN_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        use_anthropic, model_name = resolve_generation_model()

        assert use_anthropic is False
        assert model_name == "gpt-4o-mini"

    def test_custom_default_openai_model_respected(self, monkeypatch):
        monkeypatch.delenv("CODEGEN_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        _, model_name = resolve_generation_model(default_openai_model="gpt-4o")

        assert model_name == "gpt-4o"

    def test_codegen_model_override_forces_openai_model_even_with_anthropic_key(self, monkeypatch):
        monkeypatch.setenv("CODEGEN_MODEL", "gpt-5.4")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        use_anthropic, model_name = resolve_generation_model()

        assert use_anthropic is False
        assert model_name == "gpt-5.4"

    def test_codegen_model_override_of_a_claude_model_routes_to_anthropic(self, monkeypatch):
        monkeypatch.setenv("CODEGEN_MODEL", "claude-3-haiku")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        use_anthropic, model_name = resolve_generation_model()

        assert use_anthropic is True
        assert model_name == "claude-3-haiku"

    def test_blank_codegen_model_env_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("CODEGEN_MODEL", "   ")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        use_anthropic, model_name = resolve_generation_model()

        assert use_anthropic is False
        assert model_name == "gpt-4o-mini"


class TestModelSelectionAnthropicStatus:
    """model_selection.py's /status previously reported anthropic_configured=True
    whenever an OpenAI key existed, even with zero Anthropic key — a real bug."""

    def test_anthropic_not_falsely_reported_configured(self, monkeypatch):
        from app.routers.model_selection import get_model_status

        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-only")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        status = get_model_status()
        assert status["openai_configured"] is True
        assert status["anthropic_configured"] is False
        assert "anthropic" not in status["available_providers"]

    def test_anthropic_configured_when_key_present(self, monkeypatch):
        from app.routers.model_selection import get_model_status

        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")

        status = get_model_status()
        assert status["anthropic_configured"] is True
        assert "anthropic" in status["available_providers"]

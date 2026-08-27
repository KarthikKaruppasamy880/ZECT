"""AgentModelAdapter (V2 closure §13).

Previously the coding-agent tool loop called client.chat.completions.create
directly against whatever openai_compat.py's client pointed at -- so
selecting "Claude 3.5 Sonnet" in the Developer Workspace model dropdown
(a real, pre-existing UI option) would silently send that model NAME to
OpenAI's API (which has no such model) instead of actually routing to
Anthropic, or would just fail with an opaque SDK error depending on the
gateway. There was no real provider abstraction, no truthful "unavailable"
signal, and no USER_SELECTED/AUTO_ROUTED/POLICY_PINNED/LOCAL_ONLY concept.

These tests prove: (1) routing picks the right provider from the model name
and never silently substitutes a different one when that provider isn't
configured, and (2) the Anthropic adapter genuinely round-trips tool calls
through the SAME native coding-agent runtime OpenAI already uses -- not a
separate, disconnected code path.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.adapters.llm.agent_model_adapter import (
    AUTO_ROUTED,
    LOCAL_ONLY,
    POLICY_PINNED,
    USER_SELECTED,
    AnthropicAgentAdapter,
    ModelProviderError,
    OpenAICompatAdapter,
    _to_anthropic_messages,
    get_agent_model_adapter,
)


class TestRoutingNeverSilentlySubstitutes:
    def test_openai_model_with_key_configured_resolves_to_openai_adapter(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        adapter, model = get_agent_model_adapter("gpt-4o-mini", mode=USER_SELECTED)
        assert isinstance(adapter, OpenAICompatAdapter)
        assert model == "gpt-4o-mini"

    def test_claude_model_without_anthropic_key_raises_not_silently_falls_back_to_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ModelProviderError) as exc:
            get_agent_model_adapter("claude-3.5-sonnet", mode=USER_SELECTED)
        assert exc.value.reason == "anthropic_not_configured"
        assert exc.value.requested_provider == "anthropic"

    def test_claude_model_with_anthropic_key_resolves_to_anthropic_adapter(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
        adapter, model = get_agent_model_adapter("claude-3-haiku", mode=AUTO_ROUTED)
        assert isinstance(adapter, AnthropicAgentAdapter)
        assert model == "claude-3-haiku"

    def test_local_only_mode_refuses_cloud_even_if_configured(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        monkeypatch.delenv("MENTRIX_LLM_BASE_URL", raising=False)
        with pytest.raises(ModelProviderError) as exc:
            get_agent_model_adapter("gpt-4o-mini", mode=LOCAL_ONLY)
        assert "local" in exc.value.reason

    def test_policy_pinned_overrides_the_requested_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        monkeypatch.setenv("ZECT_AGENT_MODEL_PIN", "gpt-4o")
        _adapter, model = get_agent_model_adapter("gpt-4o-mini", mode=POLICY_PINNED)
        assert model == "gpt-4o"


class TestAnthropicMessageTranslation:
    def test_tool_call_and_result_round_trip_into_anthropic_blocks(self):
        openai_history = [
            {"role": "system", "content": "sys prompt"},
            {"role": "user", "content": "do the thing"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "call1", "type": "function", "function": {"name": "read_file", "arguments": '{"path":"a.py"}'}}
                ],
            },
            {"role": "tool", "tool_call_id": "call1", "content": '{"ok": true, "content": "x=1"}'},
        ]
        system, anthropic_messages = _to_anthropic_messages(openai_history)
        assert system == "sys prompt"
        assert anthropic_messages[0] == {"role": "user", "content": "do the thing"}
        assistant_block = anthropic_messages[1]
        assert assistant_block["role"] == "assistant"
        tool_use = next(b for b in assistant_block["content"] if b["type"] == "tool_use")
        assert tool_use["id"] == "call1"
        assert tool_use["name"] == "read_file"
        assert tool_use["input"] == {"path": "a.py"}
        result_block = anthropic_messages[2]
        assert result_block["role"] == "user"
        assert result_block["content"][0]["type"] == "tool_result"
        assert result_block["content"][0]["tool_use_id"] == "call1"


class _FakeAnthropicTextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAnthropicToolUseBlock:
    type = "tool_use"

    def __init__(self, id_: str, name: str, input_: dict) -> None:
        self.id = id_
        self.name = name
        self.input = input_


class _FakeAnthropicResponse:
    def __init__(self, content, stop_reason="tool_use", input_tokens=10, output_tokens=5):
        self.content = content
        self.stop_reason = stop_reason
        self.usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)


class TestAnthropicAdapterCreate:
    def test_create_translates_a_real_tool_call_response(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")

        captured = {}

        class _FakeMessages:
            def create(self, **kwargs):
                captured.update(kwargs)
                return _FakeAnthropicResponse(
                    content=[
                        _FakeAnthropicTextBlock("thinking..."),
                        _FakeAnthropicToolUseBlock("call1", "write_file", {"path": "a.py", "content": "x=1\n"}),
                    ]
                )

        class _FakeAnthropic:
            def __init__(self, api_key: str) -> None:
                self.messages = _FakeMessages()

        import app.adapters.llm.agent_model_adapter as mod

        monkeypatch.setattr("anthropic.Anthropic", _FakeAnthropic, raising=False)
        import sys

        sys.modules.setdefault("anthropic", SimpleNamespace(Anthropic=_FakeAnthropic))
        monkeypatch.setattr(sys.modules["anthropic"], "Anthropic", _FakeAnthropic)

        adapter = mod.AnthropicAgentAdapter()
        resp = adapter.create(
            model="claude-3-haiku",
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "write a file"},
            ],
            tools=[{"type": "function", "function": {"name": "write_file", "description": "", "parameters": {}}}],
            tool_choice="auto",
            temperature=0.2,
            max_tokens=1000,
        )

        assert captured["system"] == "sys"
        assert captured["tools"][0]["name"] == "write_file"
        msg = resp.choices[0].message
        assert msg.content == "thinking..."
        assert len(msg.tool_calls) == 1
        tc = msg.tool_calls[0]
        assert tc.id == "call1"
        assert tc.function.name == "write_file"
        assert json.loads(tc.function.arguments) == {"path": "a.py", "content": "x=1\n"}
        assert resp.choices[0].finish_reason == "tool_calls"
        assert resp.usage.prompt_tokens == 10
        assert resp.usage.completion_tokens == 5


class TestNativeRuntimeThroughAnthropic:
    def test_role_restricted_run_completes_through_the_anthropic_adapter(self, tmp_path, monkeypatch):
        """Same proof PR #196 established for OpenAI (an Explore-role write_file
        attempt is refused by the runtime) -- now run through Anthropic, to show
        it is genuinely the same harness/tool-restriction path, not a second one."""
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "README.md").write_text("hi\n", encoding="utf-8")
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")

        responses = [
            _FakeAnthropicResponse(
                content=[_FakeAnthropicToolUseBlock("call1", "write_file", {"path": "evil.py", "content": "x=1"})]
            ),
            _FakeAnthropicResponse(content=[_FakeAnthropicTextBlock("Done exploring.")], stop_reason="end_turn"),
        ]

        class _FakeMessages:
            def create(self, **_kwargs):
                return responses.pop(0)

        class _FakeAnthropic:
            def __init__(self, api_key: str) -> None:
                self.messages = _FakeMessages()

        import sys

        sys.modules.setdefault("anthropic", SimpleNamespace(Anthropic=_FakeAnthropic))
        monkeypatch.setattr(sys.modules["anthropic"], "Anthropic", _FakeAnthropic)

        from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime
        from app.services.coding_engine.mentrix_lead import ROLE_EXPLORE, ROLE_TOOL_ALLOWLISTS

        rt = MentrixNativeCodingRuntime()
        run_id = rt.start_run(
            "Explore this repo",
            workspace=str(ws),
            model="claude-3-haiku",
            role=ROLE_EXPLORE,
            allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_EXPLORE],
            max_steps=4,
        )
        summary = rt.wait_until_done(run_id, timeout_s=10)

        assert summary["status"] == "completed"
        assert summary["files_written"] == []
        assert not (ws / "evil.py").exists()
        tool_end = [e for e in summary["events"] if e["event"] == "tool_end" and e["data"].get("tool") == "write_file"]
        assert tool_end and tool_end[0]["data"]["ok"] is False

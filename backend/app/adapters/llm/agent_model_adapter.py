"""AgentModelAdapter — pluggable provider abstraction for the coding-agent
TOOL-CALLING loop specifically (distinct from anthropic_client.py's simpler
create_fn shim, which has no tool-calling support and is used only by the
one-shot Build/HLD/Bugfix text-generation call sites).

Every provider's create() returns an OpenAI-ChatCompletion-shaped
AdapterResponse (choices[0].message.content / .tool_calls, each tool call
carrying .id/.function.name/.function.arguments), so
coding_engine_mentrix.py's _agent_loop needs no provider-specific branching
beyond picking which adapter to call.

No silent provider substitution: get_agent_model_adapter() raises
ModelProviderError with a specific reason when the requested/routed model
isn't actually available, rather than quietly falling back to a different
model than what was asked for.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

USER_SELECTED = "user_selected"
AUTO_ROUTED = "auto_routed"
POLICY_PINNED = "policy_pinned"
LOCAL_ONLY = "local_only"
VALID_MODES = frozenset({USER_SELECTED, AUTO_ROUTED, POLICY_PINNED, LOCAL_ONLY})

_ANTHROPIC_STOP_REASON_MAP = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "tool_use": "tool_calls",
}


class ModelProviderError(Exception):
    """Raised instead of silently substituting a provider/model."""

    def __init__(self, reason: str, *, requested_model: str = "", requested_provider: str = ""):
        self.reason = reason
        self.requested_model = requested_model
        self.requested_provider = requested_provider
        super().__init__(reason)


@dataclass
class AdapterFunctionCall:
    name: str
    arguments: str


@dataclass
class AdapterToolCall:
    id: str
    function: AdapterFunctionCall
    type: str = "function"


@dataclass
class AdapterMessage:
    content: str | None
    tool_calls: list[AdapterToolCall] = field(default_factory=list)


@dataclass
class AdapterChoice:
    message: AdapterMessage
    finish_reason: str = "stop"


@dataclass
class AdapterUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class AdapterResponse:
    choices: list[AdapterChoice]
    model: str = ""
    provider: str = ""
    usage: AdapterUsage = field(default_factory=AdapterUsage)


class AgentModelAdapter(Protocol):
    provider_name: str

    def available(self) -> bool: ...

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> AdapterResponse: ...


class OpenAICompatAdapter:
    """Pass-through to the existing OpenAI-compatible gateway (cloud OpenAI
    or a Mentrix Local LLM base URL) -- the default, already-proven path.
    Normalizes the real SDK response into AdapterResponse for a uniform
    caller, but changes no behavior versus calling the SDK directly.
    """

    provider_name = "openai_compat"

    def available(self) -> bool:
        from app.adapters.llm.openai_compat import openai_compat_available

        return openai_compat_available()

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> AdapterResponse:
        from app.adapters.llm.openai_compat import get_openai_compat_client

        client = get_openai_compat_client(timeout=90.0)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        tool_calls = [
            AdapterToolCall(
                id=tc.id,
                function=AdapterFunctionCall(name=tc.function.name, arguments=tc.function.arguments or "{}"),
            )
            for tc in (getattr(msg, "tool_calls", None) or [])
        ]
        usage = getattr(resp, "usage", None)
        return AdapterResponse(
            choices=[
                AdapterChoice(
                    message=AdapterMessage(content=msg.content, tool_calls=tool_calls),
                    finish_reason=str(getattr(resp.choices[0], "finish_reason", "") or "stop"),
                )
            ],
            model=model,
            provider=self.provider_name,
            usage=AdapterUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
            ),
        )


def _split_system(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    system = ""
    rest: list[dict[str, Any]] = []
    for m in messages:
        if m.get("role") == "system" and not system:
            system = str(m.get("content") or "")
        else:
            rest.append(m)
    return system, rest


def _to_anthropic_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Translate the OpenAI-shaped conversation coding_engine_mentrix.py
    builds (assistant.tool_calls / role="tool" results) into Anthropic's
    content-block format, every call -- the shared `history` list the loop
    mutates always stays in OpenAI shape, so this can't be a one-time setup
    step."""
    system, rest = _split_system(messages)
    out: list[dict[str, Any]] = []
    for m in rest:
        role = m.get("role")
        if role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.get("tool_call_id"),
                            "content": str(m.get("content") or ""),
                        }
                    ],
                }
            )
            continue
        if role == "assistant":
            content: list[dict[str, Any]] = []
            if m.get("content"):
                content.append({"type": "text", "text": str(m["content"])})
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                try:
                    tool_input = json.loads(fn.get("arguments") or "{}")
                except (TypeError, ValueError):
                    tool_input = {}
                content.append(
                    {"type": "tool_use", "id": tc.get("id"), "name": fn.get("name"), "input": tool_input}
                )
            out.append({"role": "assistant", "content": content or [{"type": "text", "text": ""}]})
            continue
        out.append({"role": "user" if role != "assistant" else "assistant", "content": str(m.get("content") or "")})
    return system, out


def _to_anthropic_tools(tool_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for t in tool_specs:
        fn = t.get("function") or {}
        out.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description") or "",
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return out


class AnthropicAgentAdapter:
    """Real Anthropic provider for the coding-agent tool loop -- distinct
    from anthropic_client.py's create_fn, which has no tool-calling support.
    Translates ZECT's OpenAI-shaped tool specs and conversation history to
    and from Anthropic's shape so the loop itself needs no provider branch.
    """

    provider_name = "anthropic"

    def available(self) -> bool:
        from app.adapters.llm.anthropic_client import anthropic_available

        return anthropic_available()

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> AdapterResponse:
        from anthropic import Anthropic

        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise ModelProviderError("anthropic_not_configured", requested_provider=self.provider_name)
        client = Anthropic(api_key=key)

        system, anthropic_messages = _to_anthropic_messages(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = _to_anthropic_tools(tools)

        resp = client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[AdapterToolCall] = []
        for block in resp.content:
            kind = getattr(block, "type", None)
            if kind == "text":
                text_parts.append(block.text)
            elif kind == "tool_use":
                tool_calls.append(
                    AdapterToolCall(
                        id=block.id,
                        function=AdapterFunctionCall(name=block.name, arguments=json.dumps(block.input or {})),
                    )
                )
        usage = resp.usage
        return AdapterResponse(
            choices=[
                AdapterChoice(
                    message=AdapterMessage(content="".join(text_parts) or None, tool_calls=tool_calls),
                    finish_reason=_ANTHROPIC_STOP_REASON_MAP.get(resp.stop_reason or "", "stop"),
                )
            ],
            model=model,
            provider=self.provider_name,
            usage=AdapterUsage(
                prompt_tokens=usage.input_tokens if usage else 0,
                completion_tokens=usage.output_tokens if usage else 0,
                total_tokens=(usage.input_tokens + usage.output_tokens) if usage else 0,
            ),
        )


_ANTHROPIC_MODEL_PREFIXES = ("claude",)


def _provider_for_model(model: str) -> str:
    m = (model or "").strip().lower()
    if m.startswith(_ANTHROPIC_MODEL_PREFIXES):
        return "anthropic"
    return "openai_compat"


def get_agent_model_adapter(
    model: str,
    *,
    mode: str = AUTO_ROUTED,
) -> tuple[AgentModelAdapter, str]:
    """Resolve (adapter, model) for one coding-agent turn. Never silently
    substitutes a different provider/model than what was asked for --
    raises ModelProviderError instead, so the caller can surface a truthful
    BLOCKED_EXTERNAL-style failure.

    Modes:
      USER_SELECTED -- `model` names an explicit choice; use its provider or fail.
      AUTO_ROUTED    -- no strong preference; use whichever configured provider
                        the model name implies, same resolution as USER_SELECTED
                        (there is exactly one provider per model name today).
      POLICY_PINNED  -- ZECT_AGENT_MODEL_PIN overrides `model` entirely.
      LOCAL_ONLY     -- only the Mentrix Local LLM (openai_compat base_url) is
                        permitted; any other provider is refused even if configured.
    """
    if mode not in VALID_MODES:
        mode = AUTO_ROUTED

    resolved_model = model
    if mode == POLICY_PINNED:
        pinned = os.getenv("ZECT_AGENT_MODEL_PIN", "").strip()
        if pinned:
            resolved_model = pinned

    if mode == LOCAL_ONLY:
        from app.adapters.llm.openai_compat import mentrix_local_llm_configured

        if not mentrix_local_llm_configured():
            raise ModelProviderError("local_only_but_no_local_model_configured", requested_model=resolved_model)
        adapter = OpenAICompatAdapter()
        return adapter, resolved_model

    provider = _provider_for_model(resolved_model)
    adapter = AnthropicAgentAdapter() if provider == "anthropic" else OpenAICompatAdapter()
    if not adapter.available():
        raise ModelProviderError(
            f"{provider}_not_configured", requested_model=resolved_model, requested_provider=provider
        )
    return adapter, resolved_model

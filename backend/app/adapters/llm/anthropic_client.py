"""Real Anthropic client — replaces the broken model_selection.py attempt that
pointed OpenAI's SDK at Anthropic's URL (different API shape entirely: separate
`system` param, content-block list instead of `.choices[0].message.content`,
`input_tokens`/`output_tokens` instead of `prompt_tokens`/`completion_tokens`,
`stop_reason` values like "max_tokens" instead of `finish_reason="length"`).

Exposes create_fn() shaped to plug directly into
app.services.quality.truncation.complete_with_continuations's `create_fn` hook,
so the existing truncation-continuation logic works unchanged for both providers
— no Anthropic-specific branching needed at Build's call sites.
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MODEL = "claude-sonnet-5"

# Anthropic stop_reason -> OpenAI finish_reason, so callers built around OpenAI's
# shape (complete_with_continuations checks `finish_reason == "length"`) work as-is.
_STOP_REASON_MAP = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "tool_use": "tool_calls",
}


def anthropic_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def resolve_generation_model(*, default_openai_model: str = "gpt-4o-mini") -> tuple[bool, str]:
    """Pick the model for Build/HLD/Bugfix generation — was copy-pasted as the
    same 3 lines (use_anthropic = anthropic_available(); model_name = ...) at
    5 separate call sites; centralized here so CODEGEN_MODEL only has to be
    read in one place.

    CODEGEN_MODEL overrides the default Claude-else-OpenAI preference
    entirely (e.g. CODEGEN_MODEL=gpt-5.4) — provider is inferred from the
    model name (claude* -> Anthropic, else OpenAI). Falls back to the
    existing Claude Sonnet 5 (via ANTHROPIC_API_KEY) -> gpt-4o-mini
    preference when unset, so this is a no-op for anyone not using it.
    """
    override = os.getenv("CODEGEN_MODEL", "").strip()
    if override:
        return override.startswith("claude"), override
    use_anthropic = anthropic_available()
    return use_anthropic, DEFAULT_MODEL if use_anthropic else default_openai_model


def _get_client():
    from anthropic import Anthropic

    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured.")
    return Anthropic(api_key=key)


class _ShimUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens


class _ShimMessage:
    def __init__(self, content: str):
        self.content = content


class _ShimChoice:
    def __init__(self, content: str, finish_reason: str):
        self.message = _ShimMessage(content)
        self.finish_reason = finish_reason


class _ShimResponse:
    """Mimics the subset of OpenAI's ChatCompletion shape that
    complete_with_continuations actually reads, so it needs no Anthropic branch."""

    def __init__(self, content: str, finish_reason: str, prompt_tokens: int, completion_tokens: int):
        self.choices = [_ShimChoice(content, finish_reason)]
        self.usage = _ShimUsage(prompt_tokens, completion_tokens)


def _split_system(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    """Anthropic takes system prompt as a top-level param, not a message with
    role="system" — OpenAI-shaped callers always put it first in `messages`."""
    system = ""
    rest: list[dict[str, str]] = []
    for m in messages:
        if m.get("role") == "system" and not system:
            system = m.get("content", "")
        else:
            rest.append(m)
    return system, rest


def create_fn(*, model: str = DEFAULT_MODEL, messages: list[dict[str, str]], max_tokens: int = 4000, temperature: float = 0.2, **_kwargs: Any) -> _ShimResponse:
    """Drop-in replacement for `client.chat.completions.create` — pass this as
    `create_fn` to complete_with_continuations() to route through Claude instead
    of OpenAI, with zero changes to the calling code's truncation/stitching logic.
    """
    client = _get_client()
    system, rest = _split_system(messages)

    # Cost-tree lever #11: the same system prompt ("You are ZECT Build
    # Agent...") is sent on every call — marking it cacheable lets Anthropic
    # skip reprocessing it on subsequent calls within the cache TTL instead
    # of paying full input-token price every time. Below Anthropic's ~1024
    # token minimum this is simply a no-op, not an error, so it's safe to
    # always set.
    system_param: str | list[dict[str, Any]] | None
    if system:
        system_param = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    else:
        system_param = None

    resp = client.messages.create(
        model=model,
        system=system_param,
        messages=rest,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
    finish_reason = _STOP_REASON_MAP.get(resp.stop_reason or "", "stop")
    prompt_tokens = resp.usage.input_tokens if resp.usage else 0
    completion_tokens = resp.usage.output_tokens if resp.usage else 0

    return _ShimResponse(text, finish_reason, prompt_tokens, completion_tokens)

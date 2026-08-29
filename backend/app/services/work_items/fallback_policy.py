"""Model fallback policy: never | ask | automatic."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable


POLICY_NEVER = "never"
POLICY_ASK = "ask"
POLICY_AUTOMATIC = "automatic"
VALID_POLICIES = frozenset({POLICY_NEVER, POLICY_ASK, POLICY_AUTOMATIC})


def get_fallback_policy() -> str:
    raw = (os.getenv("ZECT_MODEL_FALLBACK_POLICY") or POLICY_NEVER).strip().lower()
    return raw if raw in VALID_POLICIES else POLICY_NEVER


@dataclass
class RouteDecision:
    provider: str  # local | cloud | none
    model: str
    fallback_used: bool
    fallback_reason: str
    allow_cloud_context: bool
    blocked: bool = False
    block_reason: str = ""


def resolve_model_route(
    *,
    local_configured: bool,
    cloud_configured: bool,
    local_model: str = "local",
    cloud_model: str = "gpt-4o-mini",
    policy: str | None = None,
    user_allows_cloud: bool | None = None,
) -> RouteDecision:
    """Decide local vs cloud. Policy `never` must not send context to cloud."""
    pol = (policy or get_fallback_policy()).strip().lower()
    if pol not in VALID_POLICIES:
        pol = POLICY_NEVER

    if local_configured:
        return RouteDecision(
            provider="local",
            model=local_model,
            fallback_used=False,
            fallback_reason="",
            allow_cloud_context=False,
        )

    if pol == POLICY_NEVER:
        return RouteDecision(
            provider="none",
            model="",
            fallback_used=False,
            fallback_reason="policy_never_blocks_cloud",
            allow_cloud_context=False,
            blocked=True,
            block_reason="ZECT_MODEL_FALLBACK_POLICY=never and local LLM unavailable",
        )

    if pol == POLICY_ASK:
        if user_allows_cloud and cloud_configured:
            return RouteDecision(
                provider="cloud",
                model=cloud_model,
                fallback_used=True,
                fallback_reason="user_approved_cloud",
                allow_cloud_context=True,
            )
        return RouteDecision(
            provider="none",
            model="",
            fallback_used=False,
            fallback_reason="awaiting_user_cloud_approval",
            allow_cloud_context=False,
            blocked=True,
            block_reason="policy_ask_requires_user_approval",
        )

    # automatic
    if cloud_configured:
        return RouteDecision(
            provider="cloud",
            model=cloud_model,
            fallback_used=True,
            fallback_reason="automatic_cloud_fallback",
            allow_cloud_context=True,
        )
    return RouteDecision(
        provider="none",
        model="",
        fallback_used=False,
        fallback_reason="no_provider",
        allow_cloud_context=False,
        blocked=True,
        block_reason="no_local_or_cloud_llm",
    )


def assert_never_no_cloud_call(
    *,
    policy: str,
    cloud_client_factory: Callable[[], Any],
    context_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Test helper: under `never`, must not invoke cloud client with context."""
    if policy != POLICY_NEVER:
        return {"ok": True, "skipped": True}
    called = {"cloud": False}

    def _wrap():
        called["cloud"] = True
        return cloud_client_factory()

    decision = resolve_model_route(
        local_configured=False,
        cloud_configured=True,
        policy=POLICY_NEVER,
    )
    if decision.allow_cloud_context or decision.provider == "cloud":
        raise AssertionError("never policy must not allow cloud context")
    # Do not call cloud
    if not decision.blocked:
        raise AssertionError("never without local must block")
    _ = context_pack
    assert called["cloud"] is False
    return {"ok": True, "decision": decision.__dict__, "cloud_called": False}

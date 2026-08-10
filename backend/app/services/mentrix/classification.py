"""Data classification + access policy for Mentrix Companion (reuse fallback_policy)."""

from __future__ import annotations

from typing import Any

PUBLIC = "PUBLIC"
INTERNAL = "INTERNAL"
CONFIDENTIAL = "CONFIDENTIAL"
RESTRICTED = "RESTRICTED"

LEVELS = (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED)


def classify_text(text: str, *, hint: str | None = None) -> str:
    """Heuristic classification — never claims perfect DLP."""
    if hint and hint.upper() in LEVELS:
        return hint.upper()
    t = (text or "").lower()
    restricted_markers = (
        "restricted",
        "top secret",
        "ssn",
        "passport",
        "production password",
        "customer pii",
    )
    confidential_markers = (
        "confidential",
        "internal only",
        "do not forward",
        "nonya",
        "salary",
        "compensation",
        "m&a",
        "acquisition",
    )
    if any(m in t for m in restricted_markers):
        return RESTRICTED
    if any(m in t for m in confidential_markers):
        return CONFIDENTIAL
    if "internal" in t:
        return INTERNAL
    return PUBLIC


def model_policy_for(classification: str) -> dict[str, Any]:
    """Map classification to model routing constraints (uses existing fallback_policy)."""
    c = (classification or PUBLIC).upper()
    if c in (CONFIDENTIAL, RESTRICTED):
        return {
            "classification": c,
            "allow_cloud_fallback": False,
            "allow_external_web": False,
            "allow_external_image": False,
            "prefer_local": True,
            "policy": "never_silent_cloud",
        }
    return {
        "classification": c,
        "allow_cloud_fallback": True,
        "allow_external_web": c == PUBLIC,
        "allow_external_image": c == PUBLIC,
        "prefer_local": False,
        "policy": "default",
    }


def enforce_model_route(classification: str) -> dict[str, Any]:
    """Resolve route with RESTRICTED/CONFIDENTIAL forbidding silent cloud."""
    from app.adapters.llm.openai_compat import mentrix_local_llm_configured, mentrix_llm_chat_model
    from app.services.work_items.fallback_policy import resolve_model_route
    import os

    pol = model_policy_for(classification)
    local_ok = mentrix_local_llm_configured()
    cloud_ok = bool((os.getenv("OPENAI_API_KEY") or "").strip())
    if not pol["allow_cloud_fallback"]:
        route = resolve_model_route(
            local_configured=local_ok,
            cloud_configured=cloud_ok,
            local_model=mentrix_llm_chat_model(),
            policy="never",
        )
        return {
            **pol,
            "blocked": bool(route.blocked),
            "reason": route.block_reason or route.fallback_reason,
            "provider": route.provider,
            "fallback_used": route.fallback_used,
            "fallback_reason": route.fallback_reason,
            "model": mentrix_llm_chat_model() if local_ok else "",
        }
    route = resolve_model_route(
        local_configured=local_ok,
        cloud_configured=cloud_ok,
        local_model=mentrix_llm_chat_model(),
    )
    return {
        **pol,
        "blocked": bool(route.blocked),
        "reason": route.block_reason or route.fallback_reason,
        "provider": route.provider,
        "fallback_used": route.fallback_used,
        "fallback_reason": route.fallback_reason,
        "model": (route.model or mentrix_llm_chat_model()) if (not route.blocked and (route.model or local_ok)) else "",
    }

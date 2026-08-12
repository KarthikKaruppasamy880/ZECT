"""Canonical Model Gateway profiles + readiness (single source of truth).

Present / LRR / Developer should import MODEL_PROFILES from here — do not
duplicate profile lists or invent a second provider config surface.
"""

from __future__ import annotations

import os
from typing import Any

from app.services.work_items.fallback_policy import resolve_model_route

MODEL_PROFILES = ("FAST", "QUALITY", "MAX", "LOCAL", "RESTRICTED", "CUSTOM")


def _local_configured() -> bool:
    from app.adapters.llm.openai_compat import mentrix_local_llm_configured

    return mentrix_local_llm_configured()


def _cloud_configured() -> bool:
    from app.adapters.llm.openai_compat import openai_compat_available

    return bool((os.getenv("OPENAI_API_KEY") or "").strip()) or openai_compat_available()


def canonical_llm_base_url() -> str:
    """Prefer ZECT_LLM_BASE_URL; MENTRIX_/OPENAI_ are aliases only."""
    return (
        os.getenv("ZECT_LLM_BASE_URL")
        or os.getenv("MENTRIX_LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or ""
    ).strip()


def resolve_profile_route(profile: str, *, local_model: str = "", cloud_model: str = "gpt-4o-mini") -> dict[str, Any]:
    """Honest per-profile readiness — no silent provider switch."""
    from app.adapters.llm.openai_compat import mentrix_llm_chat_model

    p = (profile or "QUALITY").strip().upper()
    if p not in MODEL_PROFILES:
        p = "QUALITY"
    local_ok = _local_configured()
    cloud_ok = _cloud_configured()
    lm = local_model or mentrix_llm_chat_model()

    if p == "LOCAL":
        route = resolve_model_route(
            local_configured=local_ok,
            cloud_configured=False,
            local_model=lm,
            cloud_model=cloud_model,
            policy="never",
        )
        return {
            "profile": p,
            "configured": local_ok,
            "blocked": route.blocked or not local_ok,
            "provider": route.provider,
            "requested_model": lm,
            "actual_model": route.model if not route.blocked else "",
            "local_or_cloud": "local",
            "fallback_used": False,
            "fallback_reason": route.fallback_reason or ("local_unavailable" if not local_ok else ""),
            "allow_cloud": False,
        }

    if p == "RESTRICTED":
        # RESTRICTED must never silently use unapproved cloud
        route = resolve_model_route(
            local_configured=local_ok,
            cloud_configured=False,
            local_model=lm,
            policy="never",
        )
        return {
            "profile": p,
            "configured": local_ok,
            "blocked": not local_ok,
            "provider": route.provider if local_ok else "none",
            "requested_model": lm,
            "actual_model": route.model if local_ok else "",
            "local_or_cloud": "local",
            "fallback_used": False,
            "fallback_reason": "" if local_ok else "restricted_requires_local",
            "allow_cloud": False,
        }

    if p == "FAST":
        # Prefer local when available, else cloud under policy
        route = resolve_model_route(
            local_configured=local_ok,
            cloud_configured=cloud_ok,
            local_model=lm,
            cloud_model=cloud_model,
        )
        return {
            "profile": p,
            "configured": local_ok or cloud_ok,
            "blocked": route.blocked,
            "provider": route.provider,
            "requested_model": lm if local_ok else cloud_model,
            "actual_model": route.model,
            "local_or_cloud": "local" if route.provider == "local" else ("cloud" if route.provider == "cloud" else ""),
            "fallback_used": route.fallback_used,
            "fallback_reason": route.fallback_reason,
            "allow_cloud": route.allow_cloud_context,
        }

    if p in ("QUALITY", "MAX", "CUSTOM"):
        # Prefer cloud when configured for QUALITY/MAX; CUSTOM follows env preference
        prefer_cloud = p in ("QUALITY", "MAX") and cloud_ok
        if prefer_cloud and not local_ok:
            return {
                "profile": p,
                "configured": True,
                "blocked": False,
                "provider": "cloud",
                "requested_model": cloud_model,
                "actual_model": cloud_model,
                "local_or_cloud": "cloud",
                "fallback_used": False,
                "fallback_reason": "",
                "allow_cloud": True,
            }
        route = resolve_model_route(
            local_configured=local_ok,
            cloud_configured=cloud_ok,
            local_model=lm,
            cloud_model=cloud_model,
        )
        return {
            "profile": p,
            "configured": local_ok or cloud_ok,
            "blocked": route.blocked,
            "provider": route.provider,
            "requested_model": lm if route.provider == "local" else cloud_model,
            "actual_model": route.model,
            "local_or_cloud": "local" if route.provider == "local" else ("cloud" if route.provider == "cloud" else ""),
            "fallback_used": route.fallback_used,
            "fallback_reason": route.fallback_reason,
            "allow_cloud": route.allow_cloud_context,
        }

    return {
        "profile": p,
        "configured": False,
        "blocked": True,
        "provider": "none",
        "requested_model": "",
        "actual_model": "",
        "local_or_cloud": "",
        "fallback_used": False,
        "fallback_reason": "unknown_profile",
        "allow_cloud": False,
    }


def build_gateway_audit() -> dict[str, Any]:
    profiles = {p: resolve_profile_route(p) for p in MODEL_PROFILES}
    return {
        "profiles": profiles,
        "canonical_base_url_configured": bool(canonical_llm_base_url()),
        "canonical_env": "ZECT_LLM_BASE_URL",
        "alias_envs": ["MENTRIX_LLM_BASE_URL", "OPENAI_BASE_URL"],
        "duplicate_config_warning": bool(
            (os.getenv("MENTRIX_LLM_BASE_URL") or "").strip()
            and (os.getenv("ZECT_LLM_BASE_URL") or "").strip()
            and (os.getenv("MENTRIX_LLM_BASE_URL") or "").strip() != (os.getenv("ZECT_LLM_BASE_URL") or "").strip()
        ),
        "local_configured": _local_configured(),
        "cloud_configured": _cloud_configured(),
        "model_profiles": list(MODEL_PROFILES),
    }

"""Presentation sensitivity helpers — wraps Mentrix classification."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.classification import (
    CONFIDENTIAL,
    PUBLIC,
    RESTRICTED,
    classify_text,
    enforce_model_route,
    model_policy_for,
)


def classify_deck_material(text: str, *, hint: str | None = None) -> dict[str, Any]:
    level = classify_text(text, hint=hint)
    pol = model_policy_for(level)
    route = enforce_model_route(level)
    return {
        "sensitivity": level,
        "policy": pol,
        "model_route": route,
        "forbid_external_retrieval": level in (CONFIDENTIAL, RESTRICTED),
        "require_user_approval": level in (CONFIDENTIAL, RESTRICTED),
    }


def can_generate(sensitivity_result: dict[str, Any]) -> tuple[bool, str]:
    route = sensitivity_result.get("model_route") or {}
    if route.get("blocked"):
        return False, str(route.get("reason") or "model_blocked_for_sensitivity")
    return True, "ok"


__all__ = ["classify_deck_material", "can_generate", "PUBLIC", "CONFIDENTIAL", "RESTRICTED"]

"""Audience profiles for Mentrix Present Deck."""

from __future__ import annotations

from typing import Any

PROFILES: dict[str, dict[str, Any]] = {
    "team": {
        "id": "team",
        "label": "Team",
        "tone": "collaborative",
        "detail": "high",
        "slide_count_hint": 8,
        "terminology": "engineering",
        "visual_density": "medium",
        "notes_depth": "detailed",
    },
    "manager": {
        "id": "manager",
        "label": "Manager",
        "tone": "status-focused",
        "detail": "medium",
        "slide_count_hint": 6,
        "terminology": "delivery",
        "visual_density": "medium",
        "notes_depth": "action-items",
    },
    "executive": {
        "id": "executive",
        "label": "Executive Leadership",
        "tone": "concise",
        "detail": "low",
        "slide_count_hint": 5,
        "terminology": "business",
        "visual_density": "low",
        "notes_depth": "decisions",
    },
    "board": {
        "id": "board",
        "label": "Board",
        "tone": "formal",
        "detail": "low",
        "slide_count_hint": 4,
        "terminology": "governance",
        "visual_density": "low",
        "notes_depth": "risks",
    },
    "customer": {
        "id": "customer",
        "label": "Customer",
        "tone": "value-focused",
        "detail": "medium",
        "slide_count_hint": 7,
        "terminology": "outcomes",
        "visual_density": "medium",
        "notes_depth": "benefits",
    },
    "investor": {
        "id": "investor",
        "label": "Investor",
        "tone": "growth",
        "detail": "medium",
        "slide_count_hint": 6,
        "terminology": "metrics",
        "visual_density": "medium",
        "notes_depth": "traction",
    },
    "technical": {
        "id": "technical",
        "label": "Technical",
        "tone": "precise",
        "detail": "high",
        "slide_count_hint": 10,
        "terminology": "architecture",
        "visual_density": "high",
        "notes_depth": "implementation",
    },
    "general": {
        "id": "general",
        "label": "General",
        "tone": "clear",
        "detail": "medium",
        "slide_count_hint": 6,
        "terminology": "plain",
        "visual_density": "medium",
        "notes_depth": "overview",
    },
}


def list_audiences() -> list[dict[str, Any]]:
    return list(PROFILES.values())


def get_audience(audience_id: str) -> dict[str, Any]:
    key = (audience_id or "general").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "executive_leadership": "executive",
        "exec": "executive",
        "ceo": "executive",
        "vp": "executive",
        "leadership": "executive",
    }
    key = aliases.get(key, key)
    return dict(PROFILES.get(key) or PROFILES["general"])


def prompt_adapter(audience_id: str, base_prompt: str, *, requested_slide_count: int | None = None) -> str:
    a = get_audience(audience_id)
    if requested_slide_count is not None and int(requested_slide_count) > 0:
        slide_line = f"Target: {int(requested_slide_count)} slides."
    else:
        slide_line = f"Target ~{a['slide_count_hint']} slides."
    return (
        f"{base_prompt.strip()}\n\n"
        f"Audience profile: {a['label']}. Tone: {a['tone']}. Detail: {a['detail']}. "
        f"{slide_line} Terminology: {a['terminology']}. "
        f"Speaker notes: {a['notes_depth']}. Visual density: {a['visual_density']}."
    )

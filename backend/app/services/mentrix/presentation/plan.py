"""Structured PresentationPlan — provider-neutral outline for native generate (S3)."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation.blocks import (
    TEXT_KINDS,
    ensure_visual_blocks,
    normalize_block,
    normalize_blocks,
    text_lines,
)

PLAN_SCHEMA_VERSION = 1
MIN_SLIDES = 3
MAX_SLIDES = 20
MAX_TITLE = 160
MAX_TEXT = 4000
ALLOWED_VISUAL = frozenset(
    {
        "none",
        "chart",
        "table",
        "image",
        "quote",
        "metric",
        "diagram",
        "comparison",
        "timeline",
        "process",
        "architecture",
    }
)
_VISUAL_TO_BLOCK = {
    "comparison": "table",
    "timeline": "diagram",
    "process": "diagram",
    "architecture": "diagram",
}
ALLOWED_LAYOUT = frozenset(
    {
        "title",
        "title_body",
        "two_column",
        "section",
        "closing",
        "text_image",
        "full_image",
        "chart_commentary",
        "table",
        "comparison",
        "metrics",
        "quote",
        "diagram",
    }
)


def clamp_slide_count(n: int | None, *, default: int = 6) -> int:
    try:
        value = int(n if n is not None else default)
    except (TypeError, ValueError):
        value = default
    return max(MIN_SLIDES, min(MAX_SLIDES, value))


def _str(value: Any, *, limit: int) -> str:
    return str(value or "").strip()[:limit]


def empty_plan(*, n_slides: int = 6, template_id: str = "", audience_id: str = "general") -> dict[str, Any]:
    count = clamp_slide_count(n_slides)
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "objective": "",
        "audience_id": audience_id or "general",
        "narrative": "",
        "template_id": template_id or "",
        "n_slides": count,
        "slides": [],
        "sensitivity": "PUBLIC",
        "planner_source": "empty",
    }


def normalize_slide(raw: Any, *, index: int) -> dict[str, Any]:
    row = raw if isinstance(raw, dict) else {}
    typed = normalize_blocks(row.get("blocks") or [], slide_index=index)
    blocks_in = row.get("content_blocks") or []
    content_blocks: list[dict[str, Any]] = []
    if isinstance(blocks_in, list):
        for item in blocks_in[:12]:
            if isinstance(item, str) and item.strip():
                content_blocks.append({"kind": "bullet", "text": item.strip()[:800]})
            elif isinstance(item, dict):
                kind = _str(item.get("kind") or "bullet", limit=24).lower() or "bullet"
                if kind in {"image", "chart", "table", "metric", "quote", "diagram"}:
                    block = normalize_block(item, slide_index=index, ordinal=len(typed))
                    if block:
                        typed.append(block)
                    continue
                text = _str(item.get("text") or item.get("content"), limit=800)
                if text:
                    content_blocks.append({"kind": "bullet" if kind in TEXT_KINDS else kind, "text": text})
    if not typed:
        for i, item in enumerate(content_blocks):
            block = normalize_block({"kind": "text", "text": item.get("text")}, slide_index=index, ordinal=i)
            if block:
                typed.append(block)
    evidence: list[dict[str, Any]] = []
    for item in list(row.get("evidence") or [])[:8]:
        if isinstance(item, dict):
            evidence.append(
                {
                    "source_type": _str(item.get("source_type") or "untrusted", limit=40),
                    "source_id": _str(item.get("source_id"), limit=120),
                    "excerpt": _str(item.get("excerpt") or item.get("content"), limit=400),
                    "untrusted": True,
                }
            )
        elif isinstance(item, str) and item.strip():
            evidence.append(
                {
                    "source_type": "untrusted",
                    "source_id": "",
                    "excerpt": item.strip()[:400],
                    "untrusted": True,
                }
            )
    visual = _str(row.get("visual_intent"), limit=24).lower() or "none"
    if visual not in ALLOWED_VISUAL:
        visual = "none"
    block_intent = _VISUAL_TO_BLOCK.get(visual, visual)
    layout = _str(row.get("layout_intent"), limit=32).lower() or "title_body"
    if layout not in ALLOWED_LAYOUT:
        layout = "title_body"
    if not content_blocks:
        lines = text_lines(typed)
        content_blocks = [{"kind": "bullet", "text": line} for line in lines[:12]] or [{"kind": "bullet", "text": "Key point"}]
    slide = {
        "index": index,
        "title": _str(row.get("title"), limit=MAX_TITLE) or f"Slide {index + 1}",
        "purpose": _str(row.get("purpose") or row.get("key_message"), limit=80),
        "key_message": _str(row.get("key_message"), limit=400),
        "content_blocks": content_blocks,
        "blocks": typed,
        "evidence": evidence,
        "visual_intent": block_intent if block_intent in {"none", "chart", "table", "image", "quote", "metric", "diagram"} else visual,
        "visual_choice": visual,
        "layout_intent": layout,
        "notes_intent": _str(row.get("notes_intent") or row.get("notes"), limit=MAX_TEXT),
    }
    return ensure_visual_blocks(slide)


def validate_plan(raw: Any, *, n_slides: int, template_id: str, audience_id: str) -> dict[str, Any]:
    """Return a schema-valid plan or raise ValueError."""
    if not isinstance(raw, dict):
        raise ValueError("plan_not_object")
    count = clamp_slide_count(raw.get("n_slides") or n_slides)
    slides_in = raw.get("slides")
    if not isinstance(slides_in, list) or not slides_in:
        raise ValueError("slides_required")
    slides = [normalize_slide(s, index=i) for i, s in enumerate(slides_in[:count])]
    while len(slides) < count:
        i = len(slides)
        slides.append(normalize_slide({"title": f"Slide {i + 1}"}, index=i))
    slides = slides[:count]
    for i, slide in enumerate(slides):
        slide["index"] = i
    objective = _str(raw.get("objective"), limit=MAX_TITLE)
    if not objective:
        raise ValueError("objective_required")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "objective": objective,
        "audience_id": _str(raw.get("audience_id") or audience_id, limit=40) or "general",
        "narrative": _str(raw.get("narrative"), limit=MAX_TEXT),
        "template_id": _str(raw.get("template_id") or template_id, limit=80),
        "n_slides": count,
        "slides": slides,
        "sensitivity": _str(raw.get("sensitivity") or "PUBLIC", limit=24) or "PUBLIC",
        "planner_source": _str(raw.get("planner_source"), limit=24),
    }

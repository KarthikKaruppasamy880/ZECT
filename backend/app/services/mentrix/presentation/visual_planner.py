"""Purpose-driven visual plan over canonical blocks. Not keyword matching."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation.audience import get_audience
from app.services.mentrix.presentation.blocks import ensure_visual_blocks

GENERIC_TITLES = frozenset(
    {
        "opening",
        "context",
        "status",
        "title",
        "slide",
        "point",
        "next actions",
        "risks and decisions",
        "what changed and why it matters",
        "metrics",
        "workstreams",
        "message",
    }
)

_ARCH_HINTS = ("architecture", "service", "services", "data flow", "system map", "dependency")
_PROCESS_HINTS = ("process", "pipeline", "sequence", "workflow", "handoff")
_STATUS_HINTS = ("status", "kpi", "metric", "rag", "delivery", "health")
_DECISION_HINTS = ("decision", "ask", "risk", "approve", "owners")
_FIGURE_HINTS = ("image", "photo", "figure", "screenshot", "caption")
_COMPARE_HINTS = ("compare", "versus", "vs ", "side by side")
_CHART_HINTS = ("trend", "dashboard", "chart", "quarter", "over time")


def _blob(slide: dict[str, Any]) -> str:
    return " ".join(
        [
            str(slide.get("title") or ""),
            str(slide.get("key_message") or ""),
            str(slide.get("purpose") or ""),
            " ".join(str(b.get("text") or "") for b in list(slide.get("content_blocks") or [])),
            " ".join(str(e.get("excerpt") or "") for e in list(slide.get("evidence") or [])),
        ]
    ).lower()


def _purpose_from_content(slide: dict[str, Any]) -> str:
    text = _blob(slide)
    if any(h in text for h in _ARCH_HINTS):
        return "architecture"
    if any(h in text for h in _PROCESS_HINTS):
        return "process"
    if any(h in text for h in _FIGURE_HINTS):
        return "figure"
    if any(h in text for h in _COMPARE_HINTS):
        return "comparison"
    if any(h in text for h in _CHART_HINTS) or any(h in text for h in _STATUS_HINTS):
        return "status"
    if any(h in text for h in _DECISION_HINTS):
        return "decision"
    return ""


def _purpose_for_index(index: int, n: int, audience_id: str) -> str:
    if index == 0:
        return "opening"
    if index >= n - 1:
        return "cta"
    audience = get_audience(audience_id)
    term = str(audience.get("terminology") or "")
    if term == "architecture" and index == 1:
        return "architecture"
    if term == "architecture" and index == 2:
        return "process"
    if audience["id"] == "executive" and index == 1:
        return "status"
    if audience["id"] == "executive" and index == 2:
        return "decision"
    if index == n - 2:
        return "decision"
    return "section"


def _has_numeric_evidence(slide: dict[str, Any]) -> bool:
    from app.services.mentrix.presentation.content_intent import has_quantitative_series

    return has_quantitative_series(slide)


def _chart_type_for(slide: dict[str, Any]) -> str:
    text = _blob(slide)
    if any(w in text for w in ("share", "breakdown", "mix", "allocation")):
        return "pie"
    if any(w in text for w in ("trend", "over time", "quarter", "kpi", "dashboard")):
        return "line"
    if any(w in text for w in ("rank", "compare", "versus")):
        return "bar"
    return "column"


def _choose_visual(
    slide: dict[str, Any],
    *,
    purpose: str,
    audience_id: str,
    asset_ids: list[str],
    deck_has_diagram: bool,
    prompt_l: str,
) -> str:
    existing = str(slide.get("visual_intent") or "none").lower()
    if existing not in {"", "none"}:
        return existing
    if purpose in {"opening"}:
        return "none"
    if purpose == "cta":
        return "quote"
    if purpose in {"architecture", "process", "flow"}:
        return "diagram"
    if purpose == "figure":
        return "image"
    if purpose == "decision":
        return "none"
    if purpose == "comparison":
        return "none"
    if purpose == "status" and _has_numeric_evidence(slide):
        return "chart"
    if purpose == "status":
        return "metric"
    if asset_ids and purpose in {"figure", "evidence"}:
        return "image"
    if get_audience(audience_id).get("terminology") == "architecture" and not deck_has_diagram:
        return "diagram"
    if any(h in prompt_l for h in _FIGURE_HINTS) and purpose == "section":
        return "image"
    return "none"


def apply_visual_plan(
    plan: dict[str, Any],
    *,
    audience_id: str,
    asset_ids: list[str] | None = None,
    prompt: str = "",
) -> dict[str, Any]:
    """Assign purpose + visual treatment. Does not invent factual chart values."""
    slides = list(plan.get("slides") or [])
    n = len(slides)
    assets = [a for a in (asset_ids or []) if a]
    seen_titles: dict[str, int] = {}
    deck_has_diagram = any(str(s.get("visual_intent") or "") == "diagram" for s in slides)
    prompt_l = (prompt or str(plan.get("objective") or "") or str(plan.get("narrative") or "")).lower()
    objective = str(plan.get("objective") or "").strip()
    for i, slide in enumerate(slides):
        allowed = {
            "opening",
            "cta",
            "architecture",
            "process",
            "status",
            "decision",
            "figure",
            "comparison",
            "section",
        }
        purpose = str(slide.get("purpose") or "").strip().lower()
        if purpose not in allowed:
            purpose = _purpose_from_content(slide) or _purpose_for_index(i, n, audience_id)
        elif purpose in {"opening", "cta", "section"}:
            inferred = _purpose_from_content(slide)
            if inferred:
                purpose = inferred
            elif purpose == "section":
                purpose = _purpose_for_index(i, n, audience_id)
        slide["purpose"] = purpose
        from app.services.mentrix.presentation.content_intent import choose_slide_intent, intent_to_visual

        prior = str(slide.get("visual_intent") or "none").lower()
        intent = choose_slide_intent(slide, purpose=purpose, asset_ids=assets, prompt=prompt)
        slide["content_intent"] = intent
        visual = intent_to_visual(intent)
        if visual == "none" and prior in {"", "none"}:
            visual = _choose_visual(
                slide,
                purpose=purpose,
                audience_id=audience_id,
                asset_ids=assets,
                deck_has_diagram=deck_has_diagram,
                prompt_l=prompt_l,
            )
            if visual == "table":
                visual = "none"
        slide["visual_intent"] = visual
        if visual == "diagram":
            deck_has_diagram = True
            slide["visual_choice"] = "architecture" if purpose == "architecture" else "process" if purpose == "process" else "flow"
        if visual == "chart":
            slide["chart_type"] = _chart_type_for(slide)
        title = str(slide.get("title") or "").strip()
        key = title.lower()
        seen_titles[key] = seen_titles.get(key, 0) + 1
        if key in GENERIC_TITLES or seen_titles[key] > 1:
            if purpose == "opening" and objective:
                slide["title"] = objective[:80]
            else:
                msg = str(slide.get("key_message") or purpose or f"Point {i + 1}").strip()
                if objective and msg.lower() in GENERIC_TITLES:
                    msg = f"{objective}: {purpose}"
                slide["title"] = (msg[:80] or title or f"Slide {i + 1}")
        ensure_visual_blocks(slide, asset_ids=assets)
        kinds = {str(b.get("kind") or "") for b in list(slide.get("blocks") or [])}
        if visual == "chart" and "chart" in kinds:
            for block in slide["blocks"]:
                if block.get("kind") != "chart":
                    continue
                content = block.get("content") if isinstance(block.get("content"), dict) else {}
                content["chart_type"] = slide.get("chart_type") or content.get("chart_type") or "column"
                block["content"] = content
                if not _has_numeric_evidence(slide):
                    block["provenance"] = {
                        **(block.get("provenance") or {}),
                        "source": "example",
                        "generated": True,
                        "note": "Example shape only — not factual measurements",
                    }
    if get_audience(audience_id).get("terminology") == "architecture" and not any(
        str(s.get("visual_intent")) == "diagram" for s in slides
    ):
        for slide in slides[1:-1] or slides:
            slide["visual_intent"] = "diagram"
            slide["purpose"] = "architecture"
            slide["visual_choice"] = "architecture"
            ensure_visual_blocks(slide, asset_ids=assets)
            break
    plan["slides"] = slides
    plan["visual_strategy"] = {
        "diagram": sum(1 for s in slides if str(s.get("visual_intent")) == "diagram"),
        "chart": sum(1 for s in slides if str(s.get("visual_intent")) == "chart"),
        "table": sum(1 for s in slides if str(s.get("visual_intent")) == "table"),
        "image": sum(1 for s in slides if str(s.get("visual_intent")) == "image"),
        "metric": sum(1 for s in slides if str(s.get("visual_intent")) == "metric"),
    }
    return plan

"""Template-aware layout composition. Uses the selected layout's placeholders, not layout[0]."""

from __future__ import annotations

from typing import Any

from pptx.util import Inches

from app.services.mentrix.presentation.content_intent import choose_slide_intent, intent_to_layout
from app.services.mentrix.presentation.quality_policy import SAFE_MARGIN_EMU, TITLE_BODY_GAP_EMU, slide_size_emu


def _layouts(definition: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [item for item in list((definition or {}).get("layouts") or []) if isinstance(item, dict)]


def _ph(layout: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in list(layout.get("placeholders") or []) if isinstance(p, dict)]


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _geom(ph: dict[str, Any]) -> dict[str, int]:
    raw = ph.get("geometry") if isinstance(ph.get("geometry"), dict) else ph
    return {
        "x": _int(raw.get("x")),
        "y": _int(raw.get("y")),
        "cx": max(1, _int(raw.get("cx"), 1)),
        "cy": max(1, _int(raw.get("cy"), 1)),
    }


def _score_layout(layout: dict[str, Any], *, want: str, intent: str, used: list[str]) -> int:
    name = str(layout.get("name") or "").lower()
    score = 0
    if want == "two_column" and ("2 column" in name or "two column" in name):
        score += 80
    if want == "title_body" and any(k in name for k in ("1 column", "subtitle + 1", "title + 1", "header")):
        score += 70
    if want in {"chart_commentary", "table", "metrics"} and any(k in name for k in ("1 column", "subtitle + 1", "header")):
        score += 60
    if want == "diagram" and ("blank" in name or "1_blank" in name):
        score += 50
    if intent == "TEXT" and ("title page" in name or "cover" in name or "title only" in name):
        score += 75
    if "blank" in name and want != "diagram":
        score -= 20
    if "quote" in name and intent != "TEXT":
        score -= 30
    used_count = used.count(str(layout.get("name") or ""))
    score -= used_count * 25
    if _ph(layout):
        score += 5
    return score


def pick_template_layout(
    definition: dict[str, Any] | None,
    slide: dict[str, Any],
    *,
    used_names: list[str] | None = None,
) -> dict[str, Any] | None:
    layouts = _layouts(definition)
    if not layouts:
        return None
    requested = str(slide.get("master_layout_name") or "").strip()
    if requested:
        for layout in layouts:
            if str(layout.get("name") or "") == requested:
                return layout
    intent = str(slide.get("content_intent") or choose_slide_intent(slide))
    want = intent_to_layout(intent)
    used = list(used_names or [])
    ranked = sorted(layouts, key=lambda layout: _score_layout(layout, want=want, intent=intent, used=used), reverse=True)
    return ranked[0]


def compose_regions(
    definition: dict[str, Any] | None,
    layout: dict[str, Any] | None,
    *,
    split_visual: bool = False,
) -> dict[str, dict[str, int]]:
    """Title/body/visual regions from the selected layout, not the first layout in the master."""
    cx, cy = slide_size_emu(definition)
    m = SAFE_MARGIN_EMU
    placeholders = _ph(layout or {})
    ordered = sorted(placeholders, key=lambda p: (int(p.get("y") or 0), int(p.get("x") or 0)))
    title_ph = next((p for p in ordered if str(p.get("type") or "").upper() == "TITLE"), None)
    body_phs = [p for p in ordered if p is not title_ph]
    if title_ph is None and ordered:
        title_ph = ordered[0]
        body_phs = ordered[1:]
    if title_ph is None:
        title = {"x": m, "y": m, "cx": cx - 2 * m, "cy": int(Inches(0.85))}
    else:
        title = _geom(title_ph)
    if body_phs:
        body = _geom(body_phs[0])
        if body["y"] < title["y"] + title["cy"] + TITLE_BODY_GAP_EMU:
            body["y"] = title["y"] + title["cy"] + TITLE_BODY_GAP_EMU
            body["cy"] = max(int(Inches(0.6)), cy - m - body["y"])
        visual = _geom(body_phs[1]) if len(body_phs) > 1 else dict(body)
    else:
        body_y = title["y"] + title["cy"] + TITLE_BODY_GAP_EMU
        body = {"x": m, "y": body_y, "cx": cx - 2 * m, "cy": max(1, cy - m - body_y)}
        visual = dict(body)
    if split_visual and visual.get("x") == body.get("x") and visual.get("y") == body.get("y"):
        gap = int(Inches(0.16))
        text_cy = max(int(Inches(0.9)), body["cy"] // 3)
        visual = {
            "x": body["x"],
            "y": body["y"] + text_cy + gap,
            "cx": body["cx"],
            "cy": max(int(Inches(0.8)), body["cy"] - text_cy - gap),
        }
        body = {**body, "cy": text_cy}
    return {"title": title, "body": body, "visual": visual, "safe": {"x": m, "y": m, "cx": cx - 2 * m, "cy": cy - 2 * m}}


def compose_plan(plan: dict[str, Any], definition: dict[str, Any] | None, *, prompt: str = "") -> dict[str, Any]:
    used: list[str] = []
    from app.services.mentrix.presentation.blocks import VISUAL_KINDS

    for slide in list(plan.get("slides") or []):
        intent = choose_slide_intent(slide, purpose=str(slide.get("purpose") or ""), prompt=prompt)
        slide["content_intent"] = intent
        layout = pick_template_layout(definition, slide, used_names=used)
        name = str((layout or {}).get("name") or "")
        if name:
            slide["master_layout_name"] = name
            used.append(name)
        has_visual = any(str(b.get("kind") or "") in VISUAL_KINDS for b in list(slide.get("blocks") or []))
        regions = compose_regions(definition, layout, split_visual=has_visual)
        slide["composed_regions"] = regions
        slide["layout"] = intent_to_layout(intent)
    return plan

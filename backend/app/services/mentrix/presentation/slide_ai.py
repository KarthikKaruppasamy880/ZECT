"""Typed slide/block patches from an editor prompt (no invented KPIs)."""

from __future__ import annotations

import re
from typing import Any

from app.services.mentrix.presentation.blocks import CHART_TYPES

_CHART_HITS: list[tuple[str, re.Pattern[str]]] = [
    ("radar", re.compile(r"\bradar\b", re.I)),
    ("donut", re.compile(r"\bdonut\b|\bdoughnut\b", re.I)),
    ("pie", re.compile(r"\bpie\b", re.I)),
    ("area", re.compile(r"\barea\b", re.I)),
    ("line", re.compile(r"\bline\b", re.I)),
    ("scatter", re.compile(r"\bscatter\b", re.I)),
    ("polar", re.compile(r"\bpolar\b", re.I)),
    ("gauge", re.compile(r"\bgauge\b", re.I)),
    ("progress", re.compile(r"\bprogress\b", re.I)),
    ("stacked_horizontal", re.compile(r"\bhorizontal stack", re.I)),
    ("stacked", re.compile(r"\bstacked\b", re.I)),
    ("bar", re.compile(r"\bhorizontal bar\b", re.I)),
    ("column", re.compile(r"\bbar chart\b|\bcolumn\b", re.I)),
]

_LAYOUT_HITS: list[tuple[str, re.Pattern[str]]] = [
    ("title_body", re.compile(r"title\s*\+?\s*body|title and body", re.I)),
    ("split_image", re.compile(r"split\s+image", re.I)),
    ("two_col", re.compile(r"two[\s-]?col", re.I)),
]


def chart_type_from_prompt(prompt: str) -> str | None:
    text = prompt or ""
    for chart_id, pattern in _CHART_HITS:
        if pattern.search(text) and chart_id in CHART_TYPES:
            return chart_id
    return None


def layout_from_prompt(prompt: str) -> str | None:
    text = prompt or ""
    for layout_id, pattern in _LAYOUT_HITS:
        if pattern.search(text):
            return layout_id
    return None


def patch_slide_from_prompt(
    *,
    prompt: str,
    slide_text: str = "",
    notes: str = "",
    selected_kind: str = "",
    selected_chart_type: str = "",
    attach_excerpts: list[str] | None = None,
) -> dict[str, Any]:
    """Return a typed JSON patch. Honest fail if nothing can be applied without inventing facts."""
    text = (prompt or "").strip()
    if not text:
        return {"ok": False, "error": "empty_prompt", "message": "Enter a prompt for this slide."}

    excerpts = [e.strip() for e in (attach_excerpts or []) if str(e).strip()]
    chart_type = chart_type_from_prompt(text)
    layout = layout_from_prompt(text)
    wants_notes = bool(re.search(r"\b(rewrite|notes|speaker)\b", text, re.I))
    wants_title = bool(re.search(r"\b(title|headline)\b", text, re.I))

    patch: dict[str, Any] = {
        "ok": True,
        "action": "none",
        "chart_type": chart_type,
        "layout": layout,
        "selected_kind": selected_kind,
        "selected_chart_type": selected_chart_type or None,
        "grounded": bool(excerpts),
    }

    if chart_type:
        patch["action"] = "chart_type"
        return patch

    if layout:
        patch["action"] = "layout"
        return patch

    if wants_notes or wants_title:
        from app.services.mentrix.presentation import analyze_existing_deck

        blob_parts = [text, notes, slide_text, *excerpts[:4]]
        analyzed = analyze_existing_deck(
            slides=[{"index": 0, "text": slide_text, "notes": notes}],
            notes_blob="\n\n".join(p for p in blob_parts if p),
            audience_id="exec",
        )
        if not analyzed.get("ok"):
            return {
                "ok": False,
                "error": analyzed.get("reason") or "llm_blocked",
                "message": "Could not rewrite this slide (sensitivity or model unavailable).",
            }
        improved = (analyzed.get("improved_notes") or [{}])[0]
        notes_out = str(improved.get("notes") or "").strip()
        if not notes_out:
            return {
                "ok": False,
                "error": "llm_offline_or_unparsed",
                "message": "Rewrite returned no notes — original kept.",
            }
        patch["action"] = "notes" if wants_notes or not wants_title else "text"
        patch["notes"] = notes_out
        if wants_title and slide_text:
            first = notes_out.splitlines()[0][:160]
            patch["text"] = first
        return patch

    return {
        "ok": False,
        "error": "unparsed_prompt",
        "message": "Could not apply a typed patch. Name a chart type, ask to rewrite notes, or attach a source document.",
    }

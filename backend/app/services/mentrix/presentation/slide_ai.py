"""Typed slide/block patches from an editor prompt (no invented KPIs)."""

from __future__ import annotations

import re
from typing import Any

from app.services.mentrix.presentation.blocks import CHART_TYPES, example_diagram_block, example_table_block
from app.services.mentrix.presentation.geometry import boxes_overlap, normalize_geometry
from app.services.mentrix.presentation.insert_placement import place_insert_geometry


def _placed_block(kind: str, block: dict[str, Any], existing: list[dict[str, Any]]) -> dict[str, Any]:
    out = dict(block)
    out["geometry"] = place_insert_geometry(kind, existing)
    return out


def _points_from_slide(slide_text: str, notes: str, blocks: list[dict[str, Any]]) -> list[str]:
    points: list[str] = []
    for raw in blocks:
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        kind = str(raw.get("kind") or "")
        if kind in {"text", "quote", "bullet", "body"}:
            blob = str(content.get("text") or "").strip()
            for line in blob.splitlines():
                cleaned = re.sub(r"^[\s•\-\*]+", "", line).strip()
                if cleaned:
                    points.append(cleaned[:80])
    if not points:
        for line in f"{slide_text}\n{notes}".splitlines():
            cleaned = re.sub(r"^[\s•\-\*]+", "", line).strip()
            if cleaned:
                points.append(cleaned[:80])
    return points[:8]


def _document_tree_patch(
    prompt: str,
    *,
    slide_text: str,
    notes: str,
    blocks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Deterministic PresentationDocument patches. Never invent numeric values."""
    points = _points_from_slide(slide_text, notes, blocks)
    if re.search(r"bullets?\s+to\s+diagram|into a diagram|make (this )?slide visual", prompt, re.I):
        if len(points) < 2:
            return None
        diagram = example_diagram_block(0, len(blocks), nodes=points[:5])
        diagram = _placed_block("diagram", diagram, blocks)
        return {"action": "bullets_to_diagram", "blocks": [*blocks, diagram]}
    if re.search(r"comparison table|add a table", prompt, re.I):
        if not points:
            return None
        rows = [[p, "On slide"] for p in points[:4]]
        table = example_table_block(0, len(blocks), headers=["Column 1", "Column 2", "Status"], rows=rows, title="Comparison")
        table = _placed_block("table", table, blocks)
        return {"action": "add_table", "blocks": [*blocks, table]}
    if re.search(r"reduce density|fewer bullets|first three", prompt, re.I):
        kept = 0
        next_blocks: list[dict[str, Any]] = []
        for raw in blocks:
            kind = str(raw.get("kind") or "")
            content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
            if kind in {"text", "quote"} and kept < 3:
                blob = str(content.get("text") or "")
                lines = [ln for ln in blob.splitlines() if ln.strip()][:3]
                next_blocks.append({**raw, "content": {**content, "text": "\n".join(lines) or blob}})
                kept += 1
            elif kind in {"text", "quote"} and kept >= 3:
                continue
            else:
                next_blocks.append(raw)
        text_out = "\n".join(points[:3]) if points else slide_text
        return {"action": "reduce_density", "blocks": next_blocks, "text": text_out}
    if re.search(r"fix layout", prompt, re.I):
        laid = [dict(raw) for raw in blocks]
        for i, raw in enumerate(laid):
            gi = normalize_geometry(raw.get("geometry"))
            if not gi:
                continue
            for j in range(i):
                gj = normalize_geometry(laid[j].get("geometry"))
                if not gj:
                    continue
                if boxes_overlap(gi, gj, pad=0):
                    gi = {**gi, "y": gj["y"] + gj["cy"] + 80000}
                    laid[i] = {**raw, "geometry": gi}
        return {"action": "fix_layout", "blocks": laid}
    return None

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
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a typed JSON patch. Honest fail if nothing can be applied without inventing facts."""
    text = (prompt or "").strip()
    if not text:
        return {"ok": False, "error": "empty_prompt", "message": "Enter a prompt for this slide."}

    excerpts = [e.strip() for e in (attach_excerpts or []) if str(e).strip()]
    current_blocks = [b for b in (blocks or []) if isinstance(b, dict)]
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

    tree = _document_tree_patch(text, slide_text=slide_text, notes=notes, blocks=current_blocks)
    if tree:
        patch.update(tree)
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

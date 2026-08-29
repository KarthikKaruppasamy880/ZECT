"""Rendered-layout quality estimates — text capacity vs box geometry (pre-browser CDP pass)."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation.quality_policy import MIN_FONT_PT, boxes_overlap
from app.services.mentrix.presentation.geometry import geometry_valid, normalize_geometry


def _text_blocks(spec: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in list(spec.get("blocks") or []):
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "")
        if kind not in {"text", "body", "title", "subtitle", "bullet", "quote", "metric"}:
            continue
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        text = str(content.get("text") or content.get("value") or "").strip()
        if not text:
            continue
        geo = normalize_geometry(raw.get("geometry"))
        if not geo:
            continue
        font_pt = content.get("font_size_pt")
        try:
            pt = float(font_pt) if font_pt is not None else (28.0 if kind in {"title", "subtitle"} else 16.0)
        except (TypeError, ValueError):
            pt = 16.0
        out.append({"text": text, "geometry": geo, "font_size_pt": max(MIN_FONT_PT, pt), "kind": kind})
    return out


def estimate_text_overflow(block: dict[str, Any]) -> bool:
    """Heuristic: wrapped lines exceed vertical box at declared font size."""
    geo = block["geometry"]
    text = str(block.get("text") or "")
    pt = float(block.get("font_size_pt") or 16.0)
    cx = max(1, int(geo.get("cx") or 1))
    cy = max(1, int(geo.get("cy") or 1))
    # EMU: ~12700 per point width heuristic; ~9525 per line height
    chars_per_line = max(12, int(cx / (pt * 900)))
    lines = max(1, (len(text) + chars_per_line - 1) // chars_per_line)
    needed = int(lines * pt * 9525)
    return needed > cy * 1.05


def inspect_rendered_document(doc: dict[str, Any], *, definition: dict[str, Any] | None = None) -> dict[str, Any]:
    from app.services.mentrix.presentation.template_semantics import enrich_definition_semantics, region_overlaps_protected

    definition = enrich_definition_semantics(definition)
    clipped = 0
    overlap = 0
    unreadable = 0
    template_conflicts = 0
    boxes: list[dict[str, int]] = []
    slide_cx = int(doc.get("slide_cx") or 0)
    slide_cy = int(doc.get("slide_cy") or 0)
    protected_all: list[dict[str, int]] = []
    if definition:
        for layout in list(definition.get("layouts") or []):
            sem = layout.get("semantic_map") if isinstance(layout.get("semantic_map"), dict) else {}
            for prot in list(sem.get("protected_regions") or []):
                if isinstance(prot, dict):
                    protected_all.append(prot)
    for spec in list(doc.get("slides") or []):
        if not isinstance(spec, dict):
            continue
        slide_boxes: list[dict[str, int]] = []
        for block in _text_blocks(spec):
            geo = block["geometry"]
            if estimate_text_overflow(block):
                clipped += 1
            if float(block.get("font_size_pt") or 16) < MIN_FONT_PT + 0.5:
                unreadable += 1
            if slide_cx and slide_cy:
                if geo.get("x", 0) < -1000 or geo.get("y", 0) < -1000:
                    clipped += 1
                if geo.get("x", 0) + geo.get("cx", 0) > slide_cx + 1000:
                    clipped += 1
                if geo.get("y", 0) + geo.get("cy", 0) > slide_cy + 1000:
                    clipped += 1
            for prev in slide_boxes:
                if boxes_overlap(prev, geo):
                    overlap += 1
            if protected_all and region_overlaps_protected(geo, protected_all):
                template_conflicts += 1
                overlap += 1
            slide_boxes.append(geo)
            boxes.append(geo)
    status = "FAIL" if overlap or clipped or unreadable or template_conflicts else "PASS"
    return {
        "status": status,
        "rendered_clipped_text_count": clipped,
        "rendered_overlap_count": overlap,
        "rendered_unreadable_count": unreadable,
        "template_conflict_count": template_conflicts,
        "rendered_geometry_inspected": True,
    }


__all__ = ["estimate_text_overflow", "inspect_rendered_document"]

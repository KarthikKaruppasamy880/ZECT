"""Deterministic slide-quality policy. Template-aware thresholds, not a single Zinnia layout."""

from __future__ import annotations

from typing import Any

from pptx.util import Inches, Pt

from app.services.mentrix.presentation.geometry import (
    WIDESCREEN_CX,
    WIDESCREEN_CY,
    boxes_overlap as geometry_boxes_overlap,
    within_slide,
)

MIN_FONT_PT = 12
TITLE_MIN_PT = 18
MAX_BULLETS = 6
MAX_BULLET_CHARS = 140
MAX_TITLE_CHARS = 80
SAFE_MARGIN_EMU = int(Inches(0.28))
TITLE_BODY_GAP_EMU = int(Inches(0.12))
MAX_REPEATED_LAYOUT = 2
MAX_REPAIR_ATTEMPTS = 3
WHITESPACE_SPARSE = 0.72
DENSITY_CRAMPED = 0.92
MIN_READABLE_CY = int(Inches(0.28))


def slide_size_emu(definition: dict[str, Any] | None, *, fallback: tuple[int, int] = (WIDESCREEN_CX, WIDESCREEN_CY)) -> tuple[int, int]:
    size = (definition or {}).get("slide_size") or {}
    try:
        cx = int(size.get("cx") or fallback[0])
        cy = int(size.get("cy") or fallback[1])
    except (TypeError, ValueError):
        return fallback
    return (cx if cx > 0 else fallback[0], cy if cy > 0 else fallback[1])


def safe_rect(definition: dict[str, Any] | None) -> dict[str, int]:
    cx, cy = slide_size_emu(definition)
    m = SAFE_MARGIN_EMU
    return {"x": m, "y": m, "cx": max(1, cx - 2 * m), "cy": max(1, cy - 2 * m)}


def within_bounds(geom: dict[str, int], definition: dict[str, Any] | None, *, pad: int = 20000) -> bool:
    cx, cy = slide_size_emu(definition)
    return within_slide(geom, cx, cy, pad=pad)


def boxes_overlap(a: dict[str, int], b: dict[str, int], *, pad: int = 8000) -> bool:
    return geometry_boxes_overlap(a, b, pad=pad)


def min_font_pt() -> int:
    return int(Pt(MIN_FONT_PT))  # used as documentation; callers use MIN_FONT_PT

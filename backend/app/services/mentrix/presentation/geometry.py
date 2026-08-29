"""Single EMU geometry layer for Present (E1).

Thumbs, canvas overlays, quality critic, and serializers must use this module
instead of ad-hoc CSS fallbacks. Missing geometry fails closed: never expand a
shape to cover the slide.
"""

from __future__ import annotations

from typing import Any

WIDESCREEN_CX = 9144000
WIDESCREEN_CY = 5143500


def geometry_valid(geo: Any) -> bool:
    if not isinstance(geo, dict):
        return False
    try:
        return int(geo.get("cx") or 0) > 0 and int(geo.get("cy") or 0) > 0
    except (TypeError, ValueError):
        return False


def normalize_geometry(geo: Any) -> dict[str, int] | None:
    if not geometry_valid(geo):
        return None
    assert isinstance(geo, dict)
    return {
        "x": int(geo.get("x") or 0),
        "y": int(geo.get("y") or 0),
        "cx": int(geo.get("cx") or 0),
        "cy": int(geo.get("cy") or 0),
        "rot": int(geo.get("rot") or 0),
    }


def geometry_to_percent(geo: Any, slide_cx: int, slide_cy: int) -> dict[str, float] | None:
    g = normalize_geometry(geo)
    if g is None:
        return None
    cx = slide_cx if slide_cx > 0 else WIDESCREEN_CX
    cy = slide_cy if slide_cy > 0 else WIDESCREEN_CY
    return {
        "left": 100.0 * g["x"] / cx,
        "top": 100.0 * g["y"] / cy,
        "width": 100.0 * g["cx"] / cx,
        "height": 100.0 * g["cy"] / cy,
        "rot": float(g["rot"]),
    }


def boxes_overlap(a: dict[str, int], b: dict[str, int], *, pad: int = 8000) -> bool:
    return not (
        a["x"] + a["cx"] + pad <= b["x"]
        or b["x"] + b["cx"] + pad <= a["x"]
        or a["y"] + a["cy"] + pad <= b["y"]
        or b["y"] + b["cy"] + pad <= a["y"]
    )


def within_slide(geo: dict[str, int], slide_cx: int, slide_cy: int, *, pad: int = 20000) -> bool:
    cx = slide_cx if slide_cx > 0 else WIDESCREEN_CX
    cy = slide_cy if slide_cy > 0 else WIDESCREEN_CY
    return (
        geo["x"] >= -pad
        and geo["y"] >= -pad
        and geo["x"] + geo["cx"] <= cx + pad
        and geo["y"] + geo["cy"] <= cy + pad
    )


def compose_child_geometry(parent: Any, child: Any) -> dict[str, int] | None:
    """Absolute child box = parent origin + child offset (group / placeholder inherit)."""
    c = normalize_geometry(child)
    if c is None:
        return None
    p = normalize_geometry(parent)
    if p is None:
        return c
    return {
        "x": p["x"] + c["x"],
        "y": p["y"] + c["y"],
        "cx": c["cx"],
        "cy": c["cy"],
        "rot": p["rot"] + c["rot"],
    }

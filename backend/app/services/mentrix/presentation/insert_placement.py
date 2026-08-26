"""Smart insert placement for Present (mirrors frontend presentInsertPlacement.ts)."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation.geometry import WIDESCREEN_CX, WIDESCREEN_CY, boxes_overlap

MARGIN_X = int(WIDESCREEN_CX * 0.08)
MARGIN_Y = int(WIDESCREEN_CY * 0.1)
GAP = int(WIDESCREEN_CX * 0.02)
VISUAL_KINDS = frozenset({"chart", "table", "image", "diagram", "metric", "quote", "shape", "icon"})


def _content_region() -> dict[str, int]:
    return {
        "x": MARGIN_X,
        "y": int(WIDESCREEN_CY * 0.46),
        "cx": WIDESCREEN_CX - 2 * MARGIN_X,
        "cy": int(WIDESCREEN_CY * 0.46),
    }


def _split_horizontal(box: dict[str, int], left_ratio: float = 0.5) -> tuple[dict[str, int], dict[str, int]]:
    left_w = int(box["cx"] * left_ratio) - GAP // 2
    right_w = box["cx"] - left_w - GAP
    left = {"x": box["x"], "y": box["y"], "cx": left_w, "cy": box["cy"]}
    right = {"x": box["x"] + left_w + GAP, "y": box["y"], "cx": right_w, "cy": box["cy"]}
    return left, right


def _split_vertical(box: dict[str, int], top_ratio: float = 0.55) -> tuple[dict[str, int], dict[str, int]]:
    top_h = int(box["cy"] * top_ratio) - GAP // 2
    bottom_h = box["cy"] - top_h - GAP
    top = {"x": box["x"], "y": box["y"], "cx": box["cx"], "cy": top_h}
    bottom = {"x": box["x"], "y": box["y"] + top_h + GAP, "cx": box["cx"], "cy": bottom_h}
    return top, bottom


def _norm_geo(block: dict[str, Any]) -> dict[str, int] | None:
    content = block.get("content") if isinstance(block.get("content"), dict) else {}
    if content.get("locked"):
        return None
    geo = block.get("geometry")
    if not isinstance(geo, dict):
        return None
    cx = int(geo.get("cx") or 0)
    cy = int(geo.get("cy") or 0)
    if cx <= 0 or cy <= 0:
        return None
    return {"x": int(geo.get("x") or 0), "y": int(geo.get("y") or 0), "cx": cx, "cy": cy}


def _fits(slot: dict[str, int], taken: list[dict[str, int]]) -> bool:
    return all(not boxes_overlap(slot, t) for t in taken)


def place_insert_geometry(kind: str, existing_blocks: list[dict[str, Any]]) -> dict[str, int]:
    taken = [g for b in existing_blocks if (g := _norm_geo(b)) is not None]
    visual = [b for b in existing_blocks if str(b.get("kind") or "") in VISUAL_KINDS]
    region = _content_region()
    left, right = _split_horizontal(region, 0.5)
    top, bottom = _split_vertical(region, 0.55)
    has_chart = any(str(b.get("kind") or "") == "chart" for b in visual)

    if kind == "chart":
        slots = [left, top, region]
    elif kind == "table":
        slots = [right, bottom, region] if has_chart else [right, bottom, region]
    elif kind == "image":
        slots = [right, bottom, region] if has_chart else [right, region, left]
    else:
        slots = [region, left, right, top, bottom]

    for slot in slots:
        if _fits(slot, taken):
            return slot

    if taken:
        lowest = max(taken, key=lambda t: t["y"] + t["cy"])
        y = min(lowest["y"] + lowest["cy"] + GAP, WIDESCREEN_CY - MARGIN_Y - int(WIDESCREEN_CY * 0.2))
        stacked = {"x": region["x"], "y": y, "cx": int(region["cx"] * 0.48), "cy": int(WIDESCREEN_CY * 0.22)}
        if _fits(stacked, taken):
            return stacked
        return {
            "x": stacked["x"] + len(taken) * GAP,
            "y": stacked["y"] + len(taken) * GAP,
            "cx": stacked["cx"],
            "cy": stacked["cy"],
        }
    left_slot, right_slot = _split_horizontal(region, 0.52)
    return left_slot if kind == "chart" else right_slot


__all__ = ["place_insert_geometry"]

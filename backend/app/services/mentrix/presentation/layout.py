"""Mixed-content layout using TemplateDefinition geometry. Never silent-drop overflow."""

from __future__ import annotations

from typing import Any

from pptx.util import Inches

from app.services.mentrix.presentation.blocks import TEXT_KINDS, VISUAL_KINDS

LAYOUT_KINDS = frozenset(
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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def slide_size(prs, definition: dict[str, Any] | None) -> tuple[int, int]:
    cx = _int((definition or {}).get("slide_size", {}).get("cx"))
    cy = _int((definition or {}).get("slide_size", {}).get("cy"))
    if cx > 0 and cy > 0:
        return cx, cy
    return int(prs.slide_width), int(prs.slide_height)


def _placeholder_box(definition: dict[str, Any] | None, *, kinds: tuple[str, ...]) -> dict[str, int] | None:
    for layout in list((definition or {}).get("layouts") or []):
        for ph in list(layout.get("placeholders") or []):
            ptype = str(ph.get("type") or "").upper()
            if ptype not in {k.upper() for k in kinds}:
                continue
            geom = ph.get("geometry") or {}
            box = {
                "x": _int(geom.get("x")),
                "y": _int(geom.get("y")),
                "cx": _int(geom.get("cx")),
                "cy": _int(geom.get("cy")),
            }
            if box["cx"] > 0 and box["cy"] > 0:
                return box
    return None


def content_region(prs, definition: dict[str, Any] | None) -> dict[str, int]:
    box = _placeholder_box(definition, kinds=("BODY", "OBJECT", "CONTENT"))
    if box:
        return box
    width, height = slide_size(prs, definition)
    pad_x = int(Inches(0.5))
    pad_y = int(Inches(1.35))
    return {"x": pad_x, "y": pad_y, "cx": max(int(Inches(3)), width - 2 * pad_x), "cy": max(int(Inches(2)), height - pad_y - int(Inches(0.4)))}


def overlaps(a: dict[str, int], b: dict[str, int], *, pad: int = 20000) -> bool:
    return not (
        a["x"] + a["cx"] + pad <= b["x"]
        or b["x"] + b["cx"] + pad <= a["x"]
        or a["y"] + a["cy"] + pad <= b["y"]
        or b["y"] + b["cy"] + pad <= a["y"]
    )


def choose_layout(slide: dict[str, Any]) -> str:
    blocks = list(slide.get("blocks") or [])
    kinds = [str(b.get("kind") or "") for b in blocks]
    visual = [k for k in kinds if k in VISUAL_KINDS]
    has_text = any(k in TEXT_KINDS for k in kinds) or bool(slide.get("content_blocks"))
    intent = str(slide.get("layout_intent") or "title_body").lower()
    if "image" in visual and not has_text and len(visual) == 1:
        return "full_image"
    if "image" in visual and has_text:
        return "text_image"
    if "chart" in visual:
        return "chart_commentary"
    if "table" in visual:
        return "table"
    if visual.count("metric") >= 1 and not ({"chart", "table", "image"} & set(visual)):
        return "metrics"
    if "quote" in visual and len(visual) == 1:
        return "quote"
    if "diagram" in visual:
        return "diagram"
    if intent in LAYOUT_KINDS:
        return intent
    return "title_body"


def _split_horizontal(box: dict[str, int], *, gap: int | None = None) -> tuple[dict[str, int], dict[str, int]]:
    gap = gap if gap is not None else int(Inches(0.25))
    left_cx = max(int(Inches(2)), (box["cx"] - gap) // 2)
    right = {"x": box["x"] + left_cx + gap, "y": box["y"], "cx": box["cx"] - left_cx - gap, "cy": box["cy"]}
    left = {"x": box["x"], "y": box["y"], "cx": left_cx, "cy": box["cy"]}
    return left, right


def _split_vertical(box: dict[str, int], *, top_ratio: float = 0.55) -> tuple[dict[str, int], dict[str, int]]:
    gap = int(Inches(0.18))
    top_cy = max(int(Inches(1.2)), int(box["cy"] * top_ratio))
    top = {"x": box["x"], "y": box["y"], "cx": box["cx"], "cy": top_cy}
    bottom = {"x": box["x"], "y": box["y"] + top_cy + gap, "cx": box["cx"], "cy": max(int(Inches(0.8)), box["cy"] - top_cy - gap)}
    return top, bottom


def _grid(box: dict[str, int], count: int) -> list[dict[str, int]]:
    n = max(1, min(4, count))
    gap = int(Inches(0.16))
    cell_cx = max(int(Inches(1.5)), (box["cx"] - gap * (n - 1)) // n)
    cells = []
    for i in range(n):
        cells.append({"x": box["x"] + i * (cell_cx + gap), "y": box["y"], "cx": cell_cx, "cy": box["cy"]})
    return cells


def place_blocks(slide: dict[str, Any], *, prs, definition: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return placements. Overflow blocks keep validation errors instead of being dropped."""
    box = content_region(prs, definition)
    layout = choose_layout(slide)
    slide["layout_selected"] = layout
    blocks = list(slide.get("blocks") or [])
    visuals = [b for b in blocks if str(b.get("kind") or "") in VISUAL_KINDS]
    placements: list[dict[str, Any]] = []
    assigned: list[dict[str, int]] = []

    def add(block: dict[str, Any], geom: dict[str, int], *, overflow: str = "") -> None:
        errors = list((block.get("validation") or {}).get("errors") or [])
        if overflow:
            errors.append(overflow)
        if any(overlaps(geom, other) for other in assigned):
            errors.append("layout_collision")
        width, height = slide_size(prs, definition)
        if geom["x"] < 0 or geom["y"] < 0 or geom["x"] + geom["cx"] > width + 20000 or geom["y"] + geom["cy"] > height + 20000:
            errors.append("layout_out_of_bounds")
        block["geometry"] = geom
        block["layout_intent"] = layout
        block["validation"] = {"ok": not errors, "errors": errors}
        if "layout_collision" in errors or "layout_out_of_bounds" in errors or overflow == "layout_overflow":
            return
        assigned.append(geom)
        placements.append({"block": block, "geometry": geom})

    if layout == "text_image":
        left, right = _split_horizontal(box)
        images = [b for b in visuals if b.get("kind") == "image"]
        others = [b for b in visuals if b.get("kind") != "image"]
        if images:
            add(images[0], right)
        for extra in images[1:] + others:
            add(extra, right, overflow="layout_overflow")
        return placements
    if layout == "full_image":
        images = [b for b in visuals if b.get("kind") == "image"]
        primary = images[0] if images else None
        if primary:
            add(primary, box)
        for extra in [b for b in visuals if b is not primary]:
            add(extra, box, overflow="layout_overflow")
        return placements
    if layout == "chart_commentary":
        top, bottom = _split_vertical(box, top_ratio=0.62)
        charts = [b for b in visuals if b.get("kind") == "chart"]
        rest = [b for b in visuals if b.get("kind") != "chart"]
        if charts:
            add(charts[0], top)
        for extra in charts[1:]:
            add(extra, top, overflow="layout_overflow")
        if rest:
            cells = _grid(bottom, len(rest))
            for i, block in enumerate(rest):
                add(block, cells[i] if i < len(cells) else bottom, overflow="" if i < len(cells) else "layout_overflow")
        return placements
    if layout == "table":
        tables = [b for b in visuals if b.get("kind") == "table"]
        rest = [b for b in visuals if b.get("kind") != "table"]
        if tables and rest:
            top, bottom = _split_vertical(box, top_ratio=0.7)
            add(tables[0], top)
            add(rest[0], bottom)
            for extra in tables[1:] + rest[1:]:
                add(extra, bottom, overflow="layout_overflow")
        elif tables:
            add(tables[0], box)
            for extra in tables[1:]:
                add(extra, box, overflow="layout_overflow")
        else:
            for extra in rest:
                add(extra, box, overflow="layout_overflow")
        return placements
    if layout == "metrics":
        metrics = [b for b in visuals if b.get("kind") == "metric"]
        cells = _grid(box, len(metrics) or 1)
        for i, block in enumerate(metrics):
            add(block, cells[i] if i < len(cells) else box, overflow="" if i < len(cells) else "layout_overflow")
        for extra in [b for b in visuals if b.get("kind") != "metric"]:
            add(extra, box, overflow="layout_overflow")
        return placements
    if layout == "quote":
        quotes = [b for b in visuals if b.get("kind") == "quote"]
        inset = {
            "x": box["x"] + int(Inches(0.4)),
            "y": box["y"] + int(Inches(0.4)),
            "cx": box["cx"] - int(Inches(0.8)),
            "cy": box["cy"] - int(Inches(0.8)),
        }
        if quotes:
            add(quotes[0], inset)
        for extra in [b for b in visuals if b is not (quotes[0] if quotes else None)]:
            add(extra, inset, overflow="layout_overflow")
        return placements
    if layout == "diagram":
        diagrams = [b for b in visuals if b.get("kind") == "diagram"]
        if diagrams:
            add(diagrams[0], box)
        for extra in [b for b in visuals if b.get("kind") != "diagram"]:
            add(extra, box, overflow="layout_overflow")
        return placements
    if layout == "two_column" or layout == "comparison":
        left, right = _split_horizontal(box)
        for i, block in enumerate(visuals):
            add(block, left if i % 2 == 0 else right, overflow="" if i < 4 else "layout_overflow")
        return placements
    for i, block in enumerate(visuals):
        add(block, box, overflow="" if i == 0 else "layout_overflow")
    return placements

"""TemplateLayoutSemanticMap — classify master/layout shapes and safe content bounds."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation.geometry import boxes_overlap, normalize_geometry
from app.services.mentrix.presentation.quality_policy import SAFE_MARGIN_EMU

ROLES = frozenset(
    {
        "MASTER_DECORATION",
        "LAYOUT_DECORATION",
        "TITLE_PLACEHOLDER",
        "SUBTITLE_PLACEHOLDER",
        "BODY_PLACEHOLDER",
        "IMAGE_PLACEHOLDER",
        "CHART_PLACEHOLDER",
        "TABLE_PLACEHOLDER",
        "FOOTER",
        "LOGO",
        "PROTECTED_BRAND_ELEMENT",
        "EDITABLE_CONTENT_REGION",
        "UNKNOWN",
    }
)

_PH_ROLE = {
    "title": "TITLE_PLACEHOLDER",
    "ctrTitle": "TITLE_PLACEHOLDER",
    "subTitle": "SUBTITLE_PLACEHOLDER",
    "body": "BODY_PLACEHOLDER",
    "obj": "BODY_PLACEHOLDER",
    "dt": "FOOTER",
    "ftr": "FOOTER",
    "sldNum": "FOOTER",
    "pic": "IMAGE_PLACEHOLDER",
    "chart": "CHART_PLACEHOLDER",
    "tbl": "TABLE_PLACEHOLDER",
}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def classify_placeholder_type(ph_type: str) -> str:
    key = (ph_type or "body").strip()
    return _PH_ROLE.get(key, "BODY_PLACEHOLDER")


def classify_decorative_shape(*, geometry: dict[str, Any], name: str = "", slide_cx: int = 0, slide_cy: int = 0) -> str:
    """Heuristic classification for non-placeholder layout/master shapes."""
    geo = normalize_geometry(geometry) or {}
    cx = _int(geo.get("cx"))
    cy = _int(geo.get("cy"))
    x = _int(geo.get("x"))
    y = _int(geo.get("y"))
    label = (name or "").lower()
    if any(k in label for k in ("logo", "brand", "zinnia")):
        return "LOGO"
    if any(k in label for k in ("footer", "slide number")):
        return "FOOTER"
    if slide_cx and slide_cy:
        width_ratio = cx / max(slide_cx, 1)
        height_ratio = cy / max(slide_cy, 1)
        # Tall narrow bars (common Zinnia accent strips)
        if width_ratio < 0.22 and height_ratio > 0.45:
            return "PROTECTED_BRAND_ELEMENT"
        # Large curved / hero panels occupying significant canvas
        if width_ratio > 0.35 and height_ratio > 0.55 and x + cx > slide_cx * 0.55:
            return "PROTECTED_BRAND_ELEMENT"
        if cy < slide_cy * 0.12 and height_ratio < 0.15:
            return "LAYOUT_DECORATION"
    if cx > 0 and cy > 0:
        return "LAYOUT_DECORATION"
    return "UNKNOWN"


def build_layout_semantic_map(layout: dict[str, Any], *, slide_cx: int, slide_cy: int) -> dict[str, Any]:
    """Persist semantic regions for one layout."""
    placeholders = [p for p in list(layout.get("placeholders") or []) if isinstance(p, dict)]
    shapes = [s for s in list(layout.get("shapes") or []) if isinstance(s, dict)]
    title_region = None
    subtitle_region = None
    body_regions: list[dict[str, int]] = []
    image_regions: list[dict[str, int]] = []
    chart_regions: list[dict[str, int]] = []
    table_regions: list[dict[str, int]] = []
    protected_regions: list[dict[str, int]] = []
    decorative_shapes: list[dict[str, Any]] = []
    footer_regions: list[dict[str, int]] = []
    logo_regions: list[dict[str, int]] = []

    for ph in placeholders:
        role = classify_placeholder_type(str(ph.get("type") or ""))
        geo = normalize_geometry(ph.get("geometry"))
        if not geo:
            continue
        entry = {"role": role, "geometry": geo}
        if role == "TITLE_PLACEHOLDER":
            title_region = geo
        elif role == "SUBTITLE_PLACEHOLDER":
            subtitle_region = geo
        elif role == "BODY_PLACEHOLDER":
            body_regions.append(geo)
        elif role == "IMAGE_PLACEHOLDER":
            image_regions.append(geo)
        elif role == "CHART_PLACEHOLDER":
            chart_regions.append(geo)
        elif role == "TABLE_PLACEHOLDER":
            table_regions.append(geo)
        elif role == "FOOTER":
            footer_regions.append(geo)
        decorative_shapes.append(entry)

    for shape in shapes:
        role = str(shape.get("role") or "UNKNOWN")
        geo = normalize_geometry(shape.get("geometry"))
        if not geo:
            continue
        row = {"role": role, "geometry": geo, "name": shape.get("name") or ""}
        decorative_shapes.append(row)
        if role in {"PROTECTED_BRAND_ELEMENT", "LOGO", "LAYOUT_DECORATION", "MASTER_DECORATION"}:
            protected_regions.append(geo)
        if role == "LOGO":
            logo_regions.append(geo)
        if role == "FOOTER":
            footer_regions.append(geo)

    safe = compute_safe_content_bounds(
        slide_cx=slide_cx,
        slide_cy=slide_cy,
        title_region=title_region,
        body_regions=body_regions,
        protected_regions=protected_regions,
    )
    name_l = str(layout.get("name") or "").lower()
    purpose_tags: list[str] = []
    if "title page" in name_l or "cover" in name_l:
        purpose_tags.append("opening")
    if "section" in name_l:
        purpose_tags.append("section")
    if "two column" in name_l or "2 column" in name_l:
        purpose_tags.append("comparison")
    if "blank" in name_l:
        purpose_tags.append("visual")
    if "1 column" in name_l or "content" in name_l:
        purpose_tags.append("body")

    return {
        "layout_id": layout.get("layout_id") or layout.get("name") or "",
        "name": layout.get("name") or "",
        "purpose_tags": purpose_tags,
        "title_region": title_region,
        "subtitle_region": subtitle_region,
        "body_regions": body_regions,
        "image_regions": image_regions,
        "chart_regions": chart_regions,
        "table_regions": table_regions,
        "protected_regions": protected_regions,
        "decorative_shapes": decorative_shapes,
        "footer_regions": footer_regions,
        "logo_regions": logo_regions,
        "safe_content_bounds": safe,
        "capacity": {
            "body_count": len(body_regions),
            "has_title": bool(title_region),
            "protected_count": len(protected_regions),
        },
        "visual_balance_profile": "left_text" if body_regions and protected_regions else "balanced",
    }


def compute_safe_content_bounds(
    *,
    slide_cx: int,
    slide_cy: int,
    title_region: dict[str, int] | None = None,
    body_regions: list[dict[str, int]] | None = None,
    protected_regions: list[dict[str, int]] | None = None,
) -> dict[str, int]:
    m = SAFE_MARGIN_EMU
    cx = slide_cx or 12192000
    cy = slide_cy or 6858000
    safe = {"x": m, "y": m, "cx": cx - 2 * m, "cy": cy - 2 * m}
    if body_regions:
        primary = body_regions[0]
        safe = dict(primary)
    if title_region:
        gap = 80000
        min_y = _int(title_region.get("y")) + _int(title_region.get("cy")) + gap
        if safe["y"] < min_y:
            safe["y"] = min_y
            safe["cy"] = max(int(cy * 0.15), cy - safe["y"] - m)
    for prot in list(protected_regions or []):
        safe = shrink_region_away_from(safe, prot, slide_cx=cx, slide_cy=cy)
    return safe


def shrink_region_away_from(region: dict[str, int], obstacle: dict[str, int], *, slide_cx: int, slide_cy: int) -> dict[str, int]:
    """Move/shrink region to reduce overlap with a protected decoration."""
    if not boxes_overlap(region, obstacle, pad=0):
        return region
    out = dict(region)
    ox = _int(obstacle.get("x"))
    oc = _int(obstacle.get("cx"))
    oy = _int(obstacle.get("y"))
    oc_y = _int(obstacle.get("cy"))
    # Obstacle on right half — shrink body to left of it
    if ox > slide_cx * 0.45:
        gap = 80000
        new_cx = max(int(slide_cx * 0.2), ox - out["x"] - gap)
        out["cx"] = min(out["cx"], new_cx)
    # Obstacle centered vertically on left — push body right
    elif ox < slide_cx * 0.25 and oc < slide_cx * 0.3:
        gap = 80000
        new_x = ox + oc + gap
        out["x"] = max(out["x"], new_x)
        out["cx"] = max(int(slide_cx * 0.2), slide_cx - out["x"] - SAFE_MARGIN_EMU)
    # Obstacle spans middle — use upper/lower band
    elif oy < slide_cy * 0.5 and oy + oc_y > slide_cy * 0.35:
        gap = 80000
        if out["y"] + out["cy"] > oy + oc_y + gap:
            out["cy"] = max(int(slide_cy * 0.12), oy - out["y"] - gap)
        else:
            out["y"] = oy + oc_y + gap
            out["cy"] = max(int(slide_cy * 0.12), slide_cy - out["y"] - SAFE_MARGIN_EMU)
    return out


def region_overlaps_protected(region: dict[str, int], protected_regions: list[dict[str, int]]) -> bool:
    for prot in protected_regions:
        if boxes_overlap(region, prot, pad=10000):
            return True
    return False


def enrich_definition_semantics(definition: dict[str, Any] | None) -> dict[str, Any] | None:
    if not definition or not isinstance(definition, dict):
        return definition
    slide_cx = _int((definition.get("slide_size") or {}).get("cx"), 12192000)
    slide_cy = _int((definition.get("slide_size") or {}).get("cy"), 6858000)
    layouts = []
    for layout in list(definition.get("layouts") or []):
        if not isinstance(layout, dict):
            continue
        row = dict(layout)
        row["semantic_map"] = build_layout_semantic_map(row, slide_cx=slide_cx, slide_cy=slide_cy)
        layouts.append(row)
    out = dict(definition)
    out["layouts"] = layouts
    return out


__all__ = [
    "ROLES",
    "build_layout_semantic_map",
    "classify_decorative_shape",
    "classify_placeholder_type",
    "compute_safe_content_bounds",
    "enrich_definition_semantics",
    "region_overlaps_protected",
    "shrink_region_away_from",
]

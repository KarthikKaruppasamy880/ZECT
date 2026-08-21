"""Canonical ZECT TemplateDefinition — provider UUIDs are adapter-only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.mentrix.presentation import template_registry as tmpl

PARSER_VERSION = "1"

SCOPE_ZINNIA = "ZINNIA"
SCOPE_ORG = "ORG"
SCOPE_USER = "USER"


def _def_dir() -> Path:
    d = tmpl._root() / "definitions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def definition_path(zect_id: str) -> Path:
    safe = tmpl._SAFE.sub("_", (zect_id or "").strip())[:80] or "unknown"
    return _def_dir() / f"{safe}.json"


def public_definition(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    bindings = out.get("provider_bindings")
    if isinstance(bindings, dict):
        out["provider_bindings"] = {"presenton": bool(str(bindings.get("presenton") or "").strip())}
    else:
        out["provider_bindings"] = {}
    out.pop("provider_template_id", None)
    out["provider_uuid_hidden"] = True
    return out


def load_definition(zect_id: str) -> dict[str, Any] | None:
    path = definition_path(zect_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def save_definition(row: dict[str, Any]) -> dict[str, Any]:
    zid = str(row.get("id") or "").strip()
    if not zid:
        raise ValueError("template_id_required")
    path = definition_path(zid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row


def native_ready(zect_id: str) -> bool:
    row = load_definition(tmpl.canonical_id(zect_id) or zect_id)
    return bool(row and row.get("ready") is True)


def gallery_visual(zect_id: str) -> dict[str, Any]:
    """Public gallery preview: theme swatches, fonts, layout names. No provider UUIDs."""
    tid = tmpl.canonical_id(zect_id) or zect_id
    row = load_definition(tid)
    colors: list[str] = []
    fonts: dict[str, str] = {}
    layout_names: list[str] = []
    layout_count = 0
    error = None
    if not row:
        error = "definition_missing"
    else:
        theme = row.get("theme") if isinstance(row.get("theme"), dict) else {}
        raw_colors = theme.get("colors") if isinstance(theme.get("colors"), dict) else {}
        for key in ("accent1", "accent2", "dk2", "lt1"):
            hexv = str(raw_colors.get(key) or "").strip().lstrip("#")
            if hexv:
                colors.append(f"#{hexv}")
        raw_fonts = theme.get("fonts") if isinstance(theme.get("fonts"), dict) else {}
        fonts = {
            "major": str(raw_fonts.get("major") or ""),
            "minor": str(raw_fonts.get("minor") or ""),
        }
        layouts = row.get("layouts") if isinstance(row.get("layouts"), list) else []
        layout_count = len(layouts)
        for lay in layouts[:6]:
            if isinstance(lay, dict) and lay.get("name"):
                layout_names.append(str(lay["name"]))
    ready = bool(row and row.get("ready") is True)
    cover = ensure_template_cover(tid)
    cover_data_url = ""
    if cover and cover.is_file():
        import base64

        cover_data_url = "data:image/png;base64," + base64.b64encode(cover.read_bytes()).decode("ascii")
    return {
        "colors": colors[:4],
        "fonts": fonts,
        "layout_names": layout_names,
        "layout_count": layout_count,
        "ready": ready,
        "readiness": "READY" if ready else "TEMPLATE_NOT_READY",
        "thumbnail_kind": "cover_render" if cover_data_url else "theme_swatch",
        "cover_url": f"/api/mentrix/present/template-cover/{tid}" if cover_data_url else "",
        "cover_data_url": cover_data_url,
        "error": error,
        "provider_uuid_hidden": True,
    }


def _cover_dir() -> Path:
    d = tmpl._root() / "covers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cover_png_path(zect_id: str) -> Path:
    safe = tmpl._SAFE.sub("_", (zect_id or "").strip())[:80] or "unknown"
    return _cover_dir() / f"{safe}.png"


def ensure_template_cover(zect_id: str) -> Path | None:
    """Render a cover PNG from the template master (cached)."""
    tid = tmpl.canonical_id(zect_id) or zect_id
    dest = _cover_png_path(tid)
    master = tmpl.source_pptx_path(tid)
    if dest.is_file() and (not master or dest.stat().st_mtime >= master.stat().st_mtime):
        return dest
    if not master or not master.is_file():
        return dest if dest.is_file() else None
    try:
        from app.services.mentrix.presentation.slide_preview import render_slide_png_bytes

        dest.write_bytes(render_slide_png_bytes(master.read_bytes(), 0))
        return dest
    except Exception:
        return dest if dest.is_file() else None


def template_slide_previews(zect_id: str, max_slides: int = 12) -> list[str]:
    """PNG data URLs for master slides 0..n (empty list if the master cannot render)."""
    tid = tmpl.canonical_id(zect_id) or zect_id
    master = tmpl.source_pptx_path(tid)
    if not master or not master.is_file():
        return []
    try:
        from pptx import Presentation

        from app.services.mentrix.presentation.slide_preview import render_slide_png_bytes

        n = min(max(1, int(max_slides)), len(Presentation(str(master)).slides))
        out: list[str] = []
        raw = master.read_bytes()
        import base64

        for i in range(n):
            png = render_slide_png_bytes(raw, i)
            if png:
                out.append("data:image/png;base64," + base64.b64encode(png).decode("ascii"))
        return out
    except Exception:
        cover = ensure_template_cover(tid)
        if cover and cover.is_file():
            import base64

            return ["data:image/png;base64," + base64.b64encode(cover.read_bytes()).decode("ascii")]
        return []


def list_ready_ids() -> list[str]:
    out: list[str] = []
    root = _def_dir()
    for path in sorted(root.glob("*.json")):
        row = load_definition(path.stem)
        if row and row.get("ready") is True:
            out.append(str(row.get("id") or path.stem))
    return out

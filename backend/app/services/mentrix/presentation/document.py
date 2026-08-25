"""Provider-neutral PresentationDocument for the ZECT editor (S5 + S6.5 blocks)."""

from __future__ import annotations

import io
import zipfile
from typing import Any

from app.services.mentrix.presentation.blocks import normalize_blocks
from app.services.mentrix.presentation.geometry import WIDESCREEN_CX, WIDESCREEN_CY, geometry_valid
from app.services.pptx_parse import parse_pptx_bytes, slide_emu_size

SCHEMA_VERSION = 2


def _copy_missing_geometry(sidecar: list[Any], parsed: list[Any]) -> list[dict[str, Any]]:
    """PPTX parse is the visual base; sidecar overlays editor deltas onto matching blocks."""
    parsed_rows = [p for p in parsed if isinstance(p, dict)]
    sidecar_rows = [s for s in sidecar if isinstance(s, dict)]
    if not sidecar_rows:
        return parsed_rows

    def _overlay(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        out = dict(base)
        out["id"] = extra.get("id") or base.get("id")
        pc = dict(base.get("content") or {}) if isinstance(base.get("content"), dict) else {}
        sc = dict(extra.get("content") or {}) if isinstance(extra.get("content"), dict) else {}
        content = {**pc, **sc}
        if sc.get("asset_id"):
            content.pop("data_url", None)
        elif not sc.get("data_url") and pc.get("data_url"):
            content["data_url"] = pc["data_url"]
        if extra.get("geometry") and geometry_valid(extra.get("geometry")):
            out["geometry"] = extra["geometry"]
        out["content"] = content
        if extra.get("kind"):
            out["kind"] = extra.get("kind") or out.get("kind")
        return out

    used: set[str] = set()
    by_id = {str(s.get("id") or ""): s for s in sidecar_rows if s.get("id")}
    out: list[dict[str, Any]] = []
    for pb in parsed_rows:
        sid = str(pb.get("id") or "")
        extra = by_id.get(sid)
        if extra:
            used.add(sid)
            out.append(_overlay(pb, extra))
            continue
        kind = str(pb.get("kind") or "")
        match: dict[str, Any] | None = None
        for s in sidecar_rows:
            other = str(s.get("id") or "")
            if other in used:
                continue
            if str(s.get("kind") or "") == kind:
                match = s
                break
        if match:
            used.add(str(match.get("id") or ""))
            out.append(_overlay(pb, match))
        else:
            out.append(pb)
    for s in sidecar_rows:
        sid = str(s.get("id") or "")
        if sid and sid in used:
            continue
        if not sid and s in out:
            continue
        if sid and any(str(row.get("id") or "") == sid for row in out):
            continue
        out.append(s)
    return out


def inspect_pptx_visuals(data: bytes) -> dict[str, Any]:
    if not data:
        return {"has_image": False, "has_chart": False, "has_table": False, "media": 0, "charts": 0}
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            names = [i.filename.replace("\\", "/") for i in zf.infolist()]
    except zipfile.BadZipFile:
        return {"has_image": False, "has_chart": False, "has_table": False, "media": 0, "charts": 0}
    media = [n for n in names if n.startswith("ppt/media/")]
    charts = [n for n in names if n.startswith("ppt/charts/")]
    has_table = any("a:tbl" in n.lower() or n.startswith("ppt/embeddings/") for n in names)
    if not has_table:
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                for name in names:
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                        snippet = zf.read(name)[:200_000]
                        if b"<a:tbl" in snippet or b"<p:tbl" in snippet:
                            has_table = True
                            break
        except zipfile.BadZipFile:
            pass
    return {
        "has_image": bool(media),
        "has_chart": bool(charts),
        "has_table": has_table,
        "media": len(media),
        "charts": len(charts),
    }


def document_from_plan(plan: dict[str, Any], *, path: str = "", provider: str = "") -> dict[str, Any]:
    slides = []
    for spec in list(plan.get("slides") or [])[:40]:
        if not isinstance(spec, dict):
            continue
        idx = int(spec.get("index") or len(slides))
        blocks = normalize_blocks(spec.get("blocks") or [], slide_index=idx)
        title = str(spec.get("title") or "")
        bullets = [
            str(b.get("text") or "").strip()
            for b in list(spec.get("content_blocks") or [])
            if str(b.get("text") or "").strip()
        ]
        text = "\n".join([title, *bullets]).strip()
        slides.append(
            {
                "index": idx,
                "text": text[:4000],
                "notes": str(spec.get("notes_intent") or spec.get("notes") or "")[:4000],
                "blocks": blocks,
                "layout_selected": spec.get("layout_selected") or spec.get("layout_intent") or "",
                "visual_intent": spec.get("visual_intent") or "none",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "PresentationDocument",
        "path": path,
        "provider": provider or "",
        "slide_cx": WIDESCREEN_CX,
        "slide_cy": WIDESCREEN_CY,
        "slides": slides,
    }


def document_from_pptx_bytes(data: bytes, *, path: str = "", provider: str = "") -> dict[str, Any]:
    slides = parse_pptx_bytes(data)
    visuals = inspect_pptx_visuals(data)
    slide_cx, slide_cy = slide_emu_size(data)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "PresentationDocument",
        "path": path,
        "provider": provider or "",
        "visuals": visuals,
        "slide_cx": slide_cx,
        "slide_cy": slide_cy,
        "slides": [
            {
                "index": int(s.get("index", i)),
                "text": str(s.get("text") or ""),
                "notes": str(s.get("notes") or ""),
                "blocks": normalize_blocks(
                    s.get("blocks") or [{"kind": "body", "text": str(s.get("text") or "")}],
                    slide_index=int(s.get("index", i)),
                ),
            }
            for i, s in enumerate(slides)
        ],
    }


def merge_sidecar_slides(parsed: list[dict[str, Any]], sidecar_slides: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    def _blocks_for(row: dict[str, Any], idx: int, extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        parsed_blocks = row.get("blocks") if isinstance(row.get("blocks"), list) else []
        sidecar_blocks = extra.get("blocks") if extra and isinstance(extra.get("blocks"), list) else None
        if sidecar_blocks:
            merged = _copy_missing_geometry(sidecar_blocks, parsed_blocks)
        else:
            merged = parsed_blocks
        return normalize_blocks(merged, slide_index=idx) if merged else []

    if not sidecar_slides:
        out: list[dict[str, Any]] = []
        for i, row in enumerate(parsed):
            idx = int(row.get("index", i))
            next_row = dict(row)
            next_row["index"] = idx
            next_row["blocks"] = _blocks_for(row, idx)
            out.append(next_row)
        return out
    by_index = {}
    for spec in sidecar_slides:
        if isinstance(spec, dict):
            try:
                by_index[int(spec.get("index"))] = spec
            except (TypeError, ValueError):
                continue
    out = []
    for i, row in enumerate(parsed):
        idx = int(row.get("index", i))
        extra = by_index.get(idx) or {}
        out.append(
            {
                "index": idx,
                "text": str(extra.get("text") or row.get("text") or "")[:4000],
                "notes": str(extra.get("notes") or row.get("notes") or "")[:4000],
                "blocks": _blocks_for(row, idx, extra),
            }
        )
    return out


def normalize_document(raw: Any, *, path: str = "") -> dict[str, Any]:
    row = raw if isinstance(raw, dict) else {}
    slides_in = row.get("slides") if isinstance(row.get("slides"), list) else []
    slides = []
    for i, spec in enumerate(slides_in[:40]):
        if not isinstance(spec, dict):
            continue
        slides.append(
            {
                "index": i,
                "text": str(spec.get("text") or "")[:4000],
                "notes": str(spec.get("notes") or "")[:4000],
                "blocks": normalize_blocks(spec.get("blocks") or [], slide_index=i),
            }
        )
    try:
        slide_cx = int(row.get("slide_cx") or WIDESCREEN_CX)
        slide_cy = int(row.get("slide_cy") or WIDESCREEN_CY)
    except (TypeError, ValueError):
        slide_cx, slide_cy = WIDESCREEN_CX, WIDESCREEN_CY
    visuals = row.get("visuals") if isinstance(row.get("visuals"), dict) else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "PresentationDocument",
        "path": str(row.get("path") or path or ""),
        "provider": str(row.get("provider") or ""),
        "slide_cx": slide_cx if slide_cx > 0 else WIDESCREEN_CX,
        "slide_cy": slide_cy if slide_cy > 0 else WIDESCREEN_CY,
        "visuals": visuals,
        "slides": slides,
    }


__all__ = [
    "SCHEMA_VERSION",
    "document_from_plan",
    "document_from_pptx_bytes",
    "geometry_valid",
    "inspect_pptx_visuals",
    "merge_sidecar_slides",
    "normalize_document",
]

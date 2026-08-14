"""Provider-neutral PresentationDocument for the ZECT editor (S5 + S6.5 blocks)."""

from __future__ import annotations

import io
import zipfile
from typing import Any

from app.services.mentrix.presentation.blocks import normalize_blocks
from app.services.pptx_parse import parse_pptx_bytes


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
        "schema_version": 1,
        "path": path,
        "provider": provider or "",
        "slides": slides,
    }


def document_from_pptx_bytes(data: bytes, *, path: str = "", provider: str = "") -> dict[str, Any]:
    slides = parse_pptx_bytes(data)
    visuals = inspect_pptx_visuals(data)
    return {
        "schema_version": 1,
        "path": path,
        "provider": provider or "",
        "visuals": visuals,
        "slides": [
            {
                "index": int(s.get("index", i)),
                "text": str(s.get("text") or ""),
                "notes": str(s.get("notes") or ""),
                "blocks": [{"kind": "body", "text": str(s.get("text") or "")}],
            }
            for i, s in enumerate(slides)
        ],
    }


def merge_sidecar_slides(parsed: list[dict[str, Any]], sidecar_slides: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not sidecar_slides:
        return parsed
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
        blocks = extra.get("blocks") if isinstance(extra.get("blocks"), list) else row.get("blocks") or []
        out.append(
            {
                "index": idx,
                "text": str(extra.get("text") or row.get("text") or "")[:4000],
                "notes": str(extra.get("notes") or row.get("notes") or "")[:4000],
                "blocks": normalize_blocks(blocks, slide_index=idx) if blocks else [],
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
    return {
        "schema_version": 1,
        "path": str(row.get("path") or path or ""),
        "provider": str(row.get("provider") or ""),
        "slides": slides,
    }

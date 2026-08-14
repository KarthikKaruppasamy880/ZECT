"""Provider-neutral PresentationDocument for the ZECT editor (S5)."""

from __future__ import annotations

from typing import Any

from app.services.pptx_parse import parse_pptx_bytes


def document_from_pptx_bytes(data: bytes, *, path: str = "", provider: str = "") -> dict[str, Any]:
    slides = parse_pptx_bytes(data)
    return {
        "schema_version": 1,
        "path": path,
        "provider": provider or "",
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
                "blocks": list(spec.get("blocks") or []),
            }
        )
    return {
        "schema_version": 1,
        "path": str(row.get("path") or path or ""),
        "provider": str(row.get("provider") or ""),
        "slides": slides,
    }

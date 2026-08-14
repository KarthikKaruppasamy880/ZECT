"""Write editor text/notes back into OOXML (S5 round-trip). Sidecar remains source of truth if this fails."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

from app.services.mentrix.presentation.renderer import _set_notes, validate_generated_pptx


def apply_document_to_pptx(path: str | Path, slides: list[dict[str, Any]]) -> dict[str, Any]:
    pptx = Path(path)
    prs = Presentation(str(pptx))
    for spec in slides or []:
        try:
            idx = int(spec.get("index", -1))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(prs.slides):
            continue
        slide = prs.slides[idx]
        text = str(spec.get("text") or "").strip()
        if text:
            _write_slide_text(slide, text)
        _set_notes(slide, str(spec.get("notes") or ""))
    prs.save(str(pptx))
    data = pptx.read_bytes()
    validate_generated_pptx(data, n_slides=len(prs.slides))
    return {"ok": True, "path": str(pptx), "slide_count": len(prs.slides), "ooxml_roundtrip": True}


def _write_slide_text(slide, text: str) -> None:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:160] if lines else text[:160]
    body = lines[1:]
    if slide.shapes.title is not None:
        slide.shapes.title.text = title
        rest = body
    else:
        rest = lines or [text]
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        try:
            ph_type = shape.placeholder_format.type
        except Exception:
            continue
        if ph_type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.VERTICAL_BODY):
            tf = shape.text_frame
            tf.clear()
            if rest:
                tf.text = rest[0][:800]
                for extra in rest[1:8]:
                    p = tf.add_paragraph()
                    p.text = extra[:800]
            return

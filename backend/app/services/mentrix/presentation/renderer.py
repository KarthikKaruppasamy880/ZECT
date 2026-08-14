"""Native PPTX renderer — python-pptx (MIT). Does not vendor Presenton."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Emu, Inches

from app.services.mentrix.presentation.template_importer import UnsafePptxError, inspect_pptx_archive
from app.services.pptx_parse import parse_pptx_bytes

_FALLBACK_IDS = frozenset({"modern", "general", "standard", "swift", ""})


def _safe_filename(name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", (name or "zect-deck").strip())[:80] or "zect-deck"
    if not stem.lower().endswith(".pptx"):
        stem += ".pptx"
    return stem


def _clear_slides(prs: Presentation) -> None:
    sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001 — python-pptx has no public delete
    for sld_id in list(sld_id_lst):
        r_id = sld_id.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        if r_id:
            try:
                prs.part.drop_rel(r_id)
            except Exception:
                pass
        sld_id_lst.remove(sld_id)


def _pick_layout(prs: Presentation, intent: str):
    layouts = list(prs.slide_layouts)
    if not layouts:
        raise UnsafePptxError("template_has_no_layouts")
    want = (intent or "title_body").lower()
    aliases = {
        "title": ("title slide", "title", "blank"),
        "title_body": ("title and content", "title and body", "content", "text"),
        "two_column": ("two content", "comparison", "two column"),
        "section": ("section header", "section"),
        "closing": ("blank", "title slide", "end"),
    }
    needles = aliases.get(want, ("content",))
    named = [(sl, (sl.name or "").lower()) for sl in layouts]
    for needle in needles:
        for sl, name in named:
            if needle in name:
                return sl
    # Prefer a layout with a body placeholder
    for sl in layouts:
        try:
            kinds = [ph.placeholder_format.type for ph in sl.placeholders]
        except ValueError:
            kinds = []
        if PP_PLACEHOLDER.BODY in kinds or PP_PLACEHOLDER.OBJECT in kinds:
            return sl
    return layouts[0]


def _fill_placeholder(slide, *, title: str, bullets: list[str]) -> None:
    title_set = False
    body_set = False
    if slide.shapes.title is not None:
        slide.shapes.title.text = title[:160]
        title_set = True
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        try:
            ph_type = shape.placeholder_format.type
        except ValueError:
            continue
        if ph_type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE) and not title_set:
            shape.text_frame.text = title[:160]
            title_set = True
        elif ph_type in (
            PP_PLACEHOLDER.BODY,
            PP_PLACEHOLDER.OBJECT,
            PP_PLACEHOLDER.VERTICAL_BODY,
        ) and not body_set:
            tf = shape.text_frame
            tf.clear()
            if not bullets:
                tf.text = ""
            else:
                tf.text = bullets[0][:800]
                for extra in bullets[1:8]:
                    p = tf.add_paragraph()
                    p.text = extra[:800]
                    p.level = 0
            body_set = True
    if not title_set:
        box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(1))
        box.text_frame.text = title[:160]
    if not body_set and bullets:
        box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
        tf = box.text_frame
        tf.word_wrap = True
        tf.text = bullets[0][:800]
        for extra in bullets[1:8]:
            p = tf.add_paragraph()
            p.text = extra[:800]


def _set_notes(slide, notes: str) -> None:
    text = (notes or "").strip()[:4000]
    if not text:
        return
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text


def _maybe_table(slide, blocks: list[dict[str, Any]]) -> None:
    rows = [str(b.get("text") or "") for b in blocks if str(b.get("text") or "").strip()]
    if len(rows) < 2:
        return
    table_shape = slide.shapes.add_table(len(rows), 1, Inches(0.6), Inches(4.6), Inches(8.8), Inches(1.8))
    table = table_shape.table
    for i, row in enumerate(rows[:12]):
        table.cell(i, 0).text = row[:200]


def validate_generated_pptx(data: bytes, *, n_slides: int) -> dict[str, Any]:
    zf = inspect_pptx_archive(data)
    try:
        names = [i.filename.replace("\\", "/") for i in zf.infolist()]
    finally:
        zf.close()
    if "ppt/presentation.xml" not in names:
        raise UnsafePptxError("missing_presentation_xml")
    slides = parse_pptx_bytes(data)
    if len(slides) < 1:
        raise UnsafePptxError("no_slides")
    if len(slides) != int(n_slides):
        raise UnsafePptxError("slide_count_mismatch")
    return {"ok": True, "slide_count": len(slides), "notes": sum(1 for s in slides if (s.get("notes") or "").strip())}


def render_plan_to_pptx(
    plan: dict[str, Any],
    *,
    template_path: Path | None = None,
    definition: dict[str, Any] | None = None,
) -> bytes:
    """Render a PresentationPlan to PPTX bytes. Charts/images remain PARTIAL."""
    slides_in = list(plan.get("slides") or [])
    if not slides_in:
        raise UnsafePptxError("plan_has_no_slides")
    prs = None
    if template_path and Path(template_path).is_file():
        raw = Path(template_path).read_bytes()
        zf = inspect_pptx_archive(raw)
        zf.close()
        try:
            prs = Presentation(io.BytesIO(raw))
            _clear_slides(prs)
        except Exception as exc:
            raise UnsafePptxError("template_open_failed") from exc
    if prs is None:
        prs = Presentation()
        cx = (definition or {}).get("slide_size", {}).get("cx") if definition else None
        cy = (definition or {}).get("slide_size", {}).get("cy") if definition else None
        if cx and cy:
            try:
                prs.slide_width = Emu(int(cx))
                prs.slide_height = Emu(int(cy))
            except (TypeError, ValueError):
                pass
    for slide_spec in slides_in:
        layout = _pick_layout(prs, str(slide_spec.get("layout_intent") or "title_body"))
        slide = prs.slides.add_slide(layout)
        try:
            fallback_index = int(slide_spec.get("index") or 0)
        except (TypeError, ValueError):
            fallback_index = 0
        title = str(slide_spec.get("title") or f"Slide {fallback_index + 1}")
        blocks = list(slide_spec.get("content_blocks") or [])
        bullets = [str(b.get("text") or "").strip() for b in blocks if str(b.get("text") or "").strip()]
        _fill_placeholder(slide, title=title, bullets=bullets)
        if str(slide_spec.get("visual_intent") or "") == "table":
            _maybe_table(slide, blocks)
        _set_notes(slide, str(slide_spec.get("notes_intent") or ""))
    buf = io.BytesIO()
    prs.save(buf)
    data = buf.getvalue()
    validate_generated_pptx(data, n_slides=len(slides_in))
    return data


def write_pptx(data: bytes, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def is_fallback_template_id(template_id: str) -> bool:
    return (template_id or "").strip().lower() in _FALLBACK_IDS

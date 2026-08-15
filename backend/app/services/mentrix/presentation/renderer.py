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


def _definition_layout_needles(definition: dict[str, Any] | None, intent: str) -> tuple[str, ...]:
    """Prefer TemplateDefinition layout names that match the slide intent."""
    names = [str(row.get("name") or "").strip().lower() for row in list((definition or {}).get("layouts") or [])]
    names = [n for n in names if n]
    want = (intent or "title_body").lower()
    prefer = {
        "title": ("title slide", "title"),
        "title_body": ("title and content", "title and body", "subtitle + 1", "1 column", "header", "content"),
        "two_column": ("two content", "comparison", "two column"),
        "section": ("section header", "section"),
        "closing": ("title slide", "blank"),
        "text_image": ("picture with caption", "title and content", "picture"),
        "full_image": ("blank", "picture"),
        "chart_commentary": ("title and content", "content"),
        "table": ("title and content", "content"),
        "comparison": ("comparison", "two content"),
        "metrics": ("title and content", "blank"),
        "quote": ("quote", "blank", "title slide"),
        "diagram": ("title and content", "blank"),
    }.get(want, ("content",))
    matched = tuple(n for n in names if any(p in n for p in prefer))
    return matched or prefer


def _pick_layout(
    prs: Presentation,
    intent: str,
    definition: dict[str, Any] | None = None,
    preferred_name: str = "",
):
    layouts = list(prs.slide_layouts)
    if not layouts:
        raise UnsafePptxError("template_has_no_layouts")
    want_name = (preferred_name or "").strip().lower()
    named = [(sl, (sl.name or "").lower()) for sl in layouts]
    if want_name:
        for sl, name in named:
            if name == want_name:
                return sl
        for sl, name in named:
            if want_name in name or (name and name in want_name):
                return sl
    want = (intent or "title_body").lower()
    aliases = {
        "title": ("title slide", "title", "blank"),
        "title_body": ("subtitle + 1", "title + 1", "1 column", "header", "title and content", "title and body", "content", "text"),
        "two_column": ("two content", "comparison", "two column", "2 column", "subtitle + 2"),
        "section": ("section header", "section"),
        "closing": ("blank", "title slide", "end"),
        "text_image": ("title and content", "picture with caption", "content"),
        "full_image": ("blank", "picture", "title and content"),
        "chart_commentary": ("subtitle + 1", "1 column", "title and content", "content", "text"),
        "table": ("subtitle + 1", "1 column", "title and content", "content"),
        "comparison": ("comparison", "two content", "two column", "2 column"),
        "metrics": ("subtitle + 1", "title and content", "content", "blank"),
        "quote": ("quote", "blank", "title slide"),
        "diagram": ("blank", "title and content", "content"),
    }
    needles = _definition_layout_needles(definition, want) + aliases.get(want, ("content",))
    for needle in needles:
        for sl, name in named:
            if needle and needle in name:
                return sl
    for sl in layouts:
        try:
            kinds = [ph.placeholder_format.type for ph in sl.placeholders]
        except ValueError:
            kinds = []
        if PP_PLACEHOLDER.BODY in kinds or PP_PLACEHOLDER.OBJECT in kinds:
            return sl
    return layouts[0]


def _geom_box(regions: dict[str, Any] | None, key: str, fallback: tuple[float, float, float, float]):
    geom = (regions or {}).get(key) if isinstance(regions, dict) else None
    if isinstance(geom, dict) and int(geom.get("cx") or 0) > 0:
        return Emu(int(geom["x"])), Emu(int(geom["y"])), Emu(int(geom["cx"])), Emu(int(geom["cy"]))
    return Inches(fallback[0]), Inches(fallback[1]), Inches(fallback[2]), Inches(fallback[3])


def _is_placeholder(shape) -> bool:
    try:
        _ = shape.placeholder_format.type
        return True
    except ValueError:
        return False


def _clear_placeholder_sample_text(slide) -> None:
    """Wipe leftover master/layout sample text before a single canonical write."""
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        if not _is_placeholder(shape):
            continue
        try:
            shape.text_frame.clear()
        except Exception:
            try:
                shape.text_frame.text = ""
            except Exception:
                pass


def _fill_text_frame(shape, lines: list[str]) -> None:
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    if not lines:
        tf.text = ""
        return
    tf.text = lines[0][:800]
    for extra in lines[1:8]:
        p = tf.add_paragraph()
        p.text = extra[:800]
        p.level = 0


def _fill_placeholder(
    slide,
    *,
    title: str,
    bullets: list[str],
    regions: dict[str, Any] | None = None,
    skip_body: bool = False,
) -> None:
    """Populate placeholders XOR generated shapes — never both for the same role."""
    _clear_placeholder_sample_text(slide)
    title_set = False
    body_set = False
    title_ph = None
    body_ph = None
    if slide.shapes.title is not None:
        title_ph = slide.shapes.title
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        try:
            ph_type = shape.placeholder_format.type
        except ValueError:
            continue
        if ph_type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE):
            if title_ph is None:
                title_ph = shape
        elif ph_type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.VERTICAL_BODY):
            if body_ph is None:
                body_ph = shape
    if title_ph is not None:
        title_ph.text_frame.text = title[:160]
        title_set = True
    if not skip_body and body_ph is not None:
        _fill_text_frame(body_ph, bullets)
        body_set = True
    if not title_set:
        x, y, cx, cy = _geom_box(regions, "title", (0.5, 0.28, 9.0, 0.7))
        box = slide.shapes.add_textbox(x, y, cx, cy)
        box.text_frame.word_wrap = True
        box.text_frame.text = title[:160]
        title_set = True
    if skip_body:
        return
    if not body_set and bullets:
        x, y, cx, cy = _geom_box(regions, "body", (0.5, 1.2, 9.0, 4.8))
        box = slide.shapes.add_textbox(x, y, cx, cy)
        _fill_text_frame(box, bullets)


def _set_notes(slide, notes: str) -> None:
    text = (notes or "").strip()[:4000]
    if not text:
        return
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text


def _prepare_image_assets(plan: dict[str, Any], *, user_id: str) -> None:
    from app.services.mentrix.presentation.asset_resolver import store_example_image

    uid = (user_id or "anon").strip() or "anon"
    for slide_spec in list(plan.get("slides") or []):
        for block in list(slide_spec.get("blocks") or []):
            if str(block.get("kind") or "") != "image":
                continue
            content = block.get("content") if isinstance(block.get("content"), dict) else {}
            if str(content.get("asset_id") or "").strip():
                continue
            meta = store_example_image(user_id=uid, label=str(slide_spec.get("title") or "ZECT")[:32])
            content["asset_id"] = meta["asset_id"]
            block["content"] = content
            block["provenance"] = {
                "source": "example",
                "generated": True,
                "note": "Generated placeholder, not a user photo",
            }
            block["validation"] = {"ok": True, "errors": []}


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
    user_id: str = "anon",
) -> bytes:
    """Render a PresentationPlan to PPTX bytes using canonical visual blocks."""
    from app.services.mentrix.presentation.blocks import VISUAL_KINDS, text_lines
    from app.services.mentrix.presentation.layout import choose_layout, place_blocks
    from app.services.mentrix.presentation.visual import paint_block

    slides_in = list(plan.get("slides") or [])
    if not slides_in:
        raise UnsafePptxError("plan_has_no_slides")
    _prepare_image_assets(plan, user_id=user_id)
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
        layout_intent = choose_layout(slide_spec)
        preferred = str(slide_spec.get("master_layout_name") or "")
        layout = _pick_layout(prs, layout_intent, definition, preferred_name=preferred)
        slide = prs.slides.add_slide(layout)
        try:
            fallback_index = int(slide_spec.get("index") or 0)
        except (TypeError, ValueError):
            fallback_index = 0
        title = str(slide_spec.get("title") or f"Slide {fallback_index + 1}")
        bullets = text_lines(list(slide_spec.get("blocks") or []))
        if not bullets:
            blocks = list(slide_spec.get("content_blocks") or [])
            bullets = [str(b.get("text") or "").strip() for b in blocks if str(b.get("text") or "").strip()]
        visuals = [b for b in list(slide_spec.get("blocks") or []) if str(b.get("kind") or "") in VISUAL_KINDS]
        skip_body = layout_intent in {"full_image", "quote"}
        regions = slide_spec.get("composed_regions") if isinstance(slide_spec.get("composed_regions"), dict) else None
        if visuals and regions:
            body = regions.get("body") if isinstance(regions.get("body"), dict) else None
            visual = regions.get("visual") if isinstance(regions.get("visual"), dict) else None
            if body and visual and body.get("x") == visual.get("x") and body.get("y") == visual.get("y"):
                skip_body = True
        _fill_placeholder(
            slide,
            title=title,
            bullets=[] if skip_body else bullets,
            regions=regions,
            skip_body=skip_body,
        )
        placements = place_blocks(slide_spec, prs=prs, definition=definition)
        for item in placements:
            paint_block(slide, item["block"], item["geometry"], user_id=user_id)
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

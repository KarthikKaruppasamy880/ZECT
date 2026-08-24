"""Write editor text/notes back into OOXML (S5 round-trip). Sidecar remains source of truth if this fails."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Inches

from app.services.mentrix.presentation.renderer import _set_notes, validate_generated_pptx


def apply_document_to_pptx(
    path: str | Path,
    slides: list[dict[str, Any]],
    *,
    user_id: str = "anon",
) -> dict[str, Any]:
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
        _apply_visual_blocks(slide, spec, user_id=user_id)
    tmp = pptx.with_name(f"{pptx.stem}.zect-tmp{pptx.suffix}")
    try:
        prs.save(str(tmp))
        data = tmp.read_bytes()
        validate_generated_pptx(data, n_slides=len(prs.slides))
        os.replace(tmp, pptx)
        try:
            from app.services.mentrix.presentation.slide_preview import invalidate_slide_previews

            invalidate_slide_previews(pptx)
        except Exception:
            pass
        try:
            from app.services.mentrix.presentation.final_pptx_inspector import inspect_and_repair_pptx

            repaired, _rep = inspect_and_repair_pptx(pptx.read_bytes())
            pptx.write_bytes(repaired)
        except Exception:
            pass
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    return {"ok": True, "path": str(pptx), "slide_count": len(prs.slides), "ooxml_roundtrip": True}


def _drop_pictures(slide) -> None:
    doomed = []
    for shape in slide.shapes:
        try:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                doomed.append(shape)
        except (ValueError, AttributeError):
            continue
    for shape in doomed:
        el = shape._element  # noqa: SLF001 — python-pptx has no public picture delete
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)


def _update_table(slide, block: dict[str, Any]) -> bool:
    content = block.get("content") if isinstance(block.get("content"), dict) else {}
    headers = [str(h) for h in list(content.get("headers") or [])]
    rows = [list(r) for r in list(content.get("rows") or []) if isinstance(r, list)]
    if not headers or not rows:
        return False
    for shape in slide.shapes:
        if not getattr(shape, "has_table", False):
            continue
        table = shape.table
        n_rows = min(len(table.rows), 1 + len(rows))
        n_cols = min(len(table.columns), len(headers))
        for j in range(n_cols):
            table.cell(0, j).text = headers[j][:80]
        for i in range(1, n_rows):
            row = rows[i - 1]
            for j in range(n_cols):
                table.cell(i, j).text = str(row[j] if j < len(row) else "")[:120]
        return True
    return False


def _apply_visual_blocks(slide, spec: dict[str, Any], *, user_id: str) -> None:
    from app.services.mentrix.presentation.charts import add_chart, replace_chart_data
    from app.services.mentrix.presentation.visual import paint_image, paint_table

    blocks = spec.get("blocks") if isinstance(spec.get("blocks"), list) else []
    default_geom = {"x": int(Inches(0.6)), "y": int(Inches(1.6)), "cx": int(Inches(8.8)), "cy": int(Inches(4.6))}
    replaced_image = False
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = str(block.get("kind") or "")
        geom = block.get("geometry") if isinstance(block.get("geometry"), dict) else default_geom
        geom = {
            "x": int(geom.get("x") or default_geom["x"]),
            "y": int(geom.get("y") or default_geom["y"]),
            "cx": int(geom.get("cx") or default_geom["cx"]),
            "cy": int(geom.get("cy") or default_geom["cy"]),
        }
        if kind == "chart":
            if not replace_chart_data(slide, block):
                add_chart(slide, block, geom)
        elif kind == "table":
            if not _update_table(slide, block):
                paint_table(slide, block, geom)
        elif kind == "image":
            if not replaced_image:
                _drop_pictures(slide)
                replaced_image = True
            paint_image(slide, block, geom, user_id=user_id)
        elif kind in {"shape", "metric", "quote", "diagram"}:
            from app.services.mentrix.presentation.visual import paint_block

            already = False
            for shape in slide.shapes:
                try:
                    if shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE:
                        already = True
                        break
                except (ValueError, AttributeError):
                    continue
            if not already:
                paint_block(slide, block, geom, user_id=user_id)


def _write_slide_text(slide, text: str) -> None:
    """Update existing title/body in place. Never add a covering dump textbox."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:160] if lines else text[:160]
    body = lines[1:]
    title_written = False
    if slide.shapes.title is not None:
        slide.shapes.title.text = title
        title_written = True
        rest = body
    else:
        rest = lines or [text]
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        try:
            ph_type = shape.placeholder_format.type
        except ValueError:
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
    if not rest:
        return
    # Prefer rewriting an existing non-placeholder text frame rather than stacking a new box.
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        try:
            shape.placeholder_format.type
            continue
        except ValueError:
            current = (shape.text_frame.text or "").strip()
            if not current:
                continue
            if title_written and current[:80] == title[:80]:
                continue
            tf = shape.text_frame
            tf.clear()
            tf.text = rest[0][:800]
            for extra in rest[1:8]:
                p = tf.add_paragraph()
                p.text = extra[:800]
            return

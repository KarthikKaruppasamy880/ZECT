"""Recent generated decks in the allowlisted PPTX output directory."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from pptx import Presentation

from app.services.mentrix.presentation.native_provider import _unique_pptx_path
from app.services.pptx_paths import default_pptx_save_dir, notes_sidecar_for_pptx, resolve_allowlisted_pptx


def list_recent_decks(*, limit: int = 24) -> list[dict[str, Any]]:
    root = default_pptx_save_dir()
    files = sorted(root.glob("*.pptx"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for path in files[: max(1, min(80, limit))]:
        sidecar = notes_sidecar_for_pptx(path)
        n_slides = 0
        try:
            prs = Presentation(str(path))
            n_slides = len(prs.slides)
        except Exception:
            n_slides = 0
        out.append(
            {
                "id": path.stem,
                "name": path.name,
                "path": str(path),
                "modified": int(path.stat().st_mtime),
                "bytes": path.stat().st_size,
                "slide_count": n_slides,
                "has_notes": sidecar.is_file(),
                "preview_available": True,
            }
        )
    return out


def create_blank_pptx(*, filename: str = "untitled.pptx") -> Path:
    prs = Presentation()
    layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = "Untitled presentation"
    dest = _unique_pptx_path(default_pptx_save_dir(), filename)
    buf = io.BytesIO()
    prs.save(buf)
    dest.write_bytes(buf.getvalue())
    return dest


def import_pptx_bytes(data: bytes, *, filename: str) -> Path:
    dest = _unique_pptx_path(default_pptx_save_dir(), filename or "imported.pptx")
    dest.write_bytes(data)
    return dest


def quality_gate_for_path(path_str: str) -> dict[str, Any]:
    from app.services.mentrix.presentation.final_pptx_inspector import inspect_pptx_bytes

    pptx = resolve_allowlisted_pptx(path_str)
    report = inspect_pptx_bytes(pptx.read_bytes())
    hard = list(report.get("hard_findings") or [])
    blocked = bool(report.get("export_blocked") or hard or report.get("status") == "FAIL")
    warnings: list[str] = []
    if not report.get("has_notes"):
        warnings.append("notes_missing")
    return {
        "ok": True,
        "path": str(pptx),
        "export_blocked": blocked,
        "hard_blocked": blocked,
        "accept_warnings_allowed": bool(warnings) and not blocked,
        "warnings": warnings,
        "hard_findings": hard,
        "quality_passed": not blocked,
        "slide_count": report.get("slide_count") or 0,
        "overlap_count": report.get("overlap_count") or 0,
        "clipped_text_count": report.get("out_of_bounds_count") or 0,
        "covering_dump_count": report.get("covering_dump_count") or 0,
        "broken_rel_count": report.get("broken_rel_count") or 0,
        "final_quality_status": report.get("status"),
        "inspector": report,
    }

"""OOXML slide preview includes chart graphicFrame; COM stays opt-in."""

from pathlib import Path

from app.services.mentrix.presentation.slide_preview import (
    KIND_OOXML,
    cache_slide_preview,
    render_slide_png_bytes,
    _try_com_png,
)
from app.services.pptx_parse import parse_pptx_bytes
from tests.fixes_and_phases.pptx_fixtures import make_chart_pptx_bytes


def test_parse_extracts_chart_frame_geometry():
    slides = parse_pptx_bytes(make_chart_pptx_bytes())
    assert slides
    charts = [b for b in (slides[0].get("blocks") or []) if b.get("kind") == "chart"]
    assert charts
    geo = charts[0].get("geometry") or {}
    assert int(geo.get("cx") or 0) > 0
    assert int(geo.get("cy") or 0) > 0


def test_ooxml_preview_includes_chart_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.mentrix.presentation.slide_preview._try_com_png",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.mentrix.presentation.slide_preview._try_libreoffice_png",
        lambda *_a, **_k: False,
    )
    data = make_chart_pptx_bytes()
    png = render_slide_png_bytes(data, 0)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 200
    dest = tmp_path / "deck.pptx"
    dest.write_bytes(data)
    path, kind = cache_slide_preview(dest, 0, force=True)
    assert kind == KIND_OOXML
    assert path.is_file()


def test_com_export_skipped_without_live_flag(monkeypatch, tmp_path):
    monkeypatch.delenv("ZECT_LIVE_PPT_COM", raising=False)
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"not-used")
    dest = tmp_path / "out.png"
    assert _try_com_png(pptx, 0, dest) is False

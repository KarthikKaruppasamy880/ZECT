"""OOXML slide preview includes chart graphicFrame; COM is opt-out via ZECT_LIVE_PPT_COM=0."""

from pathlib import Path

from app.services.mentrix.presentation.slide_preview import (
    KIND_OOXML,
    cache_slide_preview,
    render_slide_png_bytes,
    _try_com_png,
)
from app.services.pptx_parse import extract_slide_blocks, parse_pptx_bytes
from tests.fixes_and_phases.pptx_fixtures import make_chart_pptx_bytes, make_group_pptx_bytes


def test_parse_extracts_chart_frame_geometry():
    slides = parse_pptx_bytes(make_chart_pptx_bytes())
    assert slides
    charts = [b for b in (slides[0].get("blocks") or []) if b.get("kind") == "chart"]
    assert charts
    geo = charts[0].get("geometry") or {}
    assert int(geo.get("cx") or 0) > 0
    assert int(geo.get("cy") or 0) > 0


def test_grouped_shape_uses_parent_offset():
    data = make_group_pptx_bytes()
    slides = parse_pptx_bytes(data)
    blocks = slides[0].get("blocks") or []
    kinds = {str(b.get("kind")) for b in blocks}
    assert "chart" not in kinds
    texts = [b for b in blocks if "HelloGroup" in str((b.get("content") or {}).get("text") or "")]
    assert texts
    geo = texts[0].get("geometry") or {}
    assert int(geo.get("x") or 0) == 1_200_000
    assert int(geo.get("y") or 0) == 600_000
    empty_ph = [
        b
        for b in blocks
        if int((b.get("geometry") or {}).get("cy") or 0) == 800_000 and not (b.get("content") or {}).get("text")
    ]
    assert empty_ph == []


def test_extract_skips_unused_placeholder_on_xml():
    import io
    import zipfile

    data = make_group_pptx_bytes()
    xml = zipfile.ZipFile(io.BytesIO(data)).read("ppt/slides/slide1.xml")
    blocks = extract_slide_blocks(xml)
    assert any("HelloGroup" in str((b.get("content") or {}).get("text") or "") for b in blocks)
    assert not any(int((b.get("geometry") or {}).get("cy") or 0) == 800_000 for b in blocks)


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


def test_com_export_skipped_when_opted_out(monkeypatch, tmp_path):
    monkeypatch.setenv("ZECT_LIVE_PPT_COM", "0")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"not-used")
    dest = tmp_path / "out.png"
    assert _try_com_png(pptx, 0, dest) is False

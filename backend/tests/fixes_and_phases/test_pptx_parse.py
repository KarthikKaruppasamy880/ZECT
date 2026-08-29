"""PPTX parse for Present Deck browser narration."""

from io import BytesIO
import zipfile

from app.services.pptx_parse import parse_pptx_bytes


def _minimal_pptx_with_text(slide_text: str) -> bytes:
    """Build a tiny valid pptx zip with one slide containing slide_text."""
    slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:sp><p:txBody><a:p><a:r><a:t>{slide_text}</a:t></a:r></a:p></p:txBody></p:sp>
  </p:spTree></p:cSld>
</p:sld>
"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>
""",
        )
        zf.writestr("ppt/slides/slide1.xml", slide_xml)
    return buf.getvalue()


def test_parse_pptx_bytes_extracts_slide_text():
    data = _minimal_pptx_with_text("Hello Mentrix Present")
    slides = parse_pptx_bytes(data)
    assert len(slides) == 1
    assert "Hello Mentrix Present" in (slides[0].get("text") or "")
    assert "visuals" in slides[0]


def test_zinnia_large_hero_image_resolves_to_asset_id():
    """Regression: ppt/media/image12.png (~1.93MB) must not be dropped by _MAX_PART_BYTES."""
    from pathlib import Path

    master = Path(__file__).resolve().parents[3] / ".zect" / "present-templates" / "masters" / "zinnia-executive-v1.pptx"
    if not master.is_file() or master.stat().st_size < 1_000_000:
        import pytest

        pytest.skip("real Zinnia master not present locally")
    slides = parse_pptx_bytes(master.read_bytes())
    images = [
        b
        for b in (slides[0].get("blocks") or [])
        if isinstance(b, dict) and b.get("kind") == "image"
    ]
    assert images
    hero = images[0].get("content") or {}
    assert hero.get("asset_id") or str(hero.get("data_url") or "").startswith("data:image/")

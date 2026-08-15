"""Best-effort slide PNG from OOXML geometry. Not a substitute for PowerPoint proof."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

EMU_PER_PX = 9525  # 96 dpi


def _slides(data: bytes) -> list[bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = sorted(
            n
            for n in zf.namelist()
            if n.startswith("ppt/slides/slide") and n.endswith(".xml") and "/_rels/" not in n.replace("\\", "/")
        )
        return [zf.read(n) for n in names]


def _shapes(xml: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml)
    out: list[dict[str, Any]] = []
    for sp in root.findall(f".//{{{_NS_P}}}sp"):
        off = sp.find(f".//{{{_NS_A}}}off")
        ext = sp.find(f".//{{{_NS_A}}}ext")
        texts = [t.text or "" for t in sp.findall(f".//{{{_NS_A}}}t")]
        out.append(
            {
                "x": int(off.get("x") or 0) if off is not None else 0,
                "y": int(off.get("y") or 0) if off is not None else 0,
                "cx": int(ext.get("cx") or 1) if ext is not None else 1,
                "cy": int(ext.get("cy") or 1) if ext is not None else 1,
                "text": " ".join(t.strip() for t in texts if t.strip())[:180],
            }
        )
    return out


def render_slide_png_bytes(data: bytes, index: int = 0, *, width: int = 960) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    slides = _slides(data)
    if not slides:
        raise ValueError("no_slides")
    idx = max(0, min(index, len(slides) - 1))
    shapes = _shapes(slides[idx])
    slide_w, slide_h = 9144000, 5143500
    scale = width / slide_w
    height = max(1, int(slide_h * scale))
    img = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    for shape in shapes:
        x = int(shape["x"] * scale)
        y = int(shape["y"] * scale)
        x2 = x + max(4, int(shape["cx"] * scale))
        y2 = y + max(4, int(shape["cy"] * scale))
        draw.rectangle([x, y, x2, y2], outline=(15, 118, 110), fill=(255, 255, 255))
        if shape["text"] and font is not None:
            draw.text((x + 6, y + 4), shape["text"][:80], fill=(15, 23, 42), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def cache_slide_preview(pptx: Path, index: int = 0) -> Path:
    dest = pptx.parent / f"{pptx.stem}.slide-{index}.png"
    if dest.is_file() and dest.stat().st_mtime >= pptx.stat().st_mtime:
        return dest
    png = render_slide_png_bytes(pptx.read_bytes(), index)
    dest.write_bytes(png)
    return dest

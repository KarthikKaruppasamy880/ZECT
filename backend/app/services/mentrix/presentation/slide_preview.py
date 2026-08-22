"""Slide PNG: PowerPoint COM or LibreOffice when available, else OOXML wireframe."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from app.services.pptx_parse import extract_slide_blocks, slide_emu_size

_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

EMU_PER_PX = 9525  # 96 dpi
KIND_COM = "com"
KIND_LIBREOFFICE = "libreoffice"
KIND_OOXML = "ooxml"


def _slides(data: bytes) -> list[bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = sorted(
            n
            for n in zf.namelist()
            if n.startswith("ppt/slides/slide") and n.endswith(".xml") and "/_rels/" not in n.replace("\\", "/")
        )
        return [zf.read(n) for n in names]


def _kind_path(dest: Path) -> Path:
    return dest.with_name(dest.name + ".kind")


def _write_kind(dest: Path, kind: str) -> None:
    try:
        _kind_path(dest).write_text(kind, encoding="utf-8")
    except OSError:
        pass


def _read_kind(dest: Path) -> str:
    try:
        raw = _kind_path(dest).read_text(encoding="utf-8").strip()
        if raw in {KIND_COM, KIND_LIBREOFFICE, KIND_OOXML}:
            return raw
    except OSError:
        pass
    return KIND_OOXML


def invalidate_slide_previews(pptx: Path) -> None:
    """Drop cached PNGs so Save + chart type-change re-rasterize."""
    stem = pptx.stem
    parent = pptx.parent
    for path in parent.glob(f"{stem}.slide-*.png"):
        path.unlink(missing_ok=True)
        _kind_path(path).unlink(missing_ok=True)


def _shapes(xml: bytes) -> list[dict[str, Any]]:
    """Legacy p:sp boxes plus graphicFrame/pic from extract_slide_blocks."""
    out: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        root = None
    if root is not None:
        for sp in root.findall(f".//{{{_NS_P}}}sp"):
            off = sp.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}off")
            ext = sp.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
            texts = [
                t.text or ""
                for t in sp.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}t")
            ]
            out.append(
                {
                    "kind": "shape",
                    "x": int(off.get("x") or 0) if off is not None else 0,
                    "y": int(off.get("y") or 0) if off is not None else 0,
                    "cx": int(ext.get("cx") or 1) if ext is not None else 1,
                    "cy": int(ext.get("cy") or 1) if ext is not None else 1,
                    "text": " ".join(t.strip() for t in texts if t.strip())[:180],
                }
            )
    for block in extract_slide_blocks(xml):
        geo = block.get("geometry") or {}
        kind = str(block.get("kind") or "shape")
        if kind in {"text", "shape"}:
            continue
        out.append(
            {
                "kind": kind,
                "x": int(geo.get("x") or 0),
                "y": int(geo.get("y") or 0),
                "cx": int(geo.get("cx") or 1),
                "cy": int(geo.get("cy") or 1),
                "text": str((block.get("content") or {}).get("title") or kind).upper()[:40],
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
    slide_w, slide_h = slide_emu_size(data)
    scale = width / max(slide_w, 1)
    height = max(1, int(slide_h * scale))
    img = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    fills = {
        "chart": ((204, 251, 241), (13, 148, 136)),
        "table": ((224, 242, 254), (2, 132, 199)),
        "image": ((226, 232, 240), (71, 85, 105)),
        "shape": ((255, 255, 255), (15, 118, 110)),
    }
    for shape in shapes:
        kind = str(shape.get("kind") or "shape")
        fill, outline = fills.get(kind, fills["shape"])
        x = int(shape["x"] * scale)
        y = int(shape["y"] * scale)
        x2 = x + max(4, int(shape["cx"] * scale))
        y2 = y + max(4, int(shape["cy"] * scale))
        draw.rectangle([x, y, x2, y2], outline=outline, fill=fill)
        label = str(shape.get("text") or kind).strip()[:80]
        if kind in {"chart", "table", "image"}:
            label = kind.upper() + (f" {label}" if label and label.lower() != kind else "")
        if label and font is not None:
            draw.text((x + 6, y + 4), label[:80], fill=(15, 23, 42), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _try_com_png(pptx: Path, index: int, dest: Path) -> bool:
    if os.environ.get("ZECT_LIVE_PPT_COM", "").strip() != "1":
        return False
    if os.name != "nt":
        return False
    try:
        import win32com.client  # type: ignore
    except ImportError:
        return False
    app = None
    try:
        app = win32com.client.Dispatch("PowerPoint.Application")
        pres = app.Presentations.Open(str(pptx.resolve()), WithWindow=False)
        n = index + 1
        count = int(pres.Slides.Count)
        if n < 1 or n > count:
            pres.Close()
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        pres.Slides(n).Export(str(dest.resolve()), "PNG", 1920, 1080)
        pres.Close()
        return dest.is_file() and dest.stat().st_size > 32
    except Exception:
        return False
    finally:
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass


def _soffice_bin() -> str | None:
    for name in ("soffice", "soffice.exe", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path("/usr/bin/soffice"),
        Path("/usr/bin/libreoffice"),
        Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _try_libreoffice_png(pptx: Path, index: int, dest: Path) -> bool:
    soffice = _soffice_bin()
    if not soffice:
        return False
    tmp = tempfile.mkdtemp(prefix="zect-lo-")
    try:
        subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", "png", "--outdir", tmp, str(pptx.resolve())],
            check=True,
            timeout=90,
            capture_output=True,
        )
        produced = sorted(Path(tmp).glob("*.png"))
        if not produced:
            return False
        pick = produced[0]
        if len(produced) > 1:
            if index >= len(produced):
                return False
            pick = produced[index]
        elif index != 0:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pick.read_bytes())
        return dest.is_file() and dest.stat().st_size > 32
    except (subprocess.SubprocessError, OSError, TimeoutError):
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cache_slide_preview(pptx: Path, index: int = 0, *, force: bool = False) -> tuple[Path, str]:
    dest = pptx.parent / f"{pptx.stem}.slide-{index}.png"
    if not force and dest.is_file() and dest.stat().st_mtime >= pptx.stat().st_mtime:
        return dest, _read_kind(dest)
    kind = KIND_OOXML
    if _try_com_png(pptx, index, dest):
        kind = KIND_COM
    elif _try_libreoffice_png(pptx, index, dest):
        kind = KIND_LIBREOFFICE
    else:
        png = render_slide_png_bytes(pptx.read_bytes(), index)
        dest.write_bytes(png)
        kind = KIND_OOXML
    _write_kind(dest, kind)
    return dest, kind

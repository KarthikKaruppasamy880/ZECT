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

from app.services.pptx_parse import extract_slide_blocks, parse_pptx_bytes, slide_emu_size

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


def _document_shapes(data: bytes, index: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Merged master/layout/slide blocks plus slide background metadata."""
    slides = parse_pptx_bytes(data)
    if not slides:
        return [], None
    idx = max(0, min(index, len(slides) - 1))
    row = slides[idx]
    blocks = row.get("blocks") if isinstance(row.get("blocks"), list) else []
    bg = row.get("background") if isinstance(row.get("background"), dict) else None
    out: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        geo = block.get("geometry") or {}
        kind = str(block.get("kind") or "shape")
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        out.append(
            {
                "kind": kind,
                "x": int(geo.get("x") or 0),
                "y": int(geo.get("y") or 0),
                "cx": int(geo.get("cx") or 1),
                "cy": int(geo.get("cy") or 1),
                "text": str(content.get("text") or content.get("title") or content.get("alt") or "")[:800],
                "fill": str(content.get("fill") or ""),
                "color": str(content.get("color") or ""),
                "data_url": str(content.get("data_url") or ""),
            }
        )
    return out, bg


def _shapes(xml: bytes) -> list[dict[str, Any]]:
    """Legacy slide-only boxes — prefer _document_shapes for previews."""
    out: list[dict[str, Any]] = []
    for block in extract_slide_blocks(xml):
        geo = block.get("geometry") or {}
        kind = str(block.get("kind") or "shape")
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        text = str(content.get("text") or content.get("title") or content.get("alt") or "")
        if kind in {"chart", "table", "image"}:
            text = kind.upper() + (f" {text}" if text and text.lower() != kind else "")
        out.append(
            {
                "kind": kind,
                "x": int(geo.get("x") or 0),
                "y": int(geo.get("y") or 0),
                "cx": int(geo.get("cx") or 1),
                "cy": int(geo.get("cy") or 1),
                "text": text[:80],
                "fill": str(content.get("fill") or ""),
                "data_url": str(content.get("data_url") or ""),
            }
        )
    return out


def render_slide_png_bytes(data: bytes, index: int = 0, *, width: int = 960) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    slides = _slides(data)
    if not slides:
        raise ValueError("no_slides")
    idx = max(0, min(index, len(slides) - 1))
    shapes, bg = _document_shapes(data, idx)
    slide_w, slide_h = slide_emu_size(data)
    scale = width / max(slide_w, 1)
    height = max(1, int(slide_h * scale))
    canvas_fill = (255, 255, 255)
    if bg and str(bg.get("fill") or "").startswith("#"):
        try:
            raw = str(bg["fill"]).lstrip("#")
            canvas_fill = tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[assignment]
        except (TypeError, ValueError):
            pass
    img = Image.new("RGB", (width, height), canvas_fill)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    def _parse_hex(color: str) -> tuple[int, int, int] | None:
        if not color.startswith("#") or len(color) != 7:
            return None
        try:
            return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
        except ValueError:
            return None

    def _wrap_text(text: str, max_px: int, size: int) -> list[str]:
        words = text.split()
        if not words:
            return []
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if len(trial) * (size * 0.55) <= max_px:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines[:8]

    locked_first = sorted(
        shapes,
        key=lambda s: (0 if str(s.get("kind") or "") in {"shape", "image"} and s.get("fill") else 1, int(s.get("y") or 0)),
    )

    for shape in locked_first:
        kind = str(shape.get("kind") or "shape")
        x = int(shape["x"] * scale)
        y = int(shape["y"] * scale)
        x2 = x + max(4, int(shape["cx"] * scale))
        y2 = y + max(4, int(shape["cy"] * scale))
        fill_hex = _parse_hex(str(shape.get("fill") or ""))
        if kind == "image" and str(shape.get("data_url") or "").startswith("data:image/"):
            try:
                import base64

                _head, b64 = str(shape["data_url"]).split(",", 1)
                im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
                im = im.resize((max(1, x2 - x), max(1, y2 - y)))
                img.paste(im, (x, y), im if im.mode == "RGBA" else None)
                continue
            except Exception:
                pass
        if kind in {"text", "quote", "metric", "body", "title", "subtitle"}:
            label = str(shape.get("text") or "").strip()
            if not label or font is None:
                continue
            size = max(10, min(28, int(max(12, (y2 - y) / max(1, len(label.split()) // 6 + 1)))))
            try:
                tfont = ImageFont.truetype("arial.ttf", size)
            except Exception:
                tfont = font
            color = _parse_hex(str(shape.get("color") or "")) or (15, 23, 42)
            if fill_hex and kind == "shape":
                draw.rectangle([x, y, x2, y2], fill=fill_hex)
            line_h = size + 2
            for li, line in enumerate(_wrap_text(label, max(8, x2 - x - 8), size)):
                draw.text((x + 4, y + 4 + li * line_h), line[:120], fill=color, font=tfont)
            continue
        fill = fill_hex or ((226, 232, 240) if kind == "image" else (232, 236, 241))
        draw.rectangle([x, y, x2, y2], fill=fill)
        label = str(shape.get("text") or "").strip()[:80]
        if label and font is not None and kind not in {"shape", "image"}:
            draw.text((x + 4, y + 2), label, fill=(15, 23, 42), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _try_com_png(pptx: Path, index: int, dest: Path) -> bool:
    if os.environ.get("ZECT_LIVE_PPT_COM", "").strip() == "0":
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


_read_kind = _read_kind
_write_kind = _write_kind
render_slide_png_bytes = render_slide_png_bytes
cache_slide_preview = cache_slide_preview
_try_com_png = _try_com_png
_try_com_png = _try_com_png

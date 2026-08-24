"""Parse .pptx slide text + speaker notes (zip/XML) for Present Deck narration."""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"


def slide_emu_size(data: bytes) -> tuple[int, int]:
    """Presentation slide size in EMUs (defaults to 16:9 widescreen)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("ppt/presentation.xml")
        root = ET.fromstring(xml)
        sz = root.find(f".//{{{_NS_P}}}sldSz")
        if sz is not None:
            return int(sz.get("cx") or 9144000), int(sz.get("cy") or 5143500)
    except (KeyError, ET.ParseError, ValueError, zipfile.BadZipFile, OSError):
        pass
    return 9144000, 5143500


def _read_xfrm(xfrm: ET.Element | None) -> dict[str, int] | None:
    if xfrm is None:
        return None
    off = xfrm.find(f"{{{_NS_A}}}off")
    ext = xfrm.find(f"{{{_NS_A}}}ext")
    if off is None or ext is None:
        return None
    try:
        geo = {
            "x": int(off.get("x") or 0),
            "y": int(off.get("y") or 0),
            "cx": int(ext.get("cx") or 0),
            "cy": int(ext.get("cy") or 0),
            "ch_x": 0,
            "ch_y": 0,
            "ch_cx": 0,
            "ch_cy": 0,
        }
    except (TypeError, ValueError):
        return None
    ch_off = xfrm.find(f"{{{_NS_A}}}chOff")
    ch_ext = xfrm.find(f"{{{_NS_A}}}chExt")
    if ch_off is not None:
        try:
            geo["ch_x"] = int(ch_off.get("x") or 0)
            geo["ch_y"] = int(ch_off.get("y") or 0)
        except (TypeError, ValueError):
            pass
    if ch_ext is not None:
        try:
            geo["ch_cx"] = int(ch_ext.get("cx") or 0)
            geo["ch_cy"] = int(ch_ext.get("cy") or 0)
        except (TypeError, ValueError):
            pass
    if geo["cx"] <= 0 or geo["cy"] <= 0:
        return None
    return geo


def _own_xfrm(el: ET.Element) -> dict[str, int] | None:
    """Shape/group transform on this element only — not nested descendants."""
    for child in list(el):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "xfrm":
            geo = _read_xfrm(child)
            if geo:
                return geo
        if tag in {"spPr", "grpSpPr"}:
            for sub in list(child):
                if sub.tag.rsplit("}", 1)[-1] == "xfrm":
                    geo = _read_xfrm(sub)
                    if geo:
                        return geo
    return None


def _map_geo(
    geo: dict[str, int],
    origin_x: int,
    origin_y: int,
    scale_x: float,
    scale_y: float,
    ch_x: int,
    ch_y: int,
) -> dict[str, int]:
    return {
        "x": int(origin_x + (geo["x"] - ch_x) * scale_x),
        "y": int(origin_y + (geo["y"] - ch_y) * scale_y),
        "cx": max(1, int(geo["cx"] * scale_x)),
        "cy": max(1, int(geo["cy"] * scale_y)),
    }


def _shape_text(el: ET.Element) -> str:
    parts = [(t.text or "").strip() for t in el.findall(f".//{{{_NS_A}}}t")]
    return " ".join(p for p in parts if p)[:180]


def _unused_placeholder(sp: ET.Element) -> bool:
    ph = sp.find(f".//{{{_NS_P}}}ph")
    if ph is None:
        return False
    text = _shape_text(sp)
    if not text:
        return True
    if re.search(r"click to (add|edit|insert)|click to edit master", text, re.I):
        return True
    return False


def extract_slide_blocks(xml: bytes, *, slide_index: int = 0) -> list[dict]:
    """EMU-aligned hit boxes for p:sp, p:pic, and graphicFrame (charts/tables)."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    blocks: list[dict] = []
    ordinal = 0

    def _push(kind: str, extra: dict | None, geo: dict[str, int]) -> None:
        nonlocal ordinal
        row: dict = {
            "kind": kind,
            "slide_index": slide_index,
            "geometry": {"x": geo["x"], "y": geo["y"], "cx": geo["cx"], "cy": geo["cy"]},
            "id": f"blk_{slide_index}_{kind}_{ordinal}",
        }
        if extra:
            row.update(extra)
        blocks.append(row)
        ordinal += 1

    def _walk(
        el: ET.Element,
        origin_x: int,
        origin_y: int,
        scale_x: float,
        scale_y: float,
        ch_x: int,
        ch_y: int,
    ) -> None:
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "grpSp":
            g = _own_xfrm(el)
            if g:
                gx = int(origin_x + (g["x"] - ch_x) * scale_x)
                gy = int(origin_y + (g["y"] - ch_y) * scale_y)
                ch_cx = g["ch_cx"] or g["cx"]
                ch_cy = g["ch_cy"] or g["cy"]
                nsx = scale_x * (g["cx"] / ch_cx if ch_cx else 1)
                nsy = scale_y * (g["cy"] / ch_cy if ch_cy else 1)
                for child in list(el):
                    _walk(child, gx, gy, nsx, nsy, g["ch_x"], g["ch_y"])
            else:
                for child in list(el):
                    _walk(child, origin_x, origin_y, scale_x, scale_y, ch_x, ch_y)
            return
        own = _own_xfrm(el)
        mapped = _map_geo(own, origin_x, origin_y, scale_x, scale_y, ch_x, ch_y) if own else None
        if tag == "sp" and mapped and not _unused_placeholder(el):
            text = _shape_text(el)
            extra = {"content": {"text": text}} if text else None
            _push("shape" if not text else "text", extra, mapped)
            return
        if tag == "pic" and mapped:
            _push("image", {"content": {"alt": _shape_text(el) or "Slide image"}}, mapped)
            return
        if tag == "graphicFrame" and mapped:
            blob = ET.tostring(el, encoding="unicode").lower()
            if "chart" in blob or f"{{{_NS_C}}}chart" in blob:
                _push("chart", {"content": {"chart_type": "column", "title": "Chart"}}, mapped)
            elif "<a:tbl" in blob or "a:tbl>" in blob:
                _push("table", {"content": {"title": "Table"}}, mapped)
            else:
                _push("shape", None, mapped)
            return
        for child in list(el):
            _walk(child, origin_x, origin_y, scale_x, scale_y, ch_x, ch_y)

    tree = root.find(f".//{{{_NS_P}}}spTree")
    _walk(tree if tree is not None else root, 0, 0, 1.0, 1.0, 0, 0)
    return blocks


def _extract_at_text(xml: str) -> str:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return re.sub(r"<[^>]+>", " ", xml)
    parts: list[str] = []
    for node in root.iter(f"{{{_NS_A}}}t"):
        t = (node.text or "").strip()
        if t:
            parts.append(t)
    return " ".join(parts).replace("  ", " ").strip()


def _visual_markers(xml: str) -> list[str]:
    markers: list[str] = []
    low = xml.lower()
    if "c:chart" in low or "c:plotarea" in low:
        markers.append("chart")
    if "<a:tbl" in low or "a:tbl>" in low:
        markers.append("table")
    if "dsp:sp" in low or "wps:wsp" in low or "p:cxnsp" in low:
        markers.append("diagram")
    return markers


def parse_pptx_bytes(data: bytes) -> list[dict]:
    """Return [{index, notes, text}, ...] from a .pptx archive."""
    if not data:
        raise ValueError("Empty PPTX")
    slides: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="mentrix-pptx-") as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / "deck.pptx"
        archive.write_bytes(data)
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(tmp_path)
        slides_dir = tmp_path / "ppt" / "slides"
        if not slides_dir.is_dir():
            return []
        slide_files = sorted(
            [p for p in slides_dir.iterdir() if re.fullmatch(r"slide\d+\.xml", p.name, re.I)],
            key=lambda p: int(re.search(r"\d+", p.name).group(0)) if re.search(r"\d+", p.name) else 0,
        )
        notes_dir = tmp_path / "ppt" / "notesSlides"
        for i, slide_path in enumerate(slide_files):
            slide_xml = slide_path.read_text(encoding="utf-8", errors="ignore")
            text = _extract_at_text(slide_xml)[:2000]
            num_m = re.search(r"\d+", slide_path.name)
            num = int(num_m.group(0)) if num_m else i + 1
            notes = ""
            notes_path = notes_dir / f"notesSlide{num}.xml"
            if notes_path.is_file():
                notes = _extract_at_text(notes_path.read_text(encoding="utf-8", errors="ignore"))[:2000]
                if re.search(r"click to edit master", notes, re.I) and len(notes) < 80:
                    notes = ""
            slides.append(
                {
                    "index": i,
                    "notes": notes,
                    "text": text,
                    "visuals": _visual_markers(slide_xml),
                    "blocks": extract_slide_blocks(slide_path.read_bytes(), slide_index=i),
                }
            )
    return slides


parse_pptx_bytes = parse_pptx_bytes
extract_slide_blocks = extract_slide_blocks
slide_emu_size = slide_emu_size

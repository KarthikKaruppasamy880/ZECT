"""Parse .pptx slide text + speaker notes (zip/XML) for Present Deck narration."""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


_A_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
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


def _xfrm_geometry(el: ET.Element) -> dict[str, int] | None:
    xfrm_nodes = list(el.findall(f"./{{{_NS_P}}}xfrm"))
    xfrm_nodes.extend(el.findall(f".//{{{_NS_A}}}xfrm"))
    xfrm_nodes.extend(el.findall(f".//{{{_NS_P}}}xfrm"))
    for xfrm in xfrm_nodes:
        off = xfrm.find(f"{{{_NS_A}}}off")
        ext = xfrm.find(f"{{{_NS_A}}}ext")
        if off is None or ext is None:
            continue
        try:
            geo = {
                "x": int(off.get("x") or 0),
                "y": int(off.get("y") or 0),
                "cx": int(ext.get("cx") or 0),
                "cy": int(ext.get("cy") or 0),
            }
        except (TypeError, ValueError):
            continue
        if geo["cx"] > 0 and geo["cy"] > 0:
            return geo
    return None


def _shape_text(el: ET.Element) -> str:
    parts = [(t.text or "").strip() for t in el.findall(f".//{{{_NS_A}}}t")]
    return " ".join(p for p in parts if p)[:180]


def extract_slide_blocks(xml: bytes, *, slide_index: int = 0) -> list[dict]:
    """EMU-aligned hit boxes for p:sp, p:pic, and graphicFrame (charts/tables)."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    blocks: list[dict] = []
    ordinal = 0

    def _push(kind: str, el: ET.Element, extra: dict | None = None) -> None:
        nonlocal ordinal
        geo = _xfrm_geometry(el)
        if not geo:
            return
        row: dict = {"kind": kind, "slide_index": slide_index, "geometry": geo, "id": f"blk_{slide_index}_{kind}_{ordinal}"}
        if extra:
            row.update(extra)
        blocks.append(row)
        ordinal += 1

    for sp in root.findall(f".//{{{_NS_P}}}sp"):
        text = _shape_text(sp)
        _push("shape" if not text else "text", sp, {"content": {"text": text}} if text else None)
    for pic in root.findall(f".//{{{_NS_P}}}pic"):
        _push("image", pic, {"content": {"alt": _shape_text(pic) or "Slide image"}})
    for gf in root.findall(f".//{{{_NS_P}}}graphicFrame"):
        blob = ET.tostring(gf, encoding="unicode").lower()
        if "chart" in blob or f"{{{_NS_C}}}chart" in blob:
            _push("chart", gf, {"content": {"chart_type": "column", "title": "Chart"}})
        elif "<a:tbl" in blob or "a:tbl>" in blob:
            _push("table", gf, {"content": {"title": "Table"}})
        else:
            _push("shape", gf)
    return blocks


def _extract_at_text(xml: str) -> str:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return re.sub(r"<[^>]+>", " ", xml)
    parts: list[str] = []
    for node in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t"):
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
            num = int(re.search(r"\d+", slide_path.name).group(0)) if re.search(r"\d+", slide_path.name) else i + 1
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

"""Parse .pptx slide text + speaker notes (zip/XML) for Present Deck narration."""

from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


_A_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


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
            slides.append({"index": i, "notes": notes, "text": text})
    return slides

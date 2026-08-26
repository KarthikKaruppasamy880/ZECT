"""Parse .pptx slide text, notes, and PresentationDocument blocks (zip/XML)."""

from __future__ import annotations

import base64
import io
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

_MAX_INLINE_IMAGE = 280_000
_MAX_PART_BYTES = 1_500_000
_MAX_MEDIA_BYTES = 8 * 1024 * 1024


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
    paras: list[str] = []
    for para in el.findall(f".//{{{_NS_A}}}p"):
        bits = [(t.text or "").strip() for t in para.findall(f".//{{{_NS_A}}}t")]
        line = " ".join(b for b in bits if b)
        if line:
            paras.append(line)
    return "\n".join(paras)[:800]


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


def _has_placeholder(el: ET.Element) -> bool:
    return el.find(f".//{{{_NS_P}}}ph") is not None


def _nv_pr(el: ET.Element) -> dict[str, str]:
    node = el.find(f".//{{{_NS_P}}}cNvPr")
    if node is None:
        node = el.find(f".//{{{_NS_A}}}cNvPr")
    if node is None:
        return {}
    return {"name": node.get("name") or "", "id": node.get("id") or ""}


def _solid_fill(el: ET.Element) -> str | None:
    sp_pr = None
    for child in list(el):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in {"spPr", "grpSpPr"}:
            sp_pr = child
            break
    if sp_pr is None:
        return None
    srgb = sp_pr.find(f".//{{{_NS_A}}}srgbClr")
    val = (srgb.get("val") if srgb is not None else None) or ""
    if len(val) == 6 and re.fullmatch(r"[0-9A-Fa-f]{6}", val):
        return f"#{val}"
    return None


def _parse_rels(xml: bytes) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return out
    for rel in list(root):
        rid = rel.get("Id") or ""
        if not rid:
            continue
        out[rid] = {
            "type": rel.get("Type") or "",
            "target": (rel.get("Target") or "").replace("\\", "/"),
        }
    return out


def _resolve_part(target: str, *, from_dir: str) -> str:
    joined = posixpath.normpath(f"{from_dir.rstrip('/')}/{target.lstrip('/')}")
    return joined.lstrip("/")


def _data_url(data: bytes, name: str) -> str | None:
    if not data or len(data) > _MAX_INLINE_IMAGE:
        return None
    ext = name.rsplit(".", 1)[-1].lower()
    mime = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/png")
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif data[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    elif data[:6] in {b"GIF87a", b"GIF89a"}:
        mime = "image/gif"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _chart_type_from_xml(xml: bytes) -> str:
    low = xml.lower()
    if b"radarchart" in low:
        return "radar"
    if b"doughnutchart" in low or b"doughnut" in low:
        return "donut"
    if b"piechart" in low:
        return "pie"
    if b"linechart" in low:
        return "line"
    if b"areachart" in low:
        return "area"
    if b"scatterchart" in low:
        return "scatter"
    if b"barchart" in low:
        return "bar"
    return "column"


def _cache_pts(parent: ET.Element, cache_tag: str) -> list[str]:
    pts: list[tuple[int, str]] = []
    for cache in parent.findall(f".//{{{_NS_C}}}{cache_tag}"):
        for pt in cache.findall(f"{{{_NS_C}}}pt"):
            try:
                idx = int(pt.get("idx") or 0)
            except (TypeError, ValueError):
                idx = len(pts)
            val = pt.find(f"{{{_NS_C}}}v")
            pts.append((idx, (val.text or "").strip() if val is not None else ""))
    pts.sort(key=lambda row: row[0])
    return [v for _, v in pts]


def _chart_from_xml(xml: bytes) -> dict:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return {"chart_type": _chart_type_from_xml(xml), "title": "Chart"}
    categories: list[str] = []
    series: list[dict] = []
    for ser in root.findall(f".//{{{_NS_C}}}ser"):
        name = "Series"
        tx = ser.find(f"{{{_NS_C}}}tx")
        if tx is not None:
            v = tx.find(f".//{{{_NS_C}}}v")
            if v is not None and (v.text or "").strip():
                name = (v.text or "").strip()[:80]
        cat_el = ser.find(f"{{{_NS_C}}}cat")
        if cat_el is not None:
            cats = _cache_pts(cat_el, "strCache") or _cache_pts(cat_el, "strLit")
            if cats and not categories:
                categories = [c[:80] for c in cats if c][:24]
        val_el = ser.find(f"{{{_NS_C}}}val")
        nums = []
        if val_el is not None:
            nums = _cache_pts(val_el, "numCache") or _cache_pts(val_el, "numLit")
        values: list[float] = []
        for raw in nums[:24]:
            try:
                values.append(float(raw))
            except (TypeError, ValueError):
                continue
        if values:
            series.append({"name": name, "values": values})
    return {
        "chart_type": _chart_type_from_xml(xml),
        "title": "Chart",
        "categories": categories,
        "series": series,
        "legend": True,
    }


def _table_from_frame(el: ET.Element) -> dict | None:
    tbl = el.find(f".//{{{_NS_A}}}tbl")
    if tbl is None:
        return None
    rows: list[list[str]] = []
    for tr in tbl.findall(f"{{{_NS_A}}}tr"):
        cells = [_shape_text(tc) or "" for tc in tr.findall(f"{{{_NS_A}}}tc")]
        if cells:
            rows.append(cells)
    if not rows:
        return None
    headers = [h or f"Col {i + 1}" for i, h in enumerate(rows[0])]
    body = rows[1:] if len(rows) > 1 else [[""] * len(headers)]
    return {"title": "Table", "headers": headers, "rows": body}


def _rel_part(
    el: ET.Element,
    rels: dict[str, dict[str, str]] | None,
    parts: dict[str, bytes] | None,
    *,
    from_dir: str,
    attr: str = "embed",
) -> tuple[str, bytes | None]:
    blip = el.find(f".//{{{_NS_A}}}blip")
    rid = ""
    if blip is not None:
        rid = blip.get(f"{{{_NS_R}}}{attr}") or blip.get(attr) or ""
        if not rid and attr == "embed":
            rid = blip.get(f"{{{_NS_R}}}link") or blip.get("link") or ""
    if not rid:
        chart = el.find(f".//{{{_NS_C}}}chart")
        if chart is not None:
            rid = chart.get(f"{{{_NS_R}}}id") or ""
        if not rid:
            for node in el.iter():
                hit = node.get(f"{{{_NS_R}}}id")
                if hit and rels and hit in rels:
                    rid = hit
                    break
    if not rid or not rels or rid not in rels:
        return "", None
    target = rels[rid].get("target") or ""
    part = _resolve_part(target, from_dir=from_dir)
    blob = (parts or {}).get(part)
    return part, blob


def extract_slide_blocks(
    xml: bytes,
    *,
    slide_index: int = 0,
    rels: dict[str, dict[str, str]] | None = None,
    parts: dict[str, bytes] | None = None,
    from_dir: str = "ppt/slides",
    skip_all_placeholders: bool = False,
    locked: bool = False,
    id_prefix: str = "",
) -> list[dict]:
    """EMU-aligned document blocks for p:sp, p:pic, groups, and graphicFrame (charts/tables)."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    blocks: list[dict] = []
    ordinal = 0

    def _push(kind: str, extra: dict | None, geo: dict[str, int]) -> None:
        nonlocal ordinal
        content = dict((extra or {}).get("content") or {}) if extra else {}
        if locked:
            content["locked"] = True
            content["layer"] = content.get("layer") or "master"
        row: dict = {
            "kind": kind,
            "slide_index": slide_index,
            "geometry": {"x": geo["x"], "y": geo["y"], "cx": geo["cx"], "cy": geo["cy"]},
            "id": f"blk_{slide_index}_{id_prefix}{kind}_{ordinal}",
            "provenance": {"source": "document", "generated": False},
        }
        if content:
            row["content"] = content
        blocks.append(row)
        ordinal += 1

    def _identity(el: ET.Element) -> dict:
        nv = _nv_pr(el)
        fill = _solid_fill(el)
        out: dict = {}
        if nv.get("name"):
            out["shape_name"] = nv["name"]
        if fill:
            out["fill"] = fill
        return out

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
        if tag == "sp" and mapped:
            if skip_all_placeholders and _has_placeholder(el):
                return
            if not skip_all_placeholders and _unused_placeholder(el):
                return
            text = _shape_text(el)
            ident = _identity(el)
            if text:
                ident["text"] = text
                _push("text", {"content": ident}, mapped)
            else:
                _push("shape", {"content": ident} if ident else None, mapped)
            return
        if tag == "pic" and mapped:
            ident = _identity(el)
            ident["alt"] = _shape_text(el) or ident.get("shape_name") or "Slide image"
            part, blob = _rel_part(el, rels, parts, from_dir=from_dir)
            if not blob:
                part, blob = _rel_part(el, rels, parts, from_dir=from_dir, attr="link")
            if blob:
                url = _data_url(blob, part)
                if url:
                    ident["data_url"] = url
                else:
                    try:
                        from app.services.mentrix.presentation.asset_resolver import store_image

                        meta = store_image(blob, user_id="parse", filename=posixpath.basename(part) or "slide.png")
                        ident["asset_id"] = meta.get("asset_id") or ""
                    except Exception:
                        pass
            _push("image", {"content": ident}, mapped)
            return
        if tag == "graphicFrame" and mapped:
            ident = _identity(el)
            blob = ET.tostring(el, encoding="unicode").lower()
            table = _table_from_frame(el)
            if table:
                table.update(ident)
                _push("table", {"content": table}, mapped)
                return
            if "chart" in blob or f"{{{_NS_C}}}chart" in blob:
                _part, chart_xml = _rel_part(el, rels, parts, from_dir=from_dir)
                content = _chart_from_xml(chart_xml) if chart_xml else {"chart_type": "column", "title": "Chart"}
                content.update(ident)
                _push("chart", {"content": content}, mapped)
                return
            nodes = [ln for ln in _shape_text(el).splitlines() if ln][:6]
            if nodes:
                ident["nodes"] = nodes
                ident["diagram_type"] = "boxes"
                _push("diagram", {"content": ident}, mapped)
            else:
                _push("shape", {"content": ident} if ident else None, mapped)
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


def _collect_parts(root: Path) -> dict[str, bytes]:
    parts: dict[str, bytes] = {}
    ppt = root / "ppt"
    if not ppt.is_dir():
        return parts
    for path in ppt.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        try:
            size = path.stat().st_size
        except OSError:
            continue
        limit = _MAX_MEDIA_BYTES if "/media/" in rel else _MAX_PART_BYTES
        if size > limit:
            continue
        parts[rel] = path.read_bytes()
    return parts


def _rels_for(parts: dict[str, bytes], part_path: str) -> dict[str, dict[str, str]]:
    directory, name = posixpath.split(part_path)
    rels_path = f"{directory}/_rels/{name}.rels"
    raw = parts.get(rels_path)
    return _parse_rels(raw) if raw else {}


def _rel_of_type(rels: dict[str, dict[str, str]], suffix: str) -> str | None:
    for row in rels.values():
        typ = row.get("type") or ""
        target = row.get("target") or ""
        if typ.endswith(suffix) or suffix in target:
            return target
    return None


def parse_pptx_bytes(data: bytes) -> list[dict]:
    """Return [{index, notes, text, blocks}, ...] from a .pptx archive."""
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
        parts = _collect_parts(tmp_path)
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
            slide_part = slide_path.relative_to(tmp_path).as_posix()
            slide_rels = _rels_for(parts, slide_part)
            layout_target = _rel_of_type(slide_rels, "/slideLayout")
            background: list[dict] = []
            if layout_target:
                layout_part = _resolve_part(layout_target, from_dir="ppt/slides")
                layout_xml = parts.get(layout_part)
                layout_rels = _rels_for(parts, layout_part)
                if layout_xml:
                    background.extend(
                        extract_slide_blocks(
                            layout_xml,
                            slide_index=i,
                            rels=layout_rels,
                            parts=parts,
                            from_dir=posixpath.dirname(layout_part),
                            skip_all_placeholders=True,
                            locked=True,
                            id_prefix="layout_",
                        )
                    )
                master_target = _rel_of_type(layout_rels, "/slideMaster")
                if master_target:
                    master_part = _resolve_part(master_target, from_dir=posixpath.dirname(layout_part))
                    master_xml = parts.get(master_part)
                    master_rels = _rels_for(parts, master_part)
                    if master_xml:
                        background = extract_slide_blocks(
                            master_xml,
                            slide_index=i,
                            rels=master_rels,
                            parts=parts,
                            from_dir=posixpath.dirname(master_part),
                            skip_all_placeholders=True,
                            locked=True,
                            id_prefix="master_",
                        ) + background
            slide_blocks = extract_slide_blocks(
                slide_path.read_bytes(),
                slide_index=i,
                rels=slide_rels,
                parts=parts,
                from_dir="ppt/slides",
            )
            slides.append(
                {
                    "index": i,
                    "notes": notes,
                    "text": text,
                    "visuals": _visual_markers(slide_xml),
                    "blocks": background + slide_blocks,
                }
            )
    return slides


parse_pptx_bytes = parse_pptx_bytes
extract_slide_blocks = extract_slide_blocks
slide_emu_size = slide_emu_size

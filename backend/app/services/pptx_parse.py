"""Parse .pptx slide text, notes, and PresentationDocument blocks (zip/XML)."""

from __future__ import annotations

import base64
import hashlib
import io
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

_MAX_INLINE_IMAGE = 280_000
_MAX_PART_BYTES = 2_000_000
_MAX_MEDIA_BYTES = 8_000_000

_SCHEME_ALIASES = {
    "bg1": "lt1",
    "bg2": "lt2",
    "tx1": "dk1",
    "tx2": "dk2",
    "accent1": "accent1",
    "accent2": "accent2",
    "accent3": "accent3",
    "accent4": "accent4",
    "accent5": "accent5",
    "accent6": "accent6",
    "hlink": "hlink",
    "folHlink": "folHlink",
}


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


def _hex_from_rgb(val: str) -> str | None:
    raw = (val or "").strip().upper()
    if len(raw) == 6 and re.fullmatch(r"[0-9A-Fa-f]{6}", raw):
        return f"#{raw}"
    return None


def _resolve_color_node(node: ET.Element | None, theme: dict[str, str] | None) -> str | None:
    if node is None:
        return None
    tag = node.tag.rsplit("}", 1)[-1]
    if tag == "srgbClr":
        return _hex_from_rgb(node.get("val") or "")
    if tag == "sysClr":
        return _hex_from_rgb(node.get("lastClr") or node.get("val") or "")
    if tag == "schemeClr":
        name = str(node.get("val") or "").strip()
        if not name:
            return None
        key = _SCHEME_ALIASES.get(name, name)
        colors = theme or {}
        return _hex_from_rgb(colors.get(key) or colors.get(name) or "")
    return None


def _resolve_fill(el: ET.Element | None, theme: dict[str, str] | None) -> str | None:
    if el is None:
        return None
    for child in list(el):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "solidFill":
            for sub in list(child):
                hit = _resolve_color_node(sub, theme)
                if hit:
                    return hit
        if tag in {"srgbClr", "schemeClr", "sysClr"}:
            hit = _resolve_color_node(child, theme)
            if hit:
                return hit
    return None


def _gradient_fill(sp_pr: ET.Element | None, theme: dict[str, str] | None) -> dict[str, Any] | None:
    if sp_pr is None:
        return None
    grad = sp_pr.find(f"{{{_NS_A}}}gradFill")
    if grad is None:
        grad = sp_pr.find(f".//{{{_NS_A}}}gradFill")
    if grad is None:
        return None
    stops: list[dict[str, Any]] = []
    for gs in grad.findall(f".//{{{_NS_A}}}gs"):
        try:
            pos = int(gs.get("pos") or 0)
        except (TypeError, ValueError):
            pos = 0
        for sub in list(gs):
            color = _resolve_color_node(sub, theme)
            if color:
                stops.append({"pos": pos, "color": color})
                break
    if not stops:
        return None
    lin = grad.find(f"{{{_NS_A}}}lin")
    try:
        angle = int(lin.get("ang") or 0) if lin is not None else 0
    except (TypeError, ValueError):
        angle = 0
    return {"stops": sorted(stops, key=lambda row: row["pos"]), "angle": angle}


def _shape_fill(el: ET.Element, theme: dict[str, str] | None) -> tuple[str | None, dict[str, Any] | None]:
    sp_pr = None
    for child in list(el):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in {"spPr", "grpSpPr"}:
            sp_pr = child
            break
    if sp_pr is None:
        return None, None
    grad = _gradient_fill(sp_pr, theme)
    solid = _resolve_fill(sp_pr, theme)
    if grad and grad.get("stops"):
        first = str(grad["stops"][0].get("color") or "")
        return first or solid, grad
    return solid, None


def _solid_fill(el: ET.Element) -> str | None:
    fill, _grad = _shape_fill(el, None)
    return fill


def _load_theme_colors(parts: dict[str, bytes]) -> dict[str, str]:
    pres = parts.get("ppt/presentation.xml")
    if not pres:
        return {}
    try:
        pres_root = ET.fromstring(pres)
    except ET.ParseError:
        return {}
    pres_rels = _parse_rels(parts.get("ppt/_rels/presentation.xml.rels") or b"")
    theme_target = _rel_of_type(pres_rels, "/theme")
    if not theme_target:
        return {}
    theme_part = _resolve_part(theme_target, from_dir="ppt")
    theme_xml = parts.get(theme_part)
    if not theme_xml:
        return {}
    try:
        root = ET.fromstring(theme_xml)
    except ET.ParseError:
        return {}
    scheme = root.find(f".//{{{_NS_A}}}clrScheme")
    if scheme is None:
        return {}
    colors: dict[str, str] = {}
    for child in list(scheme):
        tag = child.tag.rsplit("}", 1)[-1]
        for sub in list(child):
            val = _resolve_color_node(sub, None)
            if val:
                colors[tag] = val.lstrip("#")
                break
    return colors


def _text_style(el: ET.Element, theme: dict[str, str] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    tx = el.find(f".//{{{_NS_A}}}txBody")
    if tx is None:
        return out
    def_rpr: ET.Element | None = None
    p = tx.find(f"{{{_NS_A}}}p")
    if p is not None:
        p_pr = p.find(f"{{{_NS_A}}}pPr")
        if p_pr is not None:
            algn = (p_pr.get("algn") or "").strip().lower()
            if algn in {"l", "ctr", "r", "just"}:
                out["align"] = {"l": "left", "ctr": "center", "r": "right", "just": "justify"}[algn]
            def_rpr = p_pr.find(f"{{{_NS_A}}}defRPr")
        if def_rpr is None:
            r = p.find(f"{{{_NS_A}}}r")
            if r is not None:
                def_rpr = r.find(f"{{{_NS_A}}}rPr")
    if def_rpr is None:
        lst = tx.find(f"{{{_NS_A}}}lstStyle")
        if lst is not None:
            for lvl in range(1, 10):
                lvl_el = lst.find(f"{{{_NS_A}}}lvl{lvl}pPr")
                if lvl_el is None:
                    continue
                def_rpr = lvl_el.find(f"{{{_NS_A}}}defRPr")
                if def_rpr is not None:
                    break
    if def_rpr is not None:
        sz = def_rpr.get("sz")
        if sz:
            try:
                out["font_size_pt"] = round(int(sz) / 100, 1)
            except (TypeError, ValueError):
                pass
        if def_rpr.get("b") in {"1", "true"}:
            out["bold"] = True
        if def_rpr.get("i") in {"1", "true"}:
            out["italic"] = True
        color = _resolve_fill(def_rpr, theme)
        if color:
            out["color"] = color
    return out


def _extract_background(
    xml: bytes,
    *,
    rels: dict[str, dict[str, str]] | None,
    parts: dict[str, bytes] | None,
    from_dir: str,
    theme: dict[str, str] | None,
) -> dict[str, Any] | None:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    c_sld = root.find(f".//{{{_NS_P}}}cSld")
    if c_sld is None:
        return None
    bg = c_sld.find(f"{{{_NS_P}}}bg")
    if bg is None:
        return None
    bg_pr = bg.find(f"{{{_NS_P}}}bgPr")
    if bg_pr is not None:
        fill = _resolve_fill(bg_pr, theme)
        if fill:
            return {"fill": fill, "source": "bgPr"}
        blip = bg_pr.find(f".//{{{_NS_A}}}blip")
        if blip is not None:
            rid = blip.get(f"{{{_NS_R}}}embed") or blip.get("embed") or ""
            if rid and rels and rid in rels:
                target = rels[rid].get("target") or ""
                part = _resolve_part(target, from_dir=from_dir)
                blob = (parts or {}).get(part)
                row: dict[str, Any] = {"source": "bgPr", "media_part": part}
                if blob:
                    row["media_sha256"] = hashlib.sha256(blob).hexdigest()
                    url = _data_url(blob, part)
                    if url:
                        row["data_url"] = url
                return row
    bg_ref = bg.find(f"{{{_NS_P}}}bgRef")
    if bg_ref is not None:
        for child in list(bg_ref):
            fill = _resolve_color_node(child, theme)
            if fill:
                return {"fill": fill, "source": "bgRef"}
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
    theme: dict[str, str] | None = None,
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
        fill, gradient = _shape_fill(el, theme)
        out: dict = {}
        if nv.get("name"):
            out["shape_name"] = nv["name"]
        if fill:
            out["fill"] = fill
        if gradient:
            out["fill_gradient"] = gradient
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
            ident.update(_text_style(el, theme))
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
                    ident["media_part"] = part
                    ident["media_sha256"] = hashlib.sha256(blob).hexdigest()
                    try:
                        from app.services.mentrix.presentation.asset_resolver import store_image

                        meta = store_image(blob, user_id="parse", filename=posixpath.basename(part) or "slide.png")
                        ident["asset_id"] = meta.get("asset_id") or ""
                    except Exception:
                        pass
            elif part:
                ident["media_part"] = part
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
        limit = _MAX_MEDIA_BYTES if rel.startswith("ppt/media/") else _MAX_PART_BYTES
        try:
            if path.stat().st_size > limit:
                continue
        except OSError:
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
        theme_colors = _load_theme_colors(parts)
        slide_files = sorted(
            [p for p in slides_dir.iterdir() if re.fullmatch(r"slide\d+\.xml", p.name, re.I)],
            key=lambda p: int(re.search(r"\d+", p.name).group(0)) if re.search(r"\d+", p.name) else 0,
        )
        notes_dir = tmp_path / "ppt" / "notesSlides"
        slide_cx, slide_cy = slide_emu_size(data)
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
            slide_bg: dict[str, Any] | None = None
            layout_part = ""
            layout_xml: bytes | None = None
            layout_rels: dict[str, dict[str, str]] = {}
            master_part = ""
            master_xml: bytes | None = None
            master_rels: dict[str, dict[str, str]] = {}
            if layout_target:
                layout_part = _resolve_part(layout_target, from_dir="ppt/slides")
                layout_xml = parts.get(layout_part)
                layout_rels = _rels_for(parts, layout_part)
                master_target = _rel_of_type(layout_rels, "/slideMaster")
                if master_target:
                    master_part = _resolve_part(master_target, from_dir=posixpath.dirname(layout_part))
                    master_xml = parts.get(master_part)
                    master_rels = _rels_for(parts, master_part)
            for xml, rels, from_dir in (
                (master_xml, master_rels, posixpath.dirname(master_part) if master_part else ""),
                (layout_xml, layout_rels, posixpath.dirname(layout_part) if layout_part else ""),
                (slide_path.read_bytes(), slide_rels, "ppt/slides"),
            ):
                if not xml:
                    continue
                hit = _extract_background(
                    xml,
                    rels=rels,
                    parts=parts,
                    from_dir=from_dir or "ppt/slides",
                    theme=theme_colors,
                )
                if hit:
                    slide_bg = hit
            if master_xml:
                background.extend(
                    extract_slide_blocks(
                        master_xml,
                        slide_index=i,
                        rels=master_rels,
                        parts=parts,
                        from_dir=posixpath.dirname(master_part),
                        skip_all_placeholders=True,
                        locked=True,
                        id_prefix="master_",
                        theme=theme_colors,
                    )
                )
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
                        theme=theme_colors,
                    )
                )
            slide_blocks = extract_slide_blocks(
                slide_path.read_bytes(),
                slide_index=i,
                rels=slide_rels,
                parts=parts,
                from_dir="ppt/slides",
                theme=theme_colors,
            )
            if slide_bg and slide_bg.get("media_part") and not slide_bg.get("data_url"):
                bg_block = {
                    "kind": "image",
                    "slide_index": i,
                    "geometry": {"x": 0, "y": 0, "cx": slide_cx, "cy": slide_cy},
                    "id": f"blk_{i}_background_image",
                    "content": {
                        "locked": True,
                        "layer": "background",
                        "alt": "Slide background",
                        "media_part": slide_bg.get("media_part"),
                        "media_sha256": slide_bg.get("media_sha256"),
                        "data_url": slide_bg.get("data_url"),
                        "fit": "cover",
                    },
                    "provenance": {"source": "document", "generated": False},
                }
                background = [bg_block] + background
            merged_blocks = background + slide_blocks
            slide_area = max(1, slide_cx * slide_cy)
            for block in merged_blocks:
                if str(block.get("kind") or "") != "image":
                    continue
                geo = block.get("geometry") if isinstance(block.get("geometry"), dict) else {}
                try:
                    cover = int(geo.get("cx") or 0) * int(geo.get("cy") or 0)
                except (TypeError, ValueError):
                    cover = 0
                if cover >= slide_area * 0.2:
                    content = block.setdefault("content", {})
                    if isinstance(content, dict):
                        content.setdefault("fit", "cover")
            slides.append(
                {
                    "index": i,
                    "notes": notes,
                    "text": text,
                    "visuals": _visual_markers(slide_xml),
                    "background": slide_bg,
                    "blocks": merged_blocks,
                }
            )
    return slides


parse_pptx_bytes = parse_pptx_bytes
extract_slide_blocks = extract_slide_blocks
slide_emu_size = slide_emu_size

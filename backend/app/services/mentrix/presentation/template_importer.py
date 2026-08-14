"""Secure PPTX → TemplateDefinition importer (no Presenton, no disk extract)."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

from app.services.mentrix.presentation.template_definition import PARSER_VERSION, save_definition

MAX_ARCHIVE_BYTES = 40 * 1024 * 1024
MAX_MEMBERS = 400
MAX_UNCOMPRESSED_TOTAL = 80 * 1024 * 1024
MAX_SINGLE_UNCOMPRESSED = 8 * 1024 * 1024
MAX_COMPRESSION_RATIO = 80
MAX_XML_BYTES = 2 * 1024 * 1024

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


class UnsafePptxError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_zip_name(name: str) -> str:
    raw = (name or "").replace("\\", "/")
    if not raw or "\x00" in raw:
        raise UnsafePptxError("zip_member_invalid")
    if raw.startswith("/") or raw.startswith("../") or "/../" in f"/{raw}/":
        raise UnsafePptxError("zip_path_traversal")
    if ":" in raw.split("/")[0]:
        raise UnsafePptxError("zip_path_traversal")
    return raw


def inspect_pptx_archive(data: bytes) -> zipfile.ZipFile:
    if not data or len(data) > MAX_ARCHIVE_BYTES:
        raise UnsafePptxError("pptx_too_large")
    if data[:2] != b"PK":
        raise UnsafePptxError("not_a_pptx_zip")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data), "r")
    except zipfile.BadZipFile as exc:
        raise UnsafePptxError("invalid_zip") from exc
    infos = zf.infolist()
    if len(infos) > MAX_MEMBERS:
        zf.close()
        raise UnsafePptxError("too_many_zip_members")
    total = 0
    for info in infos:
        _safe_zip_name(info.filename)
        if info.file_size < 0 or info.compress_size < 0:
            zf.close()
            raise UnsafePptxError("zip_bomb")
        if info.file_size > MAX_SINGLE_UNCOMPRESSED:
            zf.close()
            raise UnsafePptxError("zip_member_too_large")
        if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO:
            zf.close()
            raise UnsafePptxError("zip_bomb")
        total += info.file_size
        if total > MAX_UNCOMPRESSED_TOTAL:
            zf.close()
            raise UnsafePptxError("zip_bomb")
        if info.external_attr & 0xA0000000:  # symlink-ish on some zip tools
            zf.close()
            raise UnsafePptxError("zip_symlink_rejected")
    return zf


def _read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        info = zf.getinfo(name)
    except KeyError:
        return None
    if info.file_size > MAX_XML_BYTES:
        raise UnsafePptxError("xml_too_large")
    with zf.open(info, "r") as handle:
        raw = handle.read(MAX_XML_BYTES + 1)
    if len(raw) > MAX_XML_BYTES:
        raise UnsafePptxError("xml_too_large")
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        return None


def _srgb(el: ET.Element | None) -> str:
    if el is None:
        return ""
    srgb = el.find(f"{{{_A}}}srgbClr")
    if srgb is not None and srgb.get("val"):
        return str(srgb.get("val") or "").upper()
    sysc = el.find(f"{{{_A}}}sysClr")
    if sysc is not None:
        return str(sysc.get("lastClr") or sysc.get("val") or "")
    scheme = el.find(f"{{{_A}}}schemeClr")
    if scheme is not None:
        return str(scheme.get("val") or "")
    return ""


def _parse_theme(root: ET.Element | None) -> dict[str, Any]:
    colors: dict[str, str] = {}
    fonts: dict[str, str] = {}
    if root is None:
        return {"colors": colors, "fonts": fonts}
    scheme = root.find(f".//{{{_A}}}clrScheme")
    if scheme is not None:
        for child in list(scheme):
            tag = child.tag.rsplit("}", 1)[-1]
            colors[tag] = _srgb(child)
    major = root.find(f".//{{{_A}}}majorFont/{{{_A}}}latin")
    minor = root.find(f".//{{{_A}}}minorFont/{{{_A}}}latin")
    if major is not None:
        fonts["major"] = str(major.get("typeface") or "")
    if minor is not None:
        fonts["minor"] = str(minor.get("typeface") or "")
    return {"colors": colors, "fonts": fonts}


def _placeholder_kind(nv_sp: ET.Element | None) -> str:
    if nv_sp is None:
        return ""
    ph = nv_sp.find(f".//{{{_P}}}ph")
    if ph is None:
        return ""
    return str(ph.get("type") or "body")


def _geom(sp: ET.Element) -> dict[str, Any]:
    xfrm = sp.find(f".//{{{_A}}}xfrm")
    if xfrm is None:
        return {}
    off = xfrm.find(f"{{{_A}}}off")
    ext = xfrm.find(f"{{{_A}}}ext")
    out: dict[str, Any] = {}
    if off is not None:
        out["x"] = off.get("x")
        out["y"] = off.get("y")
    if ext is not None:
        out["cx"] = ext.get("cx")
        out["cy"] = ext.get("cy")
    return out


def _parse_layout(root: ET.Element | None, name: str) -> dict[str, Any]:
    placeholders: list[dict[str, Any]] = []
    if root is None:
        return {"name": name, "placeholders": placeholders}
    c_sld = root.find(f"{{{_P}}}cSld")
    layout_name = (c_sld.get("name") if c_sld is not None else "") or name
    for sp in root.iter(f"{{{_P}}}sp"):
        kind = _placeholder_kind(sp.find(f"{{{_P}}}nvSpPr"))
        if not kind:
            continue
        placeholders.append({"type": kind, "geometry": _geom(sp)})
    return {"name": layout_name, "placeholders": placeholders}


def import_pptx_bytes(
    data: bytes,
    *,
    zect_id: str,
    scope: str,
    name: str = "",
    source_filename: str = "",
) -> dict[str, Any]:
    """Parse a PPTX into a TemplateDefinition. Does not call Presenton."""
    zid = (zect_id or "").strip()
    if not zid:
        raise UnsafePptxError("template_id_required")
    zf = inspect_pptx_archive(data)
    try:
        names = {_safe_zip_name(i.filename) for i in zf.infolist()}
        pres = _read_xml(zf, "ppt/presentation.xml")
        if pres is None:
            raise UnsafePptxError("missing_presentation_xml")
        sld_sz = pres.find(f"{{{_P}}}sldSz")
        slide_size = {
            "cx": sld_sz.get("cx") if sld_sz is not None else "",
            "cy": sld_sz.get("cy") if sld_sz is not None else "",
            "type": sld_sz.get("type") if sld_sz is not None else "",
        }
        theme_name = next((n for n in sorted(names) if re.fullmatch(r"ppt/theme/theme\d+\.xml", n)), "")
        theme = _parse_theme(_read_xml(zf, theme_name) if theme_name else None)
        masters = [n for n in sorted(names) if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", n)]
        layouts = [n for n in sorted(names) if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n)]
        master_names: list[str] = []
        for m in masters:
            root = _read_xml(zf, m)
            c_sld = root.find(f"{{{_P}}}cSld") if root is not None else None
            master_names.append((c_sld.get("name") if c_sld is not None else "") or _xml_stem(m))
        layout_defs = [_parse_layout(_read_xml(zf, n), _xml_stem(n)) for n in layouts]
        content_regions = [p for lay in layout_defs for p in lay.get("placeholders") or []]
        ready = bool(theme_name and masters and layouts and slide_size.get("cx"))
        preview_bits = [
            name or zid,
            f"{len(layouts)} layouts",
            (theme.get("fonts") or {}).get("major") or "",
        ]
        row: dict[str, Any] = {
            "id": zid,
            "version": 1,
            "scope": scope,
            "name": name or zid,
            "source_filename": (source_filename or "")[:200],
            "source_pptx_sha256": hashlib.sha256(data).hexdigest(),
            "parser_version": PARSER_VERSION,
            "slide_size": slide_size,
            "theme": theme,
            "masters": master_names,
            "layouts": layout_defs,
            "content_regions": content_regions,
            "preview": " · ".join(p for p in preview_bits if p),
            "ready": ready,
            "imported_at": _now(),
            "provider_bindings": {},
        }
        save_definition(row)
        return {"ok": True, "definition": row}
    finally:
        zf.close()


def _xml_stem(name: str) -> str:
    return name.rsplit("/", 1)[-1].rsplit(".", 1)[0]

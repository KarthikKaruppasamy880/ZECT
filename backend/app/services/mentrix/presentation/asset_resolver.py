"""Presentation image assets — owned files, no URL fetch, no second Document/Web system."""

from __future__ import annotations

import hashlib
import io
import os
import re
from pathlib import Path
from typing import Any

_SAFE_USER = re.compile(r"[^a-zA-Z0-9._-]+")
ASSET_ID_RE = re.compile(r"^[a-f0-9]{64}$")
MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 25_000_000
MAX_DIM = 8192
ALLOWED_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


class UnsafeImageError(ValueError):
    pass


def _root() -> Path:
    env = (os.environ.get("ZECT_PRESENT_ASSET_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[5] / ".zect" / "present-assets").resolve()


def _user_dir(user_id: str) -> Path:
    safe = _SAFE_USER.sub("_", (user_id or "").strip())[:80] or "anon"
    path = _root() / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def _magic(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif", ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise UnsafeImageError("image_magic_rejected")


def _reject_active(data: bytes, filename: str, mime: str) -> None:
    name = (filename or "").lower()
    declared = (mime or "").lower()
    if name.endswith(".svg") or "svg" in declared or name.endswith(".html") or name.endswith(".xml"):
        raise UnsafeImageError("svg_or_active_content_rejected")
    head = data[:256].lstrip().lower()
    if head.startswith(b"<svg") or head.startswith(b"<?xml") or head.startswith(b"<!doctype") or b"<script" in head:
        raise UnsafeImageError("svg_or_active_content_rejected")


def _decode(data: bytes) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise UnsafeImageError("pillow_required") from exc
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            width, height = img.size
            fmt = (img.format or "").upper()
            if fmt not in {"PNG", "JPEG", "GIF", "WEBP"}:
                raise UnsafeImageError("image_format_rejected")
            if width > MAX_DIM or height > MAX_DIM or (width * height) > MAX_PIXELS:
                raise UnsafeImageError("image_dimensions_rejected")
            if fmt == "WEBP":
                out = io.BytesIO()
                img.convert("RGBA").save(out, format="PNG")
                return {"bytes": out.getvalue(), "width": width, "height": height, "mime": "image/png", "ext": ".png"}
            return {"bytes": data, "width": width, "height": height, "mime": _magic(data)[0], "ext": _magic(data)[1]}
    except UnsafeImageError:
        raise
    except Exception as exc:
        raise UnsafeImageError("image_decode_failed") from exc


def store_image(
    data: bytes,
    *,
    user_id: str,
    filename: str = "",
    mime: str = "",
) -> dict[str, Any]:
    if not data:
        raise UnsafeImageError("image_empty")
    if len(data) > MAX_BYTES:
        raise UnsafeImageError("image_too_large")
    if (filename or "").lower().startswith(("http://", "https://", "data:")):
        raise UnsafeImageError("image_url_rejected")
    _reject_active(data, filename, mime)
    _magic(data)
    decoded = _decode(data)
    payload: bytes = decoded["bytes"]
    digest = hashlib.sha256(payload).hexdigest()
    dest = _user_dir(user_id) / f"{digest}{decoded['ext']}"
    if not dest.is_file():
        dest.write_bytes(payload)
    return {
        "ok": True,
        "asset_id": digest,
        "mime": decoded["mime"],
        "ext": decoded["ext"],
        "width": decoded["width"],
        "height": decoded["height"],
        "bytes": len(payload),
        "owner": user_id,
        "filename": Path(filename or f"{digest}{decoded['ext']}").name[:80],
    }


def load_image(asset_id: str, *, user_id: str) -> dict[str, Any]:
    aid = (asset_id or "").strip().lower()
    if aid.startswith("sha256:"):
        aid = aid.split(":", 1)[1]
    if not ASSET_ID_RE.fullmatch(aid):
        raise UnsafeImageError("asset_id_invalid")
    folder = _user_dir(user_id)
    matches = list(folder.glob(f"{aid}.*"))
    if not matches:
        # Content-addressed assets may have been stored under a different owner key
        # (e.g. email during PPTX import vs numeric user_id on GET).
        matches = [p for p in _root().glob(f"*/{aid}.*") if p.is_file() and p.suffix.lower() in ALLOWED_EXT]
    if not matches:
        raise FileNotFoundError("asset_not_found")
    path = matches[0]
    if path.suffix.lower() not in ALLOWED_EXT:
        raise UnsafeImageError("asset_ext_rejected")
    try:
        path.relative_to(_root())
    except ValueError as exc:
        raise UnsafeImageError("asset_path_rejected") from exc
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise UnsafeImageError("image_too_large")
    mime, _ext = _magic(data)
    return {"asset_id": aid, "path": path, "bytes": data, "mime": mime, "owner": user_id}


def example_png_bytes(*, label: str = "ZECT") -> bytes:
    """Generated placeholder PNG — provenance must stay example/generated."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # pragma: no cover
        # 1x1 PNG
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01"
            b"\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
        )
    img = Image.new("RGB", (640, 360), (255, 117, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((24, 24, 616, 336), outline=(0, 98, 139), width=6)
    draw.rectangle((40, 140, 600, 220), fill=(0, 98, 139))
    draw.text((70, 165), f"{label[:32]} example image", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def store_example_image(*, user_id: str, label: str = "ZECT") -> dict[str, Any]:
    meta = store_image(example_png_bytes(label=label), user_id=user_id, filename="example.png", mime="image/png")
    meta["provenance"] = {"source": "example", "generated": True, "note": "Generated placeholder, not a user photo"}
    return meta

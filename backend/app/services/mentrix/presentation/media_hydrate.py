"""Store large PPTX embedded images in the presentation asset store after parse."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any

from app.services.mentrix.presentation.asset_resolver import UnsafeImageError, store_image


def hydrate_presentation_media(
    slides: list[dict[str, Any]],
    pptx_data: bytes,
    *,
    user_id: str,
) -> list[dict[str, Any]]:
    """Resolve media_part / media_sha256 on image blocks to asset_id via store_image."""
    if not slides or not pptx_data:
        return slides
    uid = str(user_id or "anon").strip() or "anon"
    try:
        zf = zipfile.ZipFile(io.BytesIO(pptx_data), "r")
    except zipfile.BadZipFile:
        return slides
    try:
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            for block in list(slide.get("blocks") or []):
                if not isinstance(block, dict) or str(block.get("kind") or "") != "image":
                    continue
                content = block.get("content")
                if not isinstance(content, dict):
                    continue
                if str(content.get("asset_id") or "").strip() or str(content.get("data_url") or "").startswith("data:"):
                    continue
                part = str(content.get("media_part") or "").replace("\\", "/").lstrip("/")
                if not part:
                    continue
                try:
                    blob = zf.read(part)
                except KeyError:
                    continue
                expected = str(content.get("media_sha256") or "").strip().lower()
                digest = hashlib.sha256(blob).hexdigest()
                if expected and expected != digest:
                    continue
                try:
                    meta = store_image(blob, user_id=uid, filename=Path(part).name)
                except UnsafeImageError:
                    continue
                content["asset_id"] = meta["asset_id"]
                content.pop("media_part", None)
                content.pop("media_sha256", None)
    finally:
        zf.close()
    return slides


__all__ = ["hydrate_presentation_media"]

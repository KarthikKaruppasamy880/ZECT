"""Mentrix Image / Thumbnail board — numbered generations under data/mentrix_media."""

from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

MEDIA_DIR = Path(__file__).resolve().parents[3] / "data" / "mentrix_media"
INDEX_NAME = "index.json"


def _ensure_dir() -> Path:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_DIR


def _index_path() -> Path:
    return _ensure_dir() / INDEX_NAME


def _load_index() -> list[dict[str, Any]]:
    p = _index_path()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


def _save_index(items: list[dict[str, Any]]) -> None:
    _index_path().write_text(json.dumps(items, indent=2), encoding="utf-8")


def _next_number(items: list[dict[str, Any]]) -> int:
    nums = []
    for it in items:
        try:
            nums.append(int(it.get("number") or 0))
        except (TypeError, ValueError):
            continue
    return (max(nums) if nums else 0) + 1


def list_media(limit: int = 48) -> list[dict[str, Any]]:
    items = _load_index()
    return items[:limit]


def get_media_file(number: int) -> Path | None:
    items = _load_index()
    for it in items:
        if int(it.get("number") or 0) == number:
            fn = it.get("filename") or ""
            path = _ensure_dir() / fn
            return path if path.is_file() else None
    # fallback pattern
    for path in _ensure_dir().glob(f"{number:03d}_*"):
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            return path
    return None


def _openai_image(prompt: str, *, edit_of: Path | None = None) -> bytes | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        with httpx.Client(timeout=90.0) as client:
            if edit_of and edit_of.is_file():
                # edits API — fall back to generate with prompt note if edit fails
                files = {
                    "image": (edit_of.name, edit_of.read_bytes(), "image/png"),
                }
                data = {"prompt": prompt[:1000], "n": "1", "size": "1024x1024"}
                resp = client.post(
                    "https://api.openai.com/v1/images/edits",
                    headers={"Authorization": f"Bearer {key}"},
                    data=data,
                    files=files,
                )
                if resp.status_code >= 400:
                    resp = None
                else:
                    b64 = (resp.json().get("data") or [{}])[0].get("b64_json")
                    return base64.b64decode(b64) if b64 else None
            resp = client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("MENTRIX_IMAGE_MODEL", "dall-e-3"),
                    "prompt": prompt[:3900],
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json",
                },
            )
        if resp.status_code >= 400:
            return None
        b64 = (resp.json().get("data") or [{}])[0].get("b64_json")
        return base64.b64decode(b64) if b64 else None
    except Exception:  # noqa: BLE001
        return None


def _placeholder_png(prompt: str, number: int) -> bytes:
    """Minimal 1x1 PNG when OpenAI images unavailable — still numbers the board."""
    # 1x1 teal-ish PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def generate_media(prompt: str, *, created_by: str = "") -> dict[str, Any]:
    items = _load_index()
    number = _next_number(items)
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", (prompt or "mentrix")[:40]).strip("_") or "mentrix"
    filename = f"{number:03d}_{safe}.png"
    path = _ensure_dir() / filename
    raw = _openai_image(prompt) or _placeholder_png(prompt, number)
    path.write_bytes(raw)
    entry = {
        "number": number,
        "filename": filename,
        "prompt": (prompt or "")[:2000],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdBy": created_by or "",
        "edits": [],
        "placeholder": len(raw) < 200,
        "url": f"/api/mentrix/companion/media/{number}",
    }
    items.insert(0, entry)
    _save_index(items)
    return entry


def edit_media(number: int, prompt: str, *, created_by: str = "") -> dict[str, Any]:
    src = get_media_file(number)
    items = _load_index()
    new_number = _next_number(items)
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", (prompt or "edit")[:40]).strip("_") or "edit"
    filename = f"{new_number:03d}_{safe}.png"
    path = _ensure_dir() / filename
    raw = _openai_image(prompt, edit_of=src) or _placeholder_png(prompt, new_number)
    path.write_bytes(raw)
    entry = {
        "number": new_number,
        "filename": filename,
        "prompt": (prompt or "")[:2000],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdBy": created_by or "",
        "edits": [],
        "parent": number,
        "placeholder": len(raw) < 200,
        "url": f"/api/mentrix/companion/media/{new_number}",
    }
    # annotate parent
    for it in items:
        if int(it.get("number") or 0) == number:
            it.setdefault("edits", []).append({"number": new_number, "prompt": prompt[:200]})
            break
    items.insert(0, entry)
    _save_index(items)
    return entry

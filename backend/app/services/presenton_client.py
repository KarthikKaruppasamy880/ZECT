"""Thin Presenton self-host client — prompt → PPTX path for Mentrix Present Deck."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx


def presenton_base_url() -> str:
    return (os.getenv("PRESENTON_BASE_URL") or "").strip().rstrip("/")


def presenton_configured() -> bool:
    return bool(presenton_base_url())


def _auth() -> tuple[str, str] | None:
    user = (os.getenv("PRESENTON_USERNAME") or "").strip()
    password = (os.getenv("PRESENTON_PASSWORD") or "").strip()
    if user and password:
        return (user, password)
    return None


def _bearer_headers() -> dict[str, str]:
    key = (os.getenv("PRESENTON_API_KEY") or "").strip()
    if key:
        return {"Authorization": f"Bearer {key}"}
    return {}


def _safe_filename(name: str) -> str:
    base = re.sub(r"[^\w.\- ]+", "", (name or "mentrix-deck").strip())[:80] or "mentrix-deck"
    if not base.lower().endswith(".pptx"):
        base = f"{base}.pptx"
    return base


def default_save_dir() -> Path:
    home = Path.home()
    for candidate in (
        home / "Documents",
        home / "OneDrive" / "Documents",
        home / "Desktop",
    ):
        if candidate.is_dir():
            return candidate
    return home


def generate_presentation(
    content: str,
    *,
    n_slides: int = 6,
    template: str | None = None,
    instructions: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """Call Presenton generate API and download PPTX into Documents/Desktop."""
    base = presenton_base_url()
    if not base:
        return {
            "ok": False,
            "error": "presenton_not_configured",
            "hint": "Set PRESENTON_BASE_URL (e.g. http://127.0.0.1:5000) and run Presenton Docker",
        }
    prompt = (content or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty_content"}

    payload: dict[str, Any] = {
        "content": prompt,
        "n_slides": max(3, min(int(n_slides or 6), 20)),
        "language": "English",
        "template": (template or "general").strip() or "general",
        "export_as": "pptx",
    }
    if instructions:
        payload["instructions"] = instructions

    url = f"{base}/api/v1/ppt/presentation/generate"
    headers = {"Content-Type": "application/json", **_bearer_headers()}
    try:
        with httpx.Client(timeout=180.0, auth=_auth()) as client:
            res = client.post(url, json=payload, headers=headers)
            if res.status_code >= 400:
                return {
                    "ok": False,
                    "error": "presenton_generate_failed",
                    "status": res.status_code,
                    "detail": (res.text or "")[:800],
                }
            data = res.json()
            rel = data.get("path") or data.get("edit_path") or ""
            if not rel:
                return {"ok": False, "error": "presenton_missing_path", "response": data}

            download_url = rel if str(rel).startswith("http") else urljoin(base + "/", str(rel).lstrip("/"))
            file_res = client.get(download_url, headers=_bearer_headers(), follow_redirects=True)
            if file_res.status_code >= 400 or not file_res.content:
                return {
                    "ok": False,
                    "error": "presenton_download_failed",
                    "status": file_res.status_code,
                    "url": download_url,
                }

            out_name = _safe_filename(filename or Path(str(rel)).name or "mentrix-deck.pptx")
            out_path = default_save_dir() / out_name
            out_path.write_bytes(file_res.content)
            return {
                "ok": True,
                "path": str(out_path.resolve()),
                "presentation_id": data.get("presentation_id"),
                "presenton_path": rel,
                "bytes": len(file_res.content),
            }
    except httpx.ConnectError:
        return {
            "ok": False,
            "error": "presenton_unreachable",
            "hint": f"Cannot reach {base} — start Presenton Docker or fix PRESENTON_BASE_URL",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "presenton_error", "detail": str(exc)[:500]}

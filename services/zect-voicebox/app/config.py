"""Environment config for ZECT Voicebox."""

from __future__ import annotations

import os
from pathlib import Path


def port() -> int:
    return int(os.getenv("ZECT_VOICEBOX_PORT", "17493"))


def data_dir() -> Path:
    raw = (os.getenv("ZECT_VOICEBOX_DATA_DIR") or "").strip()
    if raw:
        path = Path(raw)
    else:
        path = Path(__file__).resolve().parent.parent / "data"
    path.mkdir(parents=True, exist_ok=True)
    (path / "audio").mkdir(parents=True, exist_ok=True)
    return path


def backend() -> str:
    """Locked default: upstream proxy to jamiepine/voicebox-compatible API."""
    return (os.getenv("ZECT_VOICEBOX_BACKEND") or "upstream").strip().lower() or "upstream"


def upstream_url() -> str:
    return (os.getenv("ZECT_VOICEBOX_UPSTREAM_URL") or "http://127.0.0.1:17494").strip().rstrip("/")


BRAND = "zect-voicebox"
PRODUCT = "ZECT Voicebox"

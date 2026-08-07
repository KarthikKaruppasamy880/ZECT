"""Environment config for ZECT Voicebox (native clone TTS)."""

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
    (path / "profiles").mkdir(parents=True, exist_ok=True)
    return path


def model_dir() -> Path:
    raw = (os.getenv("ZECT_VOICEBOX_MODEL_DIR") or "").strip()
    if raw:
        path = Path(raw)
    else:
        path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def backend() -> str:
    """Always native — no third-party upstream proxy."""
    return (os.getenv("ZECT_VOICEBOX_BACKEND") or "native").strip().lower() or "native"


def synth_mode() -> str:
    """auto | chatterbox | stub"""
    return (os.getenv("ZECT_VOICEBOX_SYNTH") or "auto").strip().lower() or "auto"


def allow_stub() -> bool:
    return (os.getenv("ZECT_VOICEBOX_ALLOW_STUB") or "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


BRAND = "zect-voicebox"
PRODUCT = "ZECT Voicebox"
ENGINE_ID = "chatterbox"  # Mentrix CHATTERBOX_ENGINE default maps here

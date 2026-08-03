"""OpenAI TTS fallback when local Chatterbox engine is offline."""

from __future__ import annotations

import os

import httpx

OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
DEFAULT_VOICE = "alloy"
DEFAULT_MODEL = "tts-1"


def openai_tts_available() -> bool:
    return bool((os.getenv("OPENAI_API_KEY") or "").strip())


def synthesize_openai_speech(
    text: str,
    *,
    voice: str | None = None,
    model: str | None = None,
) -> bytes:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set — cannot fall back to OpenAI TTS")
    payload = {
        "model": (model or os.getenv("OPENAI_TTS_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "voice": (voice or os.getenv("OPENAI_TTS_VOICE") or DEFAULT_VOICE).strip() or DEFAULT_VOICE,
        "input": (text or "")[:4000],
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            OPENAI_TTS_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenAI TTS failed ({resp.status_code}): {resp.text[:300]}")
    if not resp.content:
        raise RuntimeError("OpenAI TTS returned empty audio")
    return resp.content

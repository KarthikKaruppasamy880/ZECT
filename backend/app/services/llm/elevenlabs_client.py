"""ElevenLabs hosted voice-cloning TTS — plain HTTP via httpx (already a
dependency), matching the raw-HTTP pattern realtime.py already uses for
OpenAI's client_secrets mint rather than pulling in another provider SDK.

Mentrix's voice was 100% OpenAI Realtime's stock voices with zero cloning
capability. This keeps Realtime for speech understanding (STT + reasoning)
and only swaps the output: once a user has cloned a voice, the Realtime
session switches to text-only output (see mentrixRealtime.ts) and that text
gets synthesized here instead.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_TTS_MODEL = "eleven_multilingual_v2"


def elevenlabs_available() -> bool:
    return bool(os.getenv("ELEVENLABS_API_KEY", "").strip())


def _api_key() -> str:
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise ValueError("ELEVENLABS_API_KEY not configured. Add it in Settings to enable voice cloning.")
    return key


def clone_voice(name: str, audio_bytes: bytes, filename: str, content_type: str = "audio/mpeg") -> dict[str, Any]:
    """Create an Instant Voice Clone from a single sample. Returns {"voice_id": ...}."""
    key = _api_key()
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{ELEVENLABS_BASE_URL}/v1/voices/add",
            headers={"xi-api-key": key},
            data={"name": name[:100]},
            files={"files": (filename, audio_bytes, content_type)},
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"ElevenLabs voice clone failed ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    voice_id = data.get("voice_id")
    if not voice_id:
        raise RuntimeError(f"ElevenLabs voice clone response missing voice_id: {resp.text[:300]}")
    return {"voice_id": voice_id, "name": name}


def synthesize_speech(text: str, voice_id: str, *, model_id: str = DEFAULT_TTS_MODEL) -> bytes:
    """Synthesize text in the given cloned voice. Returns raw MP3 audio bytes."""
    key = _api_key()
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{ELEVENLABS_BASE_URL}/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text[:4000], "model_id": model_id},
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"ElevenLabs speech synthesis failed ({resp.status_code}): {resp.text[:300]}")
    return resp.content


def delete_voice(voice_id: str) -> None:
    """Best-effort cleanup on ElevenLabs' side when a user resets their cloned
    voice — failures here shouldn't block clearing the local record."""
    try:
        key = _api_key()
        with httpx.Client(timeout=15.0) as client:
            client.delete(f"{ELEVENLABS_BASE_URL}/v1/voices/{voice_id}", headers={"xi-api-key": key})
    except Exception:
        pass

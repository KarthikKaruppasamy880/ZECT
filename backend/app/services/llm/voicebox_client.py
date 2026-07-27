"""Voicebox local voice-cloning TTS — talks to a locally-running Voicebox
instance (github.com/jamiepine/voicebox, MIT licensed) instead of a hosted
provider. No API key, no subscription, no data leaving the user's machine.

Replaces elevenlabs_client.py as voice_clone.py's active backend: same two
operations (clone a voice from a sample, synthesize text in it), different
wire format — Voicebox splits "clone" into two calls (create a profile, then
attach a sample) where ElevenLabs did it in one, and /generate returns a
JSON pointer to the audio rather than the audio bytes directly.

The exact audio-download route (_resolve_audio_url below) wasn't verifiable
without a running instance to inspect — Voicebox's own /docs page (served by
the local server itself) has the authoritative contract; if playback fails,
check that page and adjust VOICEBOX_AUDIO_PATH_TEMPLATE accordingly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

VOICEBOX_BASE_URL = os.getenv("VOICEBOX_BASE_URL", "http://localhost:17493")
VOICEBOX_AUDIO_PATH_TEMPLATE = os.getenv("VOICEBOX_AUDIO_PATH_TEMPLATE", "/audio/{filename}")


def voicebox_available() -> bool:
    """Voicebox has no API key — 'available' means the local server answers."""
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{VOICEBOX_BASE_URL}/profiles")
        return resp.status_code < 500
    except Exception:
        return False


def clone_voice(
    name: str,
    audio_bytes: bytes,
    filename: str,
    content_type: str = "audio/mpeg",
    *,
    reference_text: str,
    language: str = "en",
) -> dict[str, Any]:
    """Create a voice profile, then attach the sample.

    reference_text is what the sample audio actually says — Voicebox's
    cloning model needs the transcript for alignment; unlike ElevenLabs this
    can't be inferred or left blank, it has to come from the caller.
    """
    if not reference_text.strip():
        raise ValueError("reference_text is required — it must match what the audio sample says")

    with httpx.Client(timeout=60.0) as client:
        profile_resp = client.post(
            f"{VOICEBOX_BASE_URL}/profiles",
            json={"name": name[:100], "language": language, "voice_type": "cloned"},
        )
        if profile_resp.status_code >= 400:
            raise RuntimeError(f"Voicebox profile creation failed ({profile_resp.status_code}): {profile_resp.text[:300]}")
        profile_id = profile_resp.json().get("id")
        if not profile_id:
            raise RuntimeError(f"Voicebox profile response missing id: {profile_resp.text[:300]}")

        sample_resp = client.post(
            f"{VOICEBOX_BASE_URL}/profiles/{profile_id}/samples",
            files={"file": (filename, audio_bytes, content_type)},
            data={"reference_text": reference_text[:2000]},
        )
        if sample_resp.status_code >= 400:
            raise RuntimeError(f"Voicebox sample upload failed ({sample_resp.status_code}): {sample_resp.text[:300]}")

    return {"voice_id": profile_id, "name": name}


def _resolve_audio_url(audio_path: str) -> str:
    if audio_path.startswith("http://") or audio_path.startswith("https://"):
        return audio_path
    filename = Path(audio_path).name
    return f"{VOICEBOX_BASE_URL}{VOICEBOX_AUDIO_PATH_TEMPLATE.format(filename=filename)}"


def synthesize_speech(text: str, voice_id: str, *, language: str = "en", engine: str = "qwen") -> bytes:
    """Synthesize text in the given cloned voice profile. Returns raw audio bytes."""
    with httpx.Client(timeout=30.0) as client:
        gen_resp = client.post(
            f"{VOICEBOX_BASE_URL}/generate",
            json={"profile_id": voice_id, "text": text[:4000], "language": language, "engine": engine},
        )
        if gen_resp.status_code >= 400:
            raise RuntimeError(f"Voicebox generation failed ({gen_resp.status_code}): {gen_resp.text[:300]}")
        data = gen_resp.json()
        if data.get("status") == "error" or data.get("error"):
            raise RuntimeError(f"Voicebox generation error: {data.get('error')}")
        audio_path = data.get("audio_path")
        if not audio_path:
            raise RuntimeError(f"Voicebox generation response missing audio_path: {gen_resp.text[:300]}")

        audio_url = _resolve_audio_url(audio_path)
        audio_resp = client.get(audio_url)
        if audio_resp.status_code >= 400:
            raise RuntimeError(
                f"Voicebox audio download failed ({audio_resp.status_code}) for {audio_path} — "
                "check http://localhost:17493/docs on your install for the actual download route "
                "and set VOICEBOX_AUDIO_PATH_TEMPLATE if it differs."
            )
        return audio_resp.content


def delete_voice(voice_id: str) -> None:
    """Best-effort cleanup when a user resets their cloned voice."""
    try:
        with httpx.Client(timeout=15.0) as client:
            client.delete(f"{VOICEBOX_BASE_URL}/profiles/{voice_id}")
    except Exception:
        pass

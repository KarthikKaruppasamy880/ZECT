"""ZECT Chatterbox — local voice-clone TTS engine client.

Talks to a locally-running synthesis engine (pluggable HTTP service).
Env: CHATTERBOX_BASE_URL (preferred) or legacy VOICEBOX_BASE_URL.
No API key; synthesis stays on the user's machine. Product branding is
Chatterbox — ZECT owns clone persistence in DB + sample files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

CHATTERBOX_BASE_URL = os.getenv(
    "CHATTERBOX_BASE_URL",
    os.getenv("VOICEBOX_BASE_URL", "http://localhost:17493"),
)
CHATTERBOX_AUDIO_PATH_TEMPLATE = os.getenv(
    "CHATTERBOX_AUDIO_PATH_TEMPLATE",
    os.getenv("VOICEBOX_AUDIO_PATH_TEMPLATE", "/audio/{filename}"),
)
# "qwen" was hardcoded with no way to try a faster engine your local server
# might offer without a code change — synthesis is a fully synchronous HTTP
# call (POST /generate blocks until the whole clip is done, no streaming),
# so the engine's own speed is the dominant factor in perceived TTS latency.
DEFAULT_CHATTERBOX_ENGINE = os.getenv("CHATTERBOX_ENGINE", "qwen")


def chatterbox_available() -> bool:
    """Engine is available when the local server answers."""
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{CHATTERBOX_BASE_URL}/profiles")
        return resp.status_code < 500
    except Exception:
        return False


# Back-compat alias used by older tests/imports
voicebox_available = chatterbox_available


def clone_voice(
    name: str,
    audio_bytes: bytes,
    filename: str,
    content_type: str = "audio/mpeg",
    *,
    reference_text: str,
    language: str = "en",
) -> dict[str, Any]:
    """Create a voice profile on the local engine, then attach the sample."""
    if not reference_text.strip():
        raise ValueError("reference_text is required — it must match what the audio sample says")

    with httpx.Client(timeout=60.0) as client:
        profile_resp = client.post(
            f"{CHATTERBOX_BASE_URL}/profiles",
            json={"name": name[:100], "language": language, "voice_type": "cloned"},
        )
        if profile_resp.status_code >= 400:
            raise RuntimeError(
                f"Chatterbox profile creation failed ({profile_resp.status_code}): {profile_resp.text[:300]}"
            )
        profile_id = profile_resp.json().get("id")
        if not profile_id:
            raise RuntimeError(f"Chatterbox profile response missing id: {profile_resp.text[:300]}")

        sample_resp = client.post(
            f"{CHATTERBOX_BASE_URL}/profiles/{profile_id}/samples",
            files={"file": (filename, audio_bytes, content_type)},
            data={"reference_text": reference_text[:2000]},
        )
        if sample_resp.status_code >= 400:
            raise RuntimeError(
                f"Chatterbox sample upload failed ({sample_resp.status_code}): {sample_resp.text[:300]}"
            )

    return {"voice_id": profile_id, "name": name}


def _resolve_audio_url(audio_path: str) -> str:
    if audio_path.startswith("http://") or audio_path.startswith("https://"):
        return audio_path
    filename = Path(audio_path).name
    return f"{CHATTERBOX_BASE_URL}{CHATTERBOX_AUDIO_PATH_TEMPLATE.format(filename=filename)}"


def synthesize_speech(text: str, voice_id: str, *, language: str = "en", engine: str | None = None) -> bytes:
    """Synthesize text in the given cloned voice profile. Returns raw audio bytes."""
    with httpx.Client(timeout=30.0) as client:
        gen_resp = client.post(
            f"{CHATTERBOX_BASE_URL}/generate",
            json={
                "profile_id": voice_id,
                "text": text[:4000],
                "language": language,
                "engine": engine or DEFAULT_CHATTERBOX_ENGINE,
            },
        )
        if gen_resp.status_code >= 400:
            raise RuntimeError(
                f"Chatterbox generation failed ({gen_resp.status_code}): {gen_resp.text[:300]}"
            )
        data = gen_resp.json()
        if data.get("status") == "error" or data.get("error"):
            raise RuntimeError(f"Chatterbox generation error: {data.get('error')}")
        audio_path = data.get("audio_path")
        if not audio_path:
            raise RuntimeError(
                f"Chatterbox generation response missing audio_path: {gen_resp.text[:300]}"
            )

        audio_url = _resolve_audio_url(audio_path)
        audio_resp = client.get(audio_url)
        if audio_resp.status_code >= 400:
            raise RuntimeError(
                f"Chatterbox audio download failed ({audio_resp.status_code}) for {audio_path} — "
                "check the local engine /docs for the download route and set "
                "CHATTERBOX_AUDIO_PATH_TEMPLATE if it differs."
            )
        return audio_resp.content


def delete_voice(voice_id: str) -> None:
    """Best-effort cleanup of an engine-side profile."""
    try:
        with httpx.Client(timeout=15.0) as client:
            client.delete(f"{CHATTERBOX_BASE_URL}/profiles/{voice_id}")
    except Exception:
        pass

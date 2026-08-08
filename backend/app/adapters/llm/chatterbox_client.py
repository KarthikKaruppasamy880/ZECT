"""ZECT Voicebox client — local clone TTS HTTP engine.

Talks to ZECT Voicebox (pluggable HTTP service on :17493).
Env: CHATTERBOX_BASE_URL (preferred) or legacy VOICEBOX_BASE_URL.
No API key; synthesis stays on the user's machine. Product UI brand is
ZECT Voicebox — ZECT owns clone persistence in DB + sample files.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

def _base_url() -> str:
    raw = (
        os.getenv("CHATTERBOX_BASE_URL")
        or os.getenv("VOICEBOX_BASE_URL")
        or "http://127.0.0.1:17493"
    ).strip().rstrip("/")
    # Windows: localhost often resolves to ::1 while engines bind 127.0.0.1 only.
    if "://localhost" in raw.lower() or "://localhost:" in raw.lower():
        raw = raw.replace("://localhost", "://127.0.0.1").replace("://Localhost", "://127.0.0.1")
    return raw


# Back-compat for imports that read the module constant (prefer _base_url() at call sites).
CHATTERBOX_BASE_URL = _base_url()
CHATTERBOX_AUDIO_PATH_TEMPLATE = os.getenv(
    "CHATTERBOX_AUDIO_PATH_TEMPLATE",
    os.getenv("VOICEBOX_AUDIO_PATH_TEMPLATE", "/audio/{filename}"),
)
DEFAULT_CHATTERBOX_ENGINE = os.getenv("CHATTERBOX_ENGINE", "qwen")
SPEAK_TIMEOUT = float(os.getenv("CHATTERBOX_SPEAK_TIMEOUT", "15.0"))
REPROVISION_TIMEOUT = float(os.getenv("CHATTERBOX_REPROVISION_TIMEOUT", "6.0"))

# Fail-fast health probe — avoid burning ~2s on every /speak when offline.
HEALTH_PROBE_TIMEOUT = float(os.getenv("CHATTERBOX_HEALTH_TIMEOUT", "0.4"))
HEALTH_POSITIVE_TTL_S = float(os.getenv("CHATTERBOX_HEALTH_POSITIVE_TTL", "30"))
HEALTH_NEGATIVE_TTL_S = float(os.getenv("CHATTERBOX_HEALTH_NEGATIVE_TTL", "4"))

_health_cache: dict[str, Any] = {"ok": None, "checked_at": 0.0}


def invalidate_health_cache() -> None:
    """Clear cached availability (e.g. after Start engine from Desktop)."""
    _health_cache["ok"] = None
    _health_cache["checked_at"] = 0.0


def _probe_profiles() -> bool:
    try:
        with httpx.Client(timeout=HEALTH_PROBE_TIMEOUT) as client:
            resp = client.get(f"{_base_url()}/profiles")
        return resp.status_code < 500
    except Exception:
        return False


def chatterbox_available(*, force_refresh: bool = False) -> bool:
    """Engine available when ZECT Voicebox answers /profiles (TTL-cached)."""
    now = time.monotonic()
    cached = _health_cache.get("ok")
    checked_at = float(_health_cache.get("checked_at") or 0.0)
    if not force_refresh and cached is not None:
        ttl = HEALTH_POSITIVE_TTL_S if cached else HEALTH_NEGATIVE_TTL_S
        if (now - checked_at) < ttl:
            return bool(cached)
    ok = _probe_profiles()
    _health_cache["ok"] = ok
    _health_cache["checked_at"] = now
    return ok


def profile_exists(profile_id: str) -> bool:
    """True when the local Voicebox still has this profile id."""
    pid = (profile_id or "").strip()
    if not pid:
        return False
    try:
        with httpx.Client(timeout=HEALTH_PROBE_TIMEOUT) as client:
            resp = client.get(f"{_base_url()}/profiles")
        if resp.status_code >= 400:
            return False
        data = resp.json()
        items = data if isinstance(data, list) else (data.get("profiles") or data.get("items") or [])
        for it in items:
            if isinstance(it, dict) and str(it.get("id") or "") == pid:
                return True
        return False
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
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Create a voice profile on the local engine, then attach the sample."""
    if not reference_text.strip():
        raise ValueError("reference_text is required — it must match what the audio sample says")

    with httpx.Client(timeout=timeout) as client:
        profile_resp = client.post(
            f"{_base_url()}/profiles",
            json={"name": name[:100], "language": language, "voice_type": "cloned"},
        )
        if profile_resp.status_code >= 400:
            raise RuntimeError(
                f"ZECT Voicebox profile creation failed ({profile_resp.status_code}): {profile_resp.text[:300]}"
            )
        profile_id = profile_resp.json().get("id")
        if not profile_id:
            raise RuntimeError(f"ZECT Voicebox profile response missing id: {profile_resp.text[:300]}")

        sample_resp = client.post(
            f"{_base_url()}/profiles/{profile_id}/samples",
            files={"file": (filename, audio_bytes, content_type)},
            data={"reference_text": reference_text[:2000]},
        )
        if sample_resp.status_code >= 400:
            raise RuntimeError(
                f"ZECT Voicebox sample upload failed ({sample_resp.status_code}): {sample_resp.text[:300]}"
            )

    invalidate_health_cache()
    return {"voice_id": profile_id, "name": name}


def _resolve_audio_url(audio_path: str) -> str:
    if audio_path.startswith("http://") or audio_path.startswith("https://"):
        return audio_path
    filename = Path(audio_path).name
    return f"{_base_url()}{CHATTERBOX_AUDIO_PATH_TEMPLATE.format(filename=filename)}"


class ProfileNotFoundError(RuntimeError):
    """Voicebox profile id missing — caller should clear external_voice_id and re-provision."""


def synthesize_speech(text: str, voice_id: str, *, language: str = "en", engine: str | None = None) -> bytes:
    """Synthesize text in the given cloned voice profile. Returns raw audio bytes."""
    with httpx.Client(timeout=SPEAK_TIMEOUT) as client:
        gen_resp = client.post(
            f"{_base_url()}/generate",
            json={
                "profile_id": voice_id,
                "text": text[:4000],
                "language": language,
                "engine": engine or DEFAULT_CHATTERBOX_ENGINE,
            },
        )
        if gen_resp.status_code == 404:
            raise ProfileNotFoundError(
                f"ZECT Voicebox generation failed (404): {gen_resp.text[:300]}"
            )
        if gen_resp.status_code >= 400:
            raise RuntimeError(
                f"ZECT Voicebox generation failed ({gen_resp.status_code}): {gen_resp.text[:300]}"
            )
        data = gen_resp.json()
        if data.get("status") == "error" or data.get("error"):
            raise RuntimeError(f"ZECT Voicebox generation error: {data.get('error')}")
        audio_path = data.get("audio_path")
        if not audio_path:
            raise RuntimeError(
                f"ZECT Voicebox generation response missing audio_path: {gen_resp.text[:300]}"
            )

        audio_url = _resolve_audio_url(audio_path)
        audio_resp = client.get(audio_url)
        if audio_resp.status_code >= 400:
            raise RuntimeError(
                f"ZECT Voicebox audio download failed ({audio_resp.status_code}) for {audio_path} — "
                "check the local engine /docs for the download route and set "
                "CHATTERBOX_AUDIO_PATH_TEMPLATE if it differs."
            )
        return audio_resp.content


def delete_voice(voice_id: str) -> None:
    """Best-effort cleanup of an engine-side profile."""
    try:
        with httpx.Client(timeout=15.0) as client:
            client.delete(f"{_base_url()}/profiles/{voice_id}")
    except Exception:
        pass

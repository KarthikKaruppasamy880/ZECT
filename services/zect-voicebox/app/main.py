"""ZECT Voicebox FastAPI — Mentrix Chatterbox-compatible native surface."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import config
from app import store
from app.engine import backend_name, models_ready, status_detail, synthesize

app = FastAPI(
    title=config.PRODUCT,
    version="1.0.0",
    description="ZECT-native local clone TTS engine for Mentrix (Chatterbox client).",
)


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    language: str = "en"
    voice_type: str = "cloned"


class GenerateRequest(BaseModel):
    profile_id: str
    text: str = Field(..., min_length=1, max_length=4000)
    language: str = "en"
    engine: str | None = None


def _audio_dir() -> Path:
    return config.data_dir() / "audio"


def _safe_name(name: str) -> str:
    base = re.sub(r"[^\w.\-]+", "_", (name or "clip").strip())[:80] or "clip"
    return base


@app.on_event("startup")
def _warmup() -> None:
    # Best-effort preload so first Test speak is faster; never block process exit.
    try:
        from app.engine import ensure_loaded

        ensure_loaded()
    except Exception:
        pass


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "ok": True,
        "brand": config.BRAND,
        "product": config.PRODUCT,
        "health": "/health",
        "docs": "/docs",
        "profiles": "/profiles",
        "hint": "Mentrix uses GET /profiles for online checks. Prefer http://127.0.0.1:17493 (not localhost).",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    ready = models_ready()
    return {
        "ok": True,
        "brand": config.BRAND,
        "product": config.PRODUCT,
        "backend": "native",
        "models_ready": ready,
        "synth": backend_name(),
        "detail": status_detail(),
        "engine_id": config.ENGINE_ID,
    }


@app.get("/profiles")
async def list_profiles() -> list[dict[str, Any]]:
    # Fast path for Mentrix 2s health — no model load.
    return store.list_profiles()


@app.post("/profiles")
async def create_profile(body: ProfileCreate) -> dict[str, Any]:
    return store.create_profile(body.name, body.language, body.voice_type)


@app.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str) -> dict[str, Any]:
    deleted = store.delete_profile(profile_id)
    return {"ok": True, "deleted": deleted}


@app.post("/profiles/{profile_id}/samples")
async def upload_sample(
    profile_id: str,
    file: UploadFile = File(...),
    reference_text: str = Form(...),
) -> dict[str, Any]:
    if not (reference_text or "").strip():
        raise HTTPException(status_code=400, detail="reference_text is required")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio sample")
    filename = file.filename or "sample.wav"
    try:
        return store.attach_sample(profile_id, raw, filename, reference_text)
    except KeyError:
        raise HTTPException(status_code=404, detail="profile not found") from None


@app.post("/generate")
async def generate(body: GenerateRequest) -> dict[str, Any]:
    raw = store.get_profile_raw(body.profile_id)
    if not raw:
        raise HTTPException(status_code=404, detail="profile not found")
    sample_path = raw.get("sample_path") or ""
    if not sample_path or not Path(sample_path).is_file():
        raise HTTPException(
            status_code=400,
            detail="Profile has no sample — upload via POST /profiles/{id}/samples",
        )
    if not models_ready():
        raise HTTPException(
            status_code=503,
            detail=f"ZECT Voicebox models not ready: {status_detail()}",
        )
    # Mentrix may send engine=qwen; map to ZECT native chatterbox/stub.
    try:
        wav_bytes = synthesize(
            text=body.text[:4000],
            sample_path=sample_path,
            reference_text=raw.get("reference_text") or "",
            language=body.language or raw.get("language") or "en",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"ZECT Voicebox generate failed (models not ready / synthesis error): {exc}",
        ) from exc

    local_name = f"{uuid.uuid4().hex}_{_safe_name('speech')}.wav"
    dest = _audio_dir() / local_name
    dest.write_bytes(wav_bytes)
    return {
        "id": uuid.uuid4().hex,
        "profile_id": body.profile_id,
        "text": body.text[:4000],
        "language": body.language,
        "audio_path": f"/audio/{local_name}",
        "status": "ok",
        "brand": config.BRAND,
        "engine": backend_name(),
        "requested_engine": body.engine or config.ENGINE_ID,
    }


@app.get("/audio/{filename}")
async def get_audio(filename: str) -> FileResponse:
    safe = Path(filename).name
    path = _audio_dir() / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(path, media_type="audio/wav")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.port(),
        reload=False,
    )


if __name__ == "__main__":
    main()

"""ZECT Voicebox FastAPI — Mentrix Chatterbox-compatible surface."""

from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from app import config
from app.upstream import UpstreamError, proxy_request, raise_if_bad, upstream_online

app = FastAPI(
    title=config.PRODUCT,
    version="1.0.0",
    description="ZECT-branded local clone TTS engine for Mentrix (Chatterbox client).",
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
    online = False
    if config.backend() == "upstream":
        try:
            online = await asyncio.wait_for(upstream_online(), timeout=0.6)
        except asyncio.TimeoutError:
            online = False
    return {
        "ok": True,
        "brand": config.BRAND,
        "product": config.PRODUCT,
        "backend": config.backend(),
        "upstream_url": config.upstream_url() if config.backend() == "upstream" else "",
        "upstream_online": online,
    }


@app.get("/profiles")
async def list_profiles() -> Any:
    if config.backend() != "upstream":
        raise HTTPException(status_code=501, detail="Only upstream backend is implemented in this release")
    try:
        # Hard cap so Mentrix's 2s health never hangs on Windows SYN retries to :17494.
        res = await asyncio.wait_for(proxy_request("GET", "/profiles", timeout=0.5), timeout=0.6)
        raise_if_bad(res)
        return Response(content=res.content, media_type=res.headers.get("content-type", "application/json"))
    except asyncio.TimeoutError:
        return []
    except UpstreamError as exc:
        # Mentrix treats <500 on /profiles as "online". When upstream is down,
        # still answer with an empty list so ZECT Voicebox itself is reachable,
        # and surface upstream status via /health.
        if exc.status in (502, 503, 504) or exc.status >= 500:
            return []
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    except Exception:
        return []


@app.post("/profiles")
async def create_profile(body: ProfileCreate) -> Any:
    if config.backend() != "upstream":
        raise HTTPException(status_code=501, detail="Only upstream backend is implemented in this release")
    try:
        res = await proxy_request(
            "POST",
            "/profiles",
            json={"name": body.name[:100], "language": body.language, "voice_type": body.voice_type},
            timeout=60.0,
        )
        raise_if_bad(res)
        return Response(content=res.content, media_type=res.headers.get("content-type", "application/json"))
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@app.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str) -> Any:
    if config.backend() != "upstream":
        raise HTTPException(status_code=501, detail="Only upstream backend is implemented in this release")
    try:
        res = await proxy_request("DELETE", f"/profiles/{profile_id}", timeout=30.0)
        if res.status_code == 404:
            return JSONResponse({"ok": True, "deleted": False})
        raise_if_bad(res)
        if res.content:
            return Response(content=res.content, media_type=res.headers.get("content-type", "application/json"))
        return {"ok": True, "deleted": True}
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@app.post("/profiles/{profile_id}/samples")
async def upload_sample(
    profile_id: str,
    file: UploadFile = File(...),
    reference_text: str = Form(...),
) -> Any:
    if config.backend() != "upstream":
        raise HTTPException(status_code=501, detail="Only upstream backend is implemented in this release")
    if not (reference_text or "").strip():
        raise HTTPException(status_code=400, detail="reference_text is required")
    raw = await file.read()
    filename = file.filename or "sample.wav"
    content_type = file.content_type or "application/octet-stream"
    try:
        res = await proxy_request(
            "POST",
            f"/profiles/{profile_id}/samples",
            data={"reference_text": reference_text[:2000]},
            files={"file": (filename, raw, content_type)},
            timeout=120.0,
        )
        raise_if_bad(res)
        return Response(content=res.content, media_type=res.headers.get("content-type", "application/json"))
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@app.post("/generate")
async def generate(body: GenerateRequest) -> dict[str, Any]:
    if config.backend() != "upstream":
        raise HTTPException(status_code=501, detail="Only upstream backend is implemented in this release")
    payload: dict[str, Any] = {
        "profile_id": body.profile_id,
        "text": body.text[:4000],
        "language": body.language,
    }
    if body.engine:
        payload["engine"] = body.engine
    try:
        res = await proxy_request("POST", "/generate", json=payload, timeout=180.0)
        raise_if_bad(res)
        data = res.json()
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"upstream generate parse failed: {exc}") from exc

    if data.get("status") == "error" or data.get("error"):
        raise HTTPException(status_code=502, detail=str(data.get("error") or "generate_error"))

    audio_path = data.get("audio_path") or ""
    if not audio_path:
        raise HTTPException(status_code=502, detail="upstream missing audio_path")

    # Mentrix downloads via CHATTERBOX_BASE_URL + /audio/{filename}.
    # Fetch upstream audio (absolute URL, relative path, or /audio/…) and re-host locally.
    local_name = f"{uuid.uuid4().hex}_{_safe_name(Path(str(audio_path)).name)}"
    if not local_name.lower().endswith((".wav", ".mp3", ".ogg", ".flac", ".webm")):
        local_name = f"{local_name}.wav"
    dest = _audio_dir() / local_name

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if str(audio_path).startswith("http://") or str(audio_path).startswith("https://"):
                audio_res = await client.get(str(audio_path))
            else:
                base = config.upstream_url()
                rel = str(audio_path)
                if not rel.startswith("/"):
                    # Mentrix template default is /audio/{filename}
                    rel = f"/audio/{Path(rel).name}" if not rel.startswith("audio/") else f"/{rel}"
                audio_res = await client.get(f"{base}{rel}")
            if audio_res.status_code >= 400 or not audio_res.content:
                # Try raw path join once more
                audio_res = await client.get(f"{config.upstream_url()}/{str(audio_path).lstrip('/')}")
            if audio_res.status_code >= 400 or not audio_res.content:
                raise HTTPException(
                    status_code=502,
                    detail=f"upstream audio download failed ({audio_res.status_code}) for {audio_path}",
                )
            dest.write_bytes(audio_res.content)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"audio mirror failed: {exc}") from exc

    out = dict(data)
    out["audio_path"] = f"/audio/{local_name}"
    out["brand"] = config.BRAND
    return out


@app.get("/audio/{filename}")
async def get_audio(filename: str) -> FileResponse:
    safe = Path(filename).name
    path = _audio_dir() / safe
    if not path.is_file():
        # Fall through to upstream for files we did not mirror
        if config.backend() == "upstream":
            try:
                res = await proxy_request("GET", f"/audio/{safe}", timeout=60.0)
                if res.status_code < 400 and res.content:
                    path.write_bytes(res.content)
                    return FileResponse(path)
            except UpstreamError:
                pass
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(path)


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

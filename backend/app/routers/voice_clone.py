"""Mentrix voice cloning — /api/mentrix/voice/*."""

from __future__ import annotations

import os
import re
import threading
from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.core.auth.rbac import log_audit
from app.database import get_db
from app.models import ClonedVoice

router = APIRouter(prefix="/api/mentrix/voice", tags=["mentrix-voice"])

MAX_SAMPLE_BYTES = 10_000_000
MAX_NAME_LEN = 100
MAX_REFERENCE_TEXT_LEN = 2000
MAX_SPEAK_TEXT_LEN = 4000
SPEAK_RATE_LIMIT = 30  # per user per hour
CLONE_RATE_LIMIT = 5

ALLOWED_AUDIO_MIME = frozenset({
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/ogg",
    "audio/webm",
    "application/octet-stream",
})

_speak_hits: dict[int, list[float]] = defaultdict(list)
_clone_hits: dict[int, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()


def _rate_limit(bucket: dict[int, list[float]], user_id: int, limit: int, window_s: int = 3600) -> None:
    now = time()
    with _rate_lock:
        hits = [t for t in bucket[user_id] if now - t < window_s]
        if len(hits) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded — try again later")
        hits.append(now)
        bucket[user_id] = hits


def _sanitize_filename(name: str | None) -> str:
    base = os.path.basename(name or "sample.wav")
    return re.sub(r"[^\w.\-]", "_", base)[:120] or "sample.wav"


def _validate_audio_mime(content_type: str | None) -> None:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct and ct not in ALLOWED_AUDIO_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type '{ct}' — use WAV, MP3, OGG, or MP4",
        )


class ClonedVoiceOut(BaseModel):
    voice_id: str
    name: str
    provider: str


class SpeakRequest(BaseModel):
    text: str = Field(..., max_length=MAX_SPEAK_TEXT_LEN)


@router.post("/clone", response_model=ClonedVoiceOut)
async def clone_my_voice(
    name: str = Form(...),
    reference_text: str = Form(...),
    sample: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.llm.voicebox_client import clone_voice, delete_voice, voicebox_available

    _rate_limit(_clone_hits, current_user.user_id, CLONE_RATE_LIMIT)

    if not voicebox_available():
        raise HTTPException(
            status_code=503,
            detail="Voicebox isn't reachable — start it locally (see github.com/jamiepine/voicebox) to enable voice cloning.",
        )
    if not name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    if len(name.strip()) > MAX_NAME_LEN:
        raise HTTPException(status_code=400, detail=f"name too long (max {MAX_NAME_LEN} chars)")
    if not reference_text.strip():
        raise HTTPException(status_code=400, detail="reference_text is required — it must match what the sample says")
    if len(reference_text.strip()) > MAX_REFERENCE_TEXT_LEN:
        raise HTTPException(status_code=400, detail=f"reference_text too long (max {MAX_REFERENCE_TEXT_LEN} chars)")

    _validate_audio_mime(sample.content_type)

    audio_bytes = await sample.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio sample")
    if len(audio_bytes) > MAX_SAMPLE_BYTES:
        raise HTTPException(status_code=400, detail="Sample too large (max 10MB)")

    safe_name = _sanitize_filename(sample.filename)

    try:
        result = clone_voice(
            name.strip(),
            audio_bytes,
            safe_name,
            sample.content_type or "audio/wav",
            reference_text=reference_text.strip(),
        )
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    existing = db.query(ClonedVoice).filter(ClonedVoice.user_id == current_user.user_id).first()
    old_voice_id = existing.voice_id if existing else None
    if existing:
        existing.voice_id = result["voice_id"]
        existing.name = name.strip()
        existing.provider = "voicebox"
    else:
        existing = ClonedVoice(
            user_id=current_user.user_id,
            voice_id=result["voice_id"],
            name=name.strip(),
            provider="voicebox",
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)

    if old_voice_id and old_voice_id != existing.voice_id:
        delete_voice(old_voice_id)

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="voice_clone",
        resource_type="cloned_voice",
        details={"name": name.strip()[:50], "bytes": len(audio_bytes), "filename": safe_name},
    )

    return ClonedVoiceOut(voice_id=existing.voice_id, name=existing.name, provider=existing.provider)


@router.get("/my-voice")
def get_my_voice(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(ClonedVoice).filter(ClonedVoice.user_id == current_user.user_id).first()
    if not row:
        return None
    return ClonedVoiceOut(voice_id=row.voice_id, name=row.name, provider=row.provider)


@router.delete("/my-voice")
def reset_my_voice(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.llm.voicebox_client import delete_voice

    row = db.query(ClonedVoice).filter(ClonedVoice.user_id == current_user.user_id).first()
    if not row:
        return {"cleared": False}
    voice_id = row.voice_id
    db.delete(row)
    db.commit()
    delete_voice(voice_id)
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="voice_reset",
        resource_type="cloned_voice",
        details={"voice_id": voice_id[:32]},
    )
    return {"cleared": True}


@router.post("/speak")
def speak(
    req: SpeakRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.llm.voicebox_client import synthesize_speech

    _rate_limit(_speak_hits, current_user.user_id, SPEAK_RATE_LIMIT)

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    row = db.query(ClonedVoice).filter(ClonedVoice.user_id == current_user.user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="No cloned voice configured for this user")

    try:
        audio = synthesize_speech(text, row.voice_id)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="voice_speak",
        resource_type="cloned_voice",
        details={"chars": len(text), "voice_id": row.voice_id[:32]},
    )

    return Response(content=audio, media_type="audio/mpeg")

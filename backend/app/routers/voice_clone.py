"""Mentrix Chatterbox voice cloning — /api/mentrix/voice/*."""

from __future__ import annotations

import logging
import os
import re
import threading
import uuid
from collections import defaultdict
from pathlib import Path
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
logger = logging.getLogger("mentrix.voice_clone")

MAX_SAMPLE_BYTES = 10_000_000
MAX_NAME_LEN = 100
MAX_REFERENCE_TEXT_LEN = 2000
MAX_SPEAK_TEXT_LEN = 4000
# 30/hour was sized for one /speak call per full reply. Realtime companion
# now dispatches one call per SENTENCE as it streams (lower time-to-first-
# audio), and Present Deck already chunks per ~220 chars — both multiply
# calls per turn/slide 3-5x, so the old ceiling started 429ing legitimate
# single-user conversations/presentations well within normal use.
SPEAK_RATE_LIMIT = int(os.getenv("MENTRIX_SPEAK_RATE_LIMIT", "300"))  # per user per hour
CLONE_RATE_LIMIT = 5

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
VOICES_DIR = _BACKEND_ROOT / "data" / "voices"

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


def _ext_for_mime(content_type: str | None, filename: str) -> str:
    name = (filename or "").lower()
    if "." in name:
        return Path(name).suffix[:10] or ".wav"
    ct = (content_type or "").lower()
    if "mpeg" in ct or "mp3" in ct:
        return ".mp3"
    if "ogg" in ct:
        return ".ogg"
    if "webm" in ct:
        return ".webm"
    if "mp4" in ct:
        return ".mp4"
    return ".wav"


def _save_sample(user_id: int, voice_id: str, audio_bytes: bytes, filename: str, content_type: str | None) -> str:
    user_dir = VOICES_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{voice_id}{_ext_for_mime(content_type, filename)}"
    path.write_bytes(audio_bytes)
    return str(path)


def _delete_sample_file(sample_path: str | None) -> None:
    if not sample_path:
        return
    try:
        p = Path(sample_path)
        if p.is_file():
            p.unlink()
    except Exception:
        pass


def _default_voice(db: Session, user_id: int) -> ClonedVoice | None:
    row = (
        db.query(ClonedVoice)
        .filter(ClonedVoice.user_id == user_id, ClonedVoice.is_default.is_(True))
        .first()
    )
    if row:
        return row
    return (
        db.query(ClonedVoice)
        .filter(ClonedVoice.user_id == user_id)
        .order_by(ClonedVoice.created_at.desc())
        .first()
    )


def _clear_defaults(db: Session, user_id: int) -> None:
    for row in db.query(ClonedVoice).filter(ClonedVoice.user_id == user_id, ClonedVoice.is_default.is_(True)):
        row.is_default = False


def _row_out(row: ClonedVoice) -> "ClonedVoiceOut":
    return ClonedVoiceOut(
        id=row.id,
        voice_id=row.voice_id,
        name=row.name or "",
        provider=row.provider or "chatterbox",
        is_default=bool(row.is_default),
        has_sample=bool(row.sample_path),
    )


# Re-provisioning (voice cloning) is heavier than plain synthesis and only a
# fallback path (external_voice_id missing/stale) — if it just failed, don't
# repeat the same slow attempt on every subsequent sentence of a live
# conversation. Per-process, keyed by ZECT voice_id: value is the monotonic
# time() after which a retry is allowed again.
_REPROVISION_COOLDOWN_S = 60.0
_reprovision_blocked_until: dict[str, float] = {}


def _ensure_engine_profile(row: ClonedVoice) -> str:
    """Return engine profile id, re-provisioning from stored sample if needed."""
    from app.services.llm.chatterbox_client import (
        REPROVISION_TIMEOUT,
        chatterbox_available,
        clone_voice,
    )

    if row.external_voice_id:
        return row.external_voice_id
    if not row.sample_path or not Path(row.sample_path).is_file():
        raise HTTPException(
            status_code=404,
            detail="Voice sample missing — clone again to restore Present/session audio",
        )
    if not chatterbox_available():
        raise HTTPException(
            status_code=503,
            detail="Chatterbox engine offline — start the local synthesis service to speak.",
        )
    blocked_until = _reprovision_blocked_until.get(row.voice_id, 0.0)
    if time() < blocked_until:
        raise HTTPException(
            status_code=503,
            detail="Chatterbox re-provisioning failed recently — retrying shortly, using fallback voice for now.",
        )
    audio_bytes = Path(row.sample_path).read_bytes()
    filename = Path(row.sample_path).name
    try:
        result = clone_voice(
            row.name or "Mentrix Voice",
            audio_bytes,
            filename,
            "application/octet-stream",
            reference_text=(row.reference_text or "").strip() or "Hello, this is my voice sample.",
            timeout=REPROVISION_TIMEOUT,
        )
    except Exception as exc:
        _reprovision_blocked_until[row.voice_id] = time() + _REPROVISION_COOLDOWN_S
        # Chatterbox is local/no-API-key — safe to log the message, still
        # truncated in case the engine ever echoes request content back.
        logger.warning(
            "Chatterbox re-provision failed for voice_id=%s: %s — falling back for %ss",
            row.voice_id,
            str(exc)[:300],
            _REPROVISION_COOLDOWN_S,
        )
        raise HTTPException(status_code=502, detail="Chatterbox re-provisioning failed") from exc
    _reprovision_blocked_until.pop(row.voice_id, None)
    return result["voice_id"]


class ClonedVoiceOut(BaseModel):
    id: int | None = None
    voice_id: str
    name: str
    provider: str
    is_default: bool = False
    has_sample: bool = False


OPENAI_STOCK_VOICES = ("alloy", "echo", "fable", "onyx", "nova", "shimmer")


class SpeakRequest(BaseModel):
    text: str = Field(..., max_length=MAX_SPEAK_TEXT_LEN)
    voice_id: str | None = None
    # When set, bypasses Chatterbox/cloned-voice lookup entirely and speaks
    # with this specific OpenAI stock voice instead — e.g. "let me pick a
    # male/female voice for this presentation" rather than my own clone.
    stock_voice: str | None = None


@router.post("/clone", response_model=ClonedVoiceOut)
async def clone_my_voice(
    name: str = Form(...),
    reference_text: str = Form(...),
    sample: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.llm.chatterbox_client import chatterbox_available, clone_voice

    _rate_limit(_clone_hits, current_user.user_id, CLONE_RATE_LIMIT)

    if not name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    if len(name.strip()) > MAX_NAME_LEN:
        raise HTTPException(status_code=400, detail=f"name too long (max {MAX_NAME_LEN} chars)")
    if not reference_text.strip():
        raise HTTPException(
            status_code=400,
            detail="reference_text is required — it must match what the sample says",
        )
    if len(reference_text.strip()) > MAX_REFERENCE_TEXT_LEN:
        raise HTTPException(status_code=400, detail=f"reference_text too long (max {MAX_REFERENCE_TEXT_LEN} chars)")

    _validate_audio_mime(sample.content_type)

    audio_bytes = await sample.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio sample")
    if len(audio_bytes) > MAX_SAMPLE_BYTES:
        raise HTTPException(status_code=400, detail="Sample too large (max 10MB)")

    safe_name = _sanitize_filename(sample.filename)
    zect_voice_id = uuid.uuid4().hex
    sample_path = _save_sample(
        current_user.user_id,
        zect_voice_id,
        audio_bytes,
        safe_name,
        sample.content_type,
    )

    external_id: str | None = None
    if chatterbox_available():
        try:
            result = clone_voice(
                name.strip(),
                audio_bytes,
                safe_name,
                sample.content_type or "audio/wav",
                reference_text=reference_text.strip(),
            )
            external_id = result["voice_id"]
        except (RuntimeError, ValueError) as e:
            _delete_sample_file(sample_path)
            raise HTTPException(status_code=502, detail=str(e)) from e
    # Engine offline: still persist sample in ZECT DB for later provision/speak.

    _clear_defaults(db, current_user.user_id)
    row = ClonedVoice(
        user_id=current_user.user_id,
        voice_id=zect_voice_id,
        external_voice_id=external_id,
        name=name.strip(),
        provider="chatterbox",
        sample_path=sample_path,
        reference_text=reference_text.strip(),
        is_default=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="voice_clone",
        resource_type="cloned_voice",
        details={
            "name": name.strip()[:50],
            "bytes": len(audio_bytes),
            "filename": safe_name,
            "voice_id": zect_voice_id,
            "engine_provisioned": bool(external_id),
        },
    )

    return _row_out(row)


@router.get("/voices", response_model=list[ClonedVoiceOut])
def list_my_voices(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ClonedVoice)
        .filter(ClonedVoice.user_id == current_user.user_id)
        .order_by(ClonedVoice.is_default.desc(), ClonedVoice.created_at.desc())
        .all()
    )
    return [_row_out(r) for r in rows]


@router.get("/my-voice")
def get_my_voice(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    row = _default_voice(db, current_user.user_id)
    if not row:
        return None
    return _row_out(row)


@router.post("/voices/{voice_id}/default", response_model=ClonedVoiceOut)
def set_default_voice(
    voice_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(ClonedVoice)
        .filter(ClonedVoice.user_id == current_user.user_id, ClonedVoice.voice_id == voice_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Voice not found")
    _clear_defaults(db, current_user.user_id)
    row.is_default = True
    db.commit()
    db.refresh(row)
    return _row_out(row)


@router.delete("/voices/{voice_id}")
def delete_voice_by_id(
    voice_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.llm.chatterbox_client import delete_voice

    row = (
        db.query(ClonedVoice)
        .filter(ClonedVoice.user_id == current_user.user_id, ClonedVoice.voice_id == voice_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Voice not found")
    was_default = bool(row.is_default)
    ext = row.external_voice_id
    sample_path = row.sample_path
    db.delete(row)
    db.commit()
    _delete_sample_file(sample_path)
    if ext:
        delete_voice(ext)
    if was_default:
        nxt = (
            db.query(ClonedVoice)
            .filter(ClonedVoice.user_id == current_user.user_id)
            .order_by(ClonedVoice.created_at.desc())
            .first()
        )
        if nxt:
            nxt.is_default = True
            db.commit()
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="voice_delete",
        resource_type="cloned_voice",
        details={"voice_id": voice_id[:32]},
    )
    return {"deleted": True}


@router.delete("/my-voice")
def reset_my_voice(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete all clones for the user (legacy reset)."""
    from app.services.llm.chatterbox_client import delete_voice

    rows = db.query(ClonedVoice).filter(ClonedVoice.user_id == current_user.user_id).all()
    if not rows:
        return {"cleared": False}
    for row in rows:
        if row.external_voice_id:
            delete_voice(row.external_voice_id)
        _delete_sample_file(row.sample_path)
        db.delete(row)
    db.commit()
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="voice_reset",
        resource_type="cloned_voice",
        details={"count": len(rows)},
    )
    return {"cleared": True}


@router.post("/speak")
def speak(
    req: SpeakRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.llm.chatterbox_client import chatterbox_available, synthesize_speech
    from app.services.llm.openai_tts import openai_tts_available, synthesize_openai_speech

    _rate_limit(_speak_hits, current_user.user_id, SPEAK_RATE_LIMIT)

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    if req.stock_voice:
        if req.stock_voice not in OPENAI_STOCK_VOICES:
            raise HTTPException(status_code=400, detail=f"stock_voice must be one of {OPENAI_STOCK_VOICES}")
        if not openai_tts_available():
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured — cannot use a stock voice")
        try:
            audio = synthesize_openai_speech(text, voice=req.stock_voice)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        try:
            log_audit(
                db=db,
                user_id=current_user.user_id,
                action="voice_speak",
                resource_type="cloned_voice",
                details={"chars": len(text), "engine": f"openai_stock:{req.stock_voice}"},
            )
        except Exception:
            pass
        return Response(
            content=audio,
            media_type="audio/mpeg",
            headers={"X-Mentrix-TTS-Engine": f"openai_stock:{req.stock_voice}"},
        )

    if req.voice_id:
        row = (
            db.query(ClonedVoice)
            .filter(ClonedVoice.user_id == current_user.user_id, ClonedVoice.voice_id == req.voice_id)
            .first()
        )
    else:
        row = _default_voice(db, current_user.user_id)

    # Prefer Chatterbox clone; if engine offline and OpenAI is configured, still speak
    # (stock OpenAI voice — not the clone) so Present/Companion is not silent.
    audio: bytes | None = None
    engine_used = "none"
    if row:
        try:
            if chatterbox_available():
                engine_id = _ensure_engine_profile(row)
                if engine_id != row.external_voice_id:
                    row.external_voice_id = engine_id
                    db.commit()
                audio = synthesize_speech(text, engine_id)
                engine_used = "chatterbox"
            elif row.external_voice_id:
                # Profile id exists but engine may be down — try once, then fall back
                audio = synthesize_speech(text, row.external_voice_id)
                engine_used = "chatterbox"
        except HTTPException as e:
            if e.status_code not in (502, 503, 404) or not openai_tts_available():
                raise
            audio = None
        except Exception:
            # httpx ConnectError / RuntimeError when Chatterbox is down
            if not openai_tts_available():
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Chatterbox speak failed — start local engine (CHATTERBOX_BASE_URL) "
                        "or set OPENAI_API_KEY for TTS fallback"
                    ),
                )
            audio = None

    if audio is None:
        if not openai_tts_available():
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="No cloned voice configured — clone a voice in Companion → Voice, or set OPENAI_API_KEY for TTS fallback",
                )
            raise HTTPException(
                status_code=503,
                detail="Chatterbox engine offline — start CHATTERBOX_BASE_URL service, or set OPENAI_API_KEY for TTS fallback",
            )
        try:
            audio = synthesize_openai_speech(text)
            engine_used = "openai_tts_fallback"
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

    try:
        log_audit(
            db=db,
            user_id=current_user.user_id,
            action="voice_speak",
            resource_type="cloned_voice",
            details={
                "chars": len(text),
                "voice_id": (row.voice_id[:32] if row else ""),
                "engine": engine_used,
            },
        )
    except Exception:
        # Windows consoles (cp1252) can break on emoji in audit helpers — never block audio.
        pass

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"X-Mentrix-TTS-Engine": engine_used},
    )

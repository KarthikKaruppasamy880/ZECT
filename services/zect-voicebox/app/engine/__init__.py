"""ZECT native clone TTS synthesizer.

Primary path: ResembleAI Chatterbox Multilingual (optional ML deps).
Patterns adapted from open MIT Voicebox server backends; ZECT-owned packaging.
Stub path: short WAV for tests / when ZECT_VOICEBOX_ALLOW_STUB=1 and ML missing.
"""

from __future__ import annotations

import logging
import struct
import threading
import wave
from io import BytesIO
from pathlib import Path
from typing import Any

from app import config

logger = logging.getLogger("zect-voicebox.engine")

_lock = threading.Lock()
_model: Any = None
_device: str | None = None
_load_error: str = ""
_backend_name: str = "none"


def models_ready() -> bool:
    mode = config.synth_mode()
    if mode == "stub":
        return True
    if _model is not None:
        return True
    if mode == "auto" and config.allow_stub() and not _chatterbox_importable():
        # Stub stands in until ML is installed — Mentrix can still Test speak.
        return True
    return _model is not None


def backend_name() -> str:
    if _model is not None:
        return _backend_name
    if config.synth_mode() == "stub" or (
        config.synth_mode() == "auto" and config.allow_stub() and not _chatterbox_importable()
    ):
        return "stub"
    return _backend_name or "none"


def status_detail() -> str:
    if models_ready():
        return f"synth={backend_name()}"
    if _load_error:
        return _load_error
    return (
        "Models not ready — pip install -r services/zect-voicebox/requirements-ml.txt "
        "or set ZECT_VOICEBOX_ALLOW_STUB=1 for stub WAV."
    )


def _chatterbox_importable() -> bool:
    try:
        import chatterbox.mtl_tts  # noqa: F401

        return True
    except Exception:
        return False


def ensure_loaded() -> None:
    """Lazy-load Chatterbox when requested; no-op for stub."""
    global _model, _device, _load_error, _backend_name
    mode = config.synth_mode()
    if mode == "stub":
        _backend_name = "stub"
        return
    if _model is not None:
        return
    if mode == "auto" and not _chatterbox_importable():
        if config.allow_stub():
            _backend_name = "stub"
            return
        _load_error = "chatterbox-tts not installed"
        return
    with _lock:
        if _model is not None:
            return
        try:
            _load_chatterbox()
            _load_error = ""
            _backend_name = "chatterbox"
        except Exception as exc:  # noqa: BLE001
            _load_error = str(exc)[:400]
            logger.exception("Failed to load Chatterbox TTS")
            if config.allow_stub() and mode == "auto":
                _backend_name = "stub"
            else:
                raise


def _load_chatterbox() -> None:
    global _model, _device
    import os

    os.environ.setdefault("HF_HOME", str(config.model_dir() / "huggingface"))
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    _device = device
    logger.info("Loading ZECT Chatterbox Multilingual on %s …", device)

    if device == "cpu":
        _orig = torch.load

        def _patched(*args, **kwargs):
            kwargs.setdefault("map_location", "cpu")
            return _orig(*args, **kwargs)

        torch.load = _patched  # type: ignore[assignment]
        try:
            _model = ChatterboxMultilingualTTS.from_pretrained(device=device)
        finally:
            torch.load = _orig  # type: ignore[assignment]
    else:
        _model = ChatterboxMultilingualTTS.from_pretrained(device=device)

    # Stability: eager attention when available
    try:
        t3_tfmr = _model.t3.tfmr
        if hasattr(t3_tfmr, "config") and hasattr(t3_tfmr.config, "_attn_implementation"):
            t3_tfmr.config._attn_implementation = "eager"
    except Exception:
        pass
    logger.info("ZECT Chatterbox Multilingual loaded")


def synthesize(
    *,
    text: str,
    sample_path: str,
    reference_text: str,
    language: str = "en",
) -> bytes:
    """Return WAV bytes for Mentrix download."""
    ensure_loaded()
    if backend_name() == "stub":
        return _stub_wav(text=text, sample_path=sample_path)
    if _model is None:
        raise RuntimeError(status_detail())

    ref = sample_path if sample_path and Path(sample_path).is_file() else None
    lang = (language or "en")[:8]

    def _gen():
        import numpy as np
        import torch

        wav = _model.generate(
            text,
            language_id=lang,
            audio_prompt_path=ref,
            exaggeration=0.5,
            cfg_weight=0.5,
            temperature=0.8,
            repetition_penalty=2.0,
        )
        if isinstance(wav, torch.Tensor):
            audio = wav.squeeze().cpu().numpy().astype(np.float32)
        else:
            audio = np.asarray(wav, dtype=np.float32)
        sr = int(getattr(_model, "sr", 24000) or 24000)
        return _float_to_wav_bytes(audio, sr)

    return _gen()


def _float_to_wav_bytes(audio, sample_rate: int) -> bytes:
    import numpy as np

    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _stub_wav(*, text: str, sample_path: str) -> bytes:
    """Deterministic short tone WAV so Mentrix speak pipeline works without ML."""
    import math

    sample_rate = 22050
    duration = min(2.5, 0.35 + 0.04 * max(1, len(text.split())))
    n = int(sample_rate * duration)
    # Prefer sample length cue if present
    freq = 220.0
    if sample_path and Path(sample_path).is_file():
        freq = 196.0 + (Path(sample_path).stat().st_size % 200)
    frames = bytearray()
    for i in range(n):
        t = i / sample_rate
        # Soft envelope
        env = min(1.0, t * 8) * min(1.0, (duration - t) * 8)
        sample = int(12000 * env * math.sin(2 * math.pi * freq * t))
        frames += struct.pack("<h", max(-32767, min(32767, sample)))
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    return buf.getvalue()

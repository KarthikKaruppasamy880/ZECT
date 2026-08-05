"""Chatterbox voice cloning — DB-persisted clones, list/default/delete, speak."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers, UploadFile

import app.models  # noqa: F401 — register ClonedVoice
from app.database import Base
from app.models import ClonedVoice
from app.services.llm import chatterbox_client, elevenlabs_client
from app.services.mentrix.realtime import _cloned_voice_for_user, mint_realtime_session

USER = Mock(user_id=5)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _mock_httpx_client(mock_client):
    return lambda **kw: Mock(__enter__=lambda s: mock_client, __exit__=lambda s, *a: None)


class TestElevenLabsClient:
    """Dormant but still-correct — kept in case a hosted provider is wanted later."""

    def test_available_reflects_env(self, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        assert elevenlabs_client.elevenlabs_available() is False
        monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-test")
        assert elevenlabs_client.elevenlabs_available() is True

    def test_clone_voice_raises_without_key(self, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
            elevenlabs_client.clone_voice("Me", b"audio", "s.mp3")

    def test_clone_voice_success(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-test")
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"voice_id": "abc123"}
        mock_client = Mock()
        mock_client.post.return_value = mock_resp
        monkeypatch.setattr(elevenlabs_client.httpx, "Client", _mock_httpx_client(mock_client))

        result = elevenlabs_client.clone_voice("Me", b"audio-bytes", "s.mp3")

        assert result["voice_id"] == "abc123"

    def test_synthesize_speech_returns_bytes(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-test")
        mock_resp = Mock(status_code=200, content=b"fake-mp3-bytes")
        mock_client = Mock()
        mock_client.post.return_value = mock_resp
        monkeypatch.setattr(elevenlabs_client.httpx, "Client", _mock_httpx_client(mock_client))

        audio = elevenlabs_client.synthesize_speech("hello", "abc123")

        assert audio == b"fake-mp3-bytes"


class TestEnsureEngineProfileReprovisionCooldown:
    """external_voice_id missing (e.g. cloned while Chatterbox was offline)
    made _ensure_engine_profile re-clone the voice from stored sample on
    EVERY /speak call — a heavier op than plain synthesis, with a 60s
    timeout. If Chatterbox rejected/hung, that stalled every single sentence
    of a live conversation for many seconds before falling back to OpenAI.
    Now: a short timeout on the retry itself, plus a cooldown so a failure
    doesn't repeat the same slow attempt on the very next sentence."""

    def _row(self, tmp_path, voice_id="v1"):
        sample = tmp_path / "sample.wav"
        sample.write_bytes(b"fake-audio")
        return ClonedVoice(
            user_id=5,
            voice_id=voice_id,
            external_voice_id=None,
            name="Me",
            provider="chatterbox",
            sample_path=str(sample),
            reference_text="hello",
        )

    def test_failed_reprovision_uses_short_timeout_and_502(self, tmp_path, monkeypatch):
        from app.routers import voice_clone as vc

        vc._reprovision_blocked_until.clear()
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: True
        )
        clone_calls = []

        def boom(*a, timeout=None, **kw):
            clone_calls.append(timeout)
            raise RuntimeError("Chatterbox profile creation failed (500): engine error")

        monkeypatch.setattr("app.services.llm.chatterbox_client.clone_voice", boom)

        row = self._row(tmp_path)
        with pytest.raises(HTTPException) as exc:
            vc._ensure_engine_profile(row)

        assert exc.value.status_code == 502
        assert clone_calls == [chatterbox_client.REPROVISION_TIMEOUT]
        assert clone_calls[0] < 60.0  # short, not the 60s /clone default

    def test_repeat_call_within_cooldown_skips_network_entirely(self, tmp_path, monkeypatch):
        from app.routers import voice_clone as vc

        vc._reprovision_blocked_until.clear()
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: True
        )
        clone_calls = []

        def boom(*a, **kw):
            clone_calls.append(1)
            raise RuntimeError("engine error")

        monkeypatch.setattr("app.services.llm.chatterbox_client.clone_voice", boom)
        row = self._row(tmp_path)

        with pytest.raises(HTTPException):
            vc._ensure_engine_profile(row)
        assert len(clone_calls) == 1

        # Next sentence, moments later — must NOT repeat the slow attempt.
        with pytest.raises(HTTPException) as exc:
            vc._ensure_engine_profile(row)
        assert len(clone_calls) == 1
        assert exc.value.status_code == 503

    def test_cooldown_expires_and_allows_retry(self, tmp_path, monkeypatch):
        from app.routers import voice_clone as vc

        vc._reprovision_blocked_until.clear()
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: True
        )
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.clone_voice",
            lambda *a, **kw: {"voice_id": "engine-2"},
        )
        row = self._row(tmp_path, voice_id="v2")
        vc._reprovision_blocked_until["v2"] = 0.0  # already expired

        result = vc._ensure_engine_profile(row)

        assert result == "engine-2"
        assert "v2" not in vc._reprovision_blocked_until

    def test_successful_reprovision_returns_engine_id(self, tmp_path, monkeypatch):
        from app.routers import voice_clone as vc

        vc._reprovision_blocked_until.clear()
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: True
        )
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.clone_voice",
            lambda *a, **kw: {"voice_id": "engine-3"},
        )
        row = self._row(tmp_path, voice_id="v3")

        result = vc._ensure_engine_profile(row)

        assert result == "engine-3"


class TestSpeakRateLimit:
    """30/hour was sized for one /speak call per full reply. Sentence-level
    TTS streaming and Present Deck's chunking both call /speak several times
    per turn/slide, so the old ceiling started blocking normal single-user
    use well before an hour of active conversation."""

    def test_default_limit_raised_for_per_sentence_chunking(self):
        from app.routers import voice_clone as vc

        assert vc.SPEAK_RATE_LIMIT >= 300

    def test_rate_limit_still_blocks_once_actually_exceeded(self):
        from collections import defaultdict

        from app.routers.voice_clone import _rate_limit

        bucket: dict[int, list[float]] = defaultdict(list)
        for _ in range(3):
            _rate_limit(bucket, user_id=1, limit=3)
        with pytest.raises(HTTPException) as exc:
            _rate_limit(bucket, user_id=1, limit=3)
        assert exc.value.status_code == 429

    def test_rate_limit_is_per_user(self):
        from app.routers.voice_clone import _rate_limit
        from collections import defaultdict

        bucket: dict[int, list[float]] = defaultdict(list)
        for _ in range(3):
            _rate_limit(bucket, user_id=1, limit=3)
        # A different user must not be blocked by user 1's usage.
        _rate_limit(bucket, user_id=2, limit=3)


class TestChatterboxClient:
    def test_available_reflects_server_reachability(self, monkeypatch):
        mock_resp = Mock(status_code=200)
        mock_client = Mock()
        mock_client.get.return_value = mock_resp
        monkeypatch.setattr(chatterbox_client.httpx, "Client", _mock_httpx_client(mock_client))

        assert chatterbox_client.chatterbox_available() is True

    def test_available_false_when_server_unreachable(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(chatterbox_client.httpx, "Client", boom)

        assert chatterbox_client.chatterbox_available() is False

    def test_clone_voice_requires_reference_text(self):
        with pytest.raises(ValueError, match="reference_text"):
            chatterbox_client.clone_voice("Me", b"audio", "s.wav", reference_text="")

    def test_clone_voice_creates_profile_then_uploads_sample(self, monkeypatch):
        profile_resp = Mock(status_code=200)
        profile_resp.json.return_value = {"id": "profile-1"}
        sample_resp = Mock(status_code=200)
        mock_client = Mock()
        mock_client.post.side_effect = [profile_resp, sample_resp]
        monkeypatch.setattr(chatterbox_client.httpx, "Client", _mock_httpx_client(mock_client))

        result = chatterbox_client.clone_voice(
            "Me", b"audio-bytes", "s.wav", reference_text="hello world"
        )

        assert result == {"voice_id": "profile-1", "name": "Me"}
        assert mock_client.post.call_count == 2

    def test_synthesize_speech_fetches_audio_path(self, monkeypatch):
        gen_resp = Mock(status_code=200)
        gen_resp.json.return_value = {"status": "completed", "audio_path": "/data/out/gen-1.wav"}
        audio_resp = Mock(status_code=200, content=b"wav-bytes")
        mock_client = Mock()
        mock_client.post.return_value = gen_resp
        mock_client.get.return_value = audio_resp
        monkeypatch.setattr(chatterbox_client.httpx, "Client", _mock_httpx_client(mock_client))

        audio = chatterbox_client.synthesize_speech("hello there", "profile-1")

        assert audio == b"wav-bytes"
        mock_client.get.assert_called_once()

    def test_synthesize_speech_defaults_to_qwen_engine(self, monkeypatch):
        gen_resp = Mock(status_code=200)
        gen_resp.json.return_value = {"status": "completed", "audio_path": "/data/out/gen-1.wav"}
        audio_resp = Mock(status_code=200, content=b"wav-bytes")
        mock_client = Mock()
        mock_client.post.return_value = gen_resp
        mock_client.get.return_value = audio_resp
        monkeypatch.setattr(chatterbox_client.httpx, "Client", _mock_httpx_client(mock_client))

        chatterbox_client.synthesize_speech("hello there", "profile-1")

        assert mock_client.post.call_args.kwargs["json"]["engine"] == "qwen"

    def test_synthesize_speech_honors_engine_env_override(self, monkeypatch):
        """No streaming at this layer (POST /generate blocks until the whole
        clip is done) — the engine's own speed is the dominant latency
        factor, so let it be swapped without a code change. CHATTERBOX_ENGINE
        is read once at import (same pattern as CHATTERBOX_BASE_URL) — a real
        override takes effect on backend restart after editing .env, so the
        module constant is what's under test here, not a live env read."""
        monkeypatch.setattr(chatterbox_client, "DEFAULT_CHATTERBOX_ENGINE", "fast-engine")
        gen_resp = Mock(status_code=200)
        gen_resp.json.return_value = {"status": "completed", "audio_path": "/data/out/gen-1.wav"}
        audio_resp = Mock(status_code=200, content=b"wav-bytes")
        mock_client = Mock()
        mock_client.post.return_value = gen_resp
        mock_client.get.return_value = audio_resp
        monkeypatch.setattr(chatterbox_client.httpx, "Client", _mock_httpx_client(mock_client))

        chatterbox_client.synthesize_speech("hello there", "profile-1")

        assert mock_client.post.call_args.kwargs["json"]["engine"] == "fast-engine"

    def test_synthesize_speech_explicit_engine_wins_over_default(self, monkeypatch):
        gen_resp = Mock(status_code=200)
        gen_resp.json.return_value = {"status": "completed", "audio_path": "/data/out/gen-1.wav"}
        audio_resp = Mock(status_code=200, content=b"wav-bytes")
        mock_client = Mock()
        mock_client.post.return_value = gen_resp
        mock_client.get.return_value = audio_resp
        monkeypatch.setattr(chatterbox_client.httpx, "Client", _mock_httpx_client(mock_client))

        chatterbox_client.synthesize_speech("hello there", "profile-1", engine="explicit-engine")

        assert mock_client.post.call_args.kwargs["json"]["engine"] == "explicit-engine"

    def test_delete_voice_swallows_errors(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("network down")

        monkeypatch.setattr(chatterbox_client.httpx, "Client", boom)

        chatterbox_client.delete_voice("profile-1")  # must not raise


class TestVoiceCloneEndpoints:
    def test_clone_persists_sample_and_default(self, monkeypatch, tmp_path):
        from app.routers import voice_clone as vc

        monkeypatch.setattr(vc, "VOICES_DIR", tmp_path)
        db = _session()
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: True
        )
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.clone_voice",
            lambda name, audio_bytes, filename, content_type=None, *, reference_text, language="en": {
                "voice_id": "engine-1",
                "name": name,
            },
        )
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)

        upload = UploadFile(
            BytesIO(b"audio-data"),
            filename="me.wav",
            headers=Headers({"content-type": "audio/wav"}),
        )

        import asyncio

        result = asyncio.run(
            vc.clone_my_voice(
                name="My Voice",
                reference_text="hello this is my voice",
                sample=upload,
                current_user=USER,
                db=db,
            )
        )

        assert result.provider == "chatterbox"
        assert result.is_default is True
        assert result.has_sample is True
        row = db.query(ClonedVoice).filter(ClonedVoice.user_id == 5).first()
        assert row is not None
        assert row.external_voice_id == "engine-1"
        from pathlib import Path

        assert row.sample_path and Path(row.sample_path).is_file()

    def test_clone_persists_when_engine_offline(self, monkeypatch, tmp_path):
        from app.routers import voice_clone as vc

        monkeypatch.setattr(vc, "VOICES_DIR", tmp_path)
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: False
        )
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)
        db = _session()
        upload = UploadFile(
            BytesIO(b"audio-data"),
            filename="me.wav",
            headers=Headers({"content-type": "audio/wav"}),
        )

        import asyncio

        result = asyncio.run(
            vc.clone_my_voice(
                name="Offline Voice",
                reference_text="hello",
                sample=upload,
                current_user=USER,
                db=db,
            )
        )
        assert result.is_default is True
        assert db.query(ClonedVoice).filter(ClonedVoice.user_id == 5).count() == 1

    def test_clone_rejects_missing_reference_text(self, monkeypatch, tmp_path):
        from app.routers import voice_clone as vc

        monkeypatch.setattr(vc, "VOICES_DIR", tmp_path)
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: True
        )
        db = _session()
        upload = UploadFile(
            BytesIO(b"audio-data"),
            filename="me.wav",
            headers=Headers({"content-type": "audio/wav"}),
        )

        import asyncio

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                vc.clone_my_voice(
                    name="My Voice",
                    reference_text="   ",
                    sample=upload,
                    current_user=USER,
                    db=db,
                )
            )
        assert exc.value.status_code == 400

    def test_list_default_and_delete(self, monkeypatch, tmp_path):
        from app.routers import voice_clone as vc

        monkeypatch.setattr(vc, "VOICES_DIR", tmp_path)
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.delete_voice", lambda vid: None
        )
        db = _session()
        a = ClonedVoice(
            user_id=5,
            voice_id="za",
            external_voice_id="ea",
            name="A",
            provider="chatterbox",
            is_default=True,
        )
        b = ClonedVoice(
            user_id=5,
            voice_id="zb",
            external_voice_id="eb",
            name="B",
            provider="chatterbox",
            is_default=False,
        )
        db.add_all([a, b])
        db.commit()

        listed = vc.list_my_voices(current_user=USER, db=db)
        assert len(listed) == 2

        out = vc.set_default_voice("zb", current_user=USER, db=db)
        assert out.is_default is True
        assert out.voice_id == "zb"

        default = vc.get_my_voice(current_user=USER, db=db)
        assert default is not None
        assert default.voice_id == "zb"

        deleted = vc.delete_voice_by_id("zb", current_user=USER, db=db)
        assert deleted == {"deleted": True}
        remaining = db.query(ClonedVoice).filter(ClonedVoice.user_id == 5).all()
        assert len(remaining) == 1
        assert remaining[0].voice_id == "za"
        assert remaining[0].is_default is True

    def test_get_my_voice_returns_none_when_unset(self):
        from app.routers.voice_clone import get_my_voice

        db = _session()
        assert get_my_voice(current_user=USER, db=db) is None

    def test_reset_my_voice_deletes_all(self, monkeypatch):
        from app.routers.voice_clone import reset_my_voice

        db = _session()
        db.add(
            ClonedVoice(
                user_id=5,
                voice_id="v1",
                external_voice_id="e1",
                name="Me",
                provider="chatterbox",
                is_default=True,
            )
        )
        db.commit()
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.delete_voice", lambda vid: None
        )
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)

        result = reset_my_voice(current_user=USER, db=db)

        assert result == {"cleared": True}
        assert db.query(ClonedVoice).filter(ClonedVoice.user_id == 5).first() is None

    def test_speak_requires_configured_voice(self):
        from app.routers.voice_clone import SpeakRequest, speak

        db = _session()
        with pytest.raises(HTTPException) as exc:
            speak(SpeakRequest(text="hello"), current_user=USER, db=db)
        assert exc.value.status_code == 404

    def test_speak_uses_default_external_id(self, monkeypatch):
        from app.routers.voice_clone import SpeakRequest, speak

        db = _session()
        db.add(
            ClonedVoice(
                user_id=5,
                voice_id="zect-1",
                external_voice_id="engine-1",
                name="Me",
                provider="chatterbox",
                is_default=True,
            )
        )
        db.commit()
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.synthesize_speech",
            lambda text, voice_id: b"wav-bytes",
        )
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)

        result = speak(SpeakRequest(text="hello there"), current_user=USER, db=db)

        assert result.body == b"wav-bytes"
        assert result.media_type == "audio/mpeg"

    def test_speak_stock_voice_bypasses_chatterbox_entirely(self, monkeypatch):
        from app.routers.voice_clone import SpeakRequest, speak

        db = _session()
        # No ClonedVoice row at all for this user — a stock voice request
        # must not need one.
        captured = {}
        monkeypatch.setattr("app.services.llm.openai_tts.openai_tts_available", lambda: True)
        monkeypatch.setattr(
            "app.services.llm.openai_tts.synthesize_openai_speech",
            lambda text, voice=None, model=None: (captured.setdefault("voice", voice), b"mp3-bytes")[1],
        )
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)

        result = speak(SpeakRequest(text="hello", stock_voice="nova"), current_user=USER, db=db)

        assert result.body == b"mp3-bytes"
        assert result.headers["X-Mentrix-TTS-Engine"] == "openai_stock:nova"
        assert captured["voice"] == "nova"

    def test_speak_stock_voice_rejects_unknown_name(self):
        from app.routers.voice_clone import SpeakRequest, speak

        db = _session()
        with pytest.raises(HTTPException) as exc:
            speak(SpeakRequest(text="hello", stock_voice="robotic-alien-voice"), current_user=USER, db=db)
        assert exc.value.status_code == 400

    def test_speak_stock_voice_requires_openai_key(self, monkeypatch):
        from app.routers.voice_clone import SpeakRequest, speak

        db = _session()
        monkeypatch.setattr("app.services.llm.openai_tts.openai_tts_available", lambda: False)
        with pytest.raises(HTTPException) as exc:
            speak(SpeakRequest(text="hello", stock_voice="alloy"), current_user=USER, db=db)
        assert exc.value.status_code == 503

    def test_clone_rejects_bad_mime(self, monkeypatch, tmp_path):
        from app.routers import voice_clone as vc

        monkeypatch.setattr(vc, "VOICES_DIR", tmp_path)
        monkeypatch.setattr(
            "app.services.llm.chatterbox_client.chatterbox_available", lambda: True
        )

        sample = UploadFile(
            filename="x.exe",
            file=BytesIO(b"data"),
            headers=Headers({"content-type": "application/x-msdownload"}),
        )

        import asyncio

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                vc.clone_my_voice(
                    name="Me",
                    reference_text="hello world test transcript",
                    sample=sample,
                    current_user=USER,
                    db=_session(),
                )
            )
        assert exc.value.status_code == 400


class TestMintRealtimeSessionSurfacesClonedVoice:
    def test_cloned_voice_helper_returns_none_without_user(self):
        assert _cloned_voice_for_user(None, None) is None
        assert _cloned_voice_for_user(_session(), None) is None

    def test_cloned_voice_helper_prefers_default(self):
        db = _session()
        db.add(
            ClonedVoice(
                user_id=5,
                voice_id="z1",
                name="Old",
                provider="chatterbox",
                is_default=False,
            )
        )
        db.add(
            ClonedVoice(
                user_id=5,
                voice_id="z2",
                name="Default",
                provider="chatterbox",
                is_default=True,
            )
        )
        db.commit()

        result = _cloned_voice_for_user(db, 5)

        assert result == {"voice_id": "z2", "name": "Default"}

    def test_mint_includes_cloned_voice_when_present(self, monkeypatch):
        monkeypatch.setattr("app.services.mentrix.realtime.realtime_enabled", lambda: True)
        monkeypatch.setattr("app.services.mentrix.realtime._ensure_openai_env", lambda: "sk-test")

        db = _session()
        db.add(
            ClonedVoice(
                user_id=5,
                voice_id="v1",
                name="Me",
                provider="chatterbox",
                is_default=True,
            )
        )
        db.commit()

        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"value": "secret123", "session": {"model": "gpt-realtime"}}
        mock_client = Mock()
        mock_client.post.return_value = mock_resp

        import app.services.mentrix.realtime as realtime_mod

        monkeypatch.setattr(realtime_mod.httpx, "Client", _mock_httpx_client(mock_client))

        result = mint_realtime_session(db=db, user_id=5)

        assert result["ok"] is True
        assert result["cloned_voice"] == {"voice_id": "v1", "name": "Me"}
        # Mint body should request text-only when clone present
        body = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
        assert body["session"].get("output_modalities") == ["text"]

    def test_mint_cloned_voice_is_none_when_unset(self, monkeypatch):
        monkeypatch.setattr("app.services.mentrix.realtime.realtime_enabled", lambda: True)
        monkeypatch.setattr("app.services.mentrix.realtime._ensure_openai_env", lambda: "sk-test")

        db = _session()

        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"value": "secret123", "session": {"model": "gpt-realtime"}}
        mock_client = Mock()
        mock_client.post.return_value = mock_resp

        import app.services.mentrix.realtime as realtime_mod

        monkeypatch.setattr(realtime_mod.httpx, "Client", _mock_httpx_client(mock_client))

        result = mint_realtime_session(db=db, user_id=5)

        assert result["cloned_voice"] is None

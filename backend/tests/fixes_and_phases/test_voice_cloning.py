"""Voice cloning — Mentrix voice was 100% OpenAI Realtime stock voices with
zero cloning capability. Covers the ElevenLabs client (kept, dormant —
functional but no longer the router's active backend), the Voicebox client
(the active backend — local, no API key), the /api/mentrix/voice/*
endpoints, and mint_realtime_session() surfacing a user's cloned voice so
the frontend knows to switch Realtime to text-only output."""

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
from app.services.llm import elevenlabs_client, voicebox_client
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


class TestVoiceboxClient:
    def test_available_reflects_server_reachability(self, monkeypatch):
        mock_resp = Mock(status_code=200)
        mock_client = Mock()
        mock_client.get.return_value = mock_resp
        monkeypatch.setattr(voicebox_client.httpx, "Client", _mock_httpx_client(mock_client))

        assert voicebox_client.voicebox_available() is True

    def test_available_false_when_server_unreachable(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(voicebox_client.httpx, "Client", boom)

        assert voicebox_client.voicebox_available() is False

    def test_clone_voice_requires_reference_text(self):
        with pytest.raises(ValueError, match="reference_text"):
            voicebox_client.clone_voice("Me", b"audio", "s.wav", reference_text="")

    def test_clone_voice_creates_profile_then_uploads_sample(self, monkeypatch):
        profile_resp = Mock(status_code=200)
        profile_resp.json.return_value = {"id": "profile-1"}
        sample_resp = Mock(status_code=200)
        mock_client = Mock()
        mock_client.post.side_effect = [profile_resp, sample_resp]
        monkeypatch.setattr(voicebox_client.httpx, "Client", _mock_httpx_client(mock_client))

        result = voicebox_client.clone_voice("Me", b"audio-bytes", "s.wav", reference_text="hello world")

        assert result == {"voice_id": "profile-1", "name": "Me"}
        assert mock_client.post.call_count == 2
        sample_call = mock_client.post.call_args_list[1]
        assert sample_call.args[0] == "http://localhost:17493/profiles/profile-1/samples"
        assert sample_call.kwargs["data"] == {"reference_text": "hello world"}

    def test_clone_voice_raises_on_profile_error(self, monkeypatch):
        profile_resp = Mock(status_code=422, text="bad name")
        mock_client = Mock()
        mock_client.post.return_value = profile_resp
        monkeypatch.setattr(voicebox_client.httpx, "Client", _mock_httpx_client(mock_client))

        with pytest.raises(RuntimeError, match="422"):
            voicebox_client.clone_voice("Me", b"audio", "s.wav", reference_text="hi")

    def test_synthesize_speech_fetches_audio_path(self, monkeypatch):
        gen_resp = Mock(status_code=200)
        gen_resp.json.return_value = {"status": "completed", "audio_path": "/data/out/gen-1.wav"}
        audio_resp = Mock(status_code=200, content=b"wav-bytes")
        mock_client = Mock()
        mock_client.post.return_value = gen_resp
        mock_client.get.return_value = audio_resp
        monkeypatch.setattr(voicebox_client.httpx, "Client", _mock_httpx_client(mock_client))

        audio = voicebox_client.synthesize_speech("hello there", "profile-1")

        assert audio == b"wav-bytes"
        mock_client.get.assert_called_once_with("http://localhost:17493/audio/gen-1.wav")

    def test_synthesize_speech_raises_on_generation_error(self, monkeypatch):
        gen_resp = Mock(status_code=200)
        gen_resp.json.return_value = {"status": "error", "error": "engine crashed"}
        mock_client = Mock()
        mock_client.post.return_value = gen_resp
        monkeypatch.setattr(voicebox_client.httpx, "Client", _mock_httpx_client(mock_client))

        with pytest.raises(RuntimeError, match="engine crashed"):
            voicebox_client.synthesize_speech("hello", "profile-1")

    def test_delete_voice_swallows_errors(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("network down")

        monkeypatch.setattr(voicebox_client.httpx, "Client", boom)

        voicebox_client.delete_voice("profile-1")  # must not raise


class TestVoiceCloneEndpoints:
    def test_clone_persists_and_returns_voice(self, monkeypatch):
        from app.routers.voice_clone import clone_my_voice

        db = _session()
        monkeypatch.setattr("app.services.llm.voicebox_client.voicebox_available", lambda: True)
        monkeypatch.setattr(
            "app.services.llm.voicebox_client.clone_voice",
            lambda name, audio_bytes, filename, content_type=None, *, reference_text, language="en": {
                "voice_id": "v1", "name": name,
            },
        )

        upload = UploadFile(BytesIO(b"audio-data"), filename="me.wav", headers=Headers({"content-type": "audio/wav"}))

        import asyncio

        result = asyncio.run(
            clone_my_voice(name="My Voice", reference_text="hello this is my voice", sample=upload, current_user=USER, db=db)
        )

        assert result.voice_id == "v1"
        assert result.provider == "voicebox"
        row = db.query(ClonedVoice).filter(ClonedVoice.user_id == 5).first()
        assert row is not None
        assert row.voice_id == "v1"

    def test_clone_rejects_when_voicebox_not_reachable(self, monkeypatch):
        from app.routers.voice_clone import clone_my_voice

        db = _session()
        monkeypatch.setattr("app.services.llm.voicebox_client.voicebox_available", lambda: False)
        upload = UploadFile(BytesIO(b"audio-data"), filename="me.wav", headers=Headers({"content-type": "audio/wav"}))

        import asyncio

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                clone_my_voice(name="My Voice", reference_text="hello", sample=upload, current_user=USER, db=db)
            )
        assert exc.value.status_code == 503

    def test_clone_rejects_missing_reference_text(self, monkeypatch):
        from app.routers.voice_clone import clone_my_voice

        db = _session()
        monkeypatch.setattr("app.services.llm.voicebox_client.voicebox_available", lambda: True)
        upload = UploadFile(BytesIO(b"audio-data"), filename="me.wav", headers=Headers({"content-type": "audio/wav"}))

        import asyncio

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                clone_my_voice(name="My Voice", reference_text="   ", sample=upload, current_user=USER, db=db)
            )
        assert exc.value.status_code == 400

    def test_re_clone_deletes_old_voice(self, monkeypatch):
        from app.routers.voice_clone import clone_my_voice

        db = _session()
        db.add(ClonedVoice(user_id=5, voice_id="old-voice", name="Old", provider="voicebox"))
        db.commit()

        monkeypatch.setattr("app.services.llm.voicebox_client.voicebox_available", lambda: True)
        monkeypatch.setattr(
            "app.services.llm.voicebox_client.clone_voice",
            lambda name, audio_bytes, filename, content_type=None, *, reference_text, language="en": {
                "voice_id": "new-voice", "name": name,
            },
        )
        deleted = []
        monkeypatch.setattr("app.services.llm.voicebox_client.delete_voice", lambda vid: deleted.append(vid))

        upload = UploadFile(BytesIO(b"audio-data"), filename="me.wav", headers=Headers({"content-type": "audio/wav"}))

        import asyncio

        result = asyncio.run(
            clone_my_voice(name="New", reference_text="hello world", sample=upload, current_user=USER, db=db)
        )

        assert result.voice_id == "new-voice"
        assert deleted == ["old-voice"]
        assert db.query(ClonedVoice).filter(ClonedVoice.user_id == 5).count() == 1

    def test_get_my_voice_returns_none_when_unset(self):
        from app.routers.voice_clone import get_my_voice

        db = _session()
        assert get_my_voice(current_user=USER, db=db) is None

    def test_reset_my_voice_deletes_row(self, monkeypatch):
        from app.routers.voice_clone import reset_my_voice

        db = _session()
        db.add(ClonedVoice(user_id=5, voice_id="v1", name="Me", provider="voicebox"))
        db.commit()
        monkeypatch.setattr("app.services.llm.voicebox_client.delete_voice", lambda vid: None)

        result = reset_my_voice(current_user=USER, db=db)

        assert result == {"cleared": True}
        assert db.query(ClonedVoice).filter(ClonedVoice.user_id == 5).first() is None

    def test_speak_requires_configured_voice(self):
        from app.routers.voice_clone import SpeakRequest, speak

        db = _session()
        with pytest.raises(HTTPException) as exc:
            speak(SpeakRequest(text="hello"), current_user=USER, db=db)
        assert exc.value.status_code == 404

    def test_speak_returns_audio(self, monkeypatch):
        from app.routers.voice_clone import SpeakRequest, speak

        db = _session()
        db.add(ClonedVoice(user_id=5, voice_id="v1", name="Me", provider="voicebox"))
        db.commit()
        monkeypatch.setattr("app.services.llm.voicebox_client.synthesize_speech", lambda text, voice_id: b"wav-bytes")
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)

        result = speak(SpeakRequest(text="hello there"), current_user=USER, db=db)

        assert result.body == b"wav-bytes"
        assert result.media_type == "audio/mpeg"

    def test_clone_rejects_bad_mime(self, monkeypatch):
        from app.routers.voice_clone import clone_my_voice

        monkeypatch.setattr("app.services.llm.voicebox_client.voicebox_available", lambda: True)
        monkeypatch.setattr("app.routers.voice_clone.log_audit", lambda **kw: None)

        sample = UploadFile(
            filename="x.exe",
            file=BytesIO(b"data"),
            headers=Headers({"content-type": "application/x-msdownload"}),
        )

        import asyncio

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                clone_my_voice(
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

    def test_cloned_voice_helper_finds_row(self):
        db = _session()
        db.add(ClonedVoice(user_id=5, voice_id="v1", name="Me", provider="voicebox"))
        db.commit()

        result = _cloned_voice_for_user(db, 5)

        assert result == {"voice_id": "v1", "name": "Me"}

    def test_mint_includes_cloned_voice_when_present(self, monkeypatch):
        monkeypatch.setattr("app.services.mentrix.realtime.realtime_enabled", lambda: True)
        monkeypatch.setattr("app.services.mentrix.realtime._ensure_openai_env", lambda: "sk-test")

        db = _session()
        db.add(ClonedVoice(user_id=5, voice_id="v1", name="Me", provider="voicebox"))
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

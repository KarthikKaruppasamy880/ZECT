"""Unit tests for ZECT Voicebox native Mentrix API."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_VOICEBOX_BACKEND", "native")
    monkeypatch.setenv("ZECT_VOICEBOX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ZECT_VOICEBOX_MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("ZECT_VOICEBOX_SYNTH", "stub")
    monkeypatch.setenv("ZECT_VOICEBOX_ALLOW_STUB", "1")
    with TestClient(app) as c:
        yield c


def test_health_native_models_ready(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["brand"] == "zect-voicebox"
    assert data["product"] == "ZECT Voicebox"
    assert data["backend"] == "native"
    assert "models_ready" in data
    assert data["models_ready"] is True
    assert "upstream_online" not in data


def test_root_index(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["brand"] == "zect-voicebox"
    assert data["health"] == "/health"
    assert data["profiles"] == "/profiles"


def test_profiles_empty(client):
    res = client.get("/profiles")
    assert res.status_code == 200
    assert res.json() == []


def test_create_profile_and_list(client):
    res = client.post("/profiles", json={"name": "Karthik", "language": "en", "voice_type": "cloned"})
    assert res.status_code == 200
    pid = res.json()["id"]
    assert pid
    listed = client.get("/profiles")
    assert listed.status_code == 200
    assert any(p["id"] == pid for p in listed.json())


def test_generate_stub_returns_audio(client):
    created = client.post("/profiles", json={"name": "Me", "language": "en", "voice_type": "cloned"})
    pid = created.json()["id"]
    sample = client.post(
        f"/profiles/{pid}/samples",
        files={"file": ("sample.wav", b"RIFF....WAVEfmt ", "audio/wav")},
        data={"reference_text": "Hello this is my Mentrix voice."},
    )
    assert sample.status_code == 200
    assert sample.json()["has_sample"] is True

    gen = client.post(
        "/generate",
        json={"profile_id": pid, "text": "Hello from ZECT", "language": "en", "engine": "qwen"},
    )
    assert gen.status_code == 200
    data = gen.json()
    assert data["brand"] == "zect-voicebox"
    assert data["status"] == "ok"
    assert data["audio_path"].startswith("/audio/")
    assert data["engine"] == "stub"

    fname = data["audio_path"].rsplit("/", 1)[-1]
    audio = client.get(f"/audio/{fname}")
    assert audio.status_code == 200
    assert audio.content[:4] == b"RIFF"


def test_delete_profile(client):
    created = client.post("/profiles", json={"name": "Temp", "language": "en", "voice_type": "cloned"})
    pid = created.json()["id"]
    deleted = client.delete(f"/profiles/{pid}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert client.get("/profiles").json() == []

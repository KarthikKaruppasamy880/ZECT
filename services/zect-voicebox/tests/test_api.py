"""Unit tests for ZECT Voicebox upstream proxy (no live Voicebox required)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure package imports resolve when pytest cwd is services/zect-voicebox
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_VOICEBOX_BACKEND", "upstream")
    monkeypatch.setenv("ZECT_VOICEBOX_UPSTREAM_URL", "http://upstream.test:17494")
    monkeypatch.setenv("ZECT_VOICEBOX_DATA_DIR", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_health_reports_brand(client, monkeypatch):
    async def _online(_client=None):
        return True

    monkeypatch.setattr("app.main.upstream_online", _online)
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["brand"] == "zect-voicebox"
    assert data["product"] == "ZECT Voicebox"
    assert data["backend"] == "upstream"
    assert data["upstream_online"] is True


def test_root_index(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["brand"] == "zect-voicebox"
    assert data["health"] == "/health"
    assert data["profiles"] == "/profiles"


def test_profiles_empty_when_upstream_down(client, monkeypatch):
    from app.upstream import UpstreamError

    async def _fail(*_a, **_k):
        raise UpstreamError(503, "Cannot reach upstream")

    monkeypatch.setattr("app.main.proxy_request", _fail)
    res = client.get("/profiles")
    assert res.status_code == 200
    assert res.json() == []


def test_profiles_passthrough(client, monkeypatch):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.content = b'[{"id":"p1","name":"Karthik"}]'
    mock_res.headers = {"content-type": "application/json"}
    mock_res.text = mock_res.content.decode()

    async def _ok(*_a, **_k):
        return mock_res

    monkeypatch.setattr("app.main.proxy_request", _ok)
    monkeypatch.setattr("app.main.raise_if_bad", lambda _r: None)
    res = client.get("/profiles")
    assert res.status_code == 200
    assert res.json()[0]["id"] == "p1"


def test_generate_mirrors_audio(client, monkeypatch, tmp_path):
    gen_res = MagicMock()
    gen_res.status_code = 200
    gen_res.content = b'{"audio_path":"/audio/up.wav","status":"ok"}'
    gen_res.headers = {"content-type": "application/json"}
    gen_res.text = gen_res.content.decode()
    gen_res.json.return_value = {"audio_path": "/audio/up.wav", "status": "ok"}

    async def _proxy(method, path, **_k):
        assert method == "POST"
        assert path == "/generate"
        return gen_res

    monkeypatch.setattr("app.main.proxy_request", _proxy)
    monkeypatch.setattr("app.main.raise_if_bad", lambda _r: None)

    audio_bytes = b"RIFF....WAVEfmt "

    class FakeAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            r = MagicMock()
            r.status_code = 200
            r.content = audio_bytes
            return r

    monkeypatch.setattr("app.main.httpx.AsyncClient", FakeAsyncClient)

    res = client.post(
        "/generate",
        json={"profile_id": "p1", "text": "Hello from ZECT", "language": "en"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["brand"] == "zect-voicebox"
    assert data["audio_path"].startswith("/audio/")
    fname = data["audio_path"].rsplit("/", 1)[-1]
    mirrored = client.get(f"/audio/{fname}")
    assert mirrored.status_code == 200
    assert mirrored.content == audio_bytes


def test_create_profile_proxies(client, monkeypatch):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.content = b'{"id":"abc","name":"Me"}'
    mock_res.headers = {"content-type": "application/json"}
    mock_res.text = mock_res.content.decode()

    called = {}

    async def _ok(method, path, **kwargs):
        called["method"] = method
        called["path"] = path
        called["json"] = kwargs.get("json")
        return mock_res

    monkeypatch.setattr("app.main.proxy_request", _ok)
    monkeypatch.setattr("app.main.raise_if_bad", lambda _r: None)
    res = client.post("/profiles", json={"name": "Me", "language": "en", "voice_type": "cloned"})
    assert res.status_code == 200
    assert called["method"] == "POST"
    assert called["path"] == "/profiles"
    assert called["json"]["name"] == "Me"


def test_live_health_smoke_when_engine_running():
    """Optional live smoke against 127.0.0.1:17493 (Rancher/uvicorn). Skips if down."""
    import httpx

    try:
        root = httpx.get("http://127.0.0.1:17493/", timeout=2.0)
        health = httpx.get("http://127.0.0.1:17493/health", timeout=2.0)
        profiles = httpx.get("http://127.0.0.1:17493/profiles", timeout=2.0)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ZECT Voicebox not reachable on :17493 ({exc})")

    assert root.status_code == 200
    assert root.json()["brand"] == "zect-voicebox"
    assert root.json()["health"] == "/health"
    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert profiles.status_code < 500

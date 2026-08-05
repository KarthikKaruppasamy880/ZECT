"""Phase 2 Stage B — remote adapter + event translation (mocked HTTP)."""

from __future__ import annotations

from typing import Any

import pytest

from app.adapters.coding_engine_events import translate_remote_event, translate_remote_events
from app.adapters.coding_engine_remote import (
    CodingEngineRequestError,
    RemoteCodingEngine,
)


class _FakeResp:
    def __init__(self, status_code: int = 200, payload: Any = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or ("" if payload is None else str(payload))
        self.content = b"{}" if payload is not None else b""

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeClient:
    """Minimal httpx.Client stand-in; routes by method+url suffix."""

    def __init__(self, routes: dict[tuple[str, str], _FakeResp], *args, **kwargs):
        self.routes = routes
        self.calls: list[tuple[str, str, dict | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, method, url, headers=None, json=None, params=None):
        self.calls.append((method.upper(), str(url), json))
        for (m, u), resp in self.routes.items():
            if m == method.upper() and (str(url).rstrip("/").endswith(u.rstrip("/")) or u in str(url)):
                return resp
        return _FakeResp(404, {"error": "missing"}, text="missing")

    def get(self, url, headers=None):
        return self.request("GET", url, headers=headers)


def test_translate_remote_events_stable_shape():
    raw = [
        {"type": "agent_message", "content": "Planning change"},
        {"type": "file_edit", "path": "app.py", "message": "edited app.py"},
        {"type": "error", "message": "boom"},
        {"event": {"type": "finish", "content": "done"}},
    ]
    events = translate_remote_events(raw)
    assert [e.sequence_id for e in events] == [1, 2, 3, 4]
    assert events[0].event == "message"
    assert events[1].event == "file_change"
    assert events[1].data.get("path") == "app.py"
    assert events[2].event == "error"
    assert events[3].event == "completed"
    for e in events:
        assert set(e.__dataclass_fields__.keys()) >= {
            "sequence_id",
            "event",
            "message",
            "phase",
            "data",
        }


def test_translate_filters_after_cursor():
    raw = [
        {"sequence_id": 1, "type": "message", "content": "a"},
        {"sequence_id": 2, "type": "message", "content": "b"},
    ]
    events = translate_remote_events(raw, after=1)
    assert len(events) == 1
    assert events[0].sequence_id == 2
    assert events[0].message == "b"


def test_remote_start_stream_cancel():
    routes = {
        ("POST", "api/conversations"): _FakeResp(200, {"id": "conv-1", "status": "running"}),
        ("POST", "api/conversations/conv-1/events"): _FakeResp(200, {"ok": True}),
        ("GET", "api/conversations/conv-1/events"): _FakeResp(
            200,
            {
                "events": [
                    {"sequence_id": 2, "type": "file_write", "path": "main.py", "content": "wrote"},
                    {"sequence_id": 3, "type": "finish", "content": "ok"},
                ]
            },
        ),
        ("GET", "api/conversations/conv-1"): _FakeResp(
            200, {"id": "conv-1", "status": "FINISHED", "events": []}
        ),
        ("DELETE", "api/conversations/conv-1"): _FakeResp(200, {"ok": True}),
    }
    clients: list[_FakeClient] = []

    def factory(*args, **kwargs):
        c = _FakeClient(routes, *args, **kwargs)
        clients.append(c)
        return c

    engine = RemoteCodingEngine(
        "http://engine.test",
        "secret-key",
        client_factory=factory,
        timeout=5,
        max_retries=0,
    )
    run_id = engine.start_run("Add hello", workspace="/tmp/ws")
    assert run_id == "conv-1"
    assert any(c.calls for c in clients)

    evs = engine.stream_events(run_id, after=1)
    assert any(e.event == "file_change" for e in evs)
    assert any(e.event == "completed" for e in evs)
    arts = engine.get_artifacts(run_id)
    assert any(a.path == "main.py" for a in arts)

    data = engine.get_run(run_id)
    assert data["provider"] == "remote"
    assert data["status"] == "completed"
    assert "secret" not in str(data).lower()

    engine.cancel_run(run_id)
    assert engine.get_run(run_id)["status"] == "cancelled"


def test_remote_retries_on_500():
    attempts = {"n": 0}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, method, url, headers=None, json=None, params=None):
            attempts["n"] += 1
            if attempts["n"] < 3:
                return _FakeResp(500, {"error": "busy"}, text="busy")
            return _FakeResp(200, {"id": "c2"})

        def get(self, url, headers=None):
            return self.request("GET", url, headers=headers)

    engine = RemoteCodingEngine(
        "http://engine.test",
        "k",
        client_factory=_Client,
        max_retries=3,
        timeout=5,
    )
    import app.adapters.coding_engine_remote as mod

    orig = mod.time.sleep
    mod.time.sleep = lambda *_a, **_k: None
    try:
        run_id = engine.start_run("goal")
        assert run_id == "c2"
        assert attempts["n"] >= 3
    finally:
        mod.time.sleep = orig


def test_remote_request_error_surface():
    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, method, url, headers=None, json=None, params=None):
            return _FakeResp(400, {"error": "bad"}, text="bad")

        def get(self, url, headers=None):
            return self.request("GET", url, headers=headers)

    engine = RemoteCodingEngine("http://engine.test", "k", client_factory=_Client, max_retries=0)
    with pytest.raises(CodingEngineRequestError):
        engine.start_run("x")


def test_translate_single_agent_state():
    ev = translate_remote_event(
        {"type": "agent_state_changed", "agent_state": "AWAITING_USER_CONFIRMATION"},
        sequence_id=9,
    )
    assert ev.sequence_id == 9
    assert ev.event == "awaiting_approval"
    assert ev.phase == "awaiting_approval"


def test_mock_engine_run_api(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mock")
    from app.adapters.coding_runtime import reset_coding_runtime_for_tests

    reset_coding_runtime_for_tests()
    started = client.post(
        "/api/coding-engine/runs",
        headers=auth_headers,
        json={"goal": "mock stage b", "workspace": ""},
    )
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["status"] == "completed"
    assert isinstance(body.get("events"), list)
    assert all("sequence_id" in e for e in body["events"])
    run_id = body["id"]
    got = client.get(f"/api/coding-engine/runs/{run_id}", headers=auth_headers)
    assert got.status_code == 200
    ev = client.get(f"/api/coding-engine/runs/{run_id}/events?after=0", headers=auth_headers)
    assert ev.status_code == 200
    assert "openhands" not in ev.text.lower()

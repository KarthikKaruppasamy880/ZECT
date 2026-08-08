"""Voicebox profile existence + 404 re-provision helpers."""

from __future__ import annotations

from app.adapters.llm.chatterbox_client import ProfileNotFoundError, profile_exists


def test_profile_exists_false_for_missing(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return [{"id": "abc", "name": "x"}]

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return FakeResp()

    monkeypatch.setattr("app.adapters.llm.chatterbox_client.httpx.Client", FakeClient)
    assert profile_exists("abc") is True
    assert profile_exists("missing") is False
    assert profile_exists("") is False


def test_profile_not_found_is_runtime_error():
    err = ProfileNotFoundError("404")
    assert isinstance(err, RuntimeError)

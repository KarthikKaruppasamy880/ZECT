"""Fail-fast ZECT Voicebox health cache."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_health_cache():
    from app.adapters.llm import chatterbox_client as cc

    cc.invalidate_health_cache()
    yield
    cc.invalidate_health_cache()


def test_health_cache_positive_ttl_skips_probe():
    from app.adapters.llm import chatterbox_client as cc

    with patch.object(cc, "_probe_profiles", return_value=True) as probe:
        assert cc.chatterbox_available() is True
        assert cc.chatterbox_available() is True
        assert probe.call_count == 1


def test_health_cache_negative_ttl_skips_probe():
    from app.adapters.llm import chatterbox_client as cc

    with patch.object(cc, "_probe_profiles", return_value=False) as probe:
        assert cc.chatterbox_available() is False
        assert cc.chatterbox_available() is False
        assert probe.call_count == 1


def test_force_refresh_bypasses_cache():
    from app.adapters.llm import chatterbox_client as cc

    with patch.object(cc, "_probe_profiles", side_effect=[False, True]) as probe:
        assert cc.chatterbox_available() is False
        assert cc.chatterbox_available(force_refresh=True) is True
        assert probe.call_count == 2


def test_mint_includes_voicebox_online(monkeypatch):
    from app.services.mentrix import realtime as rt

    monkeypatch.setattr(rt, "realtime_enabled", lambda: True)
    monkeypatch.setattr(rt, "_ensure_openai_env", lambda: "sk-test")
    monkeypatch.setattr(rt, "_cloned_voice_for_user", lambda db, uid: {"voice_id": "v1", "name": "Karthik"})

    class FakeResp:
        status_code = 200

        def json(self):
            return {"value": "ek_test", "session": {"model": "gpt-realtime"}, "expires_at": None}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(rt.httpx, "Client", FakeClient)

    with patch("app.adapters.llm.chatterbox_client.chatterbox_available", return_value=False):
        out = rt.mint_realtime_session(db=MagicMock(), user_id=1)
    assert out.get("ok") is True
    assert out.get("voicebox_online") is False
    assert out.get("cloned_voice", {}).get("name") == "Karthik"

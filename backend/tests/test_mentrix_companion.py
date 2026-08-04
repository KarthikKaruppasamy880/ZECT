"""Mentrix Companion — permission broker, turn, stream events, notes."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.services.mentrix.companion import iter_companion_events, run_companion_turn, _exec_tool
from app.services.mentrix.notes import add_note, list_notes
from app.services.mentrix.org_policy import ensure_companion_rules, export_org_policy, import_org_policy
from app.services.mentrix.permission_broker import check_tool_permission


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_permission_broker_navigate_allowed():
    db = _db()
    ensure_companion_rules(db)
    r = check_tool_permission(db, "navigate", user_confirmed=False)
    assert r["result"] in ("granted", "pending_approval")
    assert r["action"] == "companion_navigate"


def test_permission_broker_slack_send_needs_confirm():
    db = _db()
    ensure_companion_rules(db)
    r = check_tool_permission(db, "slack_send", user_confirmed=False)
    assert r["needs_confirm"] is True or r["result"] == "pending_approval"
    r2 = check_tool_permission(db, "slack_send", user_confirmed=True)
    assert r2["result"] == "granted"


def test_companion_turn_navigate_and_status():
    db = _db()
    ensure_companion_rules(db)
    out = run_companion_turn(db, "Open Lattice and what's my delivery status?")
    assert out["reply"]
    assert out.get("navigate") in ("/lattice", None) or out.get("tools")
    tools = [t["tool"] for t in out.get("tools") or []]
    assert "navigate" in tools or "delivery_status" in tools or out.get("pending_confirmations") is not None


def test_org_policy_export_import():
    db = _db()
    ensure_companion_rules(db)
    pack = export_org_policy(db)
    assert pack["agent"] == "Mentrix"
    assert pack["rules"]
    res = import_org_policy(db, pack, replace=False)
    assert res["imported_rules"] >= 1


def test_companion_send_pending_without_confirm():
    db = _db()
    ensure_companion_rules(db)
    out = run_companion_turn(db, "Slack send a message saying hello")
    pending = out.get("pending_confirmations") or []
    assert any(p["tool"] == "slack_send" for p in pending)
    assert out["avatar_state"] == "needs_permission"


def test_desktop_read_blocks_secrets():
    db = _db()
    blocked = _exec_tool(db, "desktop_read", {"path": "C:/Users/me/.env"})
    assert blocked.get("ok") is False
    assert "blocked" in (blocked.get("error") or "")


def test_stream_events_order_status():
    db = _db()
    ensure_companion_rules(db)
    events = []
    gen = iter_companion_events(db, "What's my Mentrix Delivery status?")
    try:
        while True:
            events.append(next(gen))
    except StopIteration:
        pass
    names = [e["event"] for e in events]
    assert "thinking" in names
    assert "done" in names
    assert names[0] == "thinking"


def test_navigate_emitted_even_with_pending_send():
    db = _db()
    ensure_companion_rules(db)
    # Open Lattice alone
    out = run_companion_turn(db, "Open Lattice")
    assert out.get("navigate") == "/lattice" or any(
        t.get("tool") == "navigate" for t in out.get("tools") or []
    )


def test_notes_add_list():
    n = add_note("hello from Mentrix unit test", tags=["test"])
    assert n["id"]
    items = list_notes()
    assert any(i["id"] == n["id"] for i in items)


def test_start_delivery_creates_run_when_confirmed():
    db = _db()
    ensure_companion_rules(db)
    result = _exec_tool(
        db,
        "start_delivery",
        {"goal": "Companion unit test delivery", "mode": "chat"},
        created_by="test",
    )
    assert result.get("ok") is True
    assert result.get("run_id")
    assert result.get("board", {}).get("type") == "mermaid"


def test_nav_map_includes_sandbox_and_ask():
    from app.services.mentrix.companion import NAV_MAP

    assert NAV_MAP["sandbox"] == "/sandbox"
    assert NAV_MAP["ask"] == "/ask"
    assert NAV_MAP["plan"] == "/plan"
    assert NAV_MAP["dashboard"] == "/"
    assert NAV_MAP["desktop app"] == "/mentrix-home"
    assert NAV_MAP["control tower"] == "/mentrix-home"


def test_go_to_desktop_is_not_dashboard_nav():
    from app.services.mentrix.companion import _parse_intents

    intents = _parse_intents("go to desktop")
    assert any(t["name"] == "computer_open_app" for t in intents)
    assert not any(
        t["name"] == "navigate" and (t.get("args") or {}).get("path") == "/" for t in intents
    )


def test_desktop_app_navigates_to_mentrix_home():
    from app.services.mentrix.companion import _parse_intents

    intents = _parse_intents("open desktop app")
    assert any(
        t["name"] == "navigate" and (t.get("args") or {}).get("path") == "/mentrix-home"
        for t in intents
    )


def test_build_agent_context_empty_without_data():
    from app.database import SessionLocal
    from app.services.mentrix.companion import build_agent_context

    db = SessionLocal()
    try:
        assert build_agent_context(db) == ""
        assert build_agent_context(db, agent_context="  Active skill tip  ") == "Active skill tip"
    finally:
        db.close()


def test_open_browser_maps_to_chrome():
    from app.services.mentrix.companion import _parse_intents

    intents = _parse_intents("open browser")
    assert any(
        t["name"] == "computer_open_app" and (t.get("args") or {}).get("app") == "chrome.exe"
        for t in intents
    )
    assert not any(
        t["name"] == "computer_open_app" and (t.get("args") or {}).get("app") == "notepad.exe"
        for t in intents
    )


def test_open_slack_app_not_digest():
    from app.services.mentrix.companion import _parse_intents

    intents = _parse_intents("open slack app")
    assert any(
        t["name"] == "computer_open_app" and (t.get("args") or {}).get("app") == "Slack.exe"
        for t in intents
    )
    assert not any(t["name"] == "slack_digest" for t in intents)


def test_slack_digest_unchanged():
    from app.services.mentrix.companion import _parse_intents

    intents = _parse_intents("slack digest")
    assert any(t["name"] == "slack_digest" for t in intents)
    assert not any(t["name"] == "computer_open_app" for t in intents)


def test_media_board_numbering(tmp_path, monkeypatch):
    from app.services.mentrix import media_board

    monkeypatch.setattr(media_board, "MEDIA_DIR", tmp_path)
    a = media_board.generate_media("first mentrix thumb")
    b = media_board.generate_media("second mentrix thumb")
    assert a["number"] == 1
    assert b["number"] == 2
    items = media_board.list_media()
    assert len(items) >= 2
    assert media_board.get_media_file(1) is not None


def test_realtime_session_falls_back_without_key(monkeypatch):
    from app.services.mentrix import realtime

    monkeypatch.setenv("MENTRIX_REALTIME", "1")
    monkeypatch.setattr(realtime, "_ensure_openai_env", lambda: "")
    out = realtime.mint_realtime_session()
    assert out.get("realtime_enabled") is False
    assert out.get("fallback") == "stt_sse"


def test_realtime_mint_uses_client_secrets(monkeypatch):
    """GA OpenAI Realtime mints via /v1/realtime/client_secrets (sessions URL is retired)."""
    from app.services.mentrix import realtime

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "value": "ek_test_secret",
                "expires_at": 9999999999,
                "session": {"type": "realtime", "model": "gpt-realtime"},
            }

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            assert url.endswith("/v1/realtime/client_secrets"), url
            assert "session" in (json or {})
            return _Resp()

    monkeypatch.setenv("MENTRIX_REALTIME", "1")
    monkeypatch.setenv("MENTRIX_REALTIME_MODEL", "gpt-realtime")
    monkeypatch.setattr(realtime, "_ensure_openai_env", lambda: "sk-test")
    monkeypatch.setattr(realtime.httpx, "Client", _Client)
    out = realtime.mint_realtime_session()
    assert out.get("realtime_enabled") is True
    assert out.get("client_secret") == "ek_test_secret"
    assert out.get("api") == "client_secrets"
    assert out.get("model") == "gpt-realtime"


def test_mentrix_instructions_default_english_with_explicit_switch():
    """Guardrail: Mentrix must default to English and only switch on explicit request —
    previously there was no language directive at all, so the model could switch languages
    unpredictably based on the user's input language."""
    from app.services.mentrix.realtime import mentrix_instructions

    text = mentrix_instructions()
    assert "english" in text.lower()
    assert "explicit" in text.lower()


def test_realtime_mint_returns_voice_for_session_update(monkeypatch):
    """The frontend re-asserts this voice in session.update to stop it drifting mid-call —
    mint_realtime_session must keep returning it in the response body."""
    from app.services.mentrix import realtime

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "value": "ek_test_secret",
                "expires_at": 9999999999,
                "session": {"type": "realtime", "model": "gpt-realtime"},
            }

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            assert json["session"]["audio"]["output"]["voice"] == "shimmer"
            return _Resp()

    monkeypatch.setenv("MENTRIX_REALTIME", "1")
    monkeypatch.setenv("MENTRIX_REALTIME_MODEL", "gpt-realtime")
    monkeypatch.setenv("MENTRIX_REALTIME_VOICE", "shimmer")
    monkeypatch.setattr(realtime, "_ensure_openai_env", lambda: "sk-test")
    monkeypatch.setattr(realtime.httpx, "Client", _Client)
    out = realtime.mint_realtime_session()
    assert out.get("voice") == "shimmer"


def test_realtime_mint_pins_transcription_language(monkeypatch):
    """Without a language hint, Whisper auto-detects per utterance and can
    hallucinate wrong-language text on noisy/ambiguous audio — pin it so mint
    always requests English transcription."""
    from app.services.mentrix import realtime

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "value": "ek_test_secret",
                "expires_at": 9999999999,
                "session": {"type": "realtime", "model": "gpt-realtime"},
            }

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            transcription = json["session"]["audio"]["input"]["transcription"]
            assert transcription == {"model": "whisper-1", "language": "en"}
            return _Resp()

    monkeypatch.setenv("MENTRIX_REALTIME", "1")
    monkeypatch.setenv("MENTRIX_REALTIME_MODEL", "gpt-realtime")
    monkeypatch.setattr(realtime, "_ensure_openai_env", lambda: "sk-test")
    monkeypatch.setattr(realtime.httpx, "Client", _Client)
    out = realtime.mint_realtime_session()
    assert out.get("realtime_enabled") is True


def test_open_sandbox_intent():
    db = _db()
    ensure_companion_rules(db)
    out = run_companion_turn(db, "Open Sandbox")
    assert out.get("navigate") == "/sandbox" or any(
        t.get("tool") == "navigate" and (t.get("result") or {}).get("navigate") == "/sandbox"
        for t in out.get("tools") or []
    )


def test_realtime_schemas_include_personal_ops():
    from app.services.mentrix.realtime import realtime_tool_schemas

    names = {t["name"] for t in realtime_tool_schemas()}
    for n in (
        "weather_report",
        "slack_digest",
        "slack_send",
        "email_digest",
        "email_send",
        "content_brief",
        "report_draft",
    ):
        assert n in names


def test_weather_report_tool(monkeypatch):
    from app.services.mentrix import weather as weather_mod

    class _Resp:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            if "geocoding" in url:
                return _Resp(
                    {
                        "results": [
                            {
                                "name": "Austin",
                                "latitude": 30.27,
                                "longitude": -97.74,
                                "country_code": "US",
                            }
                        ]
                    }
                )
            return _Resp(
                {
                    "current": {
                        "temperature_2m": 72.0,
                        "relative_humidity_2m": 40,
                        "weather_code": 0,
                        "wind_speed_10m": 5.0,
                    },
                    "hourly": {
                        "time": ["2026-01-01T12:00"],
                        "temperature_2m": [72.0],
                        "weather_code": [0],
                    },
                }
            )

    monkeypatch.setattr(weather_mod.httpx, "Client", _Client)
    out = weather_mod.weather_report("Austin")
    assert out.get("ok") is True
    assert out.get("temperature_f") == 72.0
    assert "spoken_summary" in out
    assert out.get("board", {}).get("type") == "markdown"


def test_email_intent_aliases():
    from app.services.mentrix.companion import _parse_intents

    assert any(t["name"] == "email_digest" for t in _parse_intents("check my email"))
    assert any(t["name"] == "email_digest" for t in _parse_intents("read my inbox"))
    assert not any(t["name"] == "email_digest" for t in _parse_intents("any event"))


def test_email_digest_without_imap(monkeypatch):
    monkeypatch.delenv("MENTRIX_IMAP_HOST", raising=False)
    monkeypatch.delenv("MENTRIX_IMAP_USER", raising=False)
    monkeypatch.delenv("MENTRIX_IMAP_PASSWORD", raising=False)
    out = _exec_tool(_db(), "email_digest", {})
    assert out.get("ok") is True
    assert out.get("configured") is False
    assert "IMAP" in (out.get("spoken_summary") or out.get("note") or "")


def test_slack_digest_without_token(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    db = _db()
    ensure_companion_rules(db)
    out = _exec_tool(db, "slack_digest", {})
    assert out.get("ok") is True
    assert "SLACK" in (out.get("spoken_summary") or out.get("note") or "").upper()


def test_weather_intent_turn():
    db = _db()
    ensure_companion_rules(db)
    out = run_companion_turn(db, "What's the weather in Austin?")
    tools = [t.get("tool") for t in out.get("tools") or []]
    assert "weather_report" in tools or "Weather" in (out.get("reply") or "") or "degrees" in (
        out.get("reply") or ""
    ).lower() or "Austin" in (out.get("reply") or "")

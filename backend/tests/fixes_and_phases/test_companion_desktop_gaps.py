"""Companion desktop / capability heuristic smoke tests."""

from app.services.mentrix import companion as c


def test_open_notepad_plus_plus_intent():
    tools = c._parse_intents("open notepad++")
    names = [t["name"] for t in tools]
    assert "computer_open_app" in names
    open_app = next(t for t in tools if t["name"] == "computer_open_app")
    assert "notepad++" in str(open_app["args"].get("app", "")).lower()


def test_write_in_notepad_routes_to_desktop_write_note():
    tools = c._parse_intents(
        "Write the Mentrix connector architecture details in notepad++: "
        "Email IMAP, Slack bot, Notes local, Calendar ICS, Desktop allowlist."
    )
    names = [t["name"] for t in tools]
    assert "desktop_write_note" in names
    assert "computer_type" not in names


def test_zoom_schedule_refused():
    tools = c._parse_intents("Please schedule a Zoom meeting for tomorrow at 3pm")
    assert any(t["name"] == "capability_refuse" and t["args"].get("topic") == "zoom_schedule" for t in tools)


def test_coding_engine_status_intent():
    tools = c._parse_intents("Is the coding engine ready?")
    assert any(t["name"] == "coding_engine_status" for t in tools)


def test_computer_type_rejects_long_text():
    long = "x" * 600
    out = c._exec_tool(db=None, name="computer_type", args={"text": long})  # type: ignore[arg-type]
    assert out.get("ok") is False
    assert out.get("error") == "text_too_long_for_type"


def test_capability_refuse_zoom_exec():
    out = c._exec_tool(db=None, name="capability_refuse", args={"topic": "zoom_schedule"})  # type: ignore[arg-type]
    assert out.get("ok") is True
    assert out.get("refused") is True
    assert "schedule" in (out.get("spoken_summary") or "").lower()


def test_coding_engine_status_exec():
    out = c._exec_tool(db=None, name="coding_engine_status", args={})  # type: ignore[arg-type]
    assert out.get("ok") is True
    assert out.get("board", {}).get("type") == "markdown"

"""Action/Observation structured fields on RuntimeEvent (V2 closure §22).

Previously RuntimeEvent only carried sequence_id/event/message/phase/data --
no mission_id/agent_id/repo_id/tool/policy/timestamp on the action side, and
no status/duration_ms/evidence_refs on the observation side, even though the
information existed (buried in free-text messages or the run dict). These
tests prove the fields are now populated end-to-end from a real native-agent
tool call, not just present on the dataclass."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime
from app.adapters.coding_runtime import RuntimeEvent


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.function = SimpleNamespace(name=name, arguments=arguments)


class _FakeMessage:
    def __init__(self, content: str | None = None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeResp:
    def __init__(self, message: _FakeMessage) -> None:
        self.choices = [SimpleNamespace(message=message)]


class _FakeClient:
    def __init__(self, responses: list[_FakeResp]) -> None:
        self._responses = list(responses)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        return self._responses.pop(0)


def test_runtime_event_has_action_observation_fields_with_safe_defaults():
    ev = RuntimeEvent(sequence_id=1, event="started", message="hi", phase="running")
    assert ev.mission_id == ""
    assert ev.agent_id == ""
    assert ev.repo_id == ""
    assert ev.tool == ""
    assert ev.policy == ""
    assert ev.timestamp == ""
    assert ev.status == ""
    assert ev.duration_ms is None
    assert ev.evidence_refs == []


def test_real_tool_call_populates_action_observation_fields(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "README.md").write_text("hi\n", encoding="utf-8")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))

    import app.adapters.llm.openai_compat as mod

    monkeypatch.setattr(mod, "openai_compat_available", lambda: True)
    responses = [
        _FakeResp(
            _FakeMessage(
                tool_calls=[_FakeToolCall("call1", "write_file", '{"path":"a.py","content":"x=1\\n"}')]
            )
        ),
        _FakeResp(_FakeMessage(content="Done.")),
    ]
    fake_client = _FakeClient(responses)
    monkeypatch.setattr(mod, "get_openai_compat_client", lambda **_k: fake_client)

    rt = MentrixNativeCodingRuntime()
    run_id = rt.start_run(
        "Write a file",
        workspace=str(ws),
        role="coder",
        mission_id="mission-abc",
        repo_id="7",
        max_steps=4,
        # CP-08: bypass model_router.route_model() auto-routing (which
        # correctly blocks with no cloud/local LLM configured) -- this
        # test drives its own fake client instead.
        model="gpt-4o-mini",
    )
    summary = rt.wait_until_done(run_id, timeout_s=10)

    tool_end = next(e for e in summary["events"] if e["event"] == "tool_end")
    assert tool_end["mission_id"] == "mission-abc"
    assert tool_end["agent_id"] == "coder"
    assert tool_end["repo_id"] == "7"
    assert tool_end["tool"] == "write_file"
    assert tool_end["policy"] == "allowed"
    assert tool_end["status"] == "ok"
    assert isinstance(tool_end["duration_ms"], int) and tool_end["duration_ms"] >= 0
    assert tool_end["evidence_refs"] == ["a.py"]
    assert tool_end["timestamp"], "timestamp must be a real ISO string, not empty"


def test_denied_tool_call_is_recorded_with_policy_denied(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))

    import app.adapters.llm.openai_compat as mod

    monkeypatch.setattr(mod, "openai_compat_available", lambda: True)
    responses = [
        _FakeResp(
            _FakeMessage(tool_calls=[_FakeToolCall("call1", "write_file", '{"path":"a.py","content":"x=1"}')])
        ),
        _FakeResp(_FakeMessage(content="Done.")),
    ]
    fake_client = _FakeClient(responses)
    monkeypatch.setattr(mod, "get_openai_compat_client", lambda **_k: fake_client)

    rt = MentrixNativeCodingRuntime()
    run_id = rt.start_run(
        "Explore only",
        workspace=str(ws),
        role="explore",
        allowed_tools=["list_dir", "read_file"],
        mission_id="mission-xyz",
        max_steps=4,
        # CP-08: bypass model_router.route_model() auto-routing (which
        # correctly blocks with no cloud/local LLM configured) -- this
        # test drives its own fake client instead.
        model="gpt-4o-mini",
    )
    summary = rt.wait_until_done(run_id, timeout_s=10)

    tool_end = next(e for e in summary["events"] if e["event"] == "tool_end")
    assert tool_end["policy"] == "denied"
    assert tool_end["status"] == "error"
    assert tool_end["mission_id"] == "mission-xyz"
    assert tool_end["agent_id"] == "explore"

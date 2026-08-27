"""Mentrix Lead role restriction must be REAL, not just a prompt suggestion:
an agent run started with a role's bounded tool allowlist is refused by the
runtime itself (MentrixNativeCodingRuntime._run_one_tool) if the model tries
to call a tool outside that allowlist -- even though the tools-API filtering
(coding_engine_mentrix._agent_loop's role_tools) already keeps the model from
being offered it in the first place. This is defense in depth against the
JSON-fallback protocol path, which does not go through the tools API at all."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime
from app.services.coding_engine.mentrix_lead import (
    ROLE_CODER,
    ROLE_EXPLORE,
    ROLE_TOOL_ALLOWLISTS,
    run_explore_phase,
)


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
    """Replays a fixed sequence of chat-completion responses."""

    def __init__(self, responses: list[_FakeResp]) -> None:
        self._responses = list(responses)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        return self._responses.pop(0)


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "README.md").write_text("hi\n", encoding="utf-8")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    return ws


def _run_with_fake_llm(monkeypatch, workspace, *, role, allowed_tools, responses):
    import app.adapters.llm.openai_compat as openai_compat_mod

    monkeypatch.setattr(openai_compat_mod, "openai_compat_available", lambda: True)
    fake_client = _FakeClient(responses)
    monkeypatch.setattr(openai_compat_mod, "get_openai_compat_client", lambda **_k: fake_client)

    rt = MentrixNativeCodingRuntime()
    run_id = rt.start_run(
        "Do the mission goal",
        workspace=str(workspace),
        role=role,
        allowed_tools=allowed_tools,
        max_steps=4,
    )
    return rt.wait_until_done(run_id, timeout_s=10)


class TestRoleToolRestrictionIsEnforcedByTheRuntime:
    def test_explore_role_write_file_attempt_is_refused_not_executed(self, workspace, monkeypatch):
        responses = [
            _FakeResp(
                _FakeMessage(
                    tool_calls=[_FakeToolCall("call1", "write_file", '{"path":"evil.py","content":"x=1"}')]
                )
            ),
            _FakeResp(_FakeMessage(content="Done exploring.")),
        ]
        summary = _run_with_fake_llm(
            monkeypatch,
            workspace,
            role=ROLE_EXPLORE,
            allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_EXPLORE],
            responses=responses,
        )

        assert summary["status"] == "completed"
        assert summary["files_written"] == []
        assert not (workspace / "evil.py").exists()
        tool_ends = [
            e for e in summary["events"] if e["event"] == "tool_end" and e["data"].get("tool") == "write_file"
        ]
        assert tool_ends, "the denied call must still be evidenced in the mission timeline"
        assert tool_ends[0]["data"]["ok"] is False

    def test_explore_role_read_only_tool_still_works(self, workspace, monkeypatch):
        responses = [
            _FakeResp(
                _FakeMessage(tool_calls=[_FakeToolCall("call1", "list_dir", '{"path":"."}')])
            ),
            _FakeResp(_FakeMessage(content="Found README.md.")),
        ]
        summary = _run_with_fake_llm(
            monkeypatch,
            workspace,
            role=ROLE_EXPLORE,
            allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_EXPLORE],
            responses=responses,
        )
        tool_ends = [e for e in summary["events"] if e["event"] == "tool_end" and e["data"].get("tool") == "list_dir"]
        assert tool_ends and tool_ends[0]["data"]["ok"] is True

    def test_coder_role_write_file_is_allowed(self, workspace, monkeypatch):
        responses = [
            _FakeResp(
                _FakeMessage(
                    tool_calls=[_FakeToolCall("call1", "write_file", '{"path":"new.py","content":"x=1\\n"}')]
                )
            ),
            _FakeResp(_FakeMessage(content="Wrote new.py.")),
        ]
        summary = _run_with_fake_llm(
            monkeypatch,
            workspace,
            role=ROLE_CODER,
            allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_CODER],
            responses=responses,
        )
        assert (workspace / "new.py").exists()
        assert "new.py" in summary["files_written"]

    def test_no_role_falls_back_to_the_full_unrestricted_tool_set(self, workspace, monkeypatch):
        """No regression: a plain run (no role/allowed_tools kwargs) behaves
        exactly as before role restriction existed."""
        responses = [
            _FakeResp(
                _FakeMessage(
                    tool_calls=[_FakeToolCall("call1", "write_file", '{"path":"plain.py","content":"y=2\\n"}')]
                )
            ),
            _FakeResp(_FakeMessage(content="Wrote plain.py.")),
        ]
        summary = _run_with_fake_llm(
            monkeypatch, workspace, role=None, allowed_tools=None, responses=responses
        )
        assert (workspace / "plain.py").exists()
        assert "plain.py" in summary["files_written"]


class TestExplorePhaseWiring:
    def test_run_explore_phase_forces_the_explore_allowlist(self, tmp_path):
        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)
            return {"ok": True, "status": "completed", "events_tail": [{"event": "completed", "message": "found X"}]}

        mission = {"goal": "Add a widget", "project_id": None}
        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
            side_effect=fake_build,
        ):
            findings = run_explore_phase(mission, {"label": "repo1"}, tmp_path)

        assert findings == "found X"
        assert captured["role"] == ROLE_EXPLORE
        assert captured["allowed_tools"] == ROLE_TOOL_ALLOWLISTS[ROLE_EXPLORE]
        assert "write_file" not in captured["allowed_tools"]

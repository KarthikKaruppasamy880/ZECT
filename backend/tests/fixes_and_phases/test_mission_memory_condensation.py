"""Mission Memory: a long-running or resumed agent conversation must be
condensed, not rebuilt from scratch every call. Previously a follow-up
message (submit_message resuming a terminal run) discarded the ENTIRE prior
history -- the model had zero memory of what it had already done -- and a
long single run's history grew unbounded with no condensation at all. See
Phase E of ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md:
"Mission Memory/condensation for long-running missions... currently
history rebuilt fresh each call, dropping prior turns rather than
condensing."
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.adapters.coding_engine_mentrix import (
    MentrixNativeCodingRuntime,
    _condense_history,
    _group_into_turns,
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
    def __init__(self, responses: list[_FakeResp]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "README.md").write_text("hi\n", encoding="utf-8")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    return ws


class TestGroupIntoTurns:
    def test_tool_messages_join_the_preceding_turn(self):
        messages = [
            {"role": "assistant", "tool_calls": [{"id": "1"}]},
            {"role": "tool", "tool_call_id": "1", "content": "result"},
            {"role": "assistant", "content": "done"},
        ]
        turns = _group_into_turns(messages)
        assert len(turns) == 2
        assert len(turns[0]) == 2  # assistant + its tool result, never split
        assert len(turns[1]) == 1

    def test_a_leading_tool_message_with_no_prior_turn_still_gets_a_turn(self):
        turns = _group_into_turns([{"role": "tool", "content": "x"}])
        assert len(turns) == 1


class TestCondenseHistory:
    def _history(self, n_turns: int) -> list[dict]:
        history = [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "SEED"},
        ]
        for i in range(n_turns):
            history.append({"role": "assistant", "tool_calls": [{"id": str(i), "function": {"name": f"tool{i}"}}]})
            history.append({"role": "tool", "tool_call_id": str(i), "content": f"result {i}"})
        return history

    def test_returns_unchanged_when_under_the_limit(self):
        history = self._history(3)
        out = _condense_history(history, max_turns=10)
        assert out == history

    def test_condenses_older_turns_and_keeps_system_and_seed_verbatim(self):
        history = self._history(10)
        out = _condense_history(history, max_turns=3)
        assert out[0] == {"role": "system", "content": "SYS"}
        assert out[1] == {"role": "user", "content": "SEED"}
        assert "EARLIER IN THIS RUN" in out[2]["content"]
        assert "tool0" in out[2]["content"]  # oldest turn is summarized, not dropped

    def test_never_splits_a_tool_calls_message_from_its_tool_result(self):
        history = self._history(10)
        out = _condense_history(history, max_turns=3)
        # Walk the kept (post-summary) messages and verify every "tool" role
        # message is immediately preceded by an assistant message with a
        # matching tool_call_id -- never orphaned.
        kept = out[3:]
        for i, msg in enumerate(kept):
            if msg.get("role") == "tool":
                prev = kept[i - 1]
                assert prev.get("role") == "assistant"
                ids = [tc["id"] for tc in prev.get("tool_calls") or []]
                assert msg["tool_call_id"] in ids

    def test_condensation_shrinks_total_message_count(self):
        history = self._history(20)
        out = _condense_history(history, max_turns=3)
        assert len(out) < len(history)

    def test_repeated_condensation_is_stable_once_under_budget(self):
        history = self._history(10)
        once = _condense_history(history, max_turns=3)
        twice = _condense_history(once, max_turns=3)
        assert once == twice

    def test_condensation_extends_rather_than_nests_the_existing_summary(self):
        """Simulates a very long run: condense, then grow past the window
        again, then condense again -- the second summary must fold the
        newly-old turn into the first one, not wrap "EARLIER IN THIS RUN"
        inside another "EARLIER IN THIS RUN"."""
        history = self._history(10)
        once = _condense_history(history, max_turns=3)
        # Grow past budget again: one more tool turn beyond the kept window.
        grown = list(once) + [
            {"role": "assistant", "tool_calls": [{"id": "99", "function": {"name": "tool99"}}]},
            {"role": "tool", "tool_call_id": "99", "content": "result 99"},
        ]
        twice = _condense_history(grown, max_turns=3)
        summary_content = twice[2]["content"]
        assert summary_content.count("EARLIER IN THIS RUN") == 1  # never nested
        assert "tool0" in summary_content  # original fold survives
        assert "tool7" in summary_content  # newly-folded turn (was kept, now aged out) is added
        # One turn aged out of "keep" into the summary, one new turn took its
        # place -- the kept window stays the same size across growth.
        assert len(twice) == len(once)


class TestFollowUpReusesHistory:
    def test_submit_message_does_not_discard_prior_tool_calls(self, workspace, monkeypatch):
        import app.adapters.llm.openai_compat as openai_compat_mod

        monkeypatch.setattr(openai_compat_mod, "openai_compat_available", lambda: True)
        first_responses = [
            _FakeResp(
                _FakeMessage(tool_calls=[_FakeToolCall("c1", "list_dir", '{"path":"."}')])
            ),
            _FakeResp(_FakeMessage(content="Found README.md.")),
        ]
        client = _FakeClient(first_responses)
        monkeypatch.setattr(openai_compat_mod, "get_openai_compat_client", lambda **_k: client)

        rt = MentrixNativeCodingRuntime()
        # CP-08: explicit model bypasses model_router.route_model() auto-
        # routing (which correctly blocks with no cloud/local LLM
        # configured) -- this test drives its own fake client instead.
        run_id = rt.start_run("Look around", workspace=str(workspace), max_steps=4, model="gpt-4o-mini")
        rt.wait_until_done(run_id, timeout_s=10)

        # A follow-up must see the SAME seed messages plus everything the
        # first turn already did -- not a freshly rebuilt system+user pair.
        client._responses = [_FakeResp(_FakeMessage(content="Sure, noted."))]
        rt.submit_message(run_id, "Now also check for a LICENSE file")
        rt.wait_until_done(run_id, timeout_s=10)

        followup_call_messages = client.calls[-1]["messages"]
        roles_and_tools = [
            (m.get("role"), m.get("tool_calls") is not None) for m in followup_call_messages
        ]
        assert ("assistant", True) in roles_and_tools, "the first turn's tool call must survive into the follow-up"
        assert any(
            m.get("role") == "user" and "LICENSE" in str(m.get("content") or "")
            for m in followup_call_messages
        )
        # Seed system/user messages are still the first two entries, untouched.
        assert followup_call_messages[0]["role"] == "system"
        assert "## MISSION GOAL" in followup_call_messages[1]["content"]

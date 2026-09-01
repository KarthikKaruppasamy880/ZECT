"""The coding-agent system/user prompt is layered (SYSTEM POLICY -> PRODUCT
ROLE -> AGENT ROLE -> PROJECT INTELLIGENCE -> RULES/SKILLS, and MISSION GOAL
-> APPROVED PLAN -> CURRENT TASK), not one flat concatenated string.
RULES/SKILLS (.zect/rules, ZECT.md/AGENTS.md) is now a STANDING layer --
previously reachable only via an explicit @rule mention. See Phase E of
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime
from app.services.coding_engine.mention_resolver import load_workspace_rules


class _FakeMessage:
    def __init__(self, content: str | None = None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeResp:
    def __init__(self, message: _FakeMessage) -> None:
        self.choices = [SimpleNamespace(message=message)]


class _CapturingClient:
    """Records every create() call's kwargs and replays canned responses."""

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


def _run(monkeypatch, workspace, *, responses, **start_kwargs):
    import app.adapters.llm.openai_compat as openai_compat_mod

    monkeypatch.setattr(openai_compat_mod, "openai_compat_available", lambda: True)
    client = _CapturingClient(responses)
    monkeypatch.setattr(openai_compat_mod, "get_openai_compat_client", lambda **_k: client)

    rt = MentrixNativeCodingRuntime()
    run_id = rt.start_run("Fix add()", workspace=str(workspace), max_steps=2, **start_kwargs)
    rt.wait_until_done(run_id, timeout_s=10)
    return client


class TestLoadWorkspaceRules:
    def test_returns_empty_string_when_nothing_found(self, tmp_path):
        assert load_workspace_rules(tmp_path) == ""

    def test_concatenates_found_rule_files(self, tmp_path):
        (tmp_path / "ZECT.md").write_text("Never commit secrets.", encoding="utf-8")
        content = load_workspace_rules(tmp_path)
        assert "Never commit secrets" in content


class TestLayeredSystemPrompt:
    def test_static_sections_appear_in_order(self, workspace, monkeypatch):
        client = _run(monkeypatch, workspace, responses=[_FakeResp(_FakeMessage(content="done"))])
        system_content = client.calls[0]["messages"][0]["content"]
        policy_idx = system_content.index("## SYSTEM POLICY")
        role_idx = system_content.index("## PRODUCT ROLE")
        assert policy_idx < role_idx

    def test_agent_role_section_present_only_when_role_given(self, workspace, monkeypatch):
        client = _run(
            monkeypatch,
            workspace,
            responses=[_FakeResp(_FakeMessage(content="done"))],
            role="coder",
            allowed_tools=["read_file"],
        )
        system_content = client.calls[0]["messages"][0]["content"]
        assert "## AGENT ROLE" in system_content
        assert "coder" in system_content

    def test_project_intelligence_section_present_when_agent_context_given(self, workspace, monkeypatch):
        client = _run(
            monkeypatch,
            workspace,
            responses=[_FakeResp(_FakeMessage(content="done"))],
            agent_context="Lattice says: add() lives in calc.py",
        )
        system_content = client.calls[0]["messages"][0]["content"]
        assert "## PROJECT INTELLIGENCE" in system_content
        assert "add() lives in calc.py" in system_content

    def test_rules_are_a_standing_layer_not_only_an_on_demand_mention(self, workspace, monkeypatch):
        """The whole point of this gap: ZECT.md must reach the model even
        though the goal text never contains @rule."""
        (workspace / "ZECT.md").write_text("Never hardcode secrets.", encoding="utf-8")
        client = _run(monkeypatch, workspace, responses=[_FakeResp(_FakeMessage(content="done"))])
        system_content = client.calls[0]["messages"][0]["content"]
        assert "## RULES/SKILLS" in system_content
        assert "Never hardcode secrets" in system_content

    def test_no_rules_section_when_nothing_found(self, workspace, monkeypatch):
        client = _run(monkeypatch, workspace, responses=[_FakeResp(_FakeMessage(content="done"))])
        system_content = client.calls[0]["messages"][0]["content"]
        assert "## RULES/SKILLS" not in system_content

    def test_a_broken_rules_file_never_breaks_the_run(self, workspace, monkeypatch):
        with patch(
            "app.services.coding_engine.mention_resolver.load_workspace_rules",
            side_effect=RuntimeError("boom"),
        ):
            client = _run(monkeypatch, workspace, responses=[_FakeResp(_FakeMessage(content="done"))])
        system_content = client.calls[0]["messages"][0]["content"]
        assert "## RULES/SKILLS" not in system_content
        assert "## SYSTEM POLICY" in system_content


class TestLayeredUserPrompt:
    def test_mission_goal_and_approved_plan_are_separate_sections(self, workspace, monkeypatch):
        client = _run(
            monkeypatch,
            workspace,
            responses=[_FakeResp(_FakeMessage(content="done"))],
            approved_plan="## Plan\n1. Fix add() to actually add",
        )
        user_content = client.calls[0]["messages"][1]["content"]
        goal_idx = user_content.index("## MISSION GOAL")
        plan_idx = user_content.index("## APPROVED PLAN")
        task_idx = user_content.index("## CURRENT TASK")
        assert goal_idx < plan_idx < task_idx
        assert "Fix add() to actually add" in user_content

    def test_no_approved_plan_section_when_not_given(self, workspace, monkeypatch):
        client = _run(monkeypatch, workspace, responses=[_FakeResp(_FakeMessage(content="done"))])
        user_content = client.calls[0]["messages"][1]["content"]
        assert "## APPROVED PLAN" not in user_content


class TestApprovedPlanThreadedFromLifecycle:
    def test_run_mentrix_native_build_forwards_approved_plan(self):
        from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

        captured = {}

        class _FakeRuntime:
            provider_name = "mentrix_native"

            def start_run(self, goal, **kwargs):
                captured.update(kwargs)
                return "run-1"

            def wait_until_done(self, run_id, timeout_s=None):
                return {"ok": True, "status": "completed", "files_written": []}

        with patch(
            "app.adapters.coding_runtime.get_mentrix_native_runtime",
            return_value=_FakeRuntime(),
        ), patch("app.adapters.coding_runtime.selected_coding_engine", return_value="mentrix_native"):
            run_mentrix_native_build(goal="g", workspace="/tmp/x", approved_plan="## Plan\ndo it")

        assert captured["approved_plan"] == "## Plan\ndo it"

    def test_coder_role_turn_passes_the_missions_approved_plan(self, tmp_path, monkeypatch):
        import subprocess

        from app.services.coding_engine.lifecycle import approve_plan, start_mission

        def _init_repo(root):
            root.mkdir(parents=True, exist_ok=True)
            (root / "readme.txt").write_text("hi\n", encoding="utf-8")
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
            return root

        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
        repo = _init_repo(tmp_path / "repo")

        captured = {}

        def fake_build(**kwargs):
            captured.update(kwargs)
            return {"ok": True, "status": "completed", "files_written": [], "run_id": "fake"}

        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch(
                "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
                side_effect=fake_build,
            ),
        ):
            mission = start_mission(
                goal="Fix add()",
                roots=[{"id": 1, "label": "repo", "path": str(repo)}],
                plan="## Plan\nMake add() correct",
                propose_if_empty=True,
            )
            approve_plan(mission["id"])

        assert captured.get("approved_plan") == "## Plan\nMake add() correct"

"""Phase C: the Agent/Coder execution path must use the SAME provenance-aware
Project Intelligence pipeline Ask/Plan already use (ProjectIntelligenceService
+ MentrixContextEngine), not a separate, thinner approximation of it -- see
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase C.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime
from app.services.coding_engine.agent_context import compose_rich_agent_context, _workspace_grep_items


class _FakeSnapshot:
    def __init__(self, *, knowledge=None, memory=None, lattice=None, blueprint=None):
        self.knowledge = knowledge or []
        self.memory = memory or []
        self.lattice = lattice or {"hits": []}
        self.blueprint = blueprint or {"snippet": ""}


class TestComposeRichAgentContext:
    def test_returns_project_intelligence_text_when_available(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "billing.py").write_text("def calculate_premium():\n    pass\n", encoding="utf-8")

        with patch(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService.snapshot",
            return_value=_FakeSnapshot(blueprint={"snippet": "Target: use calculate_premium() everywhere"}),
        ) as snap:
            text = compose_rich_agent_context(
                goal="Fix calculate_premium rounding",
                workspace=str(ws),
                project_id=5,
                repository_id=7,
                work_item_id=42,
            )
        assert snap.called
        called_kwargs = snap.call_args.kwargs
        assert called_kwargs["project_id"] == 5
        assert called_kwargs["repository_id"] == 7
        assert "calculate_premium() everywhere" in text
        assert "billing.py" in text  # from the workspace grep

    def test_returns_empty_string_never_raises_when_project_intelligence_unavailable(self, tmp_path):
        with patch(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService.snapshot",
            side_effect=RuntimeError("db unavailable"),
        ):
            text = compose_rich_agent_context(goal="Fix something", workspace=str(tmp_path), project_id=5)
        assert text == ""

    def test_returns_empty_string_with_no_identifying_info(self, tmp_path):
        text = compose_rich_agent_context(goal="Fix something", workspace=str(tmp_path))
        # No project_id/repository_id -- snapshot() still runs (all-optional
        # signature) but should not error; content may be empty.
        assert isinstance(text, str)


class TestWorkspaceGrepItems:
    def test_finds_goal_relevant_lines_in_the_workspace(self, tmp_path):
        (tmp_path / "premium_calculator.py").write_text(
            "def calculate_premium(base):\n    return base * 1.1\n", encoding="utf-8"
        )
        (tmp_path / "unrelated.py").write_text("x = 1\n", encoding="utf-8")
        items = _workspace_grep_items(str(tmp_path), "Fix calculate_premium rounding")
        assert any("calculate_premium" in i.content for i in items)
        assert all(i.source_type == "workspace_file" for i in items)

    def test_returns_empty_for_a_missing_directory(self):
        assert _workspace_grep_items("C:/definitely/not/a/real/path", "anything") == []


class TestStartRunUsesRichContextWhenIdentityIsAvailable:
    def test_repo_id_present_tries_the_rich_pipeline_first(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "ws"
        ws.mkdir()

        with (
            patch(
                "app.services.coding_engine.agent_context.compose_rich_agent_context_pack",
                return_value={"text": "RICH CONTEXT HERE", "knowledge": True, "lattice_hits": 3, "lattice_indexed": True, "blueprint": False},
            ) as rich,
            patch(
                "app.services.coding_engine.agent_context.compose_context_pack"
            ) as thin,
        ):
            rt = MentrixNativeCodingRuntime()
            run_id = rt.start_run(
                "Fix the thing",
                workspace=str(ws),
                repo_id=7,
                project_id=5,
                work_item_id=42,
                auto_approve_edits=False,
            )
        assert rich.called
        assert not thin.called, "must not fall back to the thin pipeline when the rich one succeeds"
        run = rt._runs[run_id]  # noqa: SLF001 -- inspecting internal state is the point of this test
        assert run["agent_context"] == "RICH CONTEXT HERE"
        assert run["work_item_id"] == 42
        assert run["context_used"] == {
            "knowledge": True,
            "lattice_hits": 3,
            "lattice_indexed": True,
            "blueprint": False,
        }

    def test_falls_back_to_thin_pipeline_when_rich_context_is_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "ws"
        ws.mkdir()

        with (
            patch(
                "app.services.coding_engine.agent_context.compose_rich_agent_context_pack",
                return_value={"text": ""},
            ),
            patch(
                "app.services.coding_engine.agent_context.compose_context_pack",
                return_value={"text": "thin fallback context", "knowledge": False, "lattice_hits": 0, "lattice_indexed": False, "blueprint": False},
            ) as thin,
        ):
            rt = MentrixNativeCodingRuntime()
            run_id = rt.start_run(
                "Fix the thing", workspace=str(ws), repo_id=7, project_id=5, auto_approve_edits=False
            )
        assert thin.called
        run = rt._runs[run_id]  # noqa: SLF001
        assert run["agent_context"] == "thin fallback context"

    def test_no_repo_id_or_project_id_skips_the_rich_pipeline_entirely(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "ws"
        ws.mkdir()

        with (
            patch("app.services.coding_engine.agent_context.compose_rich_agent_context_pack") as rich,
            patch("app.services.coding_engine.agent_context.compose_context_pack", return_value={"text": ""}),
        ):
            rt = MentrixNativeCodingRuntime()
            rt.start_run("Fix the thing", workspace=str(ws), auto_approve_edits=False)
        assert not rich.called, "no identity available -- there's nothing for the rich pipeline to look up"


class TestNativeBuildThreadsIdentityThrough:
    def test_run_mentrix_native_build_forwards_repo_id_and_work_item_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_CODING_ENGINE", "mentrix_native")
        ws = tmp_path / "ws"
        ws.mkdir()

        fake_runtime = SimpleNamespace(
            provider_name="mentrix_native",
            start_run=lambda *a, **kw: "run-1",
            wait_until_done=lambda *a, **kw: {"status": "completed", "files_written": [], "events": [], "model": "m"},
        )
        captured = {}

        def _capture_start_run(*args, **kwargs):
            captured.update(kwargs)
            return "run-1"

        fake_runtime.start_run = _capture_start_run

        with patch(
            "app.adapters.coding_runtime.get_mentrix_native_runtime", return_value=fake_runtime
        ):
            from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

            run_mentrix_native_build(
                goal="Fix it",
                workspace=str(ws),
                project_id=5,
                repo_id=7,
                work_item_id=42,
            )
        assert captured["repo_id"] == "7"
        assert captured["work_item_id"] == 42

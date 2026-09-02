"""Phase D: a Mission's Coder/Tester/Debugger turn surfaces the SAME
knowledge/lattice_hits/lattice_indexed/blueprint summary Ask/Plan already
expose as "Context Used" -- not just the raw prompt text, and not nothing
at all (the gap the reconciliation found: Agent/History tabs had no trace
of what context reached the model). See
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase D.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services.coding_engine.agent_context import compose_rich_agent_context_pack


class TestComposeRichAgentContextPackShape:
    def test_shape_matches_compose_context_pack(self, tmp_path):
        """Same keys as the Ask/Plan pipeline's pack, so one Context Used
        renderer works for both -- see ContextUsedStrip in the frontend."""
        with patch(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService.snapshot",
        ) as snap:
            snap.return_value.knowledge = [{"x": 1}]
            snap.return_value.memory = []
            snap.return_value.lattice = {"status": "READY", "hits": [{"a": 1}, {"b": 2}]}
            snap.return_value.blueprint = {"snippet": "Use repository pattern"}
            pack = compose_rich_agent_context_pack(goal="fix it", workspace=str(tmp_path), project_id=5)

        assert set(pack.keys()) >= {"knowledge", "lattice_hits", "lattice_indexed", "blueprint", "text"}
        assert pack["knowledge"] is True
        assert pack["lattice_hits"] == 2
        assert pack["lattice_indexed"] is True
        assert pack["blueprint"] is True

    def test_lattice_not_ready_is_reported_as_not_indexed(self, tmp_path):
        with patch(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService.snapshot",
        ) as snap:
            snap.return_value.knowledge = []
            snap.return_value.memory = []
            snap.return_value.lattice = {"status": "STALE", "hits": []}
            snap.return_value.blueprint = {"snippet": ""}
            pack = compose_rich_agent_context_pack(goal="fix it", workspace=str(tmp_path), project_id=5)

        assert pack["lattice_indexed"] is False

    def test_returns_well_shaped_empty_dict_on_error_not_a_raise(self, tmp_path):
        with patch(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService.snapshot",
            side_effect=RuntimeError("db down"),
        ):
            pack = compose_rich_agent_context_pack(goal="fix it", workspace=str(tmp_path), project_id=5)

        assert pack == {
            "knowledge": False,
            "lattice_hits": 0,
            "lattice_indexed": False,
            "lattice_state": "NOT_APPLICABLE",
            "blueprint": False,
            "project_key": None,
            "text": "",
        }


class TestMissionSurfacesContextUsed:
    def test_coder_role_turn_sets_mission_context_used(self, tmp_path, monkeypatch):
        import subprocess

        from app.services.coding_engine.lifecycle import approve_plan, start_mission

        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "readme.txt").write_text("hi\n", encoding="utf-8")
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "zect@example.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "ZECT"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

        def _fake_build(*, workspace, **_kwargs):
            return {
                "ok": True,
                "status": "completed",
                "files_written": [],
                "run_id": "fake",
                "context_used": {"knowledge": True, "lattice_hits": 5, "lattice_indexed": True, "blueprint": False},
            }

        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch("app.services.coding_engine.mentrix_native_build.run_mentrix_native_build", side_effect=_fake_build),
        ):
            mission = start_mission(
                goal="Fix add()",
                roots=[{"id": 1, "label": "repo", "path": str(repo)}],
                propose_if_empty=True,
            )
            done = approve_plan(mission["id"])

        assert done["context_used"] == {
            "knowledge": True,
            "lattice_hits": 5,
            "lattice_indexed": True,
            "blueprint": False,
        }

    def test_context_used_is_none_when_no_context_was_composed(self, tmp_path, monkeypatch):
        import subprocess

        from app.services.coding_engine.lifecycle import approve_plan, start_mission

        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
        repo = tmp_path / "repo2"
        repo.mkdir()
        (repo / "readme.txt").write_text("hi\n", encoding="utf-8")
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "zect@example.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "ZECT"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

        def _fake_build(*, workspace, **_kwargs):
            return {"ok": True, "status": "completed", "files_written": [], "run_id": "fake"}

        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch("app.services.coding_engine.mentrix_native_build.run_mentrix_native_build", side_effect=_fake_build),
        ):
            mission = start_mission(
                goal="Fix add()",
                roots=[{"id": 1, "label": "repo", "path": str(repo)}],
                propose_if_empty=True,
            )
            done = approve_plan(mission["id"])

        assert done.get("context_used") is None

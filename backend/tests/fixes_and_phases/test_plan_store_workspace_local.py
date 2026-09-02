"""PLAN.md belongs to the repository it plans changes for.

Before this, every workspace's plans landed in one shared directory under the
ZECT install (`<zect>/.zect/plans/<slug>.md`), so a plan never appeared in the
Explorer of the repo it described, and two workspaces with the same work-item
id would collide. Plans are now written to
`<workspace>/.zect/plans/<slug>.plan.md`, with `.zect/` gitignored so agent
scratch never lands in the user's commit. See section 1 items 5-7 of
ZECT_CMS_REAL_PROJECT_CODING_AGENT_GOLDEN_BENCHMARK_V1.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.coding_engine.plan_store import (
    ensure_zect_ignored,
    list_plans,
    load_plan,
    plan_path,
    save_plan,
)


class TestWorkspaceLocalStorage:
    def test_plan_is_written_under_the_workspace(self, tmp_path):
        ws = tmp_path / "repo"
        ws.mkdir()
        out = save_plan(work_item_or_run="7", title="coding", markdown="## Plan\nstep", workspace=str(ws))

        expected = ws / ".zect" / "plans" / "7-coding.plan.md"
        assert Path(out["path"]) == expected.resolve()
        assert expected.is_file()
        assert "## Plan" in expected.read_text(encoding="utf-8")

    def test_uses_the_plan_md_suffix(self, tmp_path):
        ws = tmp_path / "repo"
        ws.mkdir()
        assert plan_path("7", "coding", str(ws)).name == "7-coding.plan.md"

    def test_plan_id_strips_the_full_suffix(self, tmp_path):
        """`Path.stem` alone would report `7-coding.plan`, which would then
        fail to load back."""
        ws = tmp_path / "repo"
        ws.mkdir()
        out = save_plan(work_item_or_run="7", title="coding", markdown="body", workspace=str(ws))
        assert out["id"] == "7-coding"
        assert load_plan(out["id"], workspace=str(ws))["markdown"] == "body"

    def test_round_trips_within_the_workspace(self, tmp_path):
        ws = tmp_path / "repo"
        ws.mkdir()
        save_plan(work_item_or_run="1", title="coding", markdown="## A\ntext", workspace=str(ws))
        loaded = load_plan("1-coding", workspace=str(ws))
        assert loaded["markdown"] == "## A\ntext"
        assert loaded["meta"]["workspace"] == str(ws)

    def test_two_workspaces_do_not_collide_on_the_same_work_item(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        save_plan(work_item_or_run="1", title="coding", markdown="plan for A", workspace=str(a))
        save_plan(work_item_or_run="1", title="coding", markdown="plan for B", workspace=str(b))

        assert load_plan("1-coding", workspace=str(a))["markdown"] == "plan for A"
        assert load_plan("1-coding", workspace=str(b))["markdown"] == "plan for B"

    def test_list_plans_is_scoped_to_the_workspace(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        save_plan(work_item_or_run="1", title="coding", markdown="A", workspace=str(a))
        save_plan(work_item_or_run="2", title="coding", markdown="B", workspace=str(b))

        assert [p["id"] for p in list_plans(workspace=str(a))] == ["1-coding"]
        assert [p["id"] for p in list_plans(workspace=str(b))] == ["2-coding"]

    def test_empty_markdown_is_rejected_before_touching_disk(self, tmp_path):
        ws = tmp_path / "repo"
        ws.mkdir()
        with pytest.raises(ValueError):
            save_plan(work_item_or_run="1", title="coding", markdown="   ", workspace=str(ws))
        assert not (ws / ".zect").exists()


class TestGitignoreHygiene:
    def test_save_gitignores_the_zect_directory(self, tmp_path):
        ws = tmp_path / "repo"
        ws.mkdir()
        save_plan(work_item_or_run="1", title="coding", markdown="body", workspace=str(ws))
        assert ".zect/" in (ws / ".gitignore").read_text(encoding="utf-8")

    def test_existing_gitignore_is_appended_not_clobbered(self, tmp_path):
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        save_plan(work_item_or_run="1", title="coding", markdown="body", workspace=str(ws))

        text = (ws / ".gitignore").read_text(encoding="utf-8")
        assert "node_modules/" in text and ".zect/" in text

    def test_ensure_zect_ignored_is_idempotent(self, tmp_path):
        ensure_zect_ignored(tmp_path)
        ensure_zect_ignored(tmp_path)
        assert (tmp_path / ".gitignore").read_text(encoding="utf-8").count(".zect/") == 1


class TestInstallLocalFallback:
    def test_no_workspace_still_works(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_PLAN_ROOT", str(tmp_path / "install-plans"))
        out = save_plan(work_item_or_run="9", title="coding", markdown="fallback body")
        assert Path(out["path"]).parent == (tmp_path / "install-plans").resolve()
        assert load_plan("9-coding")["markdown"] == "fallback body"

    def test_pre_existing_dot_md_plans_are_still_readable(self, tmp_path, monkeypatch):
        """Plans written before the `.plan.md` rename must not disappear."""
        legacy_root = tmp_path / "install-plans"
        legacy_root.mkdir()
        (legacy_root / "5-coding.md").write_text("legacy plan body\n", encoding="utf-8")
        monkeypatch.setenv("ZECT_PLAN_ROOT", str(legacy_root))

        assert load_plan("5-coding")["markdown"] == "legacy plan body"

    def test_workspace_lookup_falls_back_to_install_root(self, tmp_path, monkeypatch):
        """A plan saved before workspace-scoping existed is still found when
        the caller now passes a workspace."""
        legacy_root = tmp_path / "install-plans"
        legacy_root.mkdir()
        (legacy_root / "3-coding.md").write_text("older plan\n", encoding="utf-8")
        monkeypatch.setenv("ZECT_PLAN_ROOT", str(legacy_root))
        ws = tmp_path / "repo"
        ws.mkdir()

        assert load_plan("3-coding", workspace=str(ws))["markdown"] == "older plan"

    def test_missing_plan_raises_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_PLAN_ROOT", str(tmp_path / "install-plans"))
        with pytest.raises(FileNotFoundError):
            load_plan("does-not-exist")

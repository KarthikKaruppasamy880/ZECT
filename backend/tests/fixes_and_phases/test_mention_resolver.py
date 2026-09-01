"""Developer composer @mentions resolve against real data (not a second
retrieval system) and never crash the message on a bad/unknown mention --
each becomes a truthful "unresolved" ProvenanceItem instead."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.models import SkillDefinition, WorkItem
from app.services.coding_engine.mention_resolver import find_mentions, resolve_mentions


def test_find_mentions_parses_type_and_optional_value():
    text = "Look at @file:calc.py and @diff and also @lattice:add and @bogus"
    found = find_mentions(text)
    assert ("file", "calc.py") in found
    assert ("diff", "") in found
    assert ("lattice", "add") in found
    assert ("bogus", "") not in found  # not a real mention type at all -- regex doesn't match it


@pytest.fixture()
def ws(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return tmp_path


class TestFileAndFolder:
    def test_file_mention_reads_the_real_file(self, ws):
        items = resolve_mentions("@file:calc.py", workspace=ws)
        assert len(items) == 1
        assert items[0].verification_state == "workspace_file"
        assert "def add" in items[0].content

    def test_missing_file_is_unresolved_not_a_crash(self, ws):
        items = resolve_mentions("@file:nope.py", workspace=ws)
        assert items[0].verification_state == "unresolved"

    def test_folder_mention_lists_real_entries(self, ws):
        items = resolve_mentions("@folder:.", workspace=ws)
        assert "calc.py" in items[0].content


class TestPlanAndDiff:
    def test_plan_mention_reads_a_real_saved_plan(self, ws, monkeypatch):
        monkeypatch.setenv("ZECT_PLAN_ROOT", str(ws / "plans"))
        from app.services.coding_engine.plan_store import save_plan

        save_plan(work_item_or_run="wi1", title="fix-add", markdown="## Fix add()")
        items = resolve_mentions("@plan:wi1-fix-add", workspace=ws)
        assert items[0].verification_state == "plan_store"
        assert "Fix add" in items[0].content

    def test_unknown_plan_id_is_unresolved(self, ws, monkeypatch):
        monkeypatch.setenv("ZECT_PLAN_ROOT", str(ws / "plans"))
        items = resolve_mentions("@plan:does-not-exist", workspace=ws)
        assert items[0].verification_state == "unresolved"

    def test_diff_mention_reads_a_real_git_diff(self, ws):
        subprocess.run(["git", "init", "-b", "main"], cwd=ws, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=ws, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=ws, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=ws, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=ws, check=True, capture_output=True)
        (ws / "calc.py").write_text("def add(a, b):\n    return a - b  # oops\n", encoding="utf-8")

        items = resolve_mentions("@diff", workspace=ws)
        assert items[0].verification_state == "git_diff"
        assert "oops" in items[0].content

    def test_no_diff_is_unresolved(self, ws):
        subprocess.run(["git", "init", "-b", "main"], cwd=ws, check=True, capture_output=True)
        items = resolve_mentions("@diff", workspace=ws)
        assert items[0].verification_state == "unresolved"


class TestTerminal:
    def test_terminal_mention_reads_real_process_output(self, ws):
        from app.domains.workspace.app_runner import spawn_owned_process, stop_owned_processes_in_workspace

        info = spawn_owned_process(f'"{sys.executable}" -c "print(123)"', str(ws))
        try:
            import time

            time.sleep(0.5)
            items = resolve_mentions(f"@terminal:{info.id}", workspace=ws)
            assert items[0].verification_state == "terminal_output"
            assert "123" in items[0].content
        finally:
            stop_owned_processes_in_workspace(str(ws.resolve()))

    def test_unknown_process_id_is_unresolved(self, ws):
        items = resolve_mentions("@terminal:does-not-exist", workspace=ws)
        assert items[0].verification_state == "unresolved"


class TestTestAndError:
    def test_test_mention_reads_real_artifact(self, ws, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "work_items"))
        from app.services.work_items.artifact_store import ArtifactStore

        store = ArtifactStore(42)
        store.write_json("TEST_RESULTS.json", {"ok": True, "status": "pass"})
        items = resolve_mentions("@test", workspace=ws, work_item_id=42)
        assert items[0].verification_state == "test_results"

    def test_error_mention_derives_from_a_failed_artifact(self, ws, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "work_items"))
        from app.services.work_items.artifact_store import ArtifactStore

        store = ArtifactStore(43)
        store.write_json("TEST_RESULTS.json", {"ok": False, "status": "fail", "stderr": "boom"})
        items = resolve_mentions("@error", workspace=ws, work_item_id=43)
        assert items[0].verification_state == "derived_from_artifact"
        assert "boom" in items[0].content

    def test_error_with_no_failure_recorded_is_unresolved(self, ws, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "work_items"))
        items = resolve_mentions("@error", workspace=ws, work_item_id=44)
        assert items[0].verification_state == "unresolved"


class TestSkill:
    def _db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine)()

    def test_skill_mention_matches_a_real_registered_skill(self, ws):
        db = self._db()
        db.add(SkillDefinition(name="lean-code", description="write lean code", manifest={"template": "T"}))
        db.commit()
        items = resolve_mentions("@skill:lean", workspace=ws, db=db)
        assert items[0].verification_state == "skills_registry"
        assert "lean-code" in items[0].content

    def test_skill_mention_no_match_is_unresolved(self, ws):
        db = self._db()
        items = resolve_mentions("@skill:nonexistent", workspace=ws, db=db)
        assert items[0].verification_state == "unresolved"


class TestRule:
    def test_rule_mention_reads_real_rule_files(self, ws):
        (ws / "ZECT.md").write_text("Never commit secrets.", encoding="utf-8")
        rules_dir = ws / ".zect" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "style.md").write_text("Use 2-space indent.", encoding="utf-8")

        items = resolve_mentions("@rule", workspace=ws)
        assert items[0].verification_state == "rules_file"
        assert "Never commit secrets" in items[0].content
        assert "2-space indent" in items[0].content

    def test_no_rule_files_is_unresolved(self, ws):
        items = resolve_mentions("@rule", workspace=ws)
        assert items[0].verification_state == "unresolved"


class TestLatticeAndSymbol:
    def test_lattice_mention_uses_query_graph(self, ws):
        with patch(
            "app.services.lattice.indexer.query_graph",
            return_value=[{"kind": "function", "name": "add", "path": "calc.py", "id": "f:add"}],
        ):
            items = resolve_mentions("@lattice:add", workspace=ws, project_key="demo")
        assert items[0].verification_state == "lattice_structural"
        assert "add" in items[0].content

    def test_symbol_mention_with_no_project_key_is_unresolved(self, ws):
        items = resolve_mentions("@symbol:add", workspace=ws)
        assert items[0].verification_state == "unresolved"


def test_multiple_mentions_in_one_message_all_resolve_independently(ws):
    (ws / "ZECT.md").write_text("Rule text.", encoding="utf-8")
    items = resolve_mentions("@file:calc.py and @rule and @unknown_type_here", workspace=ws)
    assert len(items) == 2  # @unknown_type_here isn't a real mention, never matched at all
    kinds = {i.source_type for i in items}
    assert kinds == {"mention:file", "mention:rule"}


def test_a_broken_resolver_never_crashes_the_whole_message(ws):
    with patch(
        "app.services.coding_engine.mentrix_agent_tools.execute_tool",
        side_effect=RuntimeError("boom"),
    ):
        items = resolve_mentions("@file:calc.py", workspace=ws)
    assert items[0].verification_state == "unresolved"
    assert "boom" in items[0].content


def _git_init(root):
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)


class TestWorkspace:
    def test_workspace_mention_summarizes_root(self, ws):
        items = resolve_mentions("@workspace", workspace=ws)
        assert items[0].verification_state == "workspace_summary"
        assert "calc.py" in items[0].content


class TestCommit:
    def test_commit_mention_defaults_to_head(self, ws):
        _git_init(ws)
        items = resolve_mentions("@commit", workspace=ws)
        assert items[0].verification_state == "git_commit"
        assert "init" in items[0].content

    def test_commit_mention_with_bad_sha_is_unresolved(self, ws):
        _git_init(ws)
        items = resolve_mentions("@commit:deadbeef", workspace=ws)
        assert items[0].verification_state == "unresolved"


class TestBranch:
    def test_branch_mention_reports_current_branch(self, ws):
        _git_init(ws)
        items = resolve_mentions("@branch", workspace=ws)
        assert items[0].verification_state == "git_branch"
        assert "main" in items[0].content

    def test_branch_mention_with_unknown_name_is_unresolved(self, ws):
        _git_init(ws)
        items = resolve_mentions("@branch:does-not-exist", workspace=ws)
        assert items[0].verification_state == "unresolved"


class TestProblem:
    def test_problem_mention_reports_real_findings(self, ws):
        (ws / "eslint.config.js").write_text("export default [];\n", encoding="utf-8")
        bindir = ws / "node_modules" / ".bin"
        bindir.mkdir(parents=True)
        (bindir / "eslint").write_text("#!/bin/sh\n", encoding="utf-8")
        payload = (
            '[{"filePath": "a.ts", "messages": '
            '[{"ruleId": "r", "severity": 2, "message": "err", "line": 1, "column": 1}]}]'
        )

        class _FakeCompleted:
            stdout = payload
            returncode = 0

        with patch("subprocess.run", return_value=_FakeCompleted()):
            items = resolve_mentions("@problem", workspace=ws)
        assert items[0].verification_state == "lint_typecheck"
        assert "a.ts" in items[0].content

    def test_problem_mention_with_nothing_configured_is_unresolved(self, ws):
        items = resolve_mentions("@problem", workspace=ws)
        assert items[0].verification_state == "unresolved"


class TestWorkitem:
    def _db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine)()

    def test_workitem_mention_reads_a_real_row(self, ws):
        db = self._db()
        db.add(WorkItem(title="Fix add()", description="details", status="IN_PROGRESS"))
        db.commit()
        items = resolve_mentions("@workitem:1", workspace=ws, db=db)
        assert items[0].verification_state == "work_item_record"
        assert "Fix add()" in items[0].content

    def test_workitem_mention_defaults_to_active_work_item_id(self, ws):
        db = self._db()
        db.add(WorkItem(title="Active one", status="NEW"))
        db.commit()
        items = resolve_mentions("@workitem", workspace=ws, db=db, work_item_id=1)
        assert items[0].verification_state == "work_item_record"
        assert "Active one" in items[0].content

    def test_workitem_mention_no_match_is_unresolved(self, ws):
        db = self._db()
        items = resolve_mentions("@workitem:999", workspace=ws, db=db)
        assert items[0].verification_state == "unresolved"


class TestBlueprint:
    def test_blueprint_mention_reads_snapshot_snippet(self, ws):
        with patch(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService.snapshot",
        ) as snap:
            snap.return_value.blueprint = {"snippet": "Use repository pattern"}
            items = resolve_mentions("@blueprint", workspace=ws, project_key="demo", db=object())
        assert items[0].verification_state == "blueprint"
        assert "repository pattern" in items[0].content

    def test_blueprint_mention_without_project_key_is_unresolved(self, ws):
        items = resolve_mentions("@blueprint", workspace=ws, db=object())
        assert items[0].verification_state == "unresolved"

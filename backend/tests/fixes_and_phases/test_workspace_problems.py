"""Real lint/typecheck diagnostics for the Developer Workspace Problems panel.

Previously this panel only showed the last mission's error string plus the
list of git-changed paths -- no actual linter/compiler integration, so a repo
with real lint or type errors reported "No problems". See Phase D of
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database import Base
from app.models import Project, Repo
from app.services.workspace.problems import (
    _eslint_problems,
    _mypy_problems,
    _ruff_problems,
    _tsc_problems,
    collect_workspace_problems,
)
from app.services.workspace_multi_root import workspace_problems


class _FakeCompleted:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


class TestRuffProblems:
    def test_skips_when_not_configured(self, tmp_path):
        assert _ruff_problems(tmp_path) is None

    def test_skips_when_binary_missing(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
        with patch("shutil.which", return_value=None):
            assert _ruff_problems(tmp_path) is None

    def test_parses_json_findings(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
        payload = (
            '[{"code": "F401", "message": "`os` imported but unused", '
            '"filename": "app.py", "location": {"row": 3, "column": 1}}]'
        )
        with patch("shutil.which", return_value="/usr/bin/ruff"), patch(
            "subprocess.run", return_value=_FakeCompleted(stdout=payload)
        ):
            out = _ruff_problems(tmp_path)
        assert out == [
            {
                "tool": "ruff",
                "severity": "error",
                "file": "app.py",
                "line": 3,
                "column": 1,
                "message": "F401 `os` imported but unused",
            }
        ]


class TestMypyProblems:
    def test_skips_when_not_configured(self, tmp_path):
        assert _mypy_problems(tmp_path) is None

    def test_parses_text_findings(self, tmp_path):
        (tmp_path / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
        stdout = "app.py:10:5: error: Incompatible return value type [return-value]\nSuccess\n"
        with patch("shutil.which", return_value="/usr/bin/mypy"), patch(
            "subprocess.run", return_value=_FakeCompleted(stdout=stdout)
        ):
            out = _mypy_problems(tmp_path)
        assert out == [
            {
                "tool": "mypy",
                "severity": "error",
                "file": "app.py",
                "line": 10,
                "column": 5,
                "message": "Incompatible return value type [return-value]",
            }
        ]


class TestEslintProblems:
    def test_skips_when_no_config_or_binary(self, tmp_path):
        assert _eslint_problems(tmp_path) is None

    def test_parses_json_findings(self, tmp_path):
        (tmp_path / "eslint.config.js").write_text("export default [];\n", encoding="utf-8")
        bindir = tmp_path / "node_modules" / ".bin"
        bindir.mkdir(parents=True)
        (bindir / "eslint").write_text("#!/bin/sh\n", encoding="utf-8")
        payload = (
            '[{"filePath": "src/x.ts", "messages": ['
            '{"ruleId": "no-unused-vars", "severity": 2, "message": "x is unused", "line": 4, "column": 7}'
            "]}]"
        )
        with patch("subprocess.run", return_value=_FakeCompleted(stdout=payload)):
            out = _eslint_problems(tmp_path)
        assert out == [
            {
                "tool": "eslint",
                "severity": "error",
                "file": "src/x.ts",
                "line": 4,
                "column": 7,
                "message": "no-unused-vars x is unused",
            }
        ]


class TestTscProblems:
    def test_skips_when_no_config_or_binary(self, tmp_path):
        assert _tsc_problems(tmp_path) is None

    def test_parses_text_findings(self, tmp_path):
        (tmp_path / "tsconfig.json").write_text("{}\n", encoding="utf-8")
        bindir = tmp_path / "node_modules" / ".bin"
        bindir.mkdir(parents=True)
        (bindir / "tsc").write_text("#!/bin/sh\n", encoding="utf-8")
        stdout = "src/x.ts(12,3): error TS2322: Type 'string' is not assignable to type 'number'.\n"
        with patch("subprocess.run", return_value=_FakeCompleted(stdout=stdout)):
            out = _tsc_problems(tmp_path)
        assert out == [
            {
                "tool": "tsc",
                "severity": "error",
                "file": "src/x.ts",
                "line": 12,
                "column": 3,
                "message": "TS2322 Type 'string' is not assignable to type 'number'.",
            }
        ]


class TestCollectWorkspaceProblems:
    def test_reports_nothing_checked_when_unconfigured(self, tmp_path):
        out = collect_workspace_problems(tmp_path)
        assert out == {"problems": [], "checked": [], "count": 0}

    def test_aggregates_and_sorts_across_tools(self, tmp_path):
        (tmp_path / "eslint.config.js").write_text("export default [];\n", encoding="utf-8")
        bindir = tmp_path / "node_modules" / ".bin"
        bindir.mkdir(parents=True)
        (bindir / "eslint").write_text("#!/bin/sh\n", encoding="utf-8")
        payload = (
            '[{"filePath": "b.ts", "messages": [{"ruleId": "r", "severity": 1, "message": "warn", "line": 9, "column": 1}]},'
            '{"filePath": "a.ts", "messages": [{"ruleId": "r", "severity": 2, "message": "err", "line": 1, "column": 1}]}]'
        )
        with patch("subprocess.run", return_value=_FakeCompleted(stdout=payload)):
            out = collect_workspace_problems(tmp_path)
        assert out["checked"] == ["eslint"]
        assert out["count"] == 2
        assert [p["file"] for p in out["problems"]] == ["a.ts", "b.ts"]
        assert out["problems"][0]["severity"] == "error"
        assert out["problems"][1]["severity"] == "warning"


@pytest.fixture()
def mem_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    project = Project(name="ws", description="", team="t", current_stage="ask", status="active")
    db.add(project)
    db.commit()
    db.refresh(project)
    return db


def _register(db: Session, project: Project, path: Path, name: str) -> Repo:
    repo = Repo(
        project_id=project.id,
        owner="local",
        repo_name=name,
        default_branch="main",
        clone_status="cloned",
        local_path=str(path.resolve()),
        clone_branch="main",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    return root


class TestWorkspaceProblemsService:
    def test_aggregates_across_authorized_repos_with_identity(self, tmp_path, monkeypatch, mem_db):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        project = mem_db.query(Project).first()

        repo_path = _init_repo(tmp_path / "web")
        (repo_path / "eslint.config.js").write_text("export default [];\n", encoding="utf-8")
        bindir = repo_path / "node_modules" / ".bin"
        bindir.mkdir(parents=True)
        (bindir / "eslint").write_text("#!/bin/sh\n", encoding="utf-8")
        repo = _register(mem_db, project, repo_path, "web")

        payload = (
            '[{"filePath": "a.ts", "messages": '
            '[{"ruleId": "r", "severity": 2, "message": "err", "line": 1, "column": 1}]}]'
        )
        with patch("subprocess.run", return_value=_FakeCompleted(stdout=payload)):
            out = workspace_problems(mem_db, repo_ids=[repo.id])

        assert out["checked"] == ["eslint"]
        assert len(out["problems"]) == 1
        problem = out["problems"][0]
        assert problem["repo_id"] == repo.id
        assert problem["root_label"] == "local/web"
        assert problem["path"] == "a.ts"
        assert Path(problem["abs_path"]) == (repo_path / "a.ts").resolve()
        assert out["skipped"] == []

    def test_skips_unavailable_root(self, tmp_path, monkeypatch, mem_db):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        project = mem_db.query(Project).first()

        missing = _register(mem_db, project, tmp_path / "gone", "gone")
        missing.local_path = str((tmp_path / "does-not-exist").resolve())
        mem_db.commit()

        out = workspace_problems(mem_db, repo_ids=[missing.id])
        assert out["problems"] == []
        assert out["skipped"][0]["reason"] == "ROOT_UNAVAILABLE"

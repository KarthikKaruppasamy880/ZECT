"""Phase D: deterministic lint/typecheck/build gates in the Mission repair
loop. Previously only test suites were orchestrated (run_repo_tests); lint,
typecheck, and build were left entirely to the Coder/Debugger role's own
discretion via generic run_command, so a change could reach
awaiting_git_approval with a broken build or a lint violation the model
never bothered to check. See
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase D.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.coding_engine.lifecycle import (
    _run_quality_and_tests,
    approve_plan,
    run_repo_quality_gates,
    start_mission,
)


def _init_repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "zect-qg@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT QG"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    monkeypatch.setenv("MENTRIX_PR_DRY_RUN", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def _pkg(scripts: dict[str, str]) -> str:
    return json.dumps({"name": "qg-fixture", "version": "0.0.0", "scripts": scripts})


class TestRunRepoQualityGates:
    def test_skips_cleanly_when_nothing_is_configured(self, ws):
        repo = _init_repo(ws / "plain", {"readme.txt": "hi\n"})
        out = run_repo_quality_gates(repo)
        assert out == {"ok": True, "status": "skipped", "kind": "none", "detail": "no lint/typecheck/build configured"}

    def test_python_gates_skip_when_ruff_and_mypy_are_not_installed(self, ws):
        """This dev environment has no ruff/mypy on PATH -- the gate must
        skip, not fail, so a repo is never blocked on tooling it doesn't
        have available, even if it declares a [tool.ruff]/[tool.mypy]
        section in pyproject.toml."""
        repo = _init_repo(
            ws / "pyonly",
            {"pyproject.toml": "[tool.ruff]\nline-length = 100\n\n[tool.mypy]\nstrict = true\n"},
        )
        out = run_repo_quality_gates(repo)
        assert out["ok"] is True
        assert out["kind"] == "none"

    def test_failing_lint_script_fails_the_gate(self, ws):
        repo = _init_repo(
            ws / "web-lint-fail",
            {"package.json": _pkg({"lint": "node -e \"process.exit(1)\""})},
        )
        out = run_repo_quality_gates(repo)
        if out.get("kind") == "none":
            pytest.skip("npm not available in this environment")
        assert out["ok"] is False
        assert out["status"] == "fail"
        assert "eslint" in out["kind"]

    def test_passing_lint_and_build_scripts_pass_the_gate(self, ws):
        repo = _init_repo(
            ws / "web-ok",
            {"package.json": _pkg({"lint": "node -e \"process.exit(0)\"", "build": "node -e \"process.exit(0)\""})},
        )
        out = run_repo_quality_gates(repo)
        if out.get("kind") == "none":
            pytest.skip("npm not available in this environment")
        assert out["ok"] is True
        assert out["status"] == "pass"
        assert "eslint" in out["kind"] and "build" in out["kind"]

    def test_unconfigured_scripts_are_skipped_not_failed(self, ws):
        """A repo that only wires up "build" must not be penalized for
        never having declared "lint" or "typecheck"."""
        repo = _init_repo(
            ws / "web-build-only",
            {"package.json": _pkg({"build": "node -e \"process.exit(0)\""})},
        )
        out = run_repo_quality_gates(repo)
        if out.get("kind") == "none":
            pytest.skip("npm not available in this environment")
        assert out["ok"] is True
        assert out["kind"] == "build"


class TestRunQualityAndTests:
    def test_quality_failure_short_circuits_before_tests_run(self, ws):
        """lint/typecheck/build MUST pass before tests are even attempted --
        a failing build gate must be reported as the failure, and the (here,
        passing) pytest suite must never run to mask it."""
        repo = _init_repo(
            ws / "web-fail-with-tests",
            {
                "package.json": _pkg({"lint": "node -e \"process.exit(1)\""}),
                "tests/test_x.py": "def test_x():\n    assert True\n",
            },
        )
        out = _run_quality_and_tests(repo)
        if out.get("kind") == "none":
            pytest.skip("npm not available in this environment")
        assert out["ok"] is False
        assert "eslint" in out["kind"]
        assert "pytest" not in out["kind"]

    def test_quality_pass_falls_through_to_tests(self, ws):
        repo = _init_repo(
            ws / "web-pass-with-tests",
            {
                "package.json": _pkg({"lint": "node -e \"process.exit(0)\""}),
                "tests/test_x.py": "def test_x():\n    assert True\n",
            },
        )
        out = _run_quality_and_tests(repo)
        assert out["ok"] is True
        assert out["kind"] == "pytest"
        assert out["quality"]["ok"] is True


class TestMissionRepairLoopCoversQualityGates:
    def test_failing_build_script_triggers_auto_repair(self, ws, monkeypatch):
        """Closes the Phase D gap: a change that breaks the build must reach
        the same diagnose-and-repair loop test failures already use, not
        sail through to awaiting_git_approval untouched."""
        monkeypatch.setenv("MENTRIX_CODING_AGENT_AUTO_REPAIR_MAX", "1")
        repo = _init_repo(
            ws / "backend",
            {"package.json": _pkg({"build": "node -e \"process.exit(1)\""}), "README.md": "hi\n"},
        )
        if run_repo_quality_gates(repo).get("kind") != "build":
            pytest.skip("npm not available in this environment")

        m = start_mission(
            goal="Touch the repo",
            roots=[{"id": 1, "label": "backend", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "README.md", "old": "hi", "new": "hi\ntouched"}]},
            workspace_parent=str(ws / "wt"),
        )
        m = approve_plan(m["id"])

        assert m["phase"] == "blocked"
        blocker = m["repos"][0]["blocker"]
        assert "tests_fail_after_1_repair_attempt(s)" in blocker
        attempt_events = [e for e in m["events"] if e["event"] == "diagnose_attempt"]
        assert len(attempt_events) == 1

    def test_repair_that_fixes_the_build_unblocks_the_mission(self, ws, monkeypatch):
        monkeypatch.setenv("MENTRIX_CODING_AGENT_AUTO_REPAIR_MAX", "2")
        repo = _init_repo(
            ws / "backend2",
            {"package.json": _pkg({"build": "node -e \"process.exit(1)\""}), "README.md": "hi\n"},
        )
        if run_repo_quality_gates(repo).get("kind") != "build":
            pytest.skip("npm not available in this environment")

        def fake_repair(*, workspace, **_kwargs):
            pkg = Path(workspace) / "package.json"
            pkg.write_text(_pkg({"build": "node -e \"process.exit(0)\""}), encoding="utf-8")
            return {"ok": True, "status": "completed", "files_written": ["package.json"], "run_id": "fake"}

        m = start_mission(
            goal="Touch the repo",
            roots=[{"id": 1, "label": "backend2", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "README.md", "old": "hi", "new": "hi\ntouched"}]},
            workspace_parent=str(ws / "wt"),
        )
        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
            side_effect=fake_repair,
        ):
            m = approve_plan(m["id"])

        assert m["phase"] == "awaiting_git_approval", m
        assert m["repos"][0]["blocker"] == ""
        assert m["repos"][0]["auto_repair_attempts"] == 1

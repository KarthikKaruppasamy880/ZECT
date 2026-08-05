"""Phase E — orchestrator's sandbox gate used to only ever estimate PR
readiness from the review score/critical-findings count, never actually
running the repo's tests. This verifies it now runs a real test command
(via autofix.py's run_and_fix — the same App Runner-class execution Phase 4
built) when the workspace's stack is recognized, and falls back to the
original heuristic gate otherwise.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from app.services.forge_loop.orchestrator import _detect_test_command, _run_sandbox_check


class TestDetectTestCommand:
    def test_returns_none_for_empty_workspace(self):
        assert _detect_test_command("") is None

    def test_returns_none_for_nonexistent_dir(self):
        assert _detect_test_command("/path/does/not/exist/zzz") is None

    def test_detects_npm_project(self, tmp_path):
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert _detect_test_command(str(tmp_path)) == "npm test"

    def test_detects_python_project(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        assert _detect_test_command(str(tmp_path)) == "pytest -q"

    def test_detects_go_project(self, tmp_path):
        (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
        assert _detect_test_command(str(tmp_path)) == "go test ./..."

    def test_unrecognized_stack_returns_none(self, tmp_path):
        (tmp_path / "README.md").write_text("hi", encoding="utf-8")
        assert _detect_test_command(str(tmp_path)) is None


class TestRunSandboxCheck:
    def test_falls_back_to_heuristic_when_no_test_command(self):
        result = _run_sandbox_check("", 80, 0, [], "upgrade")
        assert "real_execution" not in result
        assert result["ready"] is True

    def test_falls_back_to_heuristic_outside_upgrade_mode(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        result = _run_sandbox_check(str(tmp_path), 80, 0, [], "deliver")
        assert "real_execution" not in result

    def test_runs_real_test_command_and_reports_success(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        fake_result = Mock(success=True, total_attempts=1, final_output="2 passed")

        with patch("app.domains.workspace.autofix.run_and_fix", return_value=fake_result) as mock_run:
            result = _run_sandbox_check(str(tmp_path), 80, 0, [], "upgrade")

        assert result["real_execution"] is True
        assert result["ready"] is True
        assert result["test_command"] == "pytest -q"
        assert mock_run.call_args.args[0].command == "pytest -q"
        assert mock_run.call_args.args[0].cwd == str(tmp_path)

    def test_real_test_failure_blocks_readiness_even_with_good_review_score(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        fake_result = Mock(success=False, total_attempts=3, final_output="AssertionError: boom")

        with patch("app.domains.workspace.autofix.run_and_fix", return_value=fake_result):
            result = _run_sandbox_check(str(tmp_path), 95, 0, [], "upgrade")

        assert result["ready"] is False
        assert result["create_pr_hard_blocked"] is True
        assert any("Real test run failed" in b for b in result["blockers"])

    def test_critical_findings_still_block_even_when_tests_pass(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        fake_result = Mock(success=True, total_attempts=1, final_output="all good")

        with patch("app.domains.workspace.autofix.run_and_fix", return_value=fake_result):
            result = _run_sandbox_check(str(tmp_path), 80, 2, [], "upgrade")

        assert result["ready"] is False
        assert any("critical finding" in b for b in result["blockers"])

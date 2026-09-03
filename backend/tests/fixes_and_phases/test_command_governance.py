"""CP-09A -- mode/role-aware Tool Governance for run_command.

AgentWritePolicy (CP-07) hard-gates write_file/apply_patch by path and
action, but a shell command could always bypass that entirely --
`sed -i`, `git commit`, `git checkout --`, or an arbitrary script that
rewrites files ran completely unchecked as long as it didn't match the
small, hand-picked `_DESTRUCTIVE_CMD` list. This suite proves the
classification is accurate for the categories the mandate names, that
every category outside READ_ONLY/BUILD/TEST/APP_RUNNER requires approval
(fail-closed, including UNKNOWN -- not just the old destructive list),
and that a Mission's own JSON-patch command execution (lifecycle.py::
_apply_patches, which used to silently discard this call's result)
actually blocks and reports a reason instead of quietly no-op'ing.
"""

from __future__ import annotations

import pytest

from app.services.coding_engine import command_governance as cg
from app.services.coding_engine.mentrix_agent_tools import command_needs_approval


class TestClassification:
    @pytest.mark.parametrize(
        "command,expected",
        [
            ("rm -rf /", cg.CATEGORY_DESTRUCTIVE),
            ("git reset --hard", cg.CATEGORY_DESTRUCTIVE),
            ("git push", cg.CATEGORY_DESTRUCTIVE),
            ("docker push myimage:latest", cg.CATEGORY_DEPLOYMENT),
            ("kubectl apply -f deploy.yaml", cg.CATEGORY_DEPLOYMENT),
            ("git commit -m 'wip'", cg.CATEGORY_GIT_MUTATING),
            ("git checkout -- .", cg.CATEGORY_GIT_MUTATING),
            ("git clean -fd", cg.CATEGORY_GIT_MUTATING),
            ("sed -i 's/x/y/' calc.py", cg.CATEGORY_FILE_MUTATING),
            ("echo 'malicious' > calc.py", cg.CATEGORY_FILE_MUTATING),
            ("rm calc.py", cg.CATEGORY_FILE_MUTATING),
            ("pytest -q", cg.CATEGORY_TEST),
            ("npm test", cg.CATEGORY_TEST),
            ("mvn test", cg.CATEGORY_TEST),
            ("npm run build", cg.CATEGORY_BUILD),
            ("go build ./...", cg.CATEGORY_BUILD),
            ("npm run dev", cg.CATEGORY_APP_RUNNER),
            ("uvicorn app.main:app", cg.CATEGORY_APP_RUNNER),
            ("git status", cg.CATEGORY_READ_ONLY),
            ("ls -la", cg.CATEGORY_READ_ONLY),
            ("some_bespoke_tool.sh --deploy-ish-sounding-but-unknown", cg.CATEGORY_UNKNOWN),
            ("", cg.CATEGORY_UNKNOWN),
        ],
    )
    def test_classifies_known_command_shapes(self, command, expected):
        assert cg.classify_command(command) == expected

    def test_benign_categories_do_not_require_approval(self):
        for cmd in ("pytest -q", "npm run build", "npm run dev", "git status", "ls -la"):
            needs, category = cg.requires_approval(cmd)
            assert not needs, f"{cmd!r} ({category}) should not need approval"

    def test_every_mutating_or_unknown_category_requires_approval(self):
        for cmd in (
            "rm -rf /", "git push", "docker push x", "git commit -m x",
            "sed -i s/x/y/ f.py", "totally_unrecognized_command_xyz",
        ):
            needs, category = cg.requires_approval(cmd)
            assert needs, f"{cmd!r} ({category}) should require approval"
            assert category not in cg.AUTO_ALLOWED_CATEGORIES

    def test_unknown_fails_closed_not_open(self):
        """The mandate's exact distinction from the old behavior: an
        unrecognized command must default to needing approval, never to
        silently running because it didn't match a known-bad pattern."""
        needs, category = cg.requires_approval("run_the_thing_nobody_has_seen_before")
        assert category == cg.CATEGORY_UNKNOWN
        assert needs is True


class TestCommandNeedsApprovalIntegration:
    """command_needs_approval() is the actual choke-point function
    mentrix_agent_tools.py's run_command handler calls -- proves
    classification is wired in, not just available as a standalone
    module nobody calls."""

    def test_destructive_command_still_needs_approval(self):
        assert command_needs_approval("rm -rf /") is True

    def test_benign_test_command_does_not_need_approval(self):
        assert command_needs_approval("pytest -q") is False

    def test_git_commit_now_needs_approval(self):
        """Before CP-09A, only git push/reset --hard were caught -- a
        plain git commit ran completely unchecked."""
        assert command_needs_approval("git commit -m 'oops'") is True

    def test_file_mutating_shell_redirect_now_needs_approval(self):
        assert command_needs_approval("echo bad_content > calc.py") is True

    def test_unrecognized_command_now_needs_approval(self):
        assert command_needs_approval("./do_something_nobody_documented.sh") is True


class TestApplyPatchesCommandGovernance:
    """lifecycle.py::_apply_patches used to call execute_tool("run_command",
    ...) and throw the result away entirely -- a command needing approval
    (or one that simply failed) ran, or silently didn't, with the patch
    still reported "ok": True. Proves the fix: a mutating/unknown command
    now blocks the mission with a visible, categorized reason."""

    def _mission(self, tmp_path):
        from app.services.coding_engine import lifecycle

        mission = lifecycle.start_mission(
            goal="CP-09A command governance check",
            roots=[{"id": 1, "label": "x", "path": str(tmp_path)}],
            plan="# Anything goes\n",
        )
        return lifecycle, mission, mission["repos"][0]

    def test_file_mutating_command_blocks_instead_of_silently_running(self, tmp_path):
        lifecycle, mission, repo = self._mission(tmp_path)
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        result = lifecycle._apply_patches(
            mission, repo, tmp_path,
            [{"path": "calc.py", "content": "def add(a, b):\n    return a + b\n", "command": "sed -i 's/x/y/' calc.py"}],
        )
        assert result["ok"] is False
        assert result["error"].startswith("command_blocked:FILE_MUTATING")
        # The write_file part of the patch still happened (that's a
        # separately-governed, already-authorized action) -- only the
        # ungoverned shell command after it was refused.
        assert "calc.py" in result["files"]

    def test_unknown_command_blocks_fail_closed(self, tmp_path):
        lifecycle, mission, repo = self._mission(tmp_path)
        result = lifecycle._apply_patches(
            mission, repo, tmp_path,
            [{"path": "calc.py", "content": "x = 1\n", "command": "run_the_thing_nobody_has_seen_before"}],
        )
        assert result["ok"] is False
        assert result["error"] == "command_blocked:UNKNOWN"

    def test_benign_test_command_still_runs_and_reports_ok(self, tmp_path):
        lifecycle, mission, repo = self._mission(tmp_path)
        result = lifecycle._apply_patches(
            mission, repo, tmp_path,
            [{"path": "calc.py", "content": "x = 1\n", "command": "python --version"}],
        )
        assert result["ok"] is True

    def test_blocked_command_emits_a_mission_event_with_the_category(self, tmp_path):
        lifecycle, mission, repo = self._mission(tmp_path)
        lifecycle._apply_patches(
            mission, repo, tmp_path,
            [{"path": "calc.py", "content": "x = 1\n", "command": "git commit -m x"}],
        )
        blocked = [e for e in mission["events"] if e["event"] == "tool_blocked"]
        assert blocked, mission["events"]
        assert blocked[-1]["data"].get("category") == "GIT_MUTATING"

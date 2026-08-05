"""Unit tests for git worktree list parsing."""
from unittest.mock import patch

from app.domains.repository.git_ops import git_worktrees


def test_git_worktrees_parses_porcelain():
    porcelain = """worktree /repo
HEAD abc
branch refs/heads/main

worktree /repo/.zect/wt-1
HEAD def
branch refs/heads/zect/run-1

"""
    with patch("app.domains.repository.git_ops._validate_repo", return_value="/repo"):
        with patch("app.domains.repository.git_ops._run_git") as run:
            run.return_value = {"exit_code": 0, "stdout": porcelain, "stderr": ""}
            out = git_worktrees("/repo")
    assert out["count"] == 2
    assert out["worktrees"][0]["branch"] == "main"
    assert out["worktrees"][0]["is_current"] is True
    assert out["worktrees"][1]["branch"] == "zect/run-1"
    assert out["worktrees"][1]["is_current"] is False

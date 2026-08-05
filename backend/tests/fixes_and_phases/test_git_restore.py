"""Stage C — git restore path validation (unit, no auth/HTTP stack)."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.domains.repository.git_ops import GitRestoreRequest, git_restore


def test_git_restore_rejects_traversal():
    with patch("app.domains.repository.git_ops._validate_repo", return_value="/repo"):
        with pytest.raises(HTTPException) as ei:
            git_restore(GitRestoreRequest(repo_path="/repo", files=["../outside.txt"]))
    assert ei.value.status_code == 400


def test_git_restore_rejects_absolute():
    with patch("app.domains.repository.git_ops._validate_repo", return_value="/repo"):
        with pytest.raises(HTTPException) as ei:
            git_restore(GitRestoreRequest(repo_path="/repo", files=["/etc/passwd"]))
    assert ei.value.status_code == 400


def test_git_restore_ok():
    with patch("app.domains.repository.git_ops._validate_repo", return_value="/repo") as val:
        with patch("app.domains.repository.git_ops._run_git") as run:
            run.return_value = {"exit_code": 0, "stdout": "", "stderr": ""}
            out = git_restore(GitRestoreRequest(repo_path="/repo", files=["src/a.py"]))
    assert out["status"] == "restored"
    assert out["files"] == ["src/a.py"]
    val.assert_called_once()
    assert run.call_args[0][1][:4] == ["restore", "--source=HEAD", "--staged", "--worktree"]

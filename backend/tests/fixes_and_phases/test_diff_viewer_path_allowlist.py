"""diff_viewer.py's /file endpoint used repo_path directly as subprocess cwd
with only an os.path.isdir existence check — unlike git_ops.py, it never
routed through the same path_under_allowed_roots allowlist. The subprocess
calls here use a fixed argv list (not shell=True), so this was never
shell-injectable, but an arbitrary existing directory on the host was still
reachable as a git-show cwd.
"""

from __future__ import annotations

import os

import pytest
from fastapi import HTTPException

from app.routers.diff_viewer import FileDiffRequest, file_diff


class TestFileDiffPathAllowlist:
    def test_rejects_path_outside_allowed_roots(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ZECT_WORKSPACE_ROOT", raising=False)
        monkeypatch.delenv("MENTRIX_WORKSPACE", raising=False)
        # tmp_path lives under the system temp dir, which allowed_paths.py now
        # allows by default (see test_allowed_paths.py) — use a path outside
        # every default root (POSIX list, home, and temp) instead.
        outside = os.path.abspath("C:\\Windows\\System32")

        with pytest.raises(HTTPException) as exc:
            file_diff(FileDiffRequest(repo_path=outside, commit_a="a", commit_b="b", file_path="x.py"))

        assert exc.value.status_code == 403

    def test_missing_directory_under_allowed_root_is_404(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        missing = tmp_path / "does-not-exist"

        with pytest.raises(HTTPException) as exc:
            file_diff(FileDiffRequest(repo_path=str(missing), commit_a="a", commit_b="b", file_path="x.py"))

        assert exc.value.status_code == 404

"""Tests for Windows/local workspace allowed path roots."""
from __future__ import annotations

import os

import pytest

from app.core.allowed_paths import allowed_roots, path_under_allowed_roots


def test_allowed_roots_includes_zect_workspace_root(monkeypatch, tmp_path):
    ws = tmp_path / "workspaces"
    ws.mkdir()
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(ws))
    roots = allowed_roots()
    assert str(ws.resolve()) in roots


def test_path_under_workspace_root(monkeypatch, tmp_path):
    ws = tmp_path / "workspaces"
    repo = ws / "owner" / "repo"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("hi", encoding="utf-8")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(ws))
    p = path_under_allowed_roots(str(repo))
    assert p.name == "repo"


def test_path_outside_roots_raises():
    with pytest.raises(ValueError, match="Access denied"):
        path_under_allowed_roots(os.path.abspath("C:\\Windows\\System32"))

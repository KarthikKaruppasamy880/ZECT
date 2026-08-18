"""Tests for Windows/local workspace allowed path roots."""
from __future__ import annotations

import os

import pytest

from app.infrastructure.allowed_paths import (
    allowed_roots,
    is_path_under_root,
    path_under_allowed_roots,
)


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
    # Must be outside home/tmp/POSIX defaults on both Windows and Linux CI.
    with pytest.raises(ValueError, match="Access denied"):
        path_under_allowed_roots("/__zect_not_allowed__/outside")


def test_home_and_tempdir_allowed_without_any_env_var(monkeypatch):
    """The POSIX-only defaults (/home, /tmp, /var, /opt) never match a
    resolved Windows path — a fresh install with no ZECT_WORKSPACE_ROOT set
    had File Explorer/Git Ops/Diff Viewer silently unable to reach anything
    at all on Windows. Path.home() and the system temp dir work on every
    platform without needing that env var."""
    monkeypatch.delenv("ZECT_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("MENTRIX_WORKSPACE", raising=False)
    import tempfile
    from pathlib import Path

    roots = allowed_roots()
    assert str(Path.home()) in roots
    assert str(Path(tempfile.gettempdir())) in roots


def test_prefix_sibling_is_not_inside_root(tmp_path, monkeypatch):
    """Classic startswith jail bypass: ``ws-evil`` must not match root ``ws``."""
    ws = tmp_path / "ws"
    evil = tmp_path / "ws-evil"
    ws.mkdir()
    evil.mkdir()
    (ws / "ok.txt").write_text("inside\n", encoding="utf-8")
    (evil / "secret.txt").write_text("outside\n", encoding="utf-8")
    assert str(evil.resolve()).startswith(str(ws.resolve()))
    assert is_path_under_root(ws / "ok.txt", ws) is True
    assert is_path_under_root(evil, ws) is False
    monkeypatch.setattr(
        "app.infrastructure.allowed_paths.allowed_roots",
        lambda: [str(ws.resolve())],
    )
    assert path_under_allowed_roots(str(ws / "ok.txt")).name == "ok.txt"
    with pytest.raises(ValueError, match="Access denied"):
        path_under_allowed_roots(str(evil))
    with pytest.raises(ValueError, match="Access denied"):
        path_under_allowed_roots(str(evil / "secret.txt"))


def test_symlink_escape_is_denied(tmp_path, monkeypatch):
    ws = tmp_path / "jail"
    outside = tmp_path / "outside"
    ws.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("leak\n", encoding="utf-8")
    link = ws / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS cannot create directory symlinks (Windows without privilege)")
    monkeypatch.setattr(
        "app.infrastructure.allowed_paths.allowed_roots",
        lambda: [str(ws.resolve())],
    )
    with pytest.raises(ValueError, match="Access denied"):
        path_under_allowed_roots(str(link))
    with pytest.raises(ValueError, match="Access denied"):
        path_under_allowed_roots(str(link / "secret.txt"))

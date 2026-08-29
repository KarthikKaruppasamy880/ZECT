"""Mentrix Coding Agent — tools path jail + native runtime factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.coding_runtime import (
    coding_engine_health,
    get_coding_runtime,
    get_mentrix_native_runtime,
    reset_coding_runtime_for_tests,
    selected_coding_engine,
)
from app.services.coding_engine.mentrix_agent_tools import (
    command_needs_approval,
    execute_tool,
    resolve_workspace,
)


def test_factory_mentrix_native(monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mentrix_native")
    reset_coding_runtime_for_tests()
    assert selected_coding_engine() == "mentrix_native"
    rt = get_coding_runtime()
    assert getattr(rt, "provider_name", "") == "mentrix_native"
    health = coding_engine_health()
    assert health["provider"] == "mentrix_native"


def test_path_jail_rejects_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / "a.txt").write_text("hi", encoding="utf-8")
    root = resolve_workspace(str(ws))
    out = execute_tool("read_file", {"path": "../outside.txt"}, workspace=root)
    assert out.get("ok") is False or "error" in out


def test_write_and_read_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    ws = tmp_path / "repo"
    ws.mkdir()
    root = resolve_workspace(str(ws))
    w = execute_tool("write_file", {"path": "hello.py", "content": "print(1)\n"}, workspace=root)
    assert w.get("ok") is True
    assert w.get("file_diff") is True
    r = execute_tool("read_file", {"path": "hello.py"}, workspace=root)
    assert r.get("ok") is True
    assert "print(1)" in r.get("content", "")


def test_search_code(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / "x.py").write_text("def mentrix_marker():\n    pass\n", encoding="utf-8")
    root = resolve_workspace(str(ws))
    out = execute_tool("search_code", {"query": "mentrix_marker"}, workspace=root)
    assert out.get("ok") is True
    assert any("mentrix_marker" in (h.get("text") or "") for h in out.get("hits") or [])


def test_destructive_command_needs_approval():
    assert command_needs_approval("rm -rf /") is True
    assert command_needs_approval("pytest -q") is False


def test_list_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / "f.txt").write_text("x", encoding="utf-8")
    root = resolve_workspace(str(ws))
    out = execute_tool("list_dir", {"path": "."}, workspace=root)
    assert out.get("ok") is True
    names = [e["name"] for e in out.get("entries") or []]
    assert "f.txt" in names


def test_get_mentrix_native_runtime_sticky():
    reset_coding_runtime_for_tests()
    a = get_mentrix_native_runtime()
    b = get_mentrix_native_runtime()
    assert a is b

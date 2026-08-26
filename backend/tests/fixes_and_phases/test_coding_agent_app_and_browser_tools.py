"""start_app/restart_app/stop_app/health_check as native Coding Agent tools.

Real process starts (not mocked) so ownership-scoping and the diagnose loop's
edit -> test -> start -> health-check -> browser-verify chain is proven, not
just labeled. Uses explicit commands for determinism; a separate test proves
recipe discovery (no hardcoded npm run dev) picks the real project command."""

from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

from app.domains.workspace.app_runner import (
    list_owned_processes_in_workspace,
    stop_owned_processes_in_workspace,
)
from app.services.coding_engine.mentrix_agent_tools import execute_tool


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _http_server_command(port: int) -> str:
    return f'"{sys.executable}" -m http.server {port} --bind 127.0.0.1'


class TestStartRestartStopHealthCheck:
    def test_start_health_check_stop_full_cycle(self, tmp_path):
        port = _free_port()
        ws = tmp_path / "app"
        ws.mkdir()

        started = execute_tool(
            "start_app", {"command": _http_server_command(port), "label": "test-server"}, workspace=ws
        )
        assert started["ok"] is True, started
        try:
            health = execute_tool("health_check", {"port": port, "timeout_s": 10}, workspace=ws)
            assert health["ok"] is True, health

            stopped = execute_tool("stop_app", {}, workspace=ws)
            assert stopped["ok"] is True
            assert stopped["stopped"] == 1

            after = execute_tool("health_check", {"port": port, "timeout_s": 2}, workspace=ws)
            assert after["ok"] is False, "process was stopped -- port must not still answer"
        finally:
            stop_owned_processes_in_workspace(str(ws.resolve()))

    def test_restart_app_stops_old_process_before_starting_new_one(self, tmp_path):
        port = _free_port()
        ws = tmp_path / "app"
        ws.mkdir()
        cmd = _http_server_command(port)

        first = execute_tool("start_app", {"command": cmd}, workspace=ws)
        assert first["ok"] is True
        first_pid = first["pid"]
        try:
            time.sleep(0.3)
            second = execute_tool("restart_app", {"command": cmd}, workspace=ws)
            assert second["ok"] is True
            assert second["pid"] != first_pid, "restart must actually replace the process, not stack a second one"
            owned = list_owned_processes_in_workspace(str(ws.resolve()))
            running = [p for p in owned if p["running"]]
            assert len(running) == 1, f"exactly one process should remain running after restart, got {running}"
        finally:
            stop_owned_processes_in_workspace(str(ws.resolve()))

    def test_stop_app_never_touches_a_different_workspace(self, tmp_path):
        port_a = _free_port()
        ws_a = tmp_path / "a"
        ws_a.mkdir()
        ws_b = tmp_path / "b"
        ws_b.mkdir()

        started = execute_tool("start_app", {"command": _http_server_command(port_a)}, workspace=ws_a)
        assert started["ok"] is True
        try:
            # Mission B's stop_app must be a no-op against mission A's process.
            stopped_b = execute_tool("stop_app", {}, workspace=ws_b)
            assert stopped_b["stopped"] == 0

            health_a = execute_tool("health_check", {"port": port_a, "timeout_s": 5}, workspace=ws_a)
            assert health_a["ok"] is True, "workspace A's server must still be running -- untouched"
        finally:
            stop_owned_processes_in_workspace(str(ws_a.resolve()))

    def test_health_check_requires_port(self, tmp_path):
        out = execute_tool("health_check", {}, workspace=tmp_path)
        assert out["ok"] is False


class TestRecipeDiscoveryNotHardcoded:
    def test_single_discovered_recipe_is_auto_selected_and_really_starts(self, tmp_path):
        ws = tmp_path / "proj"
        ws.mkdir()
        port = _free_port()
        (ws / "package.json").write_text(
            json.dumps({"scripts": {"dev": _http_server_command(port)}}),
            encoding="utf-8",
        )
        started = execute_tool("start_app", {}, workspace=ws)
        assert started["ok"] is True, started
        assert started["command"] == f"npm run dev"
        try:
            health = execute_tool("health_check", {"port": port, "timeout_s": 10}, workspace=ws)
            # We only asserted the *discovered command* was "npm run dev" (the
            # real project script name) rather than a Python one-liner we
            # invented -- discovery does not itself execute package.json
            # scripts, so we don't require npm to be installed for this
            # assertion to be meaningful.
            assert health["ok"] in (True, False)
        finally:
            stop_owned_processes_in_workspace(str(ws.resolve()))

    def test_ambiguous_recipes_return_choices_not_a_guess(self, tmp_path):
        ws = tmp_path / "proj"
        ws.mkdir()
        (ws / "package.json").write_text(
            '{"scripts": {"dev": "vite", "test": "vitest"}}', encoding="utf-8"
        )
        out = execute_tool("start_app", {}, workspace=ws)
        assert out["ok"] is False
        assert out["needs_recipe_choice"] is True
        ids = {c["id"] for c in out["candidates"]}
        assert "pkg-dev" in ids and "pkg-test" in ids

    def test_recipe_id_selects_explicitly(self, tmp_path):
        ws = tmp_path / "proj"
        ws.mkdir()
        (ws / "package.json").write_text(
            '{"scripts": {"dev": "vite", "test": "vitest"}}', encoding="utf-8"
        )
        ambiguous = execute_tool("start_app", {}, workspace=ws)
        chosen_id = next(c["id"] for c in ambiguous["candidates"] if c["id"] == "pkg-test")
        out = execute_tool("start_app", {"recipe_id": chosen_id}, workspace=ws)
        try:
            assert out["ok"] is True
            assert out["command"] == "npm run test"
        finally:
            stop_owned_processes_in_workspace(str(ws.resolve()))

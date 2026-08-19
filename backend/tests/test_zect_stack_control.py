"""Local stack controller: ownership, redaction, optional services. Never kill-by-port."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import zect_stack  # noqa: E402


def test_config_schema_and_dependency_order():
    cfg = zect_stack.load_config()
    assert "core" in cfg["profiles"]
    assert cfg["services"]["backend"]["port"] == 8020
    assert cfg["services"]["frontend"]["port"] == 5173
    assert "8000" not in str(cfg["services"]["backend"])
    core = zect_stack.profile_order(cfg, "core")
    assert core == ["backend", "frontend"]
    desktop = zect_stack.profile_order(cfg, "desktop")
    assert desktop.index("backend") < desktop.index("electron")
    assert desktop.index("frontend") < desktop.index("electron")


def test_redact_secrets_never_echo_values():
    raw = "GITHUB_TOKEN=ghp_secretvalue OPENAI_API_KEY=sk-live PASSWORD=hunter2"
    out = zect_stack.redact(raw)
    assert "ghp_secretvalue" not in out
    assert "sk-live" not in out
    assert "hunter2" not in out
    assert "[redacted]" in out


def test_env_names_not_values(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("DATABASE_URL=sqlite:///./zect.db\nGITHUB_TOKEN=super-secret\n", encoding="utf-8")
    names = zect_stack._env_names_present(env, ["DATABASE_URL", "GITHUB_TOKEN", "OPENAI_API_KEY"])
    assert names["DATABASE_URL"] == "present"
    assert names["GITHUB_TOKEN"] == "present"
    assert names["OPENAI_API_KEY"] == "missing"
    assert "super-secret" not in json.dumps(names)


def test_unowned_port_is_error_and_does_not_kill(monkeypatch):
    cfg = zect_stack.load_config()
    state = {"profile": "core", "services": {}}
    killed: list[int] = []
    monkeypatch.setattr(zect_stack, "listening_pid", lambda port: 4242 if port == 8020 else None)
    monkeypatch.setattr(zect_stack, "pid_alive", lambda pid: pid == 4242)
    monkeypatch.setattr(zect_stack, "stop_owned_pid", lambda pid, timeout_s=8.0: killed.append(pid))

    def _no_start(*args, **kwargs):
        raise AssertionError("must not start over an unowned port")

    monkeypatch.setattr(zect_stack.subprocess, "Popen", _no_start)
    result = zect_stack.start_service(cfg, state, "backend")
    assert result["state"] == "ERROR"
    assert result["health"] == "unowned_port_occupied"
    assert killed == []


def test_stale_owned_pid_cleared(monkeypatch):
    cfg = zect_stack.load_config()
    state = {"profile": "core", "services": {"backend": {"pid": 1}}}
    monkeypatch.setattr(zect_stack, "pid_alive", lambda pid: False)
    monkeypatch.setattr(zect_stack, "listening_pid", lambda port: None)
    row = zect_stack.classify_service(cfg, state, "backend")
    assert row["state"] == "STALE"


def test_optional_presenton_unavailable(monkeypatch):
    cfg = zect_stack.load_config()
    state = {"profile": "full", "services": {}}
    monkeypatch.setattr(zect_stack, "listening_pid", lambda port: None)
    monkeypatch.setattr(zect_stack, "health_ok", lambda url, timeout=2.0: False)
    row = zect_stack.classify_service(cfg, state, "presenton")
    assert row["state"] == "OPTIONAL_UNAVAILABLE"
    assert row["required"] is False


def test_restart_one_service_does_not_stop_others(monkeypatch, tmp_path: Path):
    cfg = zect_stack.load_config()
    monkeypatch.setenv("ZECT_STACK_STATE_DIR", str(tmp_path))
    stopped: list[str] = []
    started: list[str] = []

    def _stop(cfg, state, name):
        stopped.append(name)
        return {"service": name, "state": "STOPPED", "pid": None, "port": None, "health": "stopped", "required": True}

    def _start(cfg, state, name, wait_s=45.0):
        started.append(name)
        return {"service": name, "state": "READY", "pid": 7, "port": 8020, "health": "ok", "required": True}

    monkeypatch.setattr(zect_stack, "load_config", lambda: cfg)
    monkeypatch.setattr(zect_stack, "load_state", lambda _cfg=None: {"profile": "desktop", "services": {"backend": {"pid": 1}, "frontend": {"pid": 2}}})
    monkeypatch.setattr(zect_stack, "stop_service", _stop)
    monkeypatch.setattr(zect_stack, "start_service", _start)
    rc = zect_stack.cmd_restart("backend")
    assert rc == 0
    assert stopped == ["backend"]
    assert started == ["backend"]
    assert "frontend" not in stopped
    assert "electron" not in started

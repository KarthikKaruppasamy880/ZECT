#!/usr/bin/env python3
"""ZECT local stack controller. Owns only PIDs it started. Never kill-by-port."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

STATES = (
    "STOPPED",
    "STARTING",
    "READY",
    "DEGRADED",
    "ERROR",
    "EXTERNAL",
    "OPTIONAL_UNAVAILABLE",
    "STALE",
)

SECRET_RE = re.compile(
    r"(?i)(token|secret|password|api[_-]?key|authorization|bearer)\s*[:=]\s*\S+"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def config_path() -> Path:
    override = os.environ.get("ZECT_STACK_CONFIG")
    if override:
        return Path(override)
    return repo_root() / "config" / "zect-stack.yaml"


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.is_file():
        raise FileNotFoundError(f"missing stack config: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML is required to load config/zect-stack.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or "services" not in data or "profiles" not in data:
        raise ValueError("zect-stack.yaml must define profiles and services")
    return data


def state_dir(cfg: dict[str, Any] | None = None) -> Path:
    override = os.environ.get("ZECT_STACK_STATE_DIR")
    if override:
        path = Path(override)
    else:
        rel = ((cfg or {}).get("state_dir") or ".zect/stack")
        path = repo_root() / str(rel)
    path.mkdir(parents=True, exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    return path


def state_file(cfg: dict[str, Any] | None = None) -> Path:
    return state_dir(cfg) / "owned.json"


def load_state(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    path = state_file(cfg)
    if not path.is_file():
        return {"profile": "", "services": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"profile": "", "services": {}}
    if not isinstance(data, dict):
        return {"profile": "", "services": {}}
    data.setdefault("profile", "")
    data.setdefault("services", {})
    return data


def save_state(state: dict[str, Any], cfg: dict[str, Any] | None = None) -> None:
    path = state_file(cfg)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def redact(text: str) -> str:
    return SECRET_RE.sub(lambda m: m.group(1) + "=[redacted]", text or "")


def find_powerpoint() -> str | None:
    """Office often installs POWERPNT.EXE without putting it on PATH."""
    found = shutil.which("powerpnt") or shutil.which("POWERPNT.EXE")
    if found:
        return found
    if os.name != "nt":
        return None
    home = Path.home()
    candidates = [
        Path(r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"),
        Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE"),
        Path(r"C:\Program Files\Microsoft Office\Office16\POWERPNT.EXE"),
        Path(r"C:\Program Files\Microsoft Office\Office15\POWERPNT.EXE"),
        home / r"AppData\Local\Microsoft\WindowsApps\powerpnt.exe",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def load_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=value lines. Never log values."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return out
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue
        out[key] = val.strip().strip('"').strip("'")
    return out


def ensure_frontend_vite_api_url(root: Path | None = None) -> Path:
    """Match scripts/start-local.ps1: Vite must call local API :8020, not CI :8000."""
    frontend = (root or repo_root()) / "frontend"
    env_local = frontend / ".env.local"
    env_local.write_text("VITE_API_URL=http://127.0.0.1:8020\n", encoding="utf-8")
    return env_local


def profile_order(cfg: dict[str, Any], profile: str) -> list[str]:
    names = list(cfg.get("profiles", {}).get(profile) or [])
    if not names:
        raise ValueError(f"unknown profile: {profile}")
    services = cfg.get("services") or {}
    ordered: list[str] = []
    remaining = list(names)
    guard = 0
    while remaining and guard < 50:
        guard += 1
        progressed = False
        for name in list(remaining):
            deps = list((services.get(name) or {}).get("depends_on") or [])
            if all(d in ordered or d not in names for d in deps):
                ordered.append(name)
                remaining.remove(name)
                progressed = True
        if not progressed:
            ordered.extend(remaining)
            break
    return ordered


def listening_pid(port: int | None) -> int | None:
    if not port:
        return None
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="ignore", timeout=8)
    except (OSError, subprocess.SubprocessError):
        return None
    want = str(int(port))
    for line in out.splitlines():
        if "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        addr = next((p for p in parts if ":" in p), "")
        if addr.rsplit(":", 1)[-1] != want:
            continue
        try:
            return int(parts[-1])
        except ValueError:
            continue
    return None


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {int(pid)}"],
                text=True,
                errors="ignore",
                timeout=8,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return str(pid) in out and "No tasks" not in out
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def port_connectable(port: int | None, host: str = "127.0.0.1") -> bool:
    if not port:
        return False
    try:
        with socket.create_connection((host, int(port)), timeout=0.4):
            return True
    except OSError:
        return False


def health_ok(url: str | None, timeout: float = 2.0) -> bool:
    if not url:
        return False
    try:
        with urlopen(url, timeout=timeout) as resp:  # noqa: S310 — local health only
            return 200 <= int(getattr(resp, "status", 200)) < 500
    except (URLError, OSError, TimeoutError, ValueError):
        return False


def resolve_python() -> list[str]:
    for argv in (["py", "-3.12"], ["py", "-3"], ["python"]):
        try:
            subprocess.check_call(
                argv + ["-c", "import sys"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            return argv
        except (OSError, subprocess.SubprocessError):
            continue
    return ["python"]


def expand_argv(argv: list[str], root: Path) -> list[str]:
    python = resolve_python()
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    mapping = {
        "{python}": python,
        "{backend}": [str(root / "backend")],
        "{root}": [str(root)],
        "npm": [npm],
    }
    py = " ".join(python)
    out: list[str] = []
    for part in argv:
        if part in mapping:
            out.extend(mapping[part])
        else:
            out.append(part.replace("{python}", py).replace("{backend}", str(root / "backend")))
    return out


def owned_pid(state: dict[str, Any], name: str) -> int | None:
    row = (state.get("services") or {}).get(name) or {}
    try:
        pid = int(row.get("pid") or 0)
    except (TypeError, ValueError):
        return None
    return pid or None


def stop_owned_pid(pid: int, timeout_s: float = 8.0) -> None:
    if not pid_alive(pid):
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        deadline = time.time() + timeout_s
        while time.time() < deadline and pid_alive(pid):
            time.sleep(0.25)
        if pid_alive(pid):
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid), "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        return
    try:
        os.kill(pid, 15)
    except OSError:
        return
    deadline = time.time() + timeout_s
    while time.time() < deadline and pid_alive(pid):
        time.sleep(0.25)
    if pid_alive(pid):
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def service_row(cfg: dict[str, Any], name: str) -> dict[str, Any]:
    row = (cfg.get("services") or {}).get(name)
    if not row:
        raise ValueError(f"unknown service: {name}")
    return row


def classify_service(
    cfg: dict[str, Any],
    state: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    row = service_row(cfg, name)
    port = row.get("port")
    required = bool(row.get("required", True))
    argv = list(row.get("argv") or [])
    health_url = row.get("health_url")
    owned = owned_pid(state, name)
    listen = listening_pid(int(port)) if port else None
    if owned and not pid_alive(owned):
        return {
            "service": name,
            "state": "STALE",
            "pid": owned,
            "port": port,
            "health": "stale_pid",
            "required": required,
        }
    if owned and pid_alive(owned):
        healthy = True
        if health_url:
            healthy = health_ok(str(health_url))
        elif port:
            healthy = port_connectable(int(port))
        return {
            "service": name,
            "state": "READY" if healthy else "DEGRADED",
            "pid": owned,
            "port": port,
            "health": "ok" if healthy else "failed",
            "required": required,
        }
    if listen and pid_alive(listen):
        return {
            "service": name,
            "state": "EXTERNAL",
            "pid": listen,
            "port": port,
            "health": "unowned_port",
            "required": required,
        }
    if not argv and not required:
        healthy = health_ok(str(health_url)) if health_url else False
        return {
            "service": name,
            "state": "READY" if healthy else "OPTIONAL_UNAVAILABLE",
            "pid": None,
            "port": port,
            "health": "ok" if healthy else "optional_unavailable",
            "required": required,
        }
    return {
        "service": name,
        "state": "STOPPED",
        "pid": None,
        "port": port,
        "health": "stopped",
        "required": required,
    }


def start_service(
    cfg: dict[str, Any],
    state: dict[str, Any],
    name: str,
    *,
    wait_s: float = 45.0,
) -> dict[str, Any]:
    row = service_row(cfg, name)
    classified = classify_service(cfg, state, name)
    if classified["state"] == "READY":
        return classified
    if classified["state"] == "EXTERNAL":
        classified["state"] = "ERROR"
        classified["health"] = "unowned_port_occupied"
        return classified
    if classified["state"] == "STALE":
        services = state.setdefault("services", {})
        services.pop(name, None)
        save_state(state, cfg)
    argv = list(row.get("argv") or [])
    required = bool(row.get("required", True))
    if not argv:
        classified = classify_service(cfg, state, name)
        if classified["state"] == "OPTIONAL_UNAVAILABLE" and not required:
            return classified
        classified["state"] = "ERROR" if required else "OPTIONAL_UNAVAILABLE"
        return classified
    root = repo_root()
    cwd = root / str(row.get("cwd") or ".")
    log_path = state_dir(cfg) / "logs" / f"{name}.log"
    env = os.environ.copy()
    extra = row.get("env") or {}
    if isinstance(extra, dict):
        env.update({str(k): str(v) for k, v in extra.items()})
    if name == "backend":
        for key, val in load_env_file(root / "backend" / ".env").items():
            env.setdefault(key, val)
    if name == "frontend":
        ensure_frontend_vite_api_url(root)
    cmd = expand_argv(argv, root)
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    with log_path.open("a", encoding="utf-8") as log:
        log.write(redact(f"\n# start {name} {' '.join(cmd)}\n"))
        log.flush()
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            cwd=str(cwd),
            stdout=log,
            stderr=log,
            env=env,
            creationflags=flags,
        )
    state.setdefault("services", {})[name] = {"pid": proc.pid, "argv": cmd}
    save_state(state, cfg)
    deadline = time.time() + wait_s
    health_url = row.get("health_url")
    port = row.get("port")
    while time.time() < deadline:
        if proc.poll() is not None:
            return {
                "service": name,
                "state": "ERROR",
                "pid": proc.pid,
                "port": port,
                "health": "exited",
                "required": required,
            }
        if health_url and health_ok(str(health_url)):
            break
        if not health_url and (not port or port_connectable(int(port)) or name == "electron"):
            if name != "electron" or pid_alive(proc.pid):
                break
        time.sleep(0.4)
    classified = classify_service(cfg, state, name)
    if classified["state"] not in {"READY", "DEGRADED"} and required:
        classified["state"] = "ERROR"
    return classified


def stop_service(cfg: dict[str, Any], state: dict[str, Any], name: str) -> dict[str, Any]:
    owned = owned_pid(state, name)
    if owned:
        stop_owned_pid(owned)
    services = state.setdefault("services", {})
    services.pop(name, None)
    save_state(state, cfg)
    return classify_service(cfg, state, name)


def cmd_up(profile: str = "desktop") -> int:
    cfg = load_config()
    state = load_state(cfg)
    order = profile_order(cfg, profile)
    state["profile"] = profile
    save_state(state, cfg)
    print(f"profile={profile}")
    failed = False
    for name in order:
        row = service_row(cfg, name)
        for dep in row.get("depends_on") or []:
            dep_state = classify_service(cfg, state, dep)
            if dep_state["state"] not in {"READY", "DEGRADED"} and bool(
                (cfg["services"].get(dep) or {}).get("required", True)
            ):
                print(f"{name}\tERROR\tdependency {dep}={dep_state['state']}")
                failed = True
                break
        else:
            result = start_service(cfg, state, name)
            print(_fmt(result))
            if result["state"] in {"ERROR", "EXTERNAL"} and result.get("required"):
                failed = True
                break
    return 1 if failed else 0


def cmd_down() -> int:
    cfg = load_config()
    state = load_state(cfg)
    names = list(reversed(list((state.get("services") or {}).keys())))
    if not names and state.get("profile"):
        names = list(reversed(profile_order(cfg, str(state["profile"]))))
    for name in names:
        result = stop_service(cfg, state, name)
        print(_fmt(result))
    state["services"] = {}
    save_state(state, cfg)
    return 0


def cmd_restart(service: str | None = None) -> int:
    cfg = load_config()
    state = load_state(cfg)
    profile = str(state.get("profile") or "desktop")
    if service:
        stop_service(cfg, state, service)
        result = start_service(cfg, state, service)
        print(_fmt(result))
        return 0 if result["state"] in {"READY", "DEGRADED", "OPTIONAL_UNAVAILABLE"} else 1
    rc = cmd_down()
    if rc:
        return rc
    return cmd_up(profile)


def cmd_status(profile: str | None = None) -> int:
    cfg = load_config()
    state = load_state(cfg)
    names = profile_order(cfg, profile or state.get("profile") or "desktop")
    print("service\tstate\tpid\tport\thealth")
    worst = 0
    for name in names:
        row = classify_service(cfg, state, name)
        print(_fmt(row))
        if row["state"] in {"ERROR", "EXTERNAL"} and row.get("required"):
            worst = 1
    return worst


def cmd_health() -> int:
    return cmd_status()


def cmd_logs(service: str | None = None, lines: int = 80) -> int:
    cfg = load_config()
    log_dir = state_dir(cfg) / "logs"
    names = [service] if service else sorted(p.stem for p in log_dir.glob("*.log"))
    for name in names:
        path = log_dir / f"{name}.log"
        print(f"===== {name} =====")
        if not path.is_file():
            print("(no log)")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:]
        print(redact("\n".join(text)))
    return 0


def _env_names_present(env_file: Path, names: list[str]) -> dict[str, str]:
    present: set[str] = set()
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if val.strip().strip('"').strip("'"):
                present.add(key.strip())
    return {name: ("present" if name in present else "missing") for name in names}


def cmd_doctor() -> int:
    cfg = load_config()
    print("python", sys.version.split()[0], "ok" if sys.version_info >= (3, 11) else "old")
    print("node", shutil.which("node") or "missing")
    print("npm", shutil.which("npm") or "missing")
    doctor = cfg.get("doctor") or {}
    env_file = repo_root() / "backend" / ".env"
    required = list(doctor.get("required_env_names") or [])
    optional = list(doctor.get("optional_env_names") or [])
    for name, status in _env_names_present(env_file, required + optional).items():
        kind = "required" if name in required else "optional"
        print(f"env {kind} {name} {status}")
    db_status = _env_names_present(env_file, ["DATABASE_URL"]).get("DATABASE_URL", "missing")
    print("database_url_name", db_status)
    print("electron_dir", "ok" if (repo_root() / "electron" / "package.json").is_file() else "missing")
    ppt = find_powerpoint()
    print("powerpoint", "present" if ppt else "OPTIONAL_UNAVAILABLE")
    print("github_token_name", _env_names_present(env_file, ["GITHUB_TOKEN"]).get("GITHUB_TOKEN"))
    print("git_repo", "ok" if (repo_root() / ".git").exists() else "missing")
    for name in ("presenton", "voicebox"):
        row = classify_service(cfg, load_state(cfg), name)
        print(name, row["state"])
    cmd_status()
    return 0


def _fmt(row: dict[str, Any]) -> str:
    return "\t".join(
        str(x if x is not None else "")
        for x in (row.get("service"), row.get("state"), row.get("pid"), row.get("port"), row.get("health"))
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zect", description="ZECT local stack controller")
    parser.add_argument("command", choices=["up", "down", "restart", "status", "health", "logs", "doctor"])
    parser.add_argument("service", nargs="?", default=None)
    parser.add_argument("--profile", default="desktop", choices=["core", "desktop", "full"])
    args = parser.parse_args(argv)
    if args.command == "up":
        return cmd_up(args.profile)
    if args.command == "down":
        return cmd_down()
    if args.command == "restart":
        return cmd_restart(args.service)
    if args.command == "status":
        return cmd_status(None)
    if args.command == "health":
        return cmd_health()
    if args.command == "logs":
        return cmd_logs(args.service)
    if args.command == "doctor":
        return cmd_doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

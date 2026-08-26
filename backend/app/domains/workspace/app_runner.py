"""App Runner — execute shell commands, manage long-running processes, and
stream output so users can configure, run, and test repos directly inside ZECT."""

import asyncio
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.allowed_paths import path_under_allowed_roots
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import log_audit, require_role
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/runner", tags=["app-runner"])


def _validate_cwd(raw: Optional[str], bound_root: Optional[str] = None) -> str:
    """Resolve and enforce the same filesystem allowlist git_ops.py and
    file_explorer.py already use — previously this only checked the
    directory existed, so an arbitrary-shell-command endpoint could also
    target any directory on the host, not just the workspace root.

    When bound_root is set (per-root terminal), cwd must stay inside that root
    after symlink resolve.
    """
    candidate = raw or bound_root or os.path.expanduser("~")
    try:
        p = path_under_allowed_roots(candidate)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    if not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {candidate}")
    if bound_root:
        try:
            root = path_under_allowed_roots(bound_root)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        try:
            p.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="cwd_outside_bound_root") from exc
    return str(p)


def _reject_command_escape(command: str, bound_root: Optional[str]) -> None:
    if not bound_root:
        return
    if ".." in command:
        raise HTTPException(status_code=403, detail="path_escape")

_IS_WINDOWS = sys.platform.startswith("win")


def _popen_kwargs() -> dict:
    """Platform-safe Popen flags. ``os.setsid`` / ``killpg`` are Unix-only and
    crash App Runner Start/Configure on Windows."""
    if _IS_WINDOWS:
        # CREATE_NEW_PROCESS_GROUP = 0x00000200 — allows Ctrl-Break terminate
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    setsid = getattr(os, "setsid", None)
    return {"preexec_fn": setsid} if callable(setsid) else {}


def _stop_process_tree(proc: subprocess.Popen, pid: int) -> None:
    if not proc or proc.poll() is not None:
        return
    if _IS_WINDOWS:
        try:
            # Kill the whole tree (npm/node children included)
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# In-memory store for running processes
# ---------------------------------------------------------------------------

class ProcessInfo:
    """Tracks a subprocess started by the runner."""

    def __init__(self, pid: int, proc: subprocess.Popen, label: str, cwd: str, cmd: str):
        self.id = str(uuid.uuid4())[:8]
        self.pid = pid
        self.proc = proc
        self.label = label
        self.cwd = cwd
        self.cmd = cmd
        self.started_at = time.time()
        self.output_lines: list[str] = []
        self.max_lines = 5000  # rolling buffer

    def append_output(self, line: str):
        self.output_lines.append(line)
        if len(self.output_lines) > self.max_lines:
            self.output_lines = self.output_lines[-self.max_lines:]

    @property
    def is_running(self) -> bool:
        return self.proc.poll() is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pid": self.pid,
            "label": self.label,
            "cmd": self.cmd,
            "cwd": self.cwd,
            "running": self.is_running,
            "exit_code": self.proc.returncode,
            "started_at": self.started_at,
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "output_lines": len(self.output_lines),
        }


_processes: Dict[str, ProcessInfo] = {}
_bg_tasks: Dict[str, asyncio.Task] = {}
_bg_threads: Dict[str, threading.Thread] = {}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    bound_root: Optional[str] = None
    timeout: int = 30  # seconds


class StartRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    bound_root: Optional[str] = None
    label: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None


class ConfigureRequest(BaseModel):
    repo_path: str
    env_vars: Optional[Dict[str, str]] = None
    startup_command: Optional[str] = None
    install_command: Optional[str] = None
    preview_port: Optional[int] = None


# ---------------------------------------------------------------------------
# Background reader — reads stdout/stderr and stores in ProcessInfo
# ---------------------------------------------------------------------------

async def _read_process_output(proc_info: ProcessInfo):
    """Read stdout+stderr line by line in background."""
    proc = proc_info.proc
    try:
        while proc.poll() is None:
            if proc.stdout:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, proc.stdout.readline
                )
                if line:
                    proc_info.append_output(line.rstrip("\n"))
            else:
                await asyncio.sleep(0.1)
        # Drain remaining
        if proc.stdout:
            for line in proc.stdout.readlines():
                proc_info.append_output(line.rstrip("\n"))
        if proc.stderr:
            for line in proc.stderr.readlines():
                proc_info.append_output("[stderr] " + line.rstrip("\n"))
    except Exception as e:
        proc_info.append_output(f"[reader error] {e}")


def _read_process_output_sync(proc_info: ProcessInfo) -> None:
    """Thread-based twin of ``_read_process_output`` for callers with no
    running event loop (the Mentrix Coding Agent tool loop is plain sync).
    Daemon thread — exits on its own once the process ends, nothing to cancel."""
    proc = proc_info.proc
    try:
        if proc.stdout:
            for line in proc.stdout:
                proc_info.append_output(line.rstrip("\n"))
    except Exception as e:
        proc_info.append_output(f"[reader error] {e}")


def spawn_owned_process(
    command: str, cwd: str, label: str = "", env_vars: Optional[Dict[str, str]] = None
) -> ProcessInfo:
    """Start a tracked, owned process — the one real implementation shared by
    the /start and /configure routes and the Mentrix Coding Agent's start_app
    tool. Registers a thread-based output reader so it works from both async
    route handlers and the agent's plain-sync tool loop."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    proc = subprocess.Popen(
        command,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        **_popen_kwargs(),
    )
    info = ProcessInfo(pid=proc.pid, proc=proc, label=label or command[:40], cwd=cwd, cmd=command)
    _processes[info.id] = info
    thread = threading.Thread(target=_read_process_output_sync, args=(info,), daemon=True)
    thread.start()
    _bg_threads[info.id] = thread
    return info


def _owns_workspace(info: ProcessInfo, workspace: str) -> bool:
    try:
        return Path(info.cwd).resolve() == Path(workspace).resolve()
    except OSError:
        return info.cwd == workspace


def list_owned_processes_in_workspace(workspace: str) -> list[dict]:
    """Never returns a process outside this exact workspace -- the safety
    boundary the Mentrix Coding Agent's process tools rely on so they can
    never see or touch a port/process they didn't start themselves."""
    return [info.to_dict() for info in _processes.values() if _owns_workspace(info, workspace)]


def stop_owned_processes_in_workspace(workspace: str) -> int:
    """Stop only processes started in this exact workspace. Returns count stopped."""
    stopped = 0
    for process_id, info in list(_processes.items()):
        if not _owns_workspace(info, workspace):
            continue
        try:
            if info.is_running:
                _stop_process_tree(info.proc, info.pid)
                stopped += 1
        except Exception:
            continue
        _bg_tasks.pop(process_id, None)
        _bg_threads.pop(process_id, None)
    return stopped


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/execute")
@require_role("admin")
async def execute_command(
    req: ExecuteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run a one-shot command and return the full output (blocking, with timeout).

    Runs an arbitrary shell command as the backend process user — admin-only
    and confined to the same workspace allowlist as Git Ops/File Explorer.
    """
    from app.security.emergency_stop import require_not_emergency_stopped

    require_not_emergency_stopped(db)
    _reject_command_escape(req.command, req.bound_root)
    cwd = _validate_cwd(req.cwd, req.bound_root)
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="runner_execute",
        resource_type="app_runner",
        details={"command": req.command[:300], "cwd": cwd},
    )

    try:
        result = subprocess.run(
            req.command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=req.timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": req.command,
            "cwd": cwd,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {req.timeout}s",
            "command": req.command,
            "cwd": cwd,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/start")
@require_role("admin")
async def start_process(
    req: StartRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a long-running process (e.g. dev server) in background. Admin-only,
    confined to the same workspace allowlist as Git Ops/File Explorer."""
    from app.security.emergency_stop import require_not_emergency_stopped

    require_not_emergency_stopped(db)
    _reject_command_escape(req.command, req.bound_root)
    cwd = _validate_cwd(req.cwd, req.bound_root)
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="runner_start",
        resource_type="app_runner",
        details={"command": req.command[:300], "cwd": cwd, "label": req.label or ""},
    )

    try:
        info = spawn_owned_process(req.command, cwd, label=req.label or "", env_vars=req.env_vars)
    except Exception as e:
        raise HTTPException(500, f"Failed to start process: {e}")

    return {
        "id": info.id,
        "pid": info.pid,
        "label": info.label,
        "message": f"Process started: {info.label}",
    }


@router.post("/stop/{process_id}")
async def stop_process(process_id: str):
    """Stop a running process by its ID."""
    info = _processes.get(process_id)
    if not info:
        raise HTTPException(404, f"Process {process_id} not found")

    if info.is_running:
        _stop_process_tree(info.proc, info.pid)

    # Cancel bg reader (asyncio task or daemon thread -- thread exits on its
    # own once the process dies, nothing to cancel there)
    task = _bg_tasks.pop(process_id, None)
    if task:
        task.cancel()
    _bg_threads.pop(process_id, None)

    return {
        "id": process_id,
        "stopped": True,
        "exit_code": info.proc.returncode,
    }


def stop_all_processes() -> int:
    """Stop every tracked App Runner process (emergency stop). Returns count stopped."""
    stopped = 0
    for process_id, info in list(_processes.items()):
        try:
            if info.is_running:
                _stop_process_tree(info.proc, info.pid)
                stopped += 1
            task = _bg_tasks.pop(process_id, None)
            if task:
                task.cancel()
            _bg_threads.pop(process_id, None)
        except Exception:
            continue
    return stopped


@router.get("/processes")
async def list_processes():
    """List all tracked processes."""
    return [info.to_dict() for info in _processes.values()]


@router.get("/output/{process_id}")
async def get_output(process_id: str, offset: int = 0, limit: int = 200):
    """Get output lines from a process."""
    info = _processes.get(process_id)
    if not info:
        raise HTTPException(404, f"Process {process_id} not found")

    lines = info.output_lines[offset:offset + limit]
    return {
        "id": process_id,
        "running": info.is_running,
        "exit_code": info.proc.returncode,
        "total_lines": len(info.output_lines),
        "offset": offset,
        "lines": lines,
    }


@router.delete("/processes/{process_id}")
async def remove_process(process_id: str):
    """Remove a stopped process from the list."""
    info = _processes.get(process_id)
    if not info:
        raise HTTPException(404, f"Process {process_id} not found")

    if info.is_running:
        raise HTTPException(400, "Process is still running. Stop it first.")

    _processes.pop(process_id, None)
    _bg_tasks.pop(process_id, None)
    return {"removed": True}


@router.post("/configure")
@require_role("admin")
async def configure_project(
    req: ConfigureRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Configure a project: validate path, optionally install deps, set env vars,
    and start the dev server. Admin-only, confined to the workspace allowlist."""
    repo_path = _validate_cwd(req.repo_path)
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="runner_configure",
        resource_type="app_runner",
        details={
            "repo_path": repo_path,
            "install_command": (req.install_command or "")[:300],
            "startup_command": (req.startup_command or "")[:300],
        },
    )

    results = {"repo_path": repo_path, "steps": []}

    # 1. Install deps if requested
    if req.install_command:
        install = subprocess.run(
            req.install_command,
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        results["steps"].append({
            "step": "install",
            "command": req.install_command,
            "exit_code": install.returncode,
            "stdout": install.stdout[-2000:] if install.stdout else "",
            "stderr": install.stderr[-2000:] if install.stderr else "",
        })

    # 2. Start dev server if requested
    if req.startup_command:
        label = f"Dev Server ({os.path.basename(repo_path)})"
        info = spawn_owned_process(req.startup_command, repo_path, label=label, env_vars=req.env_vars)

        results["steps"].append({
            "step": "start",
            "command": req.startup_command,
            "process_id": info.id,
            "pid": info.pid,
        })
        results["process_id"] = info.id

    if req.preview_port:
        results["preview_url"] = f"http://localhost:{req.preview_port}"

    return results

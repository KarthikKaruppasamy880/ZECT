"""App Runner — execute shell commands, manage long-running processes, and
stream output so users can configure, run, and test repos directly inside ZECT."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import time
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/runner", tags=["app-runner"])

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

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    timeout: int = 30  # seconds


class StartRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/execute")
async def execute_command(req: ExecuteRequest):
    """Run a one-shot command and return the full output (blocking, with timeout)."""
    cwd = req.cwd or os.path.expanduser("~")
    if not os.path.isdir(cwd):
        raise HTTPException(400, f"Directory not found: {cwd}")

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
async def start_process(req: StartRequest):
    """Start a long-running process (e.g. dev server) in background."""
    cwd = req.cwd or os.path.expanduser("~")
    if not os.path.isdir(cwd):
        raise HTTPException(400, f"Directory not found: {cwd}")

    env = os.environ.copy()
    if req.env_vars:
        env.update(req.env_vars)

    try:
        proc = subprocess.Popen(
            req.command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            preexec_fn=os.setsid,
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to start process: {e}")

    label = req.label or req.command[:40]
    info = ProcessInfo(pid=proc.pid, proc=proc, label=label, cwd=cwd, cmd=req.command)
    _processes[info.id] = info

    # Start background reader
    task = asyncio.create_task(_read_process_output(info))
    _bg_tasks[info.id] = task

    return {
        "id": info.id,
        "pid": proc.pid,
        "label": label,
        "message": f"Process started: {label}",
    }


@router.post("/stop/{process_id}")
async def stop_process(process_id: str):
    """Stop a running process by its ID."""
    info = _processes.get(process_id)
    if not info:
        raise HTTPException(404, f"Process {process_id} not found")

    if info.is_running:
        try:
            os.killpg(os.getpgid(info.pid), signal.SIGTERM)
            info.proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(info.pid), signal.SIGKILL)
            except Exception:
                pass

    # Cancel bg task
    task = _bg_tasks.pop(process_id, None)
    if task:
        task.cancel()

    return {
        "id": process_id,
        "stopped": True,
        "exit_code": info.proc.returncode,
    }


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
async def configure_project(req: ConfigureRequest):
    """Configure a project: validate path, optionally install deps, set env vars,
    and start the dev server."""
    if not os.path.isdir(req.repo_path):
        raise HTTPException(400, f"Repo path not found: {req.repo_path}")

    results = {"repo_path": req.repo_path, "steps": []}

    # 1. Install deps if requested
    if req.install_command:
        install = subprocess.run(
            req.install_command,
            shell=True,
            cwd=req.repo_path,
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
        env = os.environ.copy()
        if req.env_vars:
            env.update(req.env_vars)

        proc = subprocess.Popen(
            req.startup_command,
            shell=True,
            cwd=req.repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            preexec_fn=os.setsid,
        )
        label = f"Dev Server ({os.path.basename(req.repo_path)})"
        info = ProcessInfo(pid=proc.pid, proc=proc, label=label, cwd=req.repo_path, cmd=req.startup_command)
        _processes[info.id] = info
        task = asyncio.create_task(_read_process_output(info))
        _bg_tasks[info.id] = task

        results["steps"].append({
            "step": "start",
            "command": req.startup_command,
            "process_id": info.id,
            "pid": proc.pid,
        })
        results["process_id"] = info.id

    if req.preview_port:
        results["preview_url"] = f"http://localhost:{req.preview_port}"

    return results

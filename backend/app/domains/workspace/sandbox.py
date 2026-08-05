"""Sandboxed Execution — run untrusted code in isolated environments.

Provides Docker-based sandbox for safe code execution, with resource
limits, timeout controls, and output capture.
"""

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

SANDBOX_DIR = Path(os.getenv("ZECT_SANDBOX_DIR", "/tmp/zect-sandboxes"))
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

MAX_TIMEOUT = 120
MAX_OUTPUT = 50000


class SandboxRunRequest(BaseModel):
    code: str
    language: str  # python, node, bash, ruby, go
    timeout: int = 30
    stdin: str = ""
    files: dict[str, str] | None = None  # filename -> content


class SandboxDockerRequest(BaseModel):
    image: str = "python:3.11-slim"
    command: str = "python main.py"
    files: dict[str, str] = {}  # filename -> content
    timeout: int = 30
    memory_limit: str = "256m"
    cpu_limit: str = "0.5"
    network: bool = False


# Language configurations for local sandbox
LANG_CONFIG = {
    "python": {"ext": ".py", "cmd": "python3", "image": "python:3.11-slim"},
    "node": {"ext": ".js", "cmd": "node", "image": "node:20-slim"},
    "bash": {"ext": ".sh", "cmd": "bash", "image": "ubuntu:22.04"},
    "ruby": {"ext": ".rb", "cmd": "ruby", "image": "ruby:3.2-slim"},
    "go": {"ext": ".go", "cmd": "go run", "image": "golang:1.21-alpine"},
}


def _run_local_sandbox(code: str, language: str, timeout: int, stdin: str, extra_files: dict[str, str] | None) -> dict:
    """Run code in a local subprocess sandbox with resource limits."""
    config = LANG_CONFIG.get(language)
    if not config:
        return {"success": False, "stdout": "", "stderr": f"Unsupported language: {language}", "exit_code": -1}

    sandbox_id = str(uuid.uuid4())[:8]
    sandbox_path = SANDBOX_DIR / sandbox_id
    sandbox_path.mkdir(parents=True, exist_ok=True)

    try:
        main_file = sandbox_path / f"main{config['ext']}"
        main_file.write_text(code)

        if extra_files:
            for fname, fcontent in extra_files.items():
                safe_name = Path(fname).name
                (sandbox_path / safe_name).write_text(fcontent)

        cmd = f"{config['cmd']} main{config['ext']}"
        effective_timeout = min(timeout, MAX_TIMEOUT)

        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(sandbox_path),
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            input=stdin or None,
            env={**os.environ, "HOME": str(sandbox_path), "TMPDIR": str(sandbox_path)},
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:MAX_OUTPUT],
            "stderr": result.stderr[:MAX_OUTPUT],
            "exit_code": result.returncode,
            "sandbox_id": sandbox_id,
            # No container isolation here — plain host subprocess with only a
            # scratch cwd/HOME/TMPDIR. Callers (e.g. pr_readiness) must not
            # treat this as equivalent to a docker-isolated pass without
            # surfacing that distinction.
            "mode": "local_unsandboxed",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "exit_code": -1,
            "sandbox_id": sandbox_id,
            "mode": "local_unsandboxed",
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "sandbox_id": sandbox_id,
            "mode": "local_unsandboxed",
        }
    finally:
        shutil.rmtree(sandbox_path, ignore_errors=True)


def _run_docker_sandbox(req: SandboxDockerRequest) -> dict:
    """Run code in a Docker container with resource limits."""
    docker_available = shutil.which("docker") is not None
    if not docker_available:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Docker is not available. Falling back to local sandbox.",
            "exit_code": -1,
            "mode": "docker_unavailable",
        }

    sandbox_id = str(uuid.uuid4())[:8]
    sandbox_path = SANDBOX_DIR / sandbox_id
    sandbox_path.mkdir(parents=True, exist_ok=True)

    try:
        for fname, fcontent in req.files.items():
            safe_name = Path(fname).name
            (sandbox_path / safe_name).write_text(fcontent)

        effective_timeout = min(req.timeout, MAX_TIMEOUT)

        # Argument list, not a shell string — req.image/req.command/
        # req.memory_limit/req.cpu_limit previously got concatenated into a
        # shell=True string, so shell metacharacters in any of those fields
        # executed on the HOST shell before docker even started, defeating
        # the container isolation this endpoint exists to provide. req.command
        # itself is still interpreted by a shell, but that's the container's
        # own /bin/sh, confined by the same --network/--memory/--cpus/--user
        # limits as everything else run inside it.
        args = ["docker", "run", "--rm", f"--memory={req.memory_limit}", f"--cpus={req.cpu_limit}"]
        if not req.network:
            args.append("--network=none")
        args += [
            "-v", f"{sandbox_path}:/workspace",
            "-w", "/workspace",
            "--user", "1000:1000",
            req.image,
            "sh", "-c", req.command,
        ]

        result = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=effective_timeout + 10,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:MAX_OUTPUT],
            "stderr": result.stderr[:MAX_OUTPUT],
            "exit_code": result.returncode,
            "sandbox_id": sandbox_id,
            "mode": "docker",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Docker execution timed out after {req.timeout}s",
            "exit_code": -1,
            "sandbox_id": sandbox_id,
            "mode": "docker",
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "sandbox_id": sandbox_id,
            "mode": "docker",
        }
    finally:
        shutil.rmtree(sandbox_path, ignore_errors=True)


@router.post("/run")
def run_sandboxed(req: SandboxRunRequest):
    """Run code in a local sandbox with resource limits."""
    return _run_local_sandbox(req.code, req.language, req.timeout, req.stdin, req.files)


@router.post("/docker")
def run_docker_sandboxed(req: SandboxDockerRequest):
    """Run code in a Docker container with strict isolation."""
    return _run_docker_sandbox(req)


@router.get("/languages")
def supported_languages():
    """List supported sandbox languages."""
    return {
        lang: {"extension": cfg["ext"], "command": cfg["cmd"], "docker_image": cfg["image"]}
        for lang, cfg in LANG_CONFIG.items()
    }


@router.get("/status")
def sandbox_status():
    """Check sandbox system status."""
    docker_available = shutil.which("docker") is not None
    return {
        "local_sandbox": True,
        "docker_available": docker_available,
        "sandbox_dir": str(SANDBOX_DIR),
        "max_timeout": MAX_TIMEOUT,
        "supported_languages": list(LANG_CONFIG.keys()),
    }


class PRReadinessRequest(BaseModel):
    code: str = ""
    language: str = "python"
    quality_score: int = 100
    critical_findings: int = 0
    acknowledge_issues: bool = False
    prefer_docker: bool = True


@router.post("/pr-readiness")
def pr_readiness(req: PRReadinessRequest):
    """Hard gate before PR: sandbox + review severity policy."""
    blockers: list[str] = []
    sandbox_result = None
    if req.code.strip():
        if req.prefer_docker and shutil.which("docker"):
            sandbox_result = _run_docker_sandbox(
                SandboxDockerRequest(
                    image=LANG_CONFIG.get(req.language, {}).get("image", "python:3.11-slim"),
                    command=f"{LANG_CONFIG.get(req.language, {}).get('cmd', 'python3')} main{LANG_CONFIG.get(req.language, {}).get('ext', '.py')}",
                    files={f"main{LANG_CONFIG.get(req.language, {}).get('ext', '.py')}": req.code},
                )
            )
        else:
            sandbox_result = _run_local_sandbox(req.code, req.language, 30, "", None)
        if not sandbox_result.get("success"):
            blockers.append("Sandbox execution failed")
    if req.critical_findings > 0 and not req.acknowledge_issues:
        blockers.append(f"{req.critical_findings} critical review finding(s) require acknowledge_issues=true")
    if req.quality_score < 60 and not req.acknowledge_issues:
        blockers.append(f"Quality score {req.quality_score} below threshold 60")
    return {
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "sandbox": sandbox_result,
        "create_pr_hard_blocked": len(blockers) > 0,
        # Surfaced explicitly — a passing local_unsandboxed run is not the
        # same guarantee as a passing docker-isolated one.
        "docker_isolated": bool(sandbox_result and sandbox_result.get("mode") == "docker"),
    }

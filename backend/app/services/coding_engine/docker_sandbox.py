"""Optional Docker bind-mount sandbox for coding-engine workspaces (Stage D).

Creates a short-lived container that mounts the provisioned worktree read-write
at /workspace with a restricted environment. If Docker is unavailable, callers
must fall back to worktree-only isolation.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.services.coding_engine.isolation import (
    docker_available,
    restricted_sandbox_env,
    sandbox_image,
)
from app.services.coding_engine.workspace import WorkspaceError


@dataclass
class DockerSandbox:
    container_id: str
    image: str
    mount_path: str  # host path mounted at /workspace


def start_workspace_sandbox(*, host_workspace: str, run_id: str) -> DockerSandbox:
    """Start a long-lived sleep container with the workspace bind-mounted."""
    if not docker_available():
        raise WorkspaceError("Docker is not available on this host")
    host = Path(host_workspace).resolve()
    if not host.is_dir():
        raise WorkspaceError(f"Workspace path does not exist: {host}")

    image = sandbox_image()
    env = restricted_sandbox_env({"ZECT_RUN_ID": run_id})
    cmd = [
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        f"zect-engine-{run_id}"[:63],
        "-v",
        f"{host}:/workspace",
        "-w",
        "/workspace",
        "--network",
        "none",
    ]
    for k, v in env.items():
        cmd.extend(["-e", f"{k}={v}"])
    cmd.extend([image, "sleep", "infinity"])

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    if proc.returncode != 0:
        raise WorkspaceError(
            f"docker run failed: {(proc.stderr or proc.stdout or '').strip()[:400]}"
        )
    cid = (proc.stdout or "").strip()
    if not cid:
        raise WorkspaceError("docker run returned empty container id")
    return DockerSandbox(container_id=cid, image=image, mount_path=str(host))


def stop_workspace_sandbox(container_id: str) -> bool:
    """Stop (and --rm remove) a sandbox container. Best-effort."""
    if not container_id:
        return False
    try:
        proc = subprocess.run(
            ["docker", "stop", "-t", "2", container_id],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        return proc.returncode == 0
    except Exception:
        return False

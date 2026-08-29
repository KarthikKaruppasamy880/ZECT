"""Coding-engine isolation mode selection (Phase 2 Stage D).

Modes (ZECT_CODING_ENGINE_ISOLATION):
  worktree — git worktree only (default; works without Docker)
  docker   — prefer Docker bind-mount sandbox; fall back to worktree if Docker
             is unavailable unless ZECT_CODING_ENGINE_ISOLATION_STRICT=1
  auto     — docker when available, else worktree

Docker is optional. Hosts without Docker (common on locked-down Windows) stay
on worktree isolation.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


# Pinned default image for documented remote/sandbox runs (override via env).
DEFAULT_SANDBOX_IMAGE = "python:3.12-slim"


def isolation_mode() -> str:
    raw = (os.getenv("ZECT_CODING_ENGINE_ISOLATION") or "worktree").strip().lower()
    if raw in ("docker", "auto", "worktree"):
        return raw
    return "worktree"


def isolation_strict() -> bool:
    return (os.getenv("ZECT_CODING_ENGINE_ISOLATION_STRICT") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def sandbox_image() -> str:
    return (os.getenv("ZECT_CODING_ENGINE_SANDBOX_IMAGE") or DEFAULT_SANDBOX_IMAGE).strip()


def docker_available() -> bool:
    """True when `docker` is on PATH and the daemon responds to `docker info`."""
    if not shutil.which("docker"):
        return False
    try:
        probe = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return probe.returncode == 0
    except Exception:
        return False


def resolve_isolation() -> dict[str, Any]:
    """Public health fields for isolation (no credentials, no third-party brands)."""
    requested = isolation_mode()
    available = docker_available()
    if requested == "worktree":
        effective = "worktree"
        note = "worktree_requested"
    elif requested == "docker":
        if available:
            effective = "docker"
            note = "docker_ok"
        elif isolation_strict():
            effective = "unavailable"
            note = "docker_required_but_unavailable"
        else:
            effective = "worktree"
            note = "docker_unavailable_fallback_worktree"
    else:  # auto
        effective = "docker" if available else "worktree"
        note = "auto_docker" if available else "auto_worktree"

    return {
        "isolation_requested": requested,
        "isolation": effective,
        "docker_available": available,
        "sandbox_image": sandbox_image() if effective == "docker" or requested == "docker" else None,
        "detail": note,
    }


# Env keys allowed into a Docker coding sandbox (never pass host secrets wholesale).
_ALLOWED_SANDBOX_ENV = frozenset(
    {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "TERM",
        "PYTHONUNBUFFERED",
        "ZECT_RUN_ID",
    }
)


def restricted_sandbox_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build a minimal env map for containerized runs."""
    out: dict[str, str] = {}
    for key in _ALLOWED_SANDBOX_ENV:
        val = os.environ.get(key)
        if val:
            out[key] = val
    if extra:
        for k, v in extra.items():
            if k in _ALLOWED_SANDBOX_ENV or k.startswith("ZECT_SANDBOX_"):
                out[k] = v
    out.setdefault("PYTHONUNBUFFERED", "1")
    return out

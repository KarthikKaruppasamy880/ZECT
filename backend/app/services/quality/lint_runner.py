"""Lint gate for Mentrix deliver path — Error → recovery when lint fails."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def run_lint(workspace: str = "", language_hint: str = "") -> dict[str, Any]:
    """Run a best-effort lint command against a workspace.

    Returns {ok, command, stdout, stderr, skipped, reason}.
    When no workspace or tool is available, skips with ok=True so local/CI
    smoke can proceed; set MENTRIX_LINT_STRICT=true to fail on skip.
    """
    strict = os.getenv("MENTRIX_LINT_STRICT", "false").lower() in ("1", "true", "yes")
    root = (workspace or os.getenv("MENTRIX_WORKSPACE", "")).strip()
    if not root or not Path(root).is_dir():
        return {
            "ok": not strict,
            "skipped": True,
            "reason": "No workspace path (set MENTRIX_WORKSPACE or pass workspace)",
            "command": "",
            "stdout": "",
            "stderr": "",
        }

    path = Path(root).resolve()
    cmd: list[str] | None = None
    env_cmd = os.getenv("MENTRIX_LINT_CMD", "").strip()
    if env_cmd:
        cmd = env_cmd.split()
    elif (path / "package.json").exists() and shutil.which("npx"):
        cmd = ["npx", "--yes", "eslint", ".", "--max-warnings", "0"]
        if language_hint and language_hint not in ("javascript", "typescript", "js", "ts"):
            pass
    elif shutil.which("ruff"):
        cmd = ["ruff", "check", str(path)]
    elif shutil.which("python"):
        # Syntax compile check as lightweight Python lint fallback
        py_files = list(path.rglob("*.py"))[:40]
        if py_files:
            failures = []
            for pf in py_files:
                if any(skip in str(pf) for skip in ("node_modules", ".venv", "venv", "__pycache__")):
                    continue
                r = subprocess.run(
                    ["python", "-m", "py_compile", str(pf)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if r.returncode != 0:
                    failures.append(r.stderr or r.stdout or str(pf))
            return {
                "ok": len(failures) == 0,
                "skipped": False,
                "command": "python -m py_compile <files>",
                "stdout": "",
                "stderr": "\n".join(failures)[:4000],
                "reason": "",
            }

    if not cmd:
        return {
            "ok": not strict,
            "skipped": True,
            "reason": "No lint tool detected (ruff / eslint / MENTRIX_LINT_CMD)",
            "command": "",
            "stdout": "",
            "stderr": "",
        }

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=int(os.getenv("MENTRIX_LINT_TIMEOUT", "120")),
        )
        return {
            "ok": proc.returncode == 0,
            "skipped": False,
            "command": " ".join(cmd),
            "stdout": (proc.stdout or "")[:4000],
            "stderr": (proc.stderr or "")[:4000],
            "reason": "",
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "skipped": False,
            "command": " ".join(cmd),
            "stdout": "",
            "stderr": "Lint timed out",
            "reason": "timeout",
        }
    except OSError as exc:
        return {
            "ok": not strict,
            "skipped": True,
            "command": " ".join(cmd),
            "stdout": "",
            "stderr": str(exc),
            "reason": "os_error",
        }

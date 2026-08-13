"""Server-controlled Learning practice runner (M1).

Client passed/exit_code/test_output are never authoritative.
Flow: submission → lesson hidden tests → deterministic subprocess → evidence artifact.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.learning.curriculum import get_lesson

# Bound untrusted learner code
_MAX_CODE_CHARS = 20_000
_TIMEOUT_SEC = 8


def _python_cmd() -> str:
    return sys.executable or "python"


def build_submission_id(*, user_id: int, project_id: int, lesson_key: str, code: str) -> str:
    digest = hashlib.sha256(f"{user_id}:{project_id}:{lesson_key}:{code}".encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"sub-{digest}"


def run_server_practice(
    *,
    code: str,
    path_key: str,
    lesson_key: str,
    language: str = "",
    user_id: int | None = None,
    project_id: int | None = None,
) -> dict[str, Any]:
    """Execute server-owned hidden tests against learner submission. Never trusts client pass flags."""
    lesson = get_lesson(path_key, lesson_key)
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    at = datetime.now(timezone.utc).isoformat()
    submission_id = build_submission_id(
        user_id=int(user_id or 0),
        project_id=int(project_id or 0),
        lesson_key=lesson_key,
        code=code or "",
    )

    base: dict[str, Any] = {
        "ok": False,
        "passed": False,
        "run_id": run_id,
        "submission_id": submission_id,
        "user_id": user_id,
        "project_id": project_id,
        "path_key": path_key,
        "lesson_key": lesson_key,
        "at": at,
        "server_controlled": True,
        "client_claims_ignored": True,
        "source": "learning_practice_runner",
    }

    if not lesson:
        return {**base, "error": "lesson_not_found", "exit_code": 2, "stdout": "", "stderr": "lesson_not_found"}

    lang = (language or lesson.get("language") or "Python").strip()
    hidden = str(lesson.get("hidden_tests") or "").strip()
    if not hidden:
        return {
            **base,
            "error": "no_server_tests_defined",
            "exit_code": 2,
            "stdout": "",
            "stderr": "Lesson has no server-controlled hidden_tests — cannot verify.",
            "language": lang,
        }

    src = (code or "")[:_MAX_CODE_CHARS]
    if lang.lower() not in ("python", "py"):
        # Keep scope honest: curriculum E2E path is Python; other langs need runner extension.
        return {
            **base,
            "error": "language_runner_unsupported",
            "exit_code": 2,
            "stdout": "",
            "stderr": f"Server practice runner supports Python only in D remediation (got {lang}).",
            "language": lang,
        }

    # Disallow obvious escapes in learner submission (defense-in-depth; still subprocess-isolated)
    blocked = ("os.system", "subprocess", "socket.", "__import__('os')", "open(", "pathlib", "shutil")
    lowered = src.lower()
    if any(b.lower() in lowered for b in blocked):
        return {
            **base,
            "error": "unsafe_submission",
            "exit_code": 1,
            "stdout": "",
            "stderr": "Submission rejected: disallowed APIs in practice sandbox.",
            "language": lang,
            "syntax_ok": True,
        }

    program = (
        "# ZECT Learning server-controlled practice\n"
        + src
        + "\n\n# --- server hidden tests (authoritative) ---\n"
        + hidden
        + "\n"
    )

    syntax_ok = True
    syntax_error = ""
    try:
        compile(program, "<learning-practice>", "exec")
    except SyntaxError as e:
        syntax_ok = False
        syntax_error = str(e)

    if not syntax_ok:
        return {
            **base,
            "error": "syntax_error",
            "exit_code": 1,
            "stdout": "",
            "stderr": syntax_error,
            "language": lang,
            "syntax_ok": False,
        }

    tmp_dir = Path(tempfile.mkdtemp(prefix="zect-learn-"))
    try:
        main_py = tmp_dir / "submission.py"
        main_py.write_text(program, encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "PYTHONPATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        # Strip secrets from child env
        proc = subprocess.run(
            [_python_cmd(), str(main_py)],
            cwd=str(tmp_dir),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SEC,
            check=False,
            env=env,
        )
        passed = proc.returncode == 0
        return {
            **base,
            "ok": passed,
            "passed": passed,
            "exit_code": int(proc.returncode),
            "stdout": (proc.stdout or "")[:4000],
            "stderr": (proc.stderr or "")[:4000],
            "language": lang,
            "syntax_ok": True,
            "hidden_tests_hash": hashlib.sha256(hidden.encode()).hexdigest()[:16],
        }
    except subprocess.TimeoutExpired:
        return {
            **base,
            "error": "timeout",
            "exit_code": 124,
            "stdout": "",
            "stderr": f"Practice timed out after {_TIMEOUT_SEC}s",
            "language": lang,
            "syntax_ok": True,
        }
    finally:
        try:
            for p in tmp_dir.glob("*"):
                p.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except OSError:
            pass


def evidence_from_run(run: dict[str, Any]) -> dict[str, Any]:
    """Build EvidenceVerifier-ready payload from a server run (never from client claims)."""
    passed = bool(run.get("passed"))
    return {
        "passed": passed,
        "language": run.get("language") or "Python",
        "lesson_key": run.get("lesson_key") or "",
        "path_key": run.get("path_key") or "",
        "exit_code": int(run.get("exit_code") if run.get("exit_code") is not None else 1),
        "test_output": ((run.get("stdout") or "") + "\n" + (run.get("stderr") or ""))[:4000],
        "type": "TEST_RESULT",
        "operation_id": "OP-LEARN-TEST",
        "requirement_ids": ["REQ-LEARN-PASS"],
        "acceptance_ids": ["AC-LEARN-PASS"],
        "llm_claim": False,
        "server_controlled": True,
        "run_id": run.get("run_id"),
        "submission_id": run.get("submission_id"),
        "user_id": run.get("user_id"),
        "project_id": run.get("project_id"),
        "at": run.get("at"),
        "items": [
            {
                "id": f"practice-cmd-{run.get('run_id')}",
                "type": "COMMAND_EXIT",
                "operation_id": "OP-LEARN-TEST",
                "requirement_ids": ["REQ-LEARN-PASS"],
                "acceptance_ids": ["AC-LEARN-PASS"],
                "payload": {
                    "exit_code": int(run.get("exit_code") if run.get("exit_code") is not None else 1),
                    "run_id": run.get("run_id"),
                    "submission_id": run.get("submission_id"),
                    "server_controlled": True,
                },
                "llm_claim": False,
            },
            {
                "id": f"practice-test-{run.get('run_id')}",
                "type": "TEST_RESULT",
                "operation_id": "OP-LEARN-TEST",
                "requirement_ids": ["REQ-LEARN-PASS"],
                "acceptance_ids": ["AC-LEARN-PASS"],
                "payload": {
                    "passed": passed,
                    "output": ((run.get("stdout") or "")[:2000]),
                    "lesson_key": run.get("lesson_key"),
                    "run_id": run.get("run_id"),
                    "server_controlled": True,
                },
                "llm_claim": False,
            },
        ],
    }

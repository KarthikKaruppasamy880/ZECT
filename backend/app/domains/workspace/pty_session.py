"""Real governed PTY (V2 closure §10): workspace-scoped pseudo-terminal
sessions -- genuine shell, cwd, stdin, streaming stdout/stderr, resize and
Ctrl+C, not the subprocess.Popen command-form / 2s-polling terminal this
replaces (WorkspaceTerminal.tsx's "locked root, not a PTY").

Sessions are workspace-jailed (path_under_allowed_roots) and self-owned:
this manager only ever closes/kills a process IT spawned, never scans for
or kills unrelated processes on the host. Agent tool commands are unaffected
-- they keep going through the existing policy/evidence-governed run_command
tool; this module is for the HUMAN Developer terminal only.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.infrastructure.allowed_paths import path_under_allowed_roots

_IS_WINDOWS = sys.platform.startswith("win")

if _IS_WINDOWS:
    from winpty import PtyProcess
else:
    from ptyprocess import PtyProcess


def _default_shell() -> str:
    if _IS_WINDOWS:
        return os.environ.get("COMSPEC", "cmd.exe")
    return os.environ.get("SHELL", "/bin/bash")


class PtySession:
    def __init__(self, session_id: str, proc: Any, cwd: str, label: str = "") -> None:
        self.id = session_id
        self.proc = proc
        self.cwd = cwd
        self.label = label or session_id
        self.created_at = time.time()
        self._write_lock = threading.Lock()

    def read(self, size: int = 4096) -> str:
        """Blocking read — callers must run this off the asyncio event loop
        (e.g. via asyncio.to_thread), same as any real terminal's stdout."""
        try:
            chunk = self.proc.read(size)
        except EOFError:
            return ""
        if isinstance(chunk, bytes):
            return chunk.decode("utf-8", errors="replace")
        return chunk or ""

    def write(self, data: str) -> int:
        with self._write_lock:
            payload: str | bytes = data.encode("utf-8") if not _IS_WINDOWS else data
            return self.proc.write(payload)

    def resize(self, rows: int, cols: int) -> None:
        with self._write_lock:
            self.proc.setwinsize(rows, cols)

    def interrupt(self) -> None:
        """Ctrl+C — delivered as a real terminal signal to the foreground
        process, not a host-level kill of the whole pty."""
        self.proc.sendintr()

    def isalive(self) -> bool:
        try:
            return bool(self.proc.isalive())
        except Exception:  # noqa: BLE001
            return False

    def exit_code(self) -> int | None:
        return self.proc.exitstatus

    def close(self) -> None:
        try:
            self.proc.close(force=True)
        except Exception:  # noqa: BLE001
            pass


class PtySessionManager:
    """Owns every PTY session this process created."""

    def __init__(self) -> None:
        self._sessions: dict[str, PtySession] = {}
        self._lock = threading.Lock()

    def create(
        self,
        workspace_root: str,
        *,
        cwd: str | None = None,
        shell: str | None = None,
        label: str = "",
        rows: int = 24,
        cols: int = 80,
    ) -> PtySession:
        root = path_under_allowed_roots(workspace_root)
        target = path_under_allowed_roots(cwd) if cwd else root
        try:
            target.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("cwd_outside_workspace_root") from exc
        if not target.is_dir():
            raise ValueError(f"cwd_not_found:{target}")

        argv = [shell or _default_shell()]
        proc = PtyProcess.spawn(argv, cwd=str(target), dimensions=(rows, cols))
        session_id = str(uuid.uuid4())
        session = PtySession(session_id, proc, str(target), label=label)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> PtySession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            sessions = list(self._sessions.values())
        return [
            {"id": s.id, "label": s.label, "cwd": s.cwd, "alive": s.isalive(), "created_at": s.created_at}
            for s in sessions
        ]

    def close(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        session.close()
        return True


_manager: PtySessionManager | None = None


def get_pty_manager() -> PtySessionManager:
    global _manager
    if _manager is None:
        _manager = PtySessionManager()
    return _manager

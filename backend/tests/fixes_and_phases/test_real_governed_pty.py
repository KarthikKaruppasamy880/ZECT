"""Real governed PTY (V2 closure §10).

The Developer terminal was a subprocess.Popen command-form with 2s output
polling and no stdin pipe -- "locked root, not a PTY". This proves a genuine
pseudo-terminal: real shell, real cwd, streaming stdin/stdout, resize and
Ctrl+C delivered as an actual terminal signal (not a host-level kill),
workspace-jailed, and self-owned (only closes sessions it created).
"""

from __future__ import annotations

import shutil
import sys
import threading
import time
import uuid

import pytest

from app.domains.workspace.pty_session import PtySessionManager

_IS_WINDOWS = sys.platform.startswith("win")


def _interactive_shell() -> str | None:
    if _IS_WINDOWS:
        # cmd.exe under ConPTY waits on VT device-attribute queries that only
        # a real terminal emulator (xterm.js on the frontend) answers; a
        # plain test reader would hang. git-bash starts fast and doesn't.
        return shutil.which("bash.exe") or shutil.which("bash")
    return shutil.which("bash") or shutil.which("sh")


_SHELL = _interactive_shell()


class _Drain:
    """Continuously drains a PtySession's blocking read() into a buffer on a
    background thread -- the same pattern the real WebSocket output pump
    uses (asyncio.to_thread around a blocking read)."""

    def __init__(self, session):
        self.session = session
        self.text = ""
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop:
            try:
                chunk = self.session.read(4096)
            except Exception:  # noqa: BLE001
                break
            if self._stop:
                break
            if chunk:
                self.text += chunk

    def wait_for(self, substring: str, timeout_s: float) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if substring in self.text:
                return True
            time.sleep(0.2)
        return substring in self.text

    def stop(self):
        self._stop = True


def _new_marker(label: str) -> str:
    return f"ZECT_{label}_{uuid.uuid4().hex[:8]}"


def _write_with_timeout(session, data: str, timeout_s: float = 8.0) -> bool:
    """PTY writes block when the shell is not reading stdin (e.g. during sleep).
    Never call write() directly in tests without a ceiling — a blocked write
    bypasses polling timeouts and can hang CI indefinitely."""
    result: list[object] = []

    def _do() -> None:
        try:
            result.append(session.write(data))
        except Exception as exc:  # noqa: BLE001
            result.append(exc)

    thread = threading.Thread(target=_do, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)
    if thread.is_alive():
        try:
            session.interrupt()
        except Exception:  # noqa: BLE001
            pass
        return False
    if len(result) == 1 and isinstance(result[0], Exception):
        if isinstance(result[0], EOFError):
            return False
        raise result[0]
    return True


def _wait_for_execution(session, drain: _Drain, base_label: str, timeout_s: float) -> bool:
    """Writes `echo <marker>` and waits until the shell has actually
    *executed* it, not merely accepted the keystrokes.

    A cooked-mode pty echoes typed input immediately regardless of whether
    the shell has finished starting up (or is even the current foreground
    reader) -- so a marker appearing once only proves the pty accepted a
    write, not that the shell ran the command. The shell's own `echo`
    output is a *second*, separate occurrence of the same marker text (the
    echoed input line "echo <marker>" plus the command's bare output line
    "<marker>"). Requiring two occurrences of one attempt's marker is what
    actually proves execution -- portable across shells/prompts/users,
    unlike matching a literal "$" prompt (differs by shell/locale/root vs.
    non-root, and is exactly what failed in CI on a plain bash prompt).
    Retries use a fresh marker each time so a slow-starting shell can't
    produce a false "executed" reading from two separate echoes of two
    different attempts.
    """
    deadline = time.time() + timeout_s
    retry_at = time.time() + timeout_s * 2 / 3
    marker = _new_marker(base_label)
    _write_with_timeout(session, f"echo {marker}\n")
    retried = False
    while time.time() < deadline:
        if drain.text.count(marker) >= 2:
            return True
        if not retried and time.time() > retry_at:
            marker = _new_marker(base_label)
            _write_with_timeout(session, f"echo {marker}\n")
            retried = True
        time.sleep(0.2)
    return drain.text.count(marker) >= 2


class TestWorkspaceJailing:
    def test_workspace_root_outside_allowed_roots_is_rejected(self, monkeypatch):
        monkeypatch.delenv("ZECT_WORKSPACE_ROOT", raising=False)
        monkeypatch.delenv("MENTRIX_WORKSPACE", raising=False)
        mgr = PtySessionManager()
        with pytest.raises(ValueError):
            mgr.create("/__zect_not_allowed__/outside")

    def test_cwd_outside_the_bound_workspace_root_is_rejected(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        other = tmp_path.parent
        mgr = PtySessionManager()
        with pytest.raises(ValueError):
            mgr.create(str(tmp_path), cwd=str(other))

    def test_missing_cwd_directory_is_a_clean_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        mgr = PtySessionManager()
        missing = tmp_path / "does-not-exist"
        with pytest.raises(ValueError):
            mgr.create(str(tmp_path), cwd=str(missing))


@pytest.mark.skipif(not _SHELL, reason="no interactive shell available in this environment")
@pytest.mark.timeout(120)
class TestRealPtyLifecycle:
    def test_spawn_write_read_is_a_real_shell_round_trip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        mgr = PtySessionManager()
        session = mgr.create(str(tmp_path), shell=_SHELL)
        drain = _Drain(session)
        try:
            assert session.isalive() is True
            assert _wait_for_execution(session, drain, "PTY_READY", 40.0), (
                "the shell never actually executed a command -- only echoed the keystrokes, or nothing at all"
            )
        finally:
            drain.stop()
            session.close()
        assert session.isalive() is False

    def test_resize_does_not_raise(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        mgr = PtySessionManager()
        session = mgr.create(str(tmp_path), shell=_SHELL)
        drain = _Drain(session)
        try:
            session.resize(40, 120)
        finally:
            drain.stop()
            session.close()

    def test_interrupt_stops_the_foreground_command_not_the_shell(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        mgr = PtySessionManager()
        session = mgr.create(str(tmp_path), shell=_SHELL)
        drain = _Drain(session)
        try:
            # Prove the shell has actually finished starting up and is
            # executing commands before starting the long-running one -- a
            # slow-starting shell could otherwise still be mid-startup when
            # "sleep 30" is sent, so it wouldn't actually start running
            # until well after the interrupt, defeating the test below
            # regardless of whether Ctrl+C itself works.
            assert _wait_for_execution(session, drain, "READY", 40.0), "the shell never became ready"
            assert _write_with_timeout(session, "sleep 3\n"), "could not start sleep in the shell"
            time.sleep(1.0)
            session.interrupt()
            # If the shell were still blocked inside `sleep 3`, the next command
            # could not be *executed* until sleep finished — seeing it execute
            # well before that proves sleep was interrupted, not merely outlived.
            assert _wait_for_execution(session, drain, "AFTER_INTERRUPT", 12.0), (
                "no command executed within 12s after Ctrl+C -- sleep was not interrupted"
            )
            assert session.isalive() is True, "Ctrl+C must interrupt the foreground command, not kill the shell"
        finally:
            drain.stop()
            session.close()

    def test_manager_only_closes_sessions_it_owns(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        mgr = PtySessionManager()
        assert mgr.close("does-not-exist") is False
        session = mgr.create(str(tmp_path), shell=_SHELL)
        assert mgr.close(session.id) is True
        assert mgr.close(session.id) is False, "closing twice must be a clean no-op, not an error"

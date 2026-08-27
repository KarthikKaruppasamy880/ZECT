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
class TestRealPtyLifecycle:
    def test_spawn_write_read_is_a_real_shell_round_trip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        mgr = PtySessionManager()
        session = mgr.create(str(tmp_path), shell=_SHELL)
        drain = _Drain(session)
        try:
            assert session.isalive() is True
            assert drain.wait_for("$", 20.0), "shell never produced a prompt"
            session.write("echo HELLO_REAL_PTY\n")
            assert drain.wait_for("HELLO_REAL_PTY", 10.0), "real command output never arrived"
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
            assert drain.wait_for("$", 20.0), "shell never produced a prompt"
            before = len(drain.text)
            session.write("sleep 30\n")
            time.sleep(1.5)
            session.interrupt()
            # A fresh prompt reappearing well under 30s proves the sleep was
            # interrupted, not merely waited out.
            deadline = time.time() + 10.0
            new_prompt_seen = False
            while time.time() < deadline:
                if drain.text[before:].rstrip().endswith("$"):
                    new_prompt_seen = True
                    break
                time.sleep(0.3)
            assert new_prompt_seen, "no fresh prompt after Ctrl+C -- sleep 30 was not interrupted"
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

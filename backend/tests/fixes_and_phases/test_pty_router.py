"""Real governed PTY router (V2 closure §10): admin-only REST for session
create/list/close (same gate/audit pattern as App Runner's execute/start),
plus the WebSocket input/output pump glue that turns JSON control frames
into PtySession calls and PtySession output into WS frames.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.domains.workspace.pty_router import (
    CreateSessionRequest,
    _pump_input,
    _pump_output,
    close_session,
    create_session,
)
from app.infrastructure.auth.deps import CurrentUser
from app.infrastructure.auth.rbac import PermissionDenied, RequiresAuthentication
from app.infrastructure.database import Base
from app.models import User


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _make_user(db, *, role="developer", email="user@zect.local"):
    user = User(email=email, name=email, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _current_user_for(user: User) -> CurrentUser:
    return CurrentUser(user_id=user.id, username=user.name, email=user.email, auth_mode="local", token="", role=user.role)


class TestCreateSessionRequiresAdmin:
    @pytest.mark.asyncio
    async def test_developer_role_denied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        db = _session()
        dev = _make_user(db, role="developer")
        with pytest.raises(PermissionDenied):
            await create_session(
                CreateSessionRequest(workspace_root=str(tmp_path)),
                current_user=_current_user_for(dev),
                db=db,
            )

    @pytest.mark.asyncio
    async def test_unauthenticated_call_denied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        with pytest.raises(RequiresAuthentication):
            await create_session(CreateSessionRequest(workspace_root=str(tmp_path)), current_user=None, db=None)

    @pytest.mark.asyncio
    async def test_admin_role_allowed_and_workspace_jailed(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZECT_WORKSPACE_ROOT", raising=False)
        db = _session()
        admin = _make_user(db, role="admin", email="admin@zect.local")
        with pytest.raises(HTTPException) as exc:
            await create_session(
                CreateSessionRequest(workspace_root="/__zect_not_allowed__/outside"),
                current_user=_current_user_for(admin),
                db=db,
            )
        assert exc.value.status_code == 403


class TestCloseSessionRequiresAdmin:
    @pytest.mark.asyncio
    async def test_developer_role_denied(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        db = _session()
        dev = _make_user(db, role="developer")
        with pytest.raises(PermissionDenied):
            await close_session("does-not-exist", current_user=_current_user_for(dev), db=db)

    @pytest.mark.asyncio
    async def test_admin_closing_an_unknown_session_is_404_not_a_crash(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        db = _session()
        admin = _make_user(db, role="admin", email="admin@zect.local")
        with pytest.raises(HTTPException) as exc:
            await close_session("does-not-exist", current_user=_current_user_for(admin), db=db)
        assert exc.value.status_code == 404


class _FakeSession:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.written = []
        self.resized = None
        self.interrupted = False
        self._alive = True

    def read(self, size=4096):
        if self._chunks:
            return self._chunks.pop(0)
        self._alive = False
        return ""

    def isalive(self):
        return self._alive

    def exit_code(self):
        return None if self._alive else 0

    def write(self, data):
        self.written.append(data)

    def resize(self, rows, cols):
        self.resized = (rows, cols)

    def interrupt(self):
        self.interrupted = True


class _FakeWebSocket:
    def __init__(self, incoming=None):
        self._incoming = list(incoming or [])
        self.sent_bytes = []
        self.sent_json = []

    async def receive_json(self):
        if not self._incoming:
            raise asyncio.CancelledError()
        return self._incoming.pop(0)

    async def send_bytes(self, data):
        self.sent_bytes.append(data)

    async def send_json(self, data):
        self.sent_json.append(data)


class TestOutputPump:
    @pytest.mark.asyncio
    async def test_streams_real_output_bytes_then_a_final_exited_frame(self):
        session = _FakeSession(["hello ", "world"])
        ws = _FakeWebSocket()
        await _pump_output(ws, session)
        assert b"".join(ws.sent_bytes) == b"hello world"
        assert ws.sent_json[-1]["type"] == "exited"
        assert ws.sent_json[-1]["exit_code"] == 0


class TestInputPump:
    @pytest.mark.asyncio
    async def test_input_frame_writes_to_the_session(self):
        session = _FakeSession([])
        ws = _FakeWebSocket(incoming=[{"type": "input", "data": "ls\n"}])
        with pytest.raises(asyncio.CancelledError):
            await _pump_input(ws, session)
        assert session.written == ["ls\n"]

    @pytest.mark.asyncio
    async def test_resize_frame_resizes_the_session(self):
        session = _FakeSession([])
        ws = _FakeWebSocket(incoming=[{"type": "resize", "rows": 40, "cols": 120}])
        with pytest.raises(asyncio.CancelledError):
            await _pump_input(ws, session)
        assert session.resized == (40, 120)

    @pytest.mark.asyncio
    async def test_interrupt_frame_sends_a_real_interrupt_not_a_kill(self):
        session = _FakeSession([])
        ws = _FakeWebSocket(incoming=[{"type": "interrupt"}])
        with pytest.raises(asyncio.CancelledError):
            await _pump_input(ws, session)
        assert session.interrupted is True

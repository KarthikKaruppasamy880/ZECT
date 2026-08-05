"""App Runner's /execute, /start, /configure ran arbitrary shell commands
with shell=True and NO authorization dependency at all (not even a role
check — any authenticated Bearer token could reach them) and only checked
that the target directory existed, not that it was under the same
workspace allowlist Git Ops/File Explorer already enforce. This verifies
both gaps are closed: admin-only, and confined to allowed roots.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.auth.deps import CurrentUser
from app.core.auth.rbac import PermissionDenied, RequiresAuthentication
from app.database import Base
from app.models import User
from app.routers.app_runner import ExecuteRequest, StartRequest, _validate_cwd, execute_command


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


class TestExecuteRequiresAdmin:
    @pytest.mark.asyncio
    async def test_developer_role_denied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        db = _session()
        dev = _make_user(db, role="developer")

        with pytest.raises(PermissionDenied):
            await execute_command(
                ExecuteRequest(command="echo hi", cwd=str(tmp_path)),
                current_user=_current_user_for(dev),
                db=db,
            )

    @pytest.mark.asyncio
    async def test_admin_role_allowed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        db = _session()
        admin = _make_user(db, role="admin", email="admin@zect.local")

        result = await execute_command(
            ExecuteRequest(command="echo hi", cwd=str(tmp_path)),
            current_user=_current_user_for(admin),
            db=db,
        )

        assert result["exit_code"] == 0
        assert "hi" in result["stdout"]

    @pytest.mark.asyncio
    async def test_unauthenticated_call_denied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        with pytest.raises(RequiresAuthentication):
            await execute_command(ExecuteRequest(command="echo hi", cwd=str(tmp_path)), current_user=None, db=None)


class TestValidateCwdAllowlist:
    def test_rejects_path_outside_allowed_roots(self, monkeypatch):
        # Not tmp_path: allowed_roots() includes the system tempdir as a
        # cross-platform default, so tmp_path no longer represents "outside
        # allowed roots". Use a literal path that is never allowed instead.
        monkeypatch.delenv("ZECT_WORKSPACE_ROOT", raising=False)
        monkeypatch.delenv("MENTRIX_WORKSPACE", raising=False)
        with pytest.raises(HTTPException) as exc:
            _validate_cwd(r"C:\Windows\System32")
        assert exc.value.status_code == 403

    def test_accepts_path_under_workspace_root(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        resolved = _validate_cwd(str(tmp_path))
        assert resolved

    def test_missing_directory_under_allowed_root_is_400_not_403(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        missing = tmp_path / "does-not-exist"
        with pytest.raises(HTTPException) as exc:
            _validate_cwd(str(missing))
        assert exc.value.status_code == 400


class TestStartRequiresAdmin:
    @pytest.mark.asyncio
    async def test_developer_role_denied(self, tmp_path, monkeypatch):
        from app.routers.app_runner import start_process

        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        db = _session()
        dev = _make_user(db, role="developer")

        with pytest.raises(PermissionDenied):
            await start_process(
                StartRequest(command="echo hi", cwd=str(tmp_path)),
                current_user=_current_user_for(dev),
                db=db,
            )

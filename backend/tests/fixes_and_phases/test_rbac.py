"""Unit tests for Role-Based Access Control (RBAC)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.auth.rbac import (
    require_role,
    require_authentication,
    log_audit,
    can_user_access_resource,
    get_user_from_current_user,
    PermissionDenied,
    RequiresAuthentication,
)
from app.core.auth.deps import CurrentUser
from app.models import User, SecretEntry, AuditLog, Project


class TestRequireRoleDecorator:
    """Test @require_role decorator."""

    @pytest.mark.asyncio
    async def test_allows_admin_role(self):
        """Test that @require_role('admin') allows admin users."""
        @require_role("admin")
        async def protected_endpoint(current_user: CurrentUser, db: Session):
            return {"result": "success"}

        # Mock admin user
        admin_user = CurrentUser(
            user_id=1,
            username="admin",
            email="admin@example.com",
            auth_mode="local",
            token="token123"
        )
        db_mock = Mock(spec=Session)
        db_mock.query().filter().first.return_value = Mock(role="admin")

        # Should not raise
        result = await protected_endpoint(current_user=admin_user, db=db_mock)
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_denies_non_admin_role(self):
        """Test that @require_role('admin') denies non-admin users."""
        @require_role("admin")
        async def protected_endpoint(current_user: CurrentUser, db: Session):
            return {"result": "success"}

        developer_user = CurrentUser(
            user_id=2,
            username="dev",
            email="dev@example.com",
            auth_mode="local",
            token="token123"
        )
        db_mock = Mock(spec=Session)
        db_mock.query().filter().first.return_value = Mock(role="developer")

        # Should raise PermissionDenied
        with pytest.raises(PermissionDenied):
            await protected_endpoint(current_user=developer_user, db=db_mock)

    @pytest.mark.asyncio
    async def test_allows_multiple_roles(self):
        """Test that @require_role('admin', 'lead') allows both roles."""
        @require_role("admin", "lead")
        async def protected_endpoint(current_user: CurrentUser, db: Session):
            return {"result": "success"}

        lead_user = CurrentUser(
            user_id=3,
            username="lead",
            email="lead@example.com",
            auth_mode="local",
            token="token123"
        )
        db_mock = Mock(spec=Session)
        db_mock.query().filter().first.return_value = Mock(role="lead")

        # Should not raise
        result = await protected_endpoint(current_user=lead_user, db=db_mock)
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_requires_authentication(self):
        """Test that @require_role requires authentication."""
        @require_role("admin")
        async def protected_endpoint(current_user: CurrentUser, db: Session):
            return {"result": "success"}

        # Should raise RequiresAuthentication when current_user is None
        with pytest.raises(RequiresAuthentication):
            await protected_endpoint(current_user=None, db=Mock())


class TestRequireAuthenticationDecorator:
    """Test @require_authentication decorator."""

    @pytest.mark.asyncio
    async def test_allows_authenticated_user(self):
        """Test that @require_authentication allows authenticated users."""
        @require_authentication
        async def protected_endpoint(current_user: CurrentUser):
            return {"result": "success"}

        user = CurrentUser(
            user_id=1,
            username="user",
            email="user@example.com",
            auth_mode="local",
            token="token123"
        )

        result = await protected_endpoint(current_user=user)
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_denies_unauthenticated_user(self):
        """Test that @require_authentication denies unauthenticated users."""
        @require_authentication
        async def protected_endpoint(current_user: CurrentUser):
            return {"result": "success"}

        with pytest.raises(RequiresAuthentication):
            await protected_endpoint(current_user=None)


class TestCanUserAccessResource:
    """Test resource-level access control."""

    @pytest.fixture
    def db_mock(self):
        """Create mock database."""
        return Mock(spec=Session)

    @pytest.fixture
    def admin_user(self):
        """Create admin user."""
        return Mock(spec=User, user_id=1, role="admin", team="engineering")

    @pytest.fixture
    def developer_user(self):
        """Create developer user."""
        return Mock(spec=User, user_id=2, role="developer", team="engineering")

    @pytest.fixture
    def viewer_user(self):
        """Create viewer user."""
        return Mock(spec=User, user_id=3, role="viewer", team="engineering")

    def test_admin_can_access_all_secrets(self, admin_user, db_mock):
        """Test that admins can access all secrets."""
        secret = Mock(spec=SecretEntry, id=1, scope="global")
        db_mock.query().get.return_value = secret

        result = can_user_access_resource(admin_user, "secret", 1, db_mock)
        assert result is True

    def test_developer_can_access_team_secrets(self, developer_user, db_mock):
        """Test that developers can access secrets in their team."""
        project = Mock(spec=Project, team="engineering")
        secret = Mock(spec=SecretEntry, id=1, scope="project", project=project)
        db_mock.query().get.return_value = secret

        result = can_user_access_resource(developer_user, "secret", 1, db_mock)
        assert result is True

    def test_developer_cannot_access_other_team_secrets(self, developer_user, db_mock):
        """Test that developers cannot access secrets from other teams."""
        project = Mock(spec=Project, team="marketing")
        secret = Mock(spec=SecretEntry, id=1, scope="project", project=project)
        db_mock.query().get.return_value = secret

        result = can_user_access_resource(developer_user, "secret", 1, db_mock)
        assert result is False

    def test_admin_can_access_all_projects(self, admin_user, db_mock):
        """Test that admins can access all projects."""
        project = Mock(spec=Project, id=1, team="marketing")
        db_mock.query().get.return_value = project

        result = can_user_access_resource(admin_user, "project", 1, db_mock)
        assert result is True

    def test_user_cannot_access_nonexistent_resource(self, developer_user, db_mock):
        """Test that accessing nonexistent resource returns False."""
        db_mock.query().get.return_value = None

        result = can_user_access_resource(developer_user, "secret", 999, db_mock)
        assert result is False

    def test_only_admin_can_access_user_resources(self, admin_user, developer_user, db_mock):
        """Test that only admins can access user resources."""
        admin_result = can_user_access_resource(admin_user, "user", 1, db_mock)
        dev_result = can_user_access_resource(developer_user, "user", 1, db_mock)

        assert admin_result is True
        assert dev_result is False


class TestLogAudit:
    """Test audit logging."""

    @pytest.fixture
    def db_mock(self):
        """Create mock database."""
        db = Mock(spec=Session)
        db.add = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        return db

    def test_logs_audit_entry(self, db_mock):
        """Test that audit entries are logged."""
        result = log_audit(
            db=db_mock,
            user_id=1,
            action="delete_secret",
            resource_id=5,
            resource_type="secret",
            details={"name": "api_key"}
        )

        # Should call db.add() and db.commit()
        assert db_mock.add.called
        assert db_mock.commit.called

    def test_audit_logging_failure_does_not_raise(self, db_mock):
        """Test that audit logging failures don't break operations."""
        db_mock.add.side_effect = Exception("Database error")

        # Should not raise even if db fails
        result = log_audit(
            db=db_mock,
            user_id=1,
            action="delete_secret",
            resource_id=5,
            resource_type="secret",
        )

        # Result should be None but no exception raised
        assert result is None
        assert db_mock.rollback.called

    def test_audit_entry_contains_all_fields(self, db_mock):
        """Test that audit entries contain all required fields."""
        # Capture the AuditLog object passed to db.add
        captured_entry = None

        def capture_add(obj):
            nonlocal captured_entry
            captured_entry = obj

        db_mock.add.side_effect = capture_add

        log_audit(
            db=db_mock,
            user_id=1,
            action="delete_secret",
            resource_id=5,
            resource_type="secret",
            details={"name": "api_key"}
        )

        assert captured_entry is not None
        assert captured_entry.user_id == 1
        assert captured_entry.action == "delete_secret"
        assert captured_entry.resource_id == 5
        assert captured_entry.resource_type == "secret"
        assert captured_entry.details == '{"name": "api_key"}'


class TestGetUserFromCurrentUser:
    """Test CurrentUser to User conversion."""

    @pytest.fixture
    def db_mock(self):
        """Create mock database."""
        return Mock(spec=Session)

    def test_returns_user_object(self, db_mock):
        """Test that user object is returned."""
        current_user = CurrentUser(
            user_id=1,
            username="testuser",
            email="test@example.com",
            auth_mode="local",
            token="token123"
        )
        db_user = Mock(spec=User, user_id=1, email="test@example.com", role="admin")
        db_mock.query().filter().first.return_value = db_user

        result = get_user_from_current_user(current_user, db_mock)
        assert result == db_user
        assert result.role == "admin"

    def test_raises_if_user_not_found(self, db_mock):
        """Test that RequiresAuthentication is raised if user not found."""
        current_user = CurrentUser(
            user_id=999,
            username="nonexistent",
            email="nonexistent@example.com",
            auth_mode="local",
            token="token123"
        )
        db_mock.query().filter().first.return_value = None

        with pytest.raises(RequiresAuthentication):
            get_user_from_current_user(current_user, db_mock)


class TestPermissionDeniedException:
    """Test PermissionDenied exception."""

    def test_has_403_status(self):
        """Test that PermissionDenied has 403 status."""
        exc = PermissionDenied("Access denied")
        assert exc.status_code == 403

    def test_has_custom_message(self):
        """Test that PermissionDenied has custom message."""
        exc = PermissionDenied("You need admin role")
        assert "You need admin role" in exc.detail


class TestRequiresAuthenticationException:
    """Test RequiresAuthentication exception."""

    def test_has_401_status(self):
        """Test that RequiresAuthentication has 401 status."""
        exc = RequiresAuthentication("Not authenticated")
        assert exc.status_code == 401

    def test_has_custom_message(self):
        """Test that RequiresAuthentication has custom message."""
        exc = RequiresAuthentication("Login required")
        assert "Login required" in exc.detail


class TestDecoratorsSupportPlainSyncHandlers:
    """Both decorators unconditionally did `return await func(*args, **kwargs)`
    — every real route handler either decorator is applied to in this
    codebase (audit_trail's list/stats, permissions' create/update/delete
    rule + approve_action, secrets_manager's delete_secret) is a plain
    `def`, not `async def`, so every one of those 7 endpoints raised
    TypeError: '<return type>' object can't be awaited on every call,
    regardless of the actual permission outcome — a correctness bug, not a
    permission bug. Verifies both decorators now handle a sync handler
    (returning its result directly) exactly like they handle an async one."""

    @pytest.mark.asyncio
    async def test_require_role_calls_a_sync_handler_without_raising(self):
        @require_role("admin")
        def sync_endpoint(current_user, db):
            return {"result": "sync-ok"}

        admin_user = CurrentUser(user_id=1, username="admin", email="admin@example.com", auth_mode="local", token="t")
        db_mock = Mock(spec=Session)
        db_mock.query().filter().first.return_value = Mock(role="admin")

        result = await sync_endpoint(current_user=admin_user, db=db_mock)
        assert result == {"result": "sync-ok"}

    @pytest.mark.asyncio
    async def test_require_role_still_calls_an_async_handler_correctly(self):
        @require_role("admin")
        async def async_endpoint(current_user, db):
            return {"result": "async-ok"}

        admin_user = CurrentUser(user_id=1, username="admin", email="admin@example.com", auth_mode="local", token="t")
        db_mock = Mock(spec=Session)
        db_mock.query().filter().first.return_value = Mock(role="admin")

        result = await async_endpoint(current_user=admin_user, db=db_mock)
        assert result == {"result": "async-ok"}

    @pytest.mark.asyncio
    async def test_require_authentication_calls_a_sync_handler_without_raising(self):
        @require_authentication
        def sync_endpoint(current_user):
            return [1, 2, 3]

        user = CurrentUser(user_id=1, username="dev", email="dev@example.com", auth_mode="local", token="t")

        result = await sync_endpoint(current_user=user)
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_require_role_denial_still_raised_before_calling_a_sync_handler(self):
        calls = []

        @require_role("admin")
        def sync_endpoint(current_user, db):
            calls.append(1)
            return {"should": "not run"}

        dev_user = CurrentUser(user_id=2, username="dev", email="dev@example.com", auth_mode="local", token="t")
        db_mock = Mock(spec=Session)
        db_mock.query().filter().first.return_value = Mock(role="developer")

        with pytest.raises(PermissionDenied):
            await sync_endpoint(current_user=dev_user, db=db_mock)
        assert calls == []

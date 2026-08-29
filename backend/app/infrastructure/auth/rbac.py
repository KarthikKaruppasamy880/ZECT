"""Role-Based Access Control (RBAC) decorators and helpers."""

import inspect
from functools import wraps
from typing import Optional, Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import User, AuditLog
from app.infrastructure.auth.deps import get_current_user, CurrentUser


class PermissionDenied(HTTPException):
    """Raised when user lacks required permission."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


class RequiresAuthentication(HTTPException):
    """Raised when authentication is required but not provided."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )


def _resolve_pep563_annotations(func: Callable) -> None:
    """Replace string annotations with live objects from the handler module.

    FastAPI evaluates PEP 563 annotations using the wrapper's globals (this file),
    which does not contain handler-local models (PlanRequest, etc.).
    """
    raw = getattr(func, "__annotations__", None)
    if not raw:
        return
    ns = getattr(func, "__globals__", {}) or {}
    resolved: dict = {}
    for key, val in raw.items():
        if isinstance(val, str):
            try:
                resolved[key] = eval(val, ns, ns)  # noqa: S307
            except Exception:  # noqa: BLE001
                resolved[key] = val
        else:
            resolved[key] = val
    func.__annotations__ = resolved


async def _call_maybe_async(func: Callable, *args, **kwargs):
    """Both @require_role and @require_authentication unconditionally did
    `return await func(*args, **kwargs)` — every single route handler either
    decorator was ever applied to in this codebase (list_audit_logs,
    audit_stats, create/update/delete_rule, approve_action, delete_secret) is
    a plain `def`, not `async def`, so that `await` raised
    TypeError: '<return type>' object can't be awaited on EVERY call,
    regardless of role/auth outcome — not a permission bug, a total outage
    of 7 endpoints. Detect which kind we were handed instead of assuming."""
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def require_role(*allowed_roles: str):
    """
    Decorator to enforce role-based access control.

    Usage:
        @router.delete("/api/users/{user_id}")
        @require_role("admin")
        async def delete_user(user_id: int, current_user: CurrentUser = Depends(get_current_user)):
            ...

        @router.patch("/api/projects/{project_id}")
        @require_role("admin", "lead")
        async def update_project(project_id: int, current_user: CurrentUser = Depends(get_current_user)):
            ...
    """

    def decorator(func: Callable) -> Callable:
        _resolve_pep563_annotations(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user: Optional[CurrentUser] = kwargs.get("current_user")

            if not current_user:
                raise RequiresAuthentication("User must be authenticated")

            # Check if user's role is in allowed roles
            # Note: role will be fetched from database for full check
            if current_user.auth_mode == "local":
                # For local auth, we need to fetch the user from DB to get full role info
                db = kwargs.get("db")
                if db:
                    user = db.query(User).filter(User.email == current_user.email).first()
                    if not user or user.role not in allowed_roles:
                        raise PermissionDenied(
                            f"Requires one of these roles: {', '.join(allowed_roles)}. Your role: {user.role if user else 'unknown'}"
                        )

            return await _call_maybe_async(func, *args, **kwargs)

        return wrapper

    return decorator


def require_authentication(func: Callable) -> Callable:
    """
    Decorator to enforce that user is authenticated. Wraps either a sync or
    an async route handler — see _call_maybe_async.

    Usage:
        @router.get("/api/projects")
        @require_authentication
        async def list_projects(current_user: CurrentUser = Depends(get_current_user)):
            ...
    """
    _resolve_pep563_annotations(func)

    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user: Optional[CurrentUser] = kwargs.get("current_user")

        if not current_user:
            raise RequiresAuthentication("User must be authenticated")

        return await _call_maybe_async(func, *args, **kwargs)

    return wrapper


def log_audit(
    db: Session,
    user_id: int,
    action: str,
    resource_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """
    Compatibility wrapper → canonical `domains.audit.audit_trail.log_audit`
    (Phase 5 Stage A). Prefer importing from audit_trail for new call sites.

    Usage:
        log_audit(
            db=db,
            user_id=current_user.user_id,
            action="delete_secret",
            resource_id=secret_id,
            resource_type="secret",
            details={"reason": "expired"}
        )
    """
    # Lazy import avoids circular import (audit_trail imports require_authentication).
    from app.domains.audit.audit_trail import log_audit as _canonical_log_audit

    return _canonical_log_audit(
        db,
        action=action,
        resource_type=resource_type or "unknown",
        resource_id=resource_id,
        details=details if details is not None else "",
        user_id=user_id,
    )


def can_user_access_resource(
    user: User,
    resource_type: str,
    resource_id: int,
    db: Session
) -> bool:
    """
    Check if user has access to a specific resource.

    Implements resource-level access control (RLAC).

    Usage:
        user = db.query(User).get(user_id)
        if not can_user_access_resource(user, "secret", secret_id, db):
            raise PermissionDenied("You don't have access to this secret")

    Access rules:
    - Admin: access everything
    - Lead/Developer: access resources in their team
    - Viewer: read-only access to team resources
    """

    # Admin can access anything
    if user.role == "admin":
        return True

    # Check resource-specific rules
    if resource_type == "secret":
        from app.models import SecretEntry
        secret = db.query(SecretEntry).get(resource_id)
        if not secret:
            return False

        # User can access secrets in their team
        if secret.scope == "global" and user.role == "admin":
            return True
        if secret.scope == "team":
            # Need to check if secret's project belongs to user's team
            if secret.project and secret.project.team == user.team:
                return True
        if secret.scope == "project":
            # User in project can access
            if secret.project and secret.project.team == user.team:
                return True
        return False

    if resource_type == "project":
        from app.models import Project
        project = db.query(Project).get(resource_id)
        if not project:
            return False

        # User can access projects in their team
        return project.team == user.team

    if resource_type == "user":
        # Only admins can access user resources
        return user.role == "admin"

    # Default: deny access
    return False


def get_user_from_current_user(
    current_user: CurrentUser,
    db: Session
) -> User:
    """Convert CurrentUser to full User object with role info."""
    user = db.query(User).filter(User.email == current_user.email).first()
    if not user:
        raise RequiresAuthentication(f"User {current_user.email} not found in database")
    return user

"""Role-Based Access Control (RBAC) decorators and helpers."""

import json
from functools import wraps
from typing import Optional, Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, AuditLog
from app.core.auth.deps import get_current_user, CurrentUser
from datetime import datetime, timezone


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

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_authentication(func: Callable) -> Callable:
    """
    Decorator to enforce that user is authenticated.

    Usage:
        @router.get("/api/projects")
        @require_authentication
        async def list_projects(current_user: CurrentUser = Depends(get_current_user)):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user: Optional[CurrentUser] = kwargs.get("current_user")

        if not current_user:
            raise RequiresAuthentication("User must be authenticated")

        return await func(*args, **kwargs)

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
    Log an action to the audit trail.

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
    try:
        # audit_logs.details is Text — SQLite cannot bind a raw dict.
        if details is None:
            details_value = ""
        elif isinstance(details, str):
            details_value = details
        else:
            details_value = json.dumps(details, default=str)
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_id=resource_id,
            resource_type=resource_type,
            details=details_value,
            created_at=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.commit()
        return audit_entry
    except Exception as e:
        db.rollback()
        # Don't raise — audit logging failures shouldn't break operations
        print(f"[audit] logging failed: {e}")
        return None


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

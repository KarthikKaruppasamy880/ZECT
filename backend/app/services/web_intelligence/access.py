"""Web Intelligence access control — fail-closed Permission Broker + project binding."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project, User
from app.services.mentrix.permission_broker import check_tool_permission


class ProjectAccessDenied(PermissionError):
    """Raised when the authenticated user cannot access a project."""


def user_can_access_project(db: Session, user_id: int, project_id: int | None) -> bool:
    """Independently verify project access — never trust client project_id alone.

    Rules (fail-closed):
    - project_id required and Project must exist
    - User must exist and be active
    - admin role → allow
    - matching non-empty project.team and user.team → allow
    - otherwise deny (no forged-id bypass)
    """
    if project_id is None:
        return False
    try:
        pid = int(project_id)
    except (TypeError, ValueError):
        return False
    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        return False
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not getattr(user, "is_active", True):
        return False
    role = (getattr(user, "role", None) or "").strip().lower()
    if role == "admin":
        return True
    pteam = (getattr(project, "team", None) or "").strip()
    uteam = (getattr(user, "team", None) or "").strip()
    if pteam and uteam and pteam == uteam:
        return True
    return False


def assert_project_access(db: Session, user_id: int, project_id: int | None) -> int:
    """Return validated project_id or raise ProjectAccessDenied."""
    if project_id is None:
        raise ProjectAccessDenied("project_required")
    if not user_can_access_project(db, user_id, project_id):
        raise ProjectAccessDenied("project_access_denied")
    return int(project_id)


def require_web_tool_permission(
    db: Session,
    tool_name: str,
    *,
    user_id: int,
    project_id: int | None = None,
    user_confirmed: bool = False,
) -> dict[str, Any]:
    """Fail-closed Permission Broker gate for Web Intelligence endpoints.

    ALLOW   -> proceed
    CONFIRM -> require confirmation (block unless user_confirmed)
    DENY / UNKNOWN / MISSING / ERROR -> block
    """
    try:
        perm = check_tool_permission(
            db,
            tool_name,
            user_id=user_id,
            project_id=project_id,
            user_confirmed=user_confirmed,
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            403,
            detail={"error": "permission_error", "tool": tool_name, "message": str(e)[:300]},
        ) from e

    if not isinstance(perm, dict):
        raise HTTPException(
            403,
            detail={"error": "permission_denied", "tool": tool_name, "result": "malformed"},
        )

    result = str(perm.get("result") or "").strip().lower()
    level = str(perm.get("permission_level") or perm.get("level") or "").strip().lower()
    needs_confirm = bool(perm.get("needs_confirm"))

    if result in ("denied", "deny", "error") or level in ("never", "deny", "denied"):
        raise HTTPException(
            403,
            detail={
                "error": "permission_denied",
                "tool": tool_name,
                "result": result or "denied",
                "permission_level": level or "never",
                "audit_id": perm.get("audit_id"),
            },
        )
    if result in ("pending_approval", "confirm") or needs_confirm:
        if not user_confirmed:
            raise HTTPException(
                403,
                detail={
                    "error": "confirmation_required",
                    "tool": tool_name,
                    "result": result or "pending_approval",
                    "permission_level": level or "require_approval",
                    "audit_id": perm.get("audit_id"),
                },
            )
    if result != "granted":
        raise HTTPException(
            403,
            detail={
                "error": "permission_denied",
                "tool": tool_name,
                "result": result or "unknown",
                "permission_level": level or "unknown",
                "audit_id": perm.get("audit_id"),
            },
        )

    return {
        "tool": perm.get("tool") or tool_name,
        "action": perm.get("action"),
        "result": result,
        "permission_level": level or "allow",
        "needs_confirm": False,
        "audit_id": perm.get("audit_id"),
        "grant_id": perm.get("grant_id"),
        "allowed": True,
        "level": level or "allow",
    }

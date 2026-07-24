"""FastAPI dependencies for Mentrix auth."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth.session_store import get_token_row
from app.database import get_db


@dataclass
class CurrentUser:
    user_id: int | None
    username: str
    email: str
    auth_mode: str
    token: str
    role: str = "developer"  # ✅ RBAC: Include user's role (default: developer)


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer ") and len(auth) > 10:
        return auth[7:].strip()
    # Transition: query token used by older UI verify/logout
    return (request.query_params.get("token") or "").strip()


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    token = _extract_bearer(request)
    if not token:
        return None
    row = get_token_row(db, token)
    if not row:
        return None

    # ✅ RBAC: Fetch user's role from database
    from app.models import User
    user = db.query(User).filter(User.id == row.user_id).first()
    user_role = user.role if user else "developer"

    return CurrentUser(
        user_id=row.user_id,
        username=row.username or row.email or "",
        email=row.email or row.username or "",
        auth_mode=row.auth_mode or "local",
        token=token,
        role=user_role,
    )


def get_current_user(
    user: CurrentUser | None = Depends(get_optional_user),
) -> CurrentUser:
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized — missing or invalid credentials")
    return user

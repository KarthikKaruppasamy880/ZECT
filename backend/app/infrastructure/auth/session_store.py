"""DB-backed auth token store for Mentrix / ZECT."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import AuthToken, User


def create_token(
    db: Session,
    *,
    username: str,
    email: str = "",
    user_id: int | None = None,
    auth_mode: str = "local",
    ttl_hours: int = 24 * 7,
) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    row = AuthToken(
        token=token,
        user_id=user_id,
        username=username,
        email=email or username,
        auth_mode=auth_mode,
        expires_at=now + timedelta(hours=ttl_hours),
        created_at=now,
        last_seen_at=now,
    )
    db.add(row)
    db.commit()
    return token


def get_token_row(db: Session, token: str) -> AuthToken | None:
    if not token:
        return None
    row = db.query(AuthToken).filter(AuthToken.token == token).first()
    if not row:
        return None
    if row.expires_at is not None:
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            db.delete(row)
            db.commit()
            return None
    row.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return row


def revoke_token(db: Session, token: str) -> bool:
    row = db.query(AuthToken).filter(AuthToken.token == token).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def upsert_local_user(db: Session, username: str) -> User:
    """Create or refresh the local login user.

    The configured ZECT_USERNAME (env local credential) is always promoted to
    admin so interactive Mentrix / Companion is not stuck as developer after a
    prior OIDC or seed row.
    """
    import os

    email = username.strip().lower()
    configured = (os.getenv("ZECT_USERNAME") or "").strip().lower()
    is_configured_local = bool(configured) and email == configured

    user = db.query(User).filter(User.email == email).first()
    if user:
        user.last_login = datetime.now(timezone.utc)
        if is_configured_local and (user.role or "").strip().lower() != "admin":
            user.role = "admin"
        db.commit()
        return user
    user = User(
        email=email,
        name=email.split("@")[0] or email,
        role="admin",
        sso_provider=None,
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

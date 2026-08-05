"""Authentication for ZECT — local username/password + OIDC-ready."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user, get_optional_user
from app.infrastructure.auth.oidc import oidc_configured, oidc_login_url, validate_bearer_jwt
from app.infrastructure.auth.session_store import (
    create_token,
    get_token_row,
    revoke_token,
    upsert_local_user,
)
from app.infrastructure.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


# Dev-local defaults when .env credentials are unset (local/hybrid only).
_DEV_DEFAULT_USER = "admin@zect.local"
_DEV_DEFAULT_PASS = "zect-dev-local"
_dev_defaults_logged = False


def _auth_mode() -> str:
    return os.getenv("ZECT_AUTH_MODE", "local").strip().lower() or "local"


def _auth_creds() -> tuple[str, str]:
    global _dev_defaults_logged
    if _ENV_FILE.is_file():
        # override=False — only fills in ZECT_USERNAME/ZECT_PASSWORD if they
        # aren't already set in the process environment. This still loads
        # real .env credentials on a cold start (nothing set yet), but no
        # longer stomps credentials the process environment already has —
        # override=True previously re-read .env on every single login call,
        # so a test suite injecting its own credentials before importing the
        # app had them silently overwritten by real .env values on the very
        # next login attempt. Picking up an edited .env now requires a
        # restart, same as any other env-var config in this app.
        load_dotenv(_ENV_FILE, override=False)
    user = os.getenv("ZECT_USERNAME", "").strip()
    password = os.getenv("ZECT_PASSWORD", "")
    mode = _auth_mode()
    # Never apply defaults when OIDC-only or when ENV=production
    env_name = os.getenv("ENV", os.getenv("ZECT_ENV", "")).strip().lower()
    if (not user or not password) and mode in ("local", "hybrid") and env_name not in ("production", "prod"):
        user = user or _DEV_DEFAULT_USER
        password = password or _DEV_DEFAULT_PASS
        if not _dev_defaults_logged:
            print(
                f"[ZECT AUTH] Using dev-local defaults ({_DEV_DEFAULT_USER}). "
                "Set ZECT_USERNAME/ZECT_PASSWORD to override."
            )
            _dev_defaults_logged = True
    return user, password


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    auth_mode: str = "local"


class AuthConfigResponse(BaseModel):
    auth_mode: str
    local_enabled: bool
    oidc_enabled: bool
    oidc_configured: bool


class OidcExchangeRequest(BaseModel):
    access_token: str


class MeResponse(BaseModel):
    user_id: int | None
    username: str
    email: str
    auth_mode: str


def _safe_compare(a: str, b: str) -> bool:
    ae, be = a.encode("utf-8"), b.encode("utf-8")
    if len(ae) != len(be):
        return False
    return secrets.compare_digest(ae, be)


@router.get("/config", response_model=AuthConfigResponse)
def auth_config():
    mode = _auth_mode()
    return AuthConfigResponse(
        auth_mode=mode,
        local_enabled=mode in ("local", "hybrid"),
        oidc_enabled=mode in ("oidc", "hybrid"),
        oidc_configured=oidc_configured(),
    )


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    mode = _auth_mode()
    if mode == "oidc":
        raise HTTPException(
            status_code=400,
            detail="Local login disabled. Use Azure AD / OIDC sign-in.",
        )
    valid_user, valid_pass = _auth_creds()
    if not valid_user or not valid_pass:
        raise HTTPException(
            status_code=503,
            detail="Authentication not configured. Set ZECT_USERNAME and ZECT_PASSWORD.",
        )
    username_ok = _safe_compare(req.username.strip().lower(), valid_user.lower())
    password_ok = _safe_compare(req.password, valid_pass)
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = upsert_local_user(db, req.username.strip())
    token = create_token(
        db,
        username=user.email,
        email=user.email,
        user_id=user.id,
        auth_mode="local",
    )
    return LoginResponse(token=token, username=user.email, auth_mode="local")


@router.get("/oidc/login-url")
def get_oidc_login_url(redirect_uri: str = ""):
    mode = _auth_mode()
    if mode not in ("oidc", "hybrid"):
        raise HTTPException(status_code=400, detail="OIDC mode is not enabled")
    if not oidc_configured():
        raise HTTPException(status_code=503, detail="OIDC is not configured")
    uri = redirect_uri or os.getenv("AZURE_REDIRECT_URI", "http://localhost:5173/login")
    return {"url": oidc_login_url(uri)}


@router.post("/oidc/exchange", response_model=LoginResponse)
async def oidc_exchange(req: OidcExchangeRequest, db: Session = Depends(get_db)):
    mode = _auth_mode()
    if mode not in ("oidc", "hybrid"):
        raise HTTPException(status_code=400, detail="OIDC mode is not enabled")
    try:
        claims = await validate_bearer_jwt(req.access_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    email = (claims.email or claims.sub).strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=claims.name or email,
            role="developer",
            sso_provider="azure-ad",
            sso_id=claims.sub,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.sso_provider = "azure-ad"
        user.sso_id = claims.sub
        user.name = claims.name or user.name
        db.commit()

    token = create_token(
        db,
        username=user.email,
        email=user.email,
        user_id=user.id,
        auth_mode="oidc",
    )
    return LoginResponse(token=token, username=user.email, auth_mode="oidc")


@router.post("/logout")
def logout(
    request: Request,
    token: str = "",
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_optional_user),
):
    t = token or (user.token if user else "")
    if not t:
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            t = auth[7:].strip()
    if t:
        revoke_token(db, t)
    return {"status": "logged_out"}


@router.get("/verify")
def verify(
    token: str = "",
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_optional_user),
):
    if user:
        return {"valid": True, "username": user.username, "email": user.email}
    if token:
        row = get_token_row(db, token)
        if row:
            return {"valid": True, "username": row.username, "email": row.email}
    raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser = Depends(get_current_user)):
    return MeResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        auth_mode=user.auth_mode,
    )

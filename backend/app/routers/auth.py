"""Simple token-based authentication for ZECT."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory session tokens
_active_tokens: set[str] = set()

# backend/.env (same file main.py loads)
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _auth_creds() -> tuple[str, str]:
    """Reload .env each time so password edits apply without restart; then read os.environ."""
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE, override=True)
    return os.getenv("ZECT_USERNAME", "").strip(), os.getenv("ZECT_PASSWORD", "")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


def _safe_compare(a: str, b: str) -> bool:
    """Constant-time compare for UTF-8 strings (length mismatch => no match)."""
    ae, be = a.encode("utf-8"), b.encode("utf-8")
    if len(ae) != len(be):
        return False
    return secrets.compare_digest(ae, be)


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    valid_user, valid_pass = _auth_creds()
    if not valid_user or not valid_pass:
        raise HTTPException(
            status_code=503,
            detail="Authentication not configured. Set ZECT_USERNAME and ZECT_PASSWORD environment variables.",
        )
    # Email/username: case-insensitive so zinnia.com matches Zinnia.Com from .env
    username_ok = _safe_compare(req.username.strip().lower(), valid_user.lower())
    password_ok = _safe_compare(req.password, valid_pass)
    if username_ok and password_ok:
        token = secrets.token_urlsafe(32)
        _active_tokens.add(token)
        return LoginResponse(token=token, username=req.username)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
def logout(token: str = ""):
    _active_tokens.discard(token)
    return {"status": "logged_out"}


@router.get("/verify")
def verify(token: str = ""):
    if token in _active_tokens:
        u, _ = _auth_creds()
        return {"valid": True, "username": u or ""}
    raise HTTPException(status_code=401, detail="Invalid or expired token")

"""Simple token-based authentication for ZECT."""

import os
import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory session tokens
_active_tokens: set[str] = set()

VALID_USERNAME = os.getenv("ZECT_USERNAME", "")
VALID_PASSWORD = os.getenv("ZECT_PASSWORD", "")

if not VALID_USERNAME or not VALID_PASSWORD:
    import warnings
    warnings.warn(
        "ZECT_USERNAME and ZECT_PASSWORD environment variables are not set. "
        "Login will be disabled until they are configured.",
        stacklevel=2,
    )


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    if not VALID_USERNAME or not VALID_PASSWORD:
        raise HTTPException(status_code=503, detail="Authentication not configured. Set ZECT_USERNAME and ZECT_PASSWORD environment variables.")
    username_ok = secrets.compare_digest(req.username, VALID_USERNAME)
    password_ok = secrets.compare_digest(req.password, VALID_PASSWORD)
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
        return {"valid": True, "username": VALID_USERNAME}
    raise HTTPException(status_code=401, detail="Invalid or expired token")

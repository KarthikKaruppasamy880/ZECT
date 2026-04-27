"""Simple token-based authentication for ZECT."""

import os
import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory session tokens
_active_tokens: set[str] = set()

VALID_USERNAME = os.getenv("ZECT_USERNAME", "karthik.karuppasamy@Zinnia.com")
VALID_PASSWORD = os.getenv("ZECT_PASSWORD", "Karthik@1234")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    if req.username == VALID_USERNAME and req.password == VALID_PASSWORD:
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

"""Require Bearer auth on /api/* except open paths."""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.infrastructure.auth.session_store import get_token_row
from app.infrastructure.database import SessionLocal

_OPEN_EXACT = frozenset({
    "/healthz",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
    "/api/auth/config",
    "/api/auth/oidc/login-url",
    "/api/review/webhook/github",
})

_OPEN_PREFIXES = (
    "/docs",
    "/api/auth/oidc/",
)


def auth_enforce_enabled() -> bool:
    flag = os.getenv("ZECT_AUTH_ENFORCE", "true").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return True


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/") or "/"
        if request.method == "OPTIONS":
            return await call_next(request)
        if not auth_enforce_enabled():
            return await call_next(request)
        if path in _OPEN_EXACT or any(path.startswith(p.rstrip("/")) for p in _OPEN_PREFIXES):
            return await call_next(request)
        # Allow verify/logout with query token (legacy UI)
        if path in ("/api/auth/verify", "/api/auth/logout", "/api/auth/me"):
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)

        auth = request.headers.get("Authorization") or ""
        token = ""
        if auth.startswith("Bearer ") and len(auth) > 10:
            token = auth[7:].strip()
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized — missing Bearer token"},
            )

        db = SessionLocal()
        try:
            row = get_token_row(db, token)
            if not row:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized — invalid or expired token"},
                )
            request.state.user_id = row.user_id
            request.state.username = row.username
            request.state.user_email = row.email
        finally:
            db.close()

        return await call_next(request)

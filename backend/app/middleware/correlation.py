"""HTTP correlation-id binding. Echoes X-Correlation-Id; never logs bodies."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.observability import bind_correlation, new_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = (request.headers.get("x-correlation-id") or "").strip() or new_id()
        bind_correlation(cid)
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = cid
        return response

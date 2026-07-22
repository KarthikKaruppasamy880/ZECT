"""Rate Limiting Middleware — Token-bucket rate limiter per IP/user."""

import os
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class RateLimiter:
    """Simple in-memory token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 60, burst: int = 10):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.burst = burst
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": float(burst), "last": time.monotonic()}
        )

    def allow(self, key: str) -> tuple[bool, dict]:
        bucket = self._buckets[key]
        now = time.monotonic()
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rate)
        bucket["last"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, {
                "X-RateLimit-Remaining": str(int(bucket["tokens"])),
                "X-RateLimit-Limit": str(self.burst),
            }
        retry_after = (1 - bucket["tokens"]) / self.rate if self.rate else 1
        return False, {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Limit": str(self.burst),
            "Retry-After": str(int(retry_after) + 1),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that applies rate limiting to API requests."""

    def __init__(self, app, requests_per_minute: int | None = None, burst: int | None = None):
        super().__init__(app)
        # Local/e2e: high defaults; override via ZECT_RATE_LIMIT_* env
        rpm = requests_per_minute if requests_per_minute is not None else _env_int("ZECT_RATE_LIMIT_RPM", 6000)
        burst_n = burst if burst is not None else _env_int("ZECT_RATE_LIMIT_BURST", 500)
        self.disabled = os.getenv("ZECT_RATE_LIMIT_DISABLED", "").lower() in ("1", "true", "yes")
        self.limiter = RateLimiter(requests_per_minute=rpm, burst=burst_n)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            self.disabled
            or not path.startswith("/api")
            or request.method == "OPTIONS"
            or path in ("/api/health", "/api/auth/config", "/api/auth/login")
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, headers = self.limiter.allow(client_ip)
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
            )
            for k, v in headers.items():
                response.headers[k] = v
            return response

        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response

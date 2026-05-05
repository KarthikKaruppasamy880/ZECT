"""Rate Limiting Middleware — Token-bucket rate limiter per IP/user."""

import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimiter:
    """Simple in-memory token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 60, burst: int = 10):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.burst = burst
        self._buckets: dict[str, dict] = defaultdict(lambda: {"tokens": burst, "last": time.monotonic()})

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
        else:
            retry_after = (1 - bucket["tokens"]) / self.rate
            return False, {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Limit": str(self.burst),
                "Retry-After": str(int(retry_after) + 1),
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that applies rate limiting to API requests."""

    def __init__(self, app, requests_per_minute: int = 120, burst: int = 20):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute=requests_per_minute, burst=burst)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for non-API routes (static files, health checks)
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        # Use IP as rate limit key (could be extended to user ID)
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}"

        allowed, headers = self.limiter.allow(key)
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

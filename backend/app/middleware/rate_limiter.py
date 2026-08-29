"""Rate Limiting Middleware — per-user token-bucket limiter with a stricter tier for LLM-cost paths.

Previously this keyed solely on request.client.host (IP). That meant:
  - multiple users behind one NAT/proxy/VPN shared a single bucket
  - a single user could dodge the limit entirely by rotating source IPs
  - every route shared one bucket, so cheap reads and expensive LLM calls
    (Ask, Plan, Build, Review, code review, blueprint) were throttled identically

AuthMiddleware runs before this middleware (added after it, and Starlette's
middleware order is LIFO — last added is outermost) and sets request.state.user_id
for any authenticated /api/* call, so we key on that when present and fall back
to IP only for pre-auth/unauthenticated paths.
"""

import os
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Path prefixes that spend real LLM tokens — get the stricter "expensive" bucket
# in addition to the general one. Keep in sync with routers that call OpenAI/Claude.
_EXPENSIVE_PREFIXES = (
    "/api/llm/",
    "/api/code-review",
    "/api/analysis/blueprint",
    "/api/analysis/docs",
    "/api/build",
    "/api/review",
    "/api/deploy",
    "/api/dream-engine",
    "/api/agent",
    "/api/mentrix",
    "/api/build-intel",
)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class RateLimiter:
    """Simple in-memory token bucket rate limiter, one bucket per key."""

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


def _is_expensive(path: str) -> bool:
    return any(path.startswith(p) for p in _EXPENSIVE_PREFIXES)


def _rate_limit_key(request: Request) -> tuple[str, bool]:
    """Return (bucket_key, is_authenticated). Prefer the authenticated user;
    fall back to client IP for pre-auth requests (login, health checks)."""
    user_id = getattr(request.state, "user_id", None)
    if user_id is not None:
        return f"user:{user_id}", True
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}", False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that applies per-user rate limiting to API requests.

    Two tiers, both keyed by user (or IP pre-auth):
      - general: every /api/* request (generous default)
      - expensive: LLM-cost paths only (much stricter default)
    A request must pass both tiers.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int | None = None,
        burst: int | None = None,
        llm_requests_per_minute: int | None = None,
        llm_burst: int | None = None,
    ):
        super().__init__(app)
        # Local/e2e: high defaults; override via ZECT_RATE_LIMIT_* env
        rpm = requests_per_minute if requests_per_minute is not None else _env_int("ZECT_RATE_LIMIT_RPM", 6000)
        burst_n = burst if burst is not None else _env_int("ZECT_RATE_LIMIT_BURST", 500)
        llm_rpm = llm_requests_per_minute if llm_requests_per_minute is not None else _env_int("ZECT_RATE_LIMIT_LLM_RPM", 20)
        llm_burst_n = llm_burst if llm_burst is not None else _env_int("ZECT_RATE_LIMIT_LLM_BURST", 10)
        self.disabled = os.getenv("ZECT_RATE_LIMIT_DISABLED", "").lower() in ("1", "true", "yes")
        self.limiter = RateLimiter(requests_per_minute=rpm, burst=burst_n)
        self.llm_limiter = RateLimiter(requests_per_minute=llm_rpm, burst=llm_burst_n)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            self.disabled
            or not path.startswith("/api")
            or request.method == "OPTIONS"
            or path in ("/api/health", "/api/auth/config", "/api/auth/login")
        ):
            return await call_next(request)

        key, _authenticated = _rate_limit_key(request)

        allowed, headers = self.limiter.allow(key)
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
            )
            for k, v in headers.items():
                response.headers[k] = v
            return response

        if _is_expensive(path):
            llm_allowed, llm_headers = self.llm_limiter.allow(key)
            if not llm_allowed:
                response = JSONResponse(
                    status_code=429,
                    content={
                        "detail": "LLM request rate limit exceeded for this account. "
                        "Please retry later or check Token Controls for your budget.",
                    },
                )
                for k, v in llm_headers.items():
                    response.headers[f"X-LLM-{k.removeprefix('X-')}" if k.startswith("X-") else k] = v
                return response
            headers = {**headers, **{f"X-LLM-{k.removeprefix('X-')}": v for k, v in llm_headers.items() if k.startswith("X-")}}

        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response

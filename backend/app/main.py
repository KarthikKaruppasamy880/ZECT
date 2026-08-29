from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import traceback

# Load backend/.env regardless of process cwd (fixes auth/env when uvicorn cwd differs).
# override=True so CHATTERBOX_BASE_URL from .env wins over stale shell localhost values.
# Under a real pytest run, preserve auth/DB env set by conftest so .env cannot
# silently stomp test credentials (TI-001).
# Stray ZECT_PYTEST=1 left in an interactive shell must NOT preserve test@zect.local
# over backend/.env (that caused live login 401 for the configured local admin).
import os as _os_for_dotenv
import sys as _sys_for_dotenv

_backend_root = Path(__file__).resolve().parents[1]
_ZECT_PYTEST_FLAG = (_os_for_dotenv.getenv("ZECT_PYTEST") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
_PYTEST_RUNNER = (
    "PYTEST_CURRENT_TEST" in _os_for_dotenv.environ
    or bool((_os_for_dotenv.getenv("PYTEST_VERSION") or "").strip())
    or "pytest" in _sys_for_dotenv.modules
)
_UNDER_PYTEST = _ZECT_PYTEST_FLAG and _PYTEST_RUNNER
if _ZECT_PYTEST_FLAG and not _PYTEST_RUNNER:
    print(
        "[ZECT AUTH] Ignoring stray ZECT_PYTEST outside pytest — "
        "loading auth from backend/.env (interactive uvicorn)."
    )
_PRESERVE_ENV_KEYS = (
    "ZECT_USERNAME",
    "ZECT_PASSWORD",
    "ZECT_AUTH_MODE",
    "ZECT_AUTH_ENFORCE",
    "DATABASE_URL",
)
_saved_env = {
    k: _os_for_dotenv.environ[k]
    for k in _PRESERVE_ENV_KEYS
    if _UNDER_PYTEST and k in _os_for_dotenv.environ
}
_PACKAGED = (_os_for_dotenv.getenv("ZECT_PACKAGED") or "").strip() in ("1", "true", "yes")
_user_data = (_os_for_dotenv.getenv("ZECT_USER_DATA") or "").strip()
if _PACKAGED:
    # Never load installer-tree .env (secrets). Optional per-user config only.
    if _user_data:
        from pathlib import Path as _P

        _user_env = _P(_user_data) / "config" / ".env"
        if _user_env.is_file():
            load_dotenv(_user_env, override=False)
else:
    load_dotenv(_backend_root / ".env", override=True)
if _saved_env:
    _os_for_dotenv.environ.update(_saved_env)
_auth_user = (_os_for_dotenv.getenv("ZECT_USERNAME") or "").strip()
if _auth_user and not _UNDER_PYTEST:
    print(f"[ZECT AUTH] Local login identity: {_auth_user}")

# Initialize encryption vault (must be before other imports that use secrets)
from app.security.vault import vault
try:
    _ = vault.get_key()
except Exception as e:
    raise RuntimeError(f"❌ Failed to initialize encryption vault: {e}")

from app.infrastructure.database import init_db, SessionLocal
from app.models import Project, Repo, Rule
from app.api import register_routers
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.correlation import CorrelationIdMiddleware

app = FastAPI(title="ZECT API", version="3.0.0", redirect_slashes=False)

# Rate limiting (env: ZECT_RATE_LIMIT_RPM / BURST / DISABLED) — high local defaults for e2e
# NOTE: added BEFORE CORS so CORS wraps everything (middleware order is LIFO)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# CORS — must be the LAST middleware added so it is the OUTERMOST wrapper.
# This ensures CORS headers are present on ALL responses including 500 errors.
# ✅ SECURITY: Whitelist only trusted origins, not "*"
import os
_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")

if os.getenv("ENV") == "production":
    # Override with production origins
    _ALLOWED_ORIGINS = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "https://yourdomain.com,https://app.yourdomain.com"
    ).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,  # ✅ Whitelist only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],  # ✅ Explicit methods
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Correlation-Id"],
    # Browsers only expose a small safe-listed set of response headers to JS
    # by default (Cache-Control, Content-Type, etc.) — any custom header,
    # like X-Mentrix-TTS-Engine, is invisible to fetch()'s res.headers.get()
    # unless explicitly exposed here, even though the server did send it.
    expose_headers=[
        "X-Mentrix-TTS-Engine",
        "X-Mentrix-TTS-Content-Type",
        "X-Correlation-Id",
        "X-Zect-Preview-Kind",
        "X-Zect-Preview-Kind",
    ],
)

# ✅ Add additional security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    from app.infrastructure.observability import bind_correlation, current_correlation, new_id

    cid = (request.headers.get("x-correlation-id") or current_correlation() or "").strip() or new_id()
    bind_correlation(cid)
    response = await call_next(request)
    response.headers.setdefault("X-Correlation-Id", cid)

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Enforce HTTPS in production
    if os.getenv("ENV") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # XSS Protection (legacy, but doesn't hurt)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy (basic)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return JSON with explicit CORS headers.
    
    Without this, unhandled 500 errors may skip CORS middleware and the browser
    blocks the response entirely, showing a misleading 'CORS error'.
    """
    tb = traceback.format_exc()
    try:
        print(f"[ZECT ERROR] {request.method} {request.url}: {exc}\n{tb}")
    except UnicodeEncodeError:
        print(f"[ZECT ERROR] {request.method} {request.url}: {type(exc).__name__}")
    # Echoing back any Origin header (previously done unconditionally) bypasses
    # the CORSMiddleware allowlist above for this response class specifically —
    # only reflect it when it's actually on the allowlist, same policy as every
    # other response.
    origin = request.headers.get("origin", "")
    headers = {
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    if origin in _ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc).encode("ascii", "replace").decode("ascii"),
            "error_type": type(exc).__name__,
        },
        headers=headers,
    )

# Phase 1: thin api/ layer registers domain routers (no business logic here).
register_routers(app)


@app.get("/healthz")
async def healthz():
    from app.infrastructure.database import database_mode, engine as _db_engine

    mode = database_mode()
    return {
        "status": "ok",
        "product": "ZECT",
        "agent": "Mentrix",
        "database_mode": mode,
        "database_dialect": _db_engine.dialect.name,
        "database_lifecycle": (
            "alembic_upgrade_heads" if mode == "server_postgres" else "create_all_additive"
        ),
    }


DEMO_PROJECT_NAMES = frozenset(
    {
        "Policy Admin Modernization",
        "Claims Processing API",
        "Agent Portal Redesign",
        "Underwriting Rules Engine",
        "Customer Notifications Service",
        "Document Intelligence Pipeline",
    }
)


def purge_demo_projects():
    """Remove seeded demo projects by known name so dashboards show real work only."""
    db = SessionLocal()
    try:
        rows = db.query(Project).filter(Project.name.in_(DEMO_PROJECT_NAMES)).all()
        for p in rows:
            db.delete(p)
        if rows:
            db.commit()
            print(f"[ZECT] Purged {len(rows)} demo project(s)")
    finally:
        db.close()


def seed_demo_projects():
    """Only when ZECT_SEED_DEMO_PROJECTS=true (off by default)."""
    if os.getenv("ZECT_SEED_DEMO_PROJECTS", "").strip().lower() not in ("1", "true", "yes"):
        return
    db = SessionLocal()
    if db.query(Project).count() > 0:
        db.close()
        return
    demo = [
        {
            "name": "Policy Admin Modernization",
            "description": "Migrate legacy policy administration system to microservices architecture with React frontend and Node.js APIs.",
            "team": "Platform Engineering",
            "status": "active",
            "current_stage": "build",
            "completion_percent": 55.0,
            "token_savings": 38.0,
            "risk_alerts": 2,
            "repos": [
                {"owner": "KarthikKaruppasamy880", "repo_name": "ZECT"},
            ],
        },
        {
            "name": "Claims Processing API",
            "description": "Build a new claims intake and adjudication API with real-time validation and fraud detection hooks.",
            "team": "Claims Engineering",
            "status": "active",
            "current_stage": "review",
            "completion_percent": 78.0,
            "token_savings": 42.0,
            "risk_alerts": 5,
            "repos": [
                {"owner": "KarthikKaruppasamy880", "repo_name": "ZEF"},
            ],
        },
        {
            "name": "Agent Portal Redesign",
            "description": "Redesign the insurance agent portal with improved UX, faster quote generation, and mobile-first responsive layout.",
            "team": "Product Engineering",
            "status": "active",
            "current_stage": "plan",
            "completion_percent": 28.0,
            "token_savings": 25.0,
            "risk_alerts": 1,
            "repos": [],
        },
        {
            "name": "Underwriting Rules Engine",
            "description": "Implement a configurable rules engine for automated underwriting decisions with audit trail and override capabilities.",
            "team": "Underwriting Tech",
            "status": "active",
            "current_stage": "deploy",
            "completion_percent": 92.0,
            "token_savings": 51.0,
            "risk_alerts": 0,
            "repos": [],
        },
        {
            "name": "Customer Notifications Service",
            "description": "Event-driven notification service for email, SMS, and push notifications across all Zinnia products.",
            "team": "Platform Engineering",
            "status": "completed",
            "current_stage": "deploy",
            "completion_percent": 100.0,
            "token_savings": 46.0,
            "risk_alerts": 0,
            "repos": [],
        },
        {
            "name": "Document Intelligence Pipeline",
            "description": "ML-powered document classification and data extraction pipeline for policy documents, claims forms, and regulatory filings.",
            "team": "AI/ML Engineering",
            "status": "active",
            "current_stage": "ask",
            "completion_percent": 8.0,
            "token_savings": 12.0,
            "risk_alerts": 3,
            "repos": [],
        },
    ]
    for d in demo:
        repos_data = d.pop("repos")
        project = Project(**d)
        db.add(project)
        db.flush()
        for r in repos_data:
            db.add(Repo(project_id=project.id, **r))
    db.commit()
    db.close()


def seed_default_rules():
    """Seed Mentrix default Rules Engine policies (idempotent by name)."""
    db = SessionLocal()
    defaults = [
        {
            "name": "mentrix-no-secrets-in-slack",
            "description": "Block MCP Slack posts that look like secrets",
            "rule_type": "security",
            "condition": r"(api[_-]?key|secret|password|token)\s*[:=]",
            "action": "block",
            "severity": "critical",
        },
        {
            "name": "mentrix-no-eval",
            "description": "Flag dangerous eval usage in review",
            "rule_type": "review",
            "condition": r"\beval\s*\(",
            "action": "warn",
            "severity": "high",
        },
        {
            "name": "mentrix-auto-review-kill-switch",
            "description": "Example block pattern for auto-review (inactive by default)",
            "rule_type": "review",
            "condition": r"^__never_match_mentrix_kill_switch__$",
            "action": "block",
            "severity": "medium",
        },
        {
            "name": "mentrix-sandbox-before-pr",
            "description": "Quality gate reminder — sandbox required before PR",
            "rule_type": "quality_gate",
            "condition": r"create.?pr|open.?pull.?request",
            "action": "warn",
            "severity": "high",
        },
    ]
    try:
        for d in defaults:
            exists = db.query(Rule).filter(Rule.name == d["name"]).first()
            if exists:
                continue
            db.add(Rule(is_active=d["name"] != "mentrix-auto-review-kill-switch", **d))
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db()
    purge_demo_projects()
    seed_demo_projects()
    seed_default_rules()
    try:
        from app.domains.personal_agent.schedule_ticker import start_schedule_ticker

        start_schedule_ticker()
    except Exception:  # noqa: BLE001
        pass


@app.on_event("shutdown")
def on_shutdown():
    try:
        from app.domains.personal_agent.schedule_ticker import stop_schedule_ticker

        stop_schedule_ticker()
    except Exception:  # noqa: BLE001
        pass

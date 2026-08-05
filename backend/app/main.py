from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import traceback

# Load backend/.env regardless of process cwd (fixes auth/env when uvicorn cwd differs).
_backend_root = Path(__file__).resolve().parents[1]
load_dotenv(_backend_root / ".env")

# Initialize encryption vault (must be before other imports that use secrets)
from app.security.vault import vault
try:
    _ = vault.get_key()
except Exception as e:
    raise RuntimeError(f"❌ Failed to initialize encryption vault: {e}")

from app.infrastructure.database import init_db, SessionLocal
from app.models import Project, Repo, Rule
from app.routers import projects, github, settings, analytics, repo_analysis, auth, llm, code_review
from app.routers import build_phase, review_phase, deploy_phase, token_controls, model_selection, orchestration, context_management
from app.routers import ultrareview, jira_integration, slack_integration, rules_engine, export_share, user_sessions, generated_outputs
from app.domains.audit import audit_trail
from app.routers import mcp, app_runner, file_explorer, git_ops, ci_monitor, autofix
from app.routers import memory, dream_engine, data_layer, data_flywheel, permissions, transfer, skills_engine
from app.routers import conversations, knowledge_base, playbooks, scheduler, secrets_manager, code_index, session_insights
from app.routers import repo_clone, repo_browser, build_intel
from app.routers import agent_mode, persistent_sessions, ci_remediation, sandbox, file_watcher, diff_viewer
from app.domains.voice import realtime
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.auth_middleware import AuthMiddleware
from app.routers import lattice as lattice_router
from app.routers import mentrix as mentrix_router
from app.domains.voice import voice_clone
from app.routers import confluence_integration, datadog_integration, email_integration

app = FastAPI(title="ZECT API", version="3.0.0", redirect_slashes=False)

# Rate limiting (env: ZECT_RATE_LIMIT_RPM / BURST / DISABLED) — high local defaults for e2e
# NOTE: added BEFORE CORS so CORS wraps everything (middleware order is LIFO)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

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
    allow_headers=["Content-Type", "Authorization", "Accept"],  # ✅ Explicit headers
    # Browsers only expose a small safe-listed set of response headers to JS
    # by default (Cache-Control, Content-Type, etc.) — any custom header,
    # like X-Mentrix-TTS-Engine, is invisible to fetch()'s res.headers.get()
    # unless explicitly exposed here, even though the server did send it.
    expose_headers=["X-Mentrix-TTS-Engine"],
)

# ✅ Add additional security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

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

app.include_router(projects.router)
app.include_router(github.router)
app.include_router(settings.router)
app.include_router(analytics.router)
app.include_router(repo_analysis.router)
app.include_router(auth.router)
app.include_router(llm.router)
app.include_router(code_review.router)
app.include_router(code_review.code_review_alias)
app.include_router(build_phase.router)
app.include_router(review_phase.router)
app.include_router(deploy_phase.router)
app.include_router(token_controls.router)
app.include_router(model_selection.router)
app.include_router(orchestration.router)
app.include_router(context_management.router)

# Enterprise routers
app.include_router(audit_trail.router)
app.include_router(ultrareview.router)
app.include_router(jira_integration.router)
app.include_router(slack_integration.router)
app.include_router(rules_engine.router)
app.include_router(export_share.router)
app.include_router(user_sessions.router)
app.include_router(generated_outputs.router)
app.include_router(mcp.router)
app.include_router(app_runner.router)
app.include_router(file_explorer.router)
app.include_router(git_ops.router)
app.include_router(ci_monitor.router)
app.include_router(autofix.router)

# Zinnia Agentic Intelligence System
app.include_router(memory.router)
app.include_router(dream_engine.router)
app.include_router(data_layer.router)
app.include_router(data_flywheel.router)
app.include_router(permissions.router)
app.include_router(transfer.router)
app.include_router(skills_engine.router)

# Category C: New Features
app.include_router(conversations.router)
app.include_router(knowledge_base.router)
app.include_router(playbooks.router)
app.include_router(scheduler.router)
app.include_router(secrets_manager.router)
app.include_router(code_index.router)
app.include_router(session_insights.router)

# Deep Repo Integration
app.include_router(repo_clone.router)
app.include_router(repo_browser.router)
app.include_router(build_intel.router)

# Gap Fixes — v2.0 features
app.include_router(agent_mode.router)
app.include_router(persistent_sessions.router)
app.include_router(ci_remediation.router)
app.include_router(sandbox.router)
app.include_router(realtime.router)
app.include_router(file_watcher.router)
app.include_router(diff_viewer.router)

# Mentrix platform
app.include_router(lattice_router.router)
app.include_router(mentrix_router.router)
app.include_router(voice_clone.router)
app.include_router(confluence_integration.router)
app.include_router(datadog_integration.router)
app.include_router(email_integration.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "product": "ZECT", "agent": "Mentrix"}


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

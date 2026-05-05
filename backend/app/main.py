from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import traceback

# Load backend/.env regardless of process cwd (fixes auth/env when uvicorn cwd differs).
_backend_root = Path(__file__).resolve().parents[1]
load_dotenv(_backend_root / ".env")

from app.database import init_db, SessionLocal
from app.models import Project, Repo
from app.routers import projects, github, settings, analytics, repo_analysis, auth, llm, code_review
from app.routers import build_phase, review_phase, deploy_phase, skills, token_controls, model_selection, orchestration, context_management
from app.routers import audit_trail, ultrareview, jira_integration, slack_integration, rules_engine, export_share, user_sessions, generated_outputs
from app.routers import mcp
from app.middleware.rate_limiter import RateLimitMiddleware

app = FastAPI(title="ZECT API", version="2.0.0", redirect_slashes=False)

# Rate limiting: 120 requests/minute per IP, burst of 20
# NOTE: added BEFORE CORS so CORS wraps everything (middleware order is LIFO)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst=20)

# CORS — must be the LAST middleware added so it is the OUTERMOST wrapper.
# This ensures CORS headers are present on ALL responses including 500 errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return JSON with explicit CORS headers.
    
    Without this, unhandled 500 errors may skip CORS middleware and the browser
    blocks the response entirely, showing a misleading 'CORS error'.
    """
    tb = traceback.format_exc()
    print(f"[ZECT ERROR] {request.method} {request.url}: {exc}\n{tb}")
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "error_type": type(exc).__name__,
        },
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )

app.include_router(projects.router)
app.include_router(github.router)
app.include_router(settings.router)
app.include_router(analytics.router)
app.include_router(repo_analysis.router)
app.include_router(auth.router)
app.include_router(llm.router)
app.include_router(code_review.router)
app.include_router(build_phase.router)
app.include_router(review_phase.router)
app.include_router(deploy_phase.router)
app.include_router(skills.router)
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


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


def seed_demo_projects():
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


@app.on_event("startup")
def on_startup():
    init_db()
    seed_demo_projects()

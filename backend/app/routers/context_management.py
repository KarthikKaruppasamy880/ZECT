"""Context Management — Smart context loading per page and session state.

Was an in-memory dict (_context_store), global across every user and wiped on
every restart — now backed by ContextStoreEntry, scoped per user_id so one
user's Ask/Plan/Build context can't leak into another's, and persisted across
restarts. Unauthenticated callers (no bearer token) fall back to a shared
user_id=None bucket, matching the router's previous no-auth behavior exactly.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_optional_user
from app.infrastructure.database import get_db
from app.models import ContextStoreEntry
from app.services import context_store

router = APIRouter(prefix="/api/context", tags=["context"])


def _user_id(user: CurrentUser | None) -> int | None:
    return user.user_id if user else None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ContextEntry(BaseModel):
    key: str
    value: str
    page: str  # Which page this context belongs to
    expires_at: str | None = None


class SessionContext(BaseModel):
    page: str
    entries: list[ContextEntry]
    total_tokens_estimated: int


class SaveContextRequest(BaseModel):
    page: str
    key: str
    value: str


class LoadContextRequest(BaseModel):
    page: str
    keys: list[str] | None = None  # None = load all for page


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/save")
def save_context(
    req: SaveContextRequest,
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Save context for a specific page (upsert by user_id+page+key)."""
    context_store.save(db, _user_id(user), req.page, req.key, req.value)
    return {"saved": True, "page": req.page, "key": req.key}


@router.post("/load", response_model=SessionContext)
def load_context(
    req: LoadContextRequest,
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Load context for a specific page."""
    stored = context_store.load(db, _user_id(user), req.page, req.keys)
    entries = [ContextEntry(key=k, value=v, page=req.page) for k, v in stored.items()]

    # Rough token estimation (4 chars ~ 1 token)
    total_chars = sum(len(e.value) for e in entries)
    token_estimate = total_chars // 4

    return SessionContext(
        page=req.page,
        entries=entries,
        total_tokens_estimated=token_estimate,
    )


@router.delete("/clear/{page}")
def clear_context(
    page: str,
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Clear all context for a page."""
    db.query(ContextStoreEntry).filter(
        ContextStoreEntry.user_id == _user_id(user), ContextStoreEntry.page == page
    ).delete()
    db.commit()
    return {"cleared": True, "page": page}


@router.get("/pages")
def list_pages_with_context(
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """List all pages that have stored context."""
    rows = db.query(ContextStoreEntry).filter(ContextStoreEntry.user_id == _user_id(user)).all()
    by_page: dict[str, list] = {}
    for r in rows:
        by_page.setdefault(r.page, []).append(r.value)

    return [
        {
            "page": page,
            "entries_count": len(values),
            "estimated_tokens": sum(len(v) for v in values) // 4,
        }
        for page, values in by_page.items()
    ]


@router.get("/recommendations/{page}")
def get_context_recommendations(
    page: str,
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Get recommended context to load for a specific page."""
    recommendations = {
        "ask": ["repo_analysis", "project_description", "tech_stack"],
        "plan": ["repo_analysis", "project_description", "tech_stack", "constraints"],
        "build": ["plan_output", "tech_stack", "file_structure", "coding_standards"],
        "review": ["code_context", "project_standards", "security_requirements"],
        "deploy": ["infrastructure", "environment_config", "deployment_history"],
        "blueprint": ["repo_analysis", "multi_repo_analysis", "architecture_notes"],
        "skills": ["detected_patterns", "project_conventions"],
    }

    currently_loaded = [
        r.key
        for r in db.query(ContextStoreEntry)
        .filter(ContextStoreEntry.user_id == _user_id(user), ContextStoreEntry.page == page)
        .all()
    ]

    return {
        "page": page,
        "recommended_keys": recommendations.get(page, []),
        "currently_loaded": currently_loaded,
    }

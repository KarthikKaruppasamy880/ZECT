"""Context Management — Smart context loading per page and session state."""

import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Setting
from datetime import datetime, timezone

router = APIRouter(prefix="/api/context", tags=["context"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# In-memory context store (per-session, resets on restart)
# In production, this would be Redis or database-backed
_context_store: dict[str, dict[str, str]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/save")
def save_context(req: SaveContextRequest):
    """Save context for a specific page."""
    page_key = f"page:{req.page}"
    if page_key not in _context_store:
        _context_store[page_key] = {}
    _context_store[page_key][req.key] = req.value
    return {"saved": True, "page": req.page, "key": req.key}


@router.post("/load", response_model=SessionContext)
def load_context(req: LoadContextRequest):
    """Load context for a specific page."""
    page_key = f"page:{req.page}"
    stored = _context_store.get(page_key, {})

    if req.keys:
        filtered = {k: v for k, v in stored.items() if k in req.keys}
    else:
        filtered = stored

    entries = [
        ContextEntry(key=k, value=v, page=req.page)
        for k, v in filtered.items()
    ]

    # Rough token estimation (4 chars ~ 1 token)
    total_chars = sum(len(e.value) for e in entries)
    token_estimate = total_chars // 4

    return SessionContext(
        page=req.page,
        entries=entries,
        total_tokens_estimated=token_estimate,
    )


@router.delete("/clear/{page}")
def clear_context(page: str):
    """Clear all context for a page."""
    page_key = f"page:{page}"
    if page_key in _context_store:
        del _context_store[page_key]
    return {"cleared": True, "page": page}


@router.get("/pages")
def list_pages_with_context():
    """List all pages that have stored context."""
    pages = []
    for key, entries in _context_store.items():
        if key.startswith("page:"):
            page_name = key[5:]
            total_chars = sum(len(v) for v in entries.values())
            pages.append({
                "page": page_name,
                "entries_count": len(entries),
                "estimated_tokens": total_chars // 4,
            })
    return pages


@router.get("/recommendations/{page}")
def get_context_recommendations(page: str):
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

    return {
        "page": page,
        "recommended_keys": recommendations.get(page, []),
        "currently_loaded": list(_context_store.get(f"page:{page}", {}).keys()),
    }

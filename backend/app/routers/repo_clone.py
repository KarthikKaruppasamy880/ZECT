"""Repo Clone Router — REST API for cloning, pulling, branching, deleting local repo workspaces."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Repo, Setting
from app.services.repo_clone import (
    clone_repo,
    pull_repo,
    checkout_branch,
    list_branches,
    delete_clone,
    get_clone_status,
)

router = APIRouter(prefix="/api/repos", tags=["repo-clone"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CloneRequest(BaseModel):
    repo_id: int
    branch: Optional[str] = None
    shallow: bool = True


class CheckoutRequest(BaseModel):
    branch: str


class CloneStatusResponse(BaseModel):
    repo_id: int
    owner: str
    repo_name: str
    clone_status: str
    local_path: Optional[str] = None
    clone_branch: Optional[str] = None
    clone_depth: Optional[int] = None
    disk_usage_mb: float = 0.0
    last_pulled_at: Optional[str] = None
    indexed_at: Optional[str] = None
    index_stats: dict = {}
    clone_error: Optional[str] = None
    total_files: int = 0
    total_lines: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_github_token(db: Session) -> Optional[str]:
    """Read the GitHub token from settings (configured via Settings page)."""
    setting = db.query(Setting).filter(Setting.key == "github_token").first()
    if setting and setting.value:
        return setting.value
    return os.getenv("GITHUB_TOKEN")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/clone")
def clone(req: CloneRequest, db: Session = Depends(get_db)):
    """Clone a GitHub repo to the local workspace directory."""
    token = _get_github_token(db)
    result = clone_repo(db, req.repo_id, branch=req.branch, shallow=req.shallow, token=token)
    if "error" in result and result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{repo_id}/pull")
def pull(repo_id: int, db: Session = Depends(get_db)):
    """Pull latest changes for a cloned repo."""
    token = _get_github_token(db)
    result = pull_repo(db, repo_id, token=token)
    if "error" in result and result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{repo_id}/status")
def status(repo_id: int, db: Session = Depends(get_db)):
    """Get clone status + disk usage + last pulled for a repo."""
    result = get_clone_status(db, repo_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{repo_id}/branches")
def branches(repo_id: int, db: Session = Depends(get_db)):
    """List branches (local + remote) for a cloned repo."""
    result = list_branches(db, repo_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{repo_id}/checkout")
def checkout(repo_id: int, req: CheckoutRequest, db: Session = Depends(get_db)):
    """Checkout a specific branch in the cloned repo."""
    result = checkout_branch(db, repo_id, req.branch)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/{repo_id}/clone")
def delete(repo_id: int, db: Session = Depends(get_db)):
    """Delete the local clone from disk and reset tracking."""
    result = delete_clone(db, repo_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{repo_id}/index")
def index(repo_id: int, db: Session = Depends(get_db)):
    """Index code symbols in a cloned repo for search and context injection."""
    from app.services.auto_indexer import index_repo as do_index
    result = do_index(db, repo_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/cloned")
def list_cloned(db: Session = Depends(get_db)):
    """List all repos that have been cloned locally."""
    repos = db.query(Repo).filter(Repo.clone_status == "cloned").all()
    return [
        {
            "repo_id": r.id,
            "owner": r.owner,
            "repo_name": r.repo_name,
            "project_id": r.project_id,
            "clone_branch": r.clone_branch,
            "local_path": r.local_path,
            "disk_usage_mb": r.disk_usage_mb or 0.0,
            "last_pulled_at": str(r.last_pulled_at) if r.last_pulled_at else None,
            "total_files": r.total_files or 0,
            "total_lines": r.total_lines or 0,
        }
        for r in repos
    ]

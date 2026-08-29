"""Repo Clone Router — REST API for cloning, pulling, branching, deleting local repo workspaces."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser
from app.infrastructure.budget import enforce_token_budget
from app.infrastructure.database import get_db
from app.models import Repo, Setting
from app.services.repo_clone import (
    checkout_branch,
    clone_repo,
    delete_clone,
    get_clone_status,
    list_branches,
    pull_repo,
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
    # require_clean (default) | stash | force_discard
    dirty_action: str = "require_clean"


class RegisterLocalRequest(BaseModel):
    project_id: int
    local_path: str
    role: str = ""


class DiscoverRequest(BaseModel):
    root: str
    max_depth: int = 3


class CloneUrlRequest(BaseModel):
    project_id: int
    git_url: str
    destination: str = ""
    branch: str = ""


class AttachRepoRequest(BaseModel):
    repo_id: int


class PrWorktreeRequest(BaseModel):
    pr_number: int
    head_branch: str
    head_sha: str = ""


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
    """Checkout a branch with dirty-working-tree protection (default: require_clean)."""
    from app.services.repo_onboarding import safe_checkout

    result = safe_checkout(
        db, repo_id=repo_id, branch=req.branch, action=req.dirty_action or "require_clean"
    )
    if not result.get("ok"):
        status = 409 if result.get("error") == "dirty_working_tree" else 400
        raise HTTPException(status_code=status, detail=result)
    return result


@router.delete("/{repo_id}/clone")
def delete(repo_id: int, db: Session = Depends(get_db)):
    """Delete the local clone from disk and reset tracking."""
    result = delete_clone(db, repo_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{repo_id}/index")
def index(
    repo_id: int,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Index code symbols (free, regex-based) and build the semantic index
    (real embedding-API cost) for a cloned repo — one action, both indexes."""
    from app.services.auto_indexer import index_repo as do_index
    from app.services.build_intel.indexer import index_repo_semantic

    result = do_index(db, repo_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    result["semantic_index"] = index_repo_semantic(db, repo_id, user_id=current_user.user_id)
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


@router.post("/register-local")
def register_local(req: RegisterLocalRequest, db: Session = Depends(get_db)):
    """Open existing local Git folder and bind to a Project (no duplicate)."""
    from app.services.repo_onboarding import register_local_repo

    try:
        out = register_local_repo(
            db, project_id=req.project_id, local_path=req.local_path, role=req.role
        )
    except ValueError as e:
        raise HTTPException(403, detail=str(e)) from e
    if not out.get("ok"):
        code = 403 if "denied" in str(out.get("error") or "").lower() else 400
        raise HTTPException(code, detail=out)
    return out


@router.post("/discover")
def discover(req: DiscoverRequest, db: Session = Depends(get_db)):
    """Discover Git repos under an explicit user-approved root."""
    from app.services.repo_onboarding import discover_local_repos

    try:
        out = discover_local_repos(db, root=req.root, max_depth=min(max(req.max_depth, 1), 5))
    except ValueError as e:
        raise HTTPException(403, detail=str(e)) from e
    if not out.get("ok"):
        raise HTTPException(400, detail=out)
    return out


@router.post("/clone-url")
def clone_url(req: CloneUrlRequest, db: Session = Depends(get_db)):
    """Clone from a Git URL into Project (optional destination under allowed roots)."""
    from app.services.repo_onboarding import clone_from_url

    token = _get_github_token(db)
    try:
        out = clone_from_url(
            db,
            project_id=req.project_id,
            git_url=req.git_url,
            destination=req.destination,
            branch=req.branch,
            token=token,
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e
    if not out.get("ok"):
        raise HTTPException(400, detail=out)
    return out


@router.get("/{repo_id}/identity")
def repo_identity(repo_id: int, db: Session = Depends(get_db)):
    """Current branch, HEAD SHA, dirty/clean for a registered repo."""
    from app.services.repo_onboarding import repo_git_identity

    out = repo_git_identity(db, repo_id)
    if not out.get("ok"):
        raise HTTPException(404 if out.get("error") == "repo_not_found" else 400, detail=out)
    return out


@router.post("/{repo_id}/pr-worktree")
def pr_worktree(repo_id: int, req: PrWorktreeRequest, db: Session = Depends(get_db)):
    """Create/reuse isolated worktree for a PR without modifying main checkout."""
    from app.services.repo_onboarding import ensure_pr_worktree

    out = ensure_pr_worktree(
        db,
        repo_id=repo_id,
        pr_number=req.pr_number,
        head_branch=req.head_branch,
        head_sha=req.head_sha,
    )
    if not out.get("ok"):
        raise HTTPException(400, detail=out)
    return out

"""Workspace-wide search across authorized Developer Workspace roots."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import get_db
from app.services.workspace_multi_root import search_workspace, workspace_problems

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class WorkspaceSearchRequest(BaseModel):
    pattern: str
    scope: str = "workspace"
    repo_ids: list[int] = Field(default_factory=list)
    active_repo_id: int | None = None
    current_file: str | None = None
    max_results: int = 80


@router.post("/search")
def workspace_search(
    req: WorkspaceSearchRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    return search_workspace(
        db,
        pattern=req.pattern,
        scope=req.scope,
        repo_ids=req.repo_ids,
        active_repo_id=req.active_repo_id,
        current_file=req.current_file,
        max_results=req.max_results,
    )


class WorkspaceProblemsRequest(BaseModel):
    repo_ids: list[int] = Field(default_factory=list)


@router.post("/problems")
def workspace_problems_endpoint(
    req: WorkspaceProblemsRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    return workspace_problems(db, repo_ids=req.repo_ids)

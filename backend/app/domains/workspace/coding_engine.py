"""Coding engine HTTP surface — health + workspace provision/dispose (Phase 2 Stage A).

Public provider values: mock | remote. No third-party product names in payloads.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.adapters.coding_runtime import coding_engine_health, get_coding_runtime, selected_coding_engine
from app.adapters.coding_engine_remote import CodingEngineConfigError
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.services.coding_engine.workspace import WorkspaceError, dispose_worktree, provision_worktree

router = APIRouter(prefix="/api/coding-engine", tags=["coding-engine"])


class ProvisionRequest(BaseModel):
    repo_path: str = Field(..., min_length=1)
    run_id: str | None = None


class DisposeRequest(BaseModel):
    workspace_id: str = Field(..., min_length=1)
    repo_path: str | None = None
    workspace_path: str | None = None
    preserve_artifacts: bool = True


@router.get("/health")
def engine_health(_user: CurrentUser = Depends(get_current_user)):
    """Engine readiness — never returns remote credentials."""
    body = coding_engine_health()
    body["selected"] = selected_coding_engine()
    return body


@router.post("/workspaces")
def create_workspace(req: ProvisionRequest, _user: CurrentUser = Depends(get_current_user)):
    try:
        ws = provision_worktree(repo_path=req.repo_path, run_id=req.run_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {
        "workspace_id": ws.workspace_id,
        "path": ws.path,
        "branch": ws.branch,
        "repo_path": ws.repo_path,
        "artifact_dir": ws.artifact_dir,
        "isolation": "worktree",
        "provider": selected_coding_engine(),
    }


@router.post("/workspaces/dispose")
def remove_workspace(req: DisposeRequest, _user: CurrentUser = Depends(get_current_user)):
    try:
        result = dispose_worktree(
            workspace_id=req.workspace_id,
            repo_path=req.repo_path,
            workspace_path=req.workspace_path,
            preserve_artifacts=req.preserve_artifacts,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return result


@router.get("/runtime")
def runtime_info(_user: CurrentUser = Depends(get_current_user)):
    """Confirm factory selection; remote misconfig returns 503."""
    try:
        rt = get_coding_runtime()
    except CodingEngineConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    provider = getattr(rt, "provider_name", selected_coding_engine())
    return {"provider": provider, "ready": True}

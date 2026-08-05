"""Coding engine HTTP surface — health + workspace provision/dispose (Phase 2 Stage A).

Public provider values: mock | remote. No third-party product names in payloads.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.adapters.coding_runtime import coding_engine_health, get_coding_runtime, selected_coding_engine
from app.adapters.coding_engine_remote import CodingEngineConfigError, CodingEngineRequestError
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


class StartEngineRunRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    workspace: str = ""


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


@router.post("/runs")
def start_engine_run(req: StartEngineRunRequest, _user: CurrentUser = Depends(get_current_user)):
    """Start a coding-engine run (mock or remote). Returns ZECT-shaped events only."""
    try:
        rt = get_coding_runtime()
        run_id = rt.start_run(req.goal.strip(), workspace=req.workspace or "")
        return rt.get_run(run_id)
    except CodingEngineConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CodingEngineRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
def get_engine_run(run_id: str, _user: CurrentUser = Depends(get_current_user)):
    try:
        rt = get_coding_runtime()
        return rt.get_run(run_id)
    except CodingEngineConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None
    except CodingEngineRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/runs/{run_id}/events")
def list_engine_events(
    run_id: str,
    after: int = 0,
    _user: CurrentUser = Depends(get_current_user),
):
    """Reconnect-friendly event list (sequence_id > after)."""
    try:
        rt = get_coding_runtime()
        events = rt.stream_events(run_id, after=after)
        return {
            "run_id": run_id,
            "events": [
                {
                    "sequence_id": e.sequence_id,
                    "event": e.event,
                    "message": e.message,
                    "phase": e.phase,
                    "data": e.data,
                }
                for e in events
            ],
        }
    except CodingEngineConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None
    except CodingEngineRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/runs/{run_id}")
def cancel_engine_run(run_id: str, _user: CurrentUser = Depends(get_current_user)):
    try:
        rt = get_coding_runtime()
        rt.cancel_run(run_id)
        return rt.get_run(run_id)
    except CodingEngineConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None
    except CodingEngineRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

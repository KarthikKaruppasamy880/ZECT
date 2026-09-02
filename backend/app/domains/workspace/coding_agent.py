"""Mentrix Coding Agent HTTP surface — session API."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.adapters.coding_runtime import get_mentrix_native_runtime
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/coding-agent", tags=["coding-agent"])


class SessionCreate(BaseModel):
    goal: str = Field(..., min_length=1)
    workspace: str = Field(..., min_length=1)
    model: str | None = None
    auto_approve_edits: bool = True
    max_steps: int | None = None
    expected_files: list[str] = Field(default_factory=list)
    project_id: int | None = None
    skill_id: int | None = None
    project_key: str | None = None


class SessionMessage(BaseModel):
    message: str = Field(..., min_length=1)


class SessionApprove(BaseModel):
    action_id: str = Field(..., min_length=1)
    approve: bool = True


class ResolveMentionsIn(BaseModel):
    text: str = Field(..., min_length=1)
    workspace: str = Field(..., min_length=1)
    project_key: str = ""
    work_item_id: int | None = None


@router.post("/sessions")
def create_session(req: SessionCreate, _user: CurrentUser = Depends(get_current_user)):
    """Start a Mentrix Coding Agent session against a workspace path."""
    rt = get_mentrix_native_runtime()
    try:
        run_id = rt.start_run(
            req.goal.strip(),
            workspace=req.workspace.strip(),
            model=req.model,
            auto_approve_edits=req.auto_approve_edits,
            max_steps=req.max_steps,
            expected_files=req.expected_files,
            project_id=req.project_id,
            skill_id=req.skill_id,
            project_key=req.project_key,
        )
        return rt.get_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/sessions/{session_id}")
def get_session(session_id: str, _user: CurrentUser = Depends(get_current_user)):
    rt = get_mentrix_native_runtime()
    try:
        return rt.get_run(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found") from None


@router.get("/sessions/{session_id}/stream")
def stream_session(
    session_id: str,
    after: int = Query(0, ge=0),
    _user: CurrentUser = Depends(get_current_user),
):
    """SSE stream of Mentrix Coding Agent events."""
    rt = get_mentrix_native_runtime()
    try:
        rt.get_run(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found") from None

    def gen() -> Iterator[str]:
        cursor = after
        idle = 0
        while idle < 600:
            try:
                events = rt.stream_events(session_id, after=cursor)
            except KeyError:
                yield f"event: error\ndata: {json.dumps({'error': 'session_not_found'})}\n\n"
                return
            if events:
                idle = 0
                for ev in events:
                    cursor = ev.sequence_id
                    payload = {
                        "sequence_id": ev.sequence_id,
                        "event": ev.event,
                        "message": ev.message,
                        "phase": ev.phase,
                        "data": ev.data,
                    }
                    yield f"event: {ev.event}\ndata: {json.dumps(payload, default=str)}\n\n"
                    if ev.event in ("completed", "failed", "cancelled"):
                        return
            else:
                idle += 1
                try:
                    status = rt.get_run(session_id).get("status")
                except KeyError:
                    return
                if status in ("completed", "failed", "cancelled"):
                    yield f"event: done\ndata: {json.dumps({'status': status})}\n\n"
                    return
                yield f"event: ping\ndata: {json.dumps({'after': cursor})}\n\n"
                time.sleep(0.5)
        yield f"event: timeout\ndata: {json.dumps({'after': cursor})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sessions/{session_id}/message")
def session_message(
    session_id: str,
    req: SessionMessage,
    _user: CurrentUser = Depends(get_current_user),
):
    rt = get_mentrix_native_runtime()
    try:
        rt.submit_message(session_id, req.message.strip())
        return rt.get_run(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found") from None


@router.post("/sessions/{session_id}/approve")
def session_approve(
    session_id: str,
    req: SessionApprove,
    _user: CurrentUser = Depends(get_current_user),
):
    rt = get_mentrix_native_runtime()
    try:
        if req.approve:
            rt.approve_action(session_id, req.action_id)
        else:
            rt.reject_action(session_id, req.action_id)
        return rt.get_run(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found") from None


@router.post("/sessions/{session_id}/cancel")
def session_cancel(session_id: str, _user: CurrentUser = Depends(get_current_user)):
    rt = get_mentrix_native_runtime()
    try:
        rt.cancel_run(session_id)
        return rt.get_run(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session_not_found") from None


class MissionCreate(BaseModel):
    goal: str = Field(..., min_length=1)
    project_id: int | None = None
    work_item_id: int | None = None
    roots: list[dict] = Field(default_factory=list)
    patches_by_repo: dict[str, list] | None = None
    plan: str = ""
    workspace_parent: str = ""
    propose_if_empty: bool = False

    @model_validator(mode="before")
    @classmethod
    def accept_ui_aliases(cls, data: Any) -> Any:
        """Accept PLAN UI aliases (plan, workspace_parent, propose_if_empty)."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if not str(out.get("plan") or "").strip():
            alias_plan = out.get("plan")
            if alias_plan:
                out["plan"] = alias_plan
        if not str(out.get("workspace_parent") or "").strip():
            alias_ws = out.get("workspace_parent") or out.get("workspace_id")
            if alias_ws:
                out["workspace_parent"] = alias_ws
        if "propose_if_empty" not in out:
            if "propose_if_empty" in out:
                out["propose_if_empty"] = out["propose_if_empty"]
        return out


class MissionRepair(BaseModel):
    patches_by_repo: dict[str, list] = Field(default_factory=dict)


def _mission_roots(db: Session, req: MissionCreate) -> list[dict]:
    roots = list(req.roots or [])
    if roots:
        return roots
    if not req.project_id:
        return []
    from app.models import Repo

    rows = db.query(Repo).filter(Repo.project_id == int(req.project_id)).all()
    return [
        {
            "id": r.id,
            "label": r.repo_name or f"repo-{r.id}",
            "path": r.local_path or "",
            "local_path": r.local_path or "",
        }
        for r in rows
        if r.local_path
    ]


@router.post("/missions")
def create_mission(req: MissionCreate, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.lifecycle import start_mission
    from app.services.coding_engine.sync_pull import is_pull_sync_intent, sync_authorized_roots

    try:
        roots = _mission_roots(db, req)
        if is_pull_sync_intent(req.goal):
            return sync_authorized_roots(roots)
        mission = start_mission(
            goal=req.goal.strip(),
            roots=roots,
            plan=req.plan,
            patches_by_repo=req.patches_by_repo,
            work_item_id=req.work_item_id,
            project_id=req.project_id,
            workspace_parent=req.workspace_parent,
            propose_if_empty=bool(req.propose_if_empty),
        )
        if req.work_item_id:
            # Canonical Mission-identity pointer -- lets the WorkItem always
            # resolve "its" Mission (see WorkItem.coding_mission_id).
            from app.models import WorkItem

            wi = db.query(WorkItem).filter(WorkItem.id == req.work_item_id).first()
            if wi is not None:
                wi.coding_mission_id = str(mission.get("id") or "")
                db.commit()
        return mission
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TypeError as exc:
        raise HTTPException(status_code=500, detail=f"mission_start_contract:{exc}") from exc


@router.get("/missions/{mission_id}")
def read_mission(mission_id: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.lifecycle import get_mission

    try:
        return get_mission(mission_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="mission_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/approve-plan")
def mission_approve_plan(mission_id: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.lifecycle import approve_plan

    try:
        return approve_plan(mission_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="mission_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/approve-git")
def mission_approve_git(mission_id: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.lifecycle import approve_git

    try:
        return approve_git(mission_id, commit=True, push=True)
    except KeyError:
        raise HTTPException(status_code=404, detail="mission_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/cancel")
def mission_cancel(mission_id: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.lifecycle import cancel_mission

    try:
        return cancel_mission(mission_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="mission_not_found") from None


@router.post("/missions/{mission_id}/resume")
def mission_resume(mission_id: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.lifecycle import resume_mission

    try:
        return resume_mission(mission_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="mission_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/retry")
def mission_retry(mission_id: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.lifecycle import retry_mission

    try:
        return retry_mission(mission_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="mission_not_found") from None


@router.post("/missions/{mission_id}/repair")
def mission_repair(
    mission_id: str,
    req: MissionRepair,
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.coding_engine.lifecycle import repair_and_retry

    try:
        return repair_and_retry(mission_id, req.patches_by_repo)
    except KeyError:
        raise HTTPException(status_code=404, detail="mission_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


class PlanSaveIn(BaseModel):
    work_item_or_run: str = Field(..., min_length=1)
    title: str = "coding"
    markdown: str = Field(..., min_length=1)
    meta: dict = Field(default_factory=dict)
    workspace: str = ""


def _authorized_workspace(workspace: str) -> str:
    """A plan is written into the target repo, so the same allowed-roots jail
    every other workspace-writing endpoint uses applies here too."""
    ws = (workspace or "").strip()
    if not ws:
        return ""
    from app.infrastructure.allowed_paths import path_under_allowed_roots

    try:
        return str(path_under_allowed_roots(ws))
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/plans")
def coding_plans(workspace: str = "", _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.plan_store import list_plans

    return {"ok": True, "plans": list_plans(workspace=_authorized_workspace(workspace))}


@router.get("/plans/{plan_id}")
def coding_plan_get(
    plan_id: str, workspace: str = "", _user: CurrentUser = Depends(get_current_user)
):
    from app.services.coding_engine.plan_store import load_plan

    try:
        return load_plan(plan_id, workspace=_authorized_workspace(workspace))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="plan_not_found") from None


@router.post("/plans")
def coding_plan_save(req: PlanSaveIn, _user: CurrentUser = Depends(get_current_user)):
    from app.services.coding_engine.plan_store import save_plan

    try:
        return save_plan(
            work_item_or_run=req.work_item_or_run,
            title=req.title,
            markdown=req.markdown,
            meta=req.meta,
            workspace=_authorized_workspace(req.workspace),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runtime-recipes")
def coding_runtime_recipes(root: str = Query(..., min_length=1), _user: CurrentUser = Depends(get_current_user)):
    from app.infrastructure.allowed_paths import path_under_allowed_roots
    from app.services.workspace.runtime_discovery import discover_runtime_recipes

    try:
        path_under_allowed_roots(root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return discover_runtime_recipes(root)


@router.post("/context/resolve-mentions")
def coding_resolve_mentions(
    req: ResolveMentionsIn,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """Resolve every @mention in a composer message against real data and
    return a truthful, bounded ContextPack -- the same one that should be
    prepended to the goal/question actually sent to the model. Never 500s on
    a bad individual mention; each becomes an "unresolved" item instead."""
    from app.infrastructure.allowed_paths import path_under_allowed_roots
    from app.services.coding_engine.mention_resolver import resolve_mentions
    from app.services.work_items.context_engine import MentrixContextEngine

    try:
        root = path_under_allowed_roots(req.workspace)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    items = resolve_mentions(
        req.text,
        workspace=root,
        project_key=req.project_key or "",
        work_item_id=req.work_item_id,
        db=db,
    )
    pack = MentrixContextEngine().build(work_item_id=req.work_item_id, extra_items=items)
    return {"ok": True, "pack": pack.to_dict()}

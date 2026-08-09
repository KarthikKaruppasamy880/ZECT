"""Mentrix Coding Agent HTTP surface — session API."""

from __future__ import annotations

import json
import time
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.adapters.coding_runtime import get_mentrix_native_runtime
from app.infrastructure.auth.deps import CurrentUser, get_current_user

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

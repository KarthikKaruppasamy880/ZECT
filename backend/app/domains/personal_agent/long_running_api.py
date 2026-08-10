"""Long-running Mentrix engineering run API — start/pause/resume/cancel/status."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication
from app.infrastructure.database import get_db
from app.services.mentrix.automation_loops.types import LoopBudget
from app.services.mentrix.long_running_runtime import LongRunningAgentRuntime, build_synthetic_operations
from app.workers.long_running_worker import run_long_running_batch_in_background

router = APIRouter(prefix="/api/mentrix/long-running", tags=["mentrix-long-running"])


class StartIn(BaseModel):
    work_item_id: int
    operation_count: int = Field(default=0, ge=0, le=500)
    operations: Optional[list[dict[str, Any]]] = None
    worktree_path: str = ""
    base_commit_sha: str = ""
    current_commit_sha: str = ""
    autonomy: str = "L1"
    model_profile: str = "QUALITY"
    synthetic: bool = True
    background: bool = False
    max_ops_batch: int = 25


class TickIn(BaseModel):
    worker_id: str = "api-worker"
    max_ops: int = 1
    inject_failure: Optional[str] = None
    switch_model: Optional[str] = None
    allow_model_switch: bool = False
    force_high_risk: Optional[str] = None
    data_classification: str = "internal"
    tokens_delta: int = 0
    cost_delta: float = 0.0
    runtime_delta_seconds: float = 0.0


@router.post("/start")
@require_authentication
def start_run(
    body: StartIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = getattr(current_user, "user_id", None)
    ops = list(body.operations or [])
    if not ops and body.operation_count > 0:
        ops = build_synthetic_operations(body.operation_count)
    rt = LongRunningAgentRuntime(db)
    try:
        out = rt.start(
            work_item_id=body.work_item_id,
            user_id=uid,
            worktree_path=body.worktree_path,
            base_commit_sha=body.base_commit_sha,
            current_commit_sha=body.current_commit_sha,
            operations=ops or None,
            autonomy=body.autonomy,
            model_profile=body.model_profile,
            budget=LoopBudget(max_actions=max(200, len(ops) + 20)),
            synthetic=body.synthetic,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)[:300]) from exc

    if body.background:
        background_tasks.add_task(
            run_long_running_batch_in_background,
            out["run_id"],
            worker_id=f"bg-{uid or 0}",
            max_ops=body.max_ops_batch,
        )
    return {"ok": True, **out}


@router.get("/{run_id}")
@require_authentication
def get_run(run_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    rt = LongRunningAgentRuntime(db)
    try:
        row = rt.get(run_id)
    except LookupError:
        raise HTTPException(404, "run_not_found") from None
    uid = getattr(current_user, "user_id", None)
    if row.user_id and uid and row.user_id != uid:
        raise HTTPException(403, "forbidden")
    return rt.serialize(row)


@router.post("/{run_id}/pause")
@require_authentication
def pause_run(run_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return LongRunningAgentRuntime(db).pause(run_id)


@router.post("/{run_id}/resume")
@require_authentication
def resume_run(run_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return LongRunningAgentRuntime(db).resume(run_id)


@router.post("/{run_id}/cancel")
@require_authentication
def cancel_run(run_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return LongRunningAgentRuntime(db).cancel(run_id)


@router.post("/{run_id}/tick")
@require_authentication
def tick_run(run_id: str, body: TickIn, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return LongRunningAgentRuntime(db).tick(
        run_id,
        worker_id=body.worker_id,
        max_ops=body.max_ops,
        inject_failure=body.inject_failure,
        switch_model=body.switch_model,
        allow_model_switch=body.allow_model_switch,
        force_high_risk=body.force_high_risk,
        data_classification=body.data_classification,
        tokens_delta=body.tokens_delta,
        cost_delta=body.cost_delta,
        runtime_delta_seconds=body.runtime_delta_seconds,
    )


@router.post("/recover")
@require_authentication
def recover_runs(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """Backend restart recovery — expire leases; durable resume points remain."""
    return LongRunningAgentRuntime(db).recover_after_restart()

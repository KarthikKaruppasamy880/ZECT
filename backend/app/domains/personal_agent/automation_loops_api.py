"""Mentrix Automation Loops API — thin control plane over MentrixAutomationLoop."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication
from app.infrastructure.database import get_db
from app.models import LoopDefinition, LoopRun
from app.services.mentrix.automation_loops import get_loop_runtime, list_builtin_definitions
from app.services.mentrix.automation_loops.types import LoopCheckpoint

router = APIRouter(prefix="/api/mentrix/automation-loops", tags=["mentrix-automation-loops"])


class RunLoopIn(BaseModel):
    loop_key: str
    autonomy: Optional[str] = None
    prompt: str = ""
    dry_run: bool = False


class AutonomyPatch(BaseModel):
    autonomy_level: str = Field(..., description="L0|L1|L2|L3 — L2/L3 need allow flags")
    allow_l2: bool = False
    allow_l3: bool = False


def _ser_def(row: LoopDefinition) -> dict:
    return {
        "id": row.id,
        "key": row.key,
        "name": row.name,
        "description": row.description,
        "user_id": row.user_id,
        "autonomy_level": row.autonomy_level,
        "status": row.status,
        "target": row.target,
        "enabled": bool(row.enabled),
        "budget": __import__("json").loads(row.budget_json or "{}"),
        "policy": __import__("json").loads(row.policy_json or "{}"),
        "trigger": __import__("json").loads(row.trigger_json or "{}"),
        "checkpoint": LoopCheckpoint.from_dict(__import__("json").loads(row.checkpoint_json or "{}")).as_dict(),
    }


@router.get("")
@require_authentication
def list_loops(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """List builtin catalog + per-user LoopDefinition rows."""
    uid = getattr(current_user, "user_id", None)
    rt = get_loop_runtime()
    rows = rt.ensure_builtins(db, user_id=uid)
    return {
        "builtins": list_builtin_definitions(),
        "definitions": [_ser_def(r) for r in rows],
    }


@router.post("/run")
@require_authentication
def run_loop(body: RunLoopIn, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    uid = getattr(current_user, "user_id", None)
    if not uid:
        raise HTTPException(401, "User must be authenticated")
    out = get_loop_runtime().run_once(
        db,
        loop_key=body.loop_key.strip().lower(),
        user_id=uid,
        autonomy=body.autonomy,
        prompt=body.prompt,
        dry_run=body.dry_run,
    )
    return out


@router.post("/{loop_key}/pause")
@require_authentication
def pause_loop(loop_key: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return get_loop_runtime().pause(db, loop_key=loop_key, user_id=getattr(current_user, "user_id", None))


@router.post("/{loop_key}/resume")
@require_authentication
def resume_loop(loop_key: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return get_loop_runtime().resume(db, loop_key=loop_key, user_id=getattr(current_user, "user_id", None))


@router.post("/{loop_key}/kill")
@require_authentication
def kill_loop(loop_key: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return get_loop_runtime().kill(db, loop_key=loop_key, user_id=getattr(current_user, "user_id", None))


@router.patch("/{loop_key}/autonomy")
@require_authentication
def patch_autonomy(
    loop_key: str,
    body: AutonomyPatch,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    import json

    uid = getattr(current_user, "user_id", None)
    row = db.query(LoopDefinition).filter(LoopDefinition.key == loop_key, LoopDefinition.user_id == uid).first()
    if not row:
        raise HTTPException(404, "loop_not_found")
    level = body.autonomy_level.upper()
    if level in ("L2", "L3") and not (body.allow_l2 or body.allow_l3):
        raise HTTPException(400, "L2/L3 require explicit allow_l2/allow_l3 policy flags")
    if level == "L3" and not body.allow_l3:
        raise HTTPException(400, "L3 requires allow_l3=true")
    if level == "L2" and not body.allow_l2:
        raise HTTPException(400, "L2 requires allow_l2=true")
    policy = json.loads(row.policy_json or "{}")
    policy["autonomy_level"] = level
    policy["allow_l2"] = bool(body.allow_l2)
    policy["allow_l3"] = bool(body.allow_l3)
    policy["require_human_gate"] = level != "L3"
    row.policy_json = json.dumps(policy)
    row.autonomy_level = level
    db.commit()
    db.refresh(row)
    return _ser_def(row)


@router.get("/runs")
@require_authentication
def list_runs(
    limit: int = 40,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = getattr(current_user, "user_id", None)
    q = db.query(LoopRun)
    if uid is not None:
        q = q.filter(LoopRun.user_id == uid)
    rows = q.order_by(LoopRun.id.desc()).limit(min(limit, 100)).all()
    return {
        "runs": [
            {
                "id": r.id,
                "loop_definition_id": r.loop_definition_id,
                "autonomy_level": r.autonomy_level,
                "status": r.status,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ]
    }

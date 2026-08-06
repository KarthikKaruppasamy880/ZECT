"""Phase 10 Stage B — condition-based automation watches."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import AutomationWatch

router = APIRouter(prefix="/api/automation-watches", tags=["automation-watches"])


class WatchCreate(BaseModel):
    name: str
    description: str = ""
    condition_type: str = "keyword"
    condition_config: dict = {}
    action_type: str = "mentrix"
    action_config: dict = {}
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    max_attempts: int = 3


class WatchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition_config: Optional[dict] = None
    action_config: Optional[dict] = None
    is_active: Optional[bool] = None
    max_attempts: Optional[int] = None


class WatchEvaluate(BaseModel):
    text: str = ""
    context: dict = {}


def _to_dict(w: AutomationWatch) -> dict:
    return {
        "id": w.id,
        "user_id": w.user_id,
        "project_id": w.project_id,
        "name": w.name,
        "description": w.description,
        "condition_type": w.condition_type,
        "condition_config": w.condition_config or {},
        "action_type": w.action_type,
        "action_config": w.action_config or {},
        "is_active": w.is_active,
        "last_triggered_at": w.last_triggered_at.isoformat() if w.last_triggered_at else None,
        "trigger_count": w.trigger_count,
        "max_attempts": w.max_attempts,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "updated_at": w.updated_at.isoformat() if w.updated_at else None,
    }


@router.get("")
def list_watches(
    project_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(AutomationWatch)
    if project_id is not None:
        q = q.filter(AutomationWatch.project_id == project_id)
    if is_active is not None:
        q = q.filter(AutomationWatch.is_active == is_active)
    return [_to_dict(w) for w in q.order_by(AutomationWatch.id.desc()).all()]


@router.post("")
def create_watch(body: WatchCreate, db: Session = Depends(get_db)):
    w = AutomationWatch(
        name=body.name,
        description=body.description,
        condition_type=body.condition_type,
        condition_config=body.condition_config or {},
        action_type=body.action_type,
        action_config=body.action_config or {},
        project_id=body.project_id,
        user_id=body.user_id,
        max_attempts=body.max_attempts,
        is_active=True,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return _to_dict(w)


@router.patch("/{watch_id}")
def update_watch(watch_id: int, body: WatchUpdate, db: Session = Depends(get_db)):
    w = db.query(AutomationWatch).filter(AutomationWatch.id == watch_id).first()
    if not w:
        raise HTTPException(404, "Watch not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(w, k, v)
    w.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(w)
    return _to_dict(w)


@router.post("/{watch_id}/toggle")
def toggle_watch(watch_id: int, db: Session = Depends(get_db)):
    w = db.query(AutomationWatch).filter(AutomationWatch.id == watch_id).first()
    if not w:
        raise HTTPException(404, "Watch not found")
    w.is_active = not w.is_active
    db.commit()
    db.refresh(w)
    return _to_dict(w)


@router.post("/{watch_id}/evaluate")
def evaluate_watch(watch_id: int, body: WatchEvaluate, db: Session = Depends(get_db)):
    """Evaluate a watch condition; on match, record trigger (no unlimited authority)."""
    from app.security.emergency_stop import is_emergency_stop_active

    w = db.query(AutomationWatch).filter(AutomationWatch.id == watch_id).first()
    if not w:
        raise HTTPException(404, "Watch not found")
    if not w.is_active:
        return {"matched": False, "reason": "inactive", "watch": _to_dict(w)}
    if is_emergency_stop_active(db):
        return {"matched": False, "reason": "emergency_stop", "watch": _to_dict(w)}
    if (w.trigger_count or 0) >= (w.max_attempts or 3) > 0:
        return {"matched": False, "reason": "max_attempts", "watch": _to_dict(w)}

    cfg = w.condition_config or {}
    matched = False
    if w.condition_type == "keyword":
        needles = cfg.get("keywords") or cfg.get("keyword") or []
        if isinstance(needles, str):
            needles = [needles]
        text = (body.text or "").lower()
        matched = any(str(n).lower() in text for n in needles if n)
    elif w.condition_type == "finding":
        severity = (body.context or {}).get("severity") or ""
        want = (cfg.get("min_severity") or "high").lower()
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        matched = order.get(str(severity).lower(), 0) >= order.get(want, 3)
    else:
        matched = bool(cfg.get("always"))

    if not matched:
        return {"matched": False, "reason": "condition_false", "watch": _to_dict(w)}

    w.trigger_count = (w.trigger_count or 0) + 1
    w.last_triggered_at = datetime.now(timezone.utc)
    action_result = {"action_type": w.action_type, "status": "recorded"}
    if w.action_type == "mentrix":
        action_result["note"] = "Mentrix action queued via watch (permission-scoped; no interactive authority)"
    db.commit()
    db.refresh(w)
    return {"matched": True, "action": action_result, "watch": _to_dict(w)}

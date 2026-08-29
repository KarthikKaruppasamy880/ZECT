"""Scheduled Tasks — cron-based recurring sessions."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import Schedule, ScheduleRun

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    name: str
    description: str = ""
    schedule_type: str = "cron"
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    scheduled_time: Optional[str] = None
    task_type: str = "review"
    task_config: dict = {}
    playbook_id: Optional[int] = None
    project_id: Optional[int] = None
    max_attempts: int = 3

class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    task_config: Optional[dict] = None
    task_type: Optional[str] = None
    playbook_id: Optional[int] = None
    is_active: Optional[bool] = None
    max_attempts: Optional[int] = None
    next_run_at: Optional[str] = None


@router.get("")
def list_schedules(
    task_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all schedules."""
    try:
        q = db.query(Schedule)
        if task_type:
            q = q.filter(Schedule.task_type == task_type)
        if is_active is not None:
            q = q.filter(Schedule.is_active == is_active)
        if project_id:
            q = q.filter(Schedule.project_id == project_id)
        total = q.count()
        items = q.order_by(Schedule.created_at.desc()).offset(skip).limit(limit).all()
        return {"items": [_sched_to_dict(s) for s in items], "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_schedule(data: ScheduleCreate, db: Session = Depends(get_db)):
    """Create a new schedule."""
    try:
        if not data.playbook_id and not (data.task_type or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Provide task_type and/or playbook_id",
            )
        sched = Schedule(
            name=data.name,
            description=data.description,
            schedule_type=data.schedule_type,
            cron_expression=data.cron_expression,
            interval_minutes=data.interval_minutes,
            task_type=data.task_type or "custom",
            task_config=data.task_config,
            playbook_id=data.playbook_id,
            project_id=data.project_id,
            max_attempts=data.max_attempts,
        )
        if data.scheduled_time:
            try:
                sched.scheduled_time = datetime.fromisoformat(data.scheduled_time)
            except ValueError:
                pass
        if data.schedule_type == "cron" or (data.cron_expression or "").strip():
            from app.domains.personal_agent.schedule_ticker import compute_next_cron_run

            nxt = compute_next_cron_run(data.cron_expression or "")
            if nxt is not None:
                sched.next_run_at = nxt
        elif data.schedule_type == "interval" and data.interval_minutes:
            from datetime import timedelta

            sched.next_run_at = datetime.now(timezone.utc) + timedelta(minutes=int(data.interval_minutes))
        db.add(sched)
        db.commit()
        db.refresh(sched)
        return _sched_to_dict(sched)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{schedule_id}")
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Get schedule with recent runs."""
    try:
        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        result = _sched_to_dict(sched)
        result["runs"] = [_run_to_dict(r) for r in (sched.runs or [])[-20:]]
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{schedule_id}")
def update_schedule(schedule_id: int, data: ScheduleUpdate, db: Session = Depends(get_db)):
    """Update a schedule."""
    try:
        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        for field in [
            "name",
            "description",
            "cron_expression",
            "interval_minutes",
            "task_config",
            "task_type",
            "playbook_id",
            "is_active",
            "max_attempts",
        ]:
            val = getattr(data, field, None)
            if val is not None:
                setattr(sched, field, val)
        if data.next_run_at:
            try:
                sched.next_run_at = datetime.fromisoformat(data.next_run_at)
            except ValueError:
                pass
        db.commit()
        db.refresh(sched)
        return _sched_to_dict(sched)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule and all runs."""
    try:
        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        db.delete(sched)
        db.commit()
        return {"status": "deleted", "id": schedule_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Toggle a schedule on/off."""
    try:
        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        sched.is_active = not sched.is_active
        db.commit()
        db.refresh(sched)
        return _sched_to_dict(sched)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/due/run")
def run_due(db: Session = Depends(get_db)):
    """Poll-and-run due schedules (Phase 10 Stage B worker hook)."""
    try:
        from app.domains.personal_agent.schedule_executor import run_due_schedules

        runs = run_due_schedules(db)
        return {"ran": len(runs), "runs": [_run_to_dict(r) for r in runs]}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{schedule_id}/trigger")
def trigger_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Manually trigger a scheduled task — executes real work (Phase 10 Stage A)."""
    try:
        from app.domains.personal_agent.schedule_executor import execute_schedule

        sched = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule not found")
        run = execute_schedule(db, sched, trigger_type="manual")
        return _run_to_dict(run)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{schedule_id}/runs")
def list_runs(schedule_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """List runs for a schedule."""
    try:
        q = db.query(ScheduleRun).filter(ScheduleRun.schedule_id == schedule_id)
        total = q.count()
        items = q.order_by(ScheduleRun.started_at.desc()).offset(skip).limit(limit).all()
        return {"items": [_run_to_dict(r) for r in items], "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _sched_to_dict(s: Schedule) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "project_id": s.project_id,
        "name": s.name,
        "description": s.description,
        "schedule_type": s.schedule_type,
        "cron_expression": s.cron_expression,
        "interval_minutes": s.interval_minutes,
        "scheduled_time": s.scheduled_time.isoformat() if s.scheduled_time else None,
        "task_type": s.task_type,
        "task_config": s.task_config or {},
        "playbook_id": s.playbook_id,
        "is_active": s.is_active,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "run_count": s.run_count,
        "failure_count": s.failure_count,
        "max_attempts": getattr(s, "max_attempts", 3),
        "retry_count": getattr(s, "retry_count", 0),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }

def _run_to_dict(r: ScheduleRun) -> dict:
    return {
        "id": r.id,
        "schedule_id": r.schedule_id,
        "status": r.status,
        "trigger_type": r.trigger_type,
        "output_summary": r.output_summary,
        "tokens_used": r.tokens_used,
        "cost_usd": r.cost_usd,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }

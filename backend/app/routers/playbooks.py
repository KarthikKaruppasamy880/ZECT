"""Playbooks — reusable prompt templates and workflows."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import Playbook, PlaybookRun

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


class PlaybookCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "general"
    steps: list = []
    variables: list = []
    trigger_pattern: Optional[str] = None
    is_public: bool = True
    project_id: Optional[int] = None

class PlaybookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    steps: Optional[list] = None
    variables: Optional[list] = None
    trigger_pattern: Optional[str] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None

class PlaybookRunCreate(BaseModel):
    variables_used: dict = {}


@router.get("")
def list_playbooks(
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List playbooks with optional filters."""
    try:
        q = db.query(Playbook).filter(Playbook.is_active == is_active)
        if category:
            q = q.filter(Playbook.category == category)
        if project_id:
            q = q.filter(Playbook.project_id == project_id)
        total = q.count()
        items = q.order_by(Playbook.usage_count.desc()).offset(skip).limit(limit).all()
        return {"items": [_pb_to_dict(p) for p in items], "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_playbook(data: PlaybookCreate, db: Session = Depends(get_db)):
    """Create a new playbook."""
    try:
        pb = Playbook(
            name=data.name,
            description=data.description,
            category=data.category,
            steps=data.steps,
            variables=data.variables,
            trigger_pattern=data.trigger_pattern,
            is_public=data.is_public,
            project_id=data.project_id,
        )
        db.add(pb)
        db.commit()
        db.refresh(pb)
        return _pb_to_dict(pb)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """Get all playbook categories with counts."""
    try:
        from sqlalchemy import func
        rows = db.query(
            Playbook.category, func.count(Playbook.id)
        ).filter(Playbook.is_active == True).group_by(Playbook.category).all()
        return [{"category": r[0], "count": r[1]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{playbook_id}")
def get_playbook(playbook_id: int, db: Session = Depends(get_db)):
    """Get a playbook with run history."""
    try:
        pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
        if not pb:
            raise HTTPException(status_code=404, detail="Playbook not found")
        result = _pb_to_dict(pb)
        result["runs"] = [_run_to_dict(r) for r in (pb.runs or [])[-10:]]
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{playbook_id}")
def update_playbook(playbook_id: int, data: PlaybookUpdate, db: Session = Depends(get_db)):
    """Update a playbook."""
    try:
        pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
        if not pb:
            raise HTTPException(status_code=404, detail="Playbook not found")
        for field in ["name", "description", "category", "steps", "variables", "trigger_pattern", "is_public", "is_active"]:
            val = getattr(data, field, None)
            if val is not None:
                setattr(pb, field, val)
        db.commit()
        db.refresh(pb)
        return _pb_to_dict(pb)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{playbook_id}")
def delete_playbook(playbook_id: int, db: Session = Depends(get_db)):
    """Delete a playbook."""
    try:
        pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
        if not pb:
            raise HTTPException(status_code=404, detail="Playbook not found")
        db.delete(pb)
        db.commit()
        return {"status": "deleted", "id": playbook_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{playbook_id}/run")
def run_playbook(playbook_id: int, data: PlaybookRunCreate, db: Session = Depends(get_db)):
    """Start a playbook run."""
    try:
        pb = db.query(Playbook).filter(Playbook.id == playbook_id).first()
        if not pb:
            raise HTTPException(status_code=404, detail="Playbook not found")
        run = PlaybookRun(
            playbook_id=playbook_id,
            variables_used=data.variables_used,
            total_steps=len(pb.steps or []),
            status="running",
        )
        db.add(run)
        pb.usage_count = (pb.usage_count or 0) + 1
        pb.last_used_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return _run_to_dict(run)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{playbook_id}/runs/{run_id}")
def update_run(playbook_id: int, run_id: int, status: str = "completed", steps_completed: int = 0, output_summary: str = "", rating: Optional[float] = None, db: Session = Depends(get_db)):
    """Update a playbook run status."""
    try:
        run = db.query(PlaybookRun).filter(PlaybookRun.id == run_id, PlaybookRun.playbook_id == playbook_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        run.status = status
        run.steps_completed = steps_completed
        run.output_summary = output_summary
        if rating is not None:
            run.rating = rating
        if status in ("completed", "failed", "cancelled"):
            run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return _run_to_dict(run)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{playbook_id}/runs")
def list_runs(playbook_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """List runs for a playbook."""
    try:
        q = db.query(PlaybookRun).filter(PlaybookRun.playbook_id == playbook_id)
        total = q.count()
        items = q.order_by(PlaybookRun.started_at.desc()).offset(skip).limit(limit).all()
        return {"items": [_run_to_dict(r) for r in items], "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _pb_to_dict(p: Playbook) -> dict:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "project_id": p.project_id,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "steps": p.steps or [],
        "variables": p.variables or [],
        "trigger_pattern": p.trigger_pattern,
        "is_public": p.is_public,
        "is_active": p.is_active,
        "usage_count": p.usage_count,
        "avg_rating": p.avg_rating,
        "last_used_at": p.last_used_at.isoformat() if p.last_used_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }

def _run_to_dict(r: PlaybookRun) -> dict:
    return {
        "id": r.id,
        "playbook_id": r.playbook_id,
        "user_id": r.user_id,
        "status": r.status,
        "variables_used": r.variables_used or {},
        "steps_completed": r.steps_completed,
        "total_steps": r.total_steps,
        "total_tokens": r.total_tokens,
        "total_cost_usd": r.total_cost_usd,
        "output_summary": r.output_summary,
        "rating": r.rating,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }

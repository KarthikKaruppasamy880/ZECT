"""Agent Mode API — autonomous multi-step execution."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal

router = APIRouter(prefix="/api/agent", tags=["agent-mode"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AgentRunRequest(BaseModel):
    task: str
    stages: list[str] | None = None
    model: str = "gpt-4o-mini"
    repo_context: str = ""
    auto_advance: bool = True


class AgentResumeRequest(BaseModel):
    model: str | None = None


@router.post("/run")
def start_agent_run(req: AgentRunRequest, db: Session = Depends(get_db)):
    """Start a Mentrix-powered autonomous run (legacy agent shell preserved)."""
    import json
    import os

    if os.getenv("MENTRIX_ENABLED", "true").lower() not in ("0", "false"):
        from app.services.forge_loop.orchestrator import run_mentrix

        mode = "deliver"
        if req.stages and len(req.stages) == 1 and req.stages[0] == "review":
            mode = "review_only"
        elif req.stages == ["ask"] or req.stages == ["plan"]:
            mode = "chat"
        run = run_mentrix(
            db,
            goal=req.task,
            mode=mode,
            project_key=req.repo_context or "",
            created_by="agent-mode",
        )
        return {
            "id": run.id,
            "run_id": f"mentrix-{run.id}",
            "task": req.task,
            "status": run.status,
            "engine": "mentrix",
            "mode": run.mode,
            "current_agent": run.current_agent,
            "stages": req.stages or ["ask", "plan", "build", "review", "deploy"],
            "model": req.model,
            "events": json.loads(run.events_json or "[]"),
            "result": json.loads(run.result_json or "{}"),
            "steps": [
                {
                    "id": i,
                    "stage": ev.get("agent", "orchestrator"),
                    "step_index": i,
                    "output": ev.get("message", ""),
                    "tokens_used": 0,
                    "duration_ms": 0,
                    "status": "completed",
                    "model": req.model,
                    "created_at": ev.get("ts"),
                }
                for i, ev in enumerate(json.loads(run.events_json or "[]"))
            ],
        }

    from app.services.agent_orchestrator import create_agent_run

    return create_agent_run(
        db=db,
        task=req.task,
        stages=req.stages,
        model=req.model,
        repo_context=req.repo_context,
        auto_advance=req.auto_advance,
    )


@router.post("/run/{run_id}/resume")
def resume_run(run_id: str, req: AgentResumeRequest, db: Session = Depends(get_db)):
    """Resume a paused agent run."""
    from app.services.agent_orchestrator import resume_agent_run
    result = resume_agent_run(db, run_id, req.model)
    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/run/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get agent run details with all steps (legacy or Mentrix)."""
    import json
    from fastapi import HTTPException
    from app.models import MentrixRun
    from app.services.agent_orchestrator import get_agent_run

    if run_id.startswith("mentrix-"):
        mid = int(run_id.split("-", 1)[1])
        run = db.query(MentrixRun).filter(MentrixRun.id == mid).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        events = json.loads(run.events_json or "[]")
        return {
            "id": run.id,
            "run_id": run_id,
            "task": run.goal,
            "status": run.status,
            "engine": "mentrix",
            "mode": run.mode,
            "current_agent": run.current_agent,
            "stages": [],
            "model": "",
            "events": events,
            "result": json.loads(run.result_json or "{}"),
            "steps": [
                {
                    "id": i,
                    "stage": ev.get("agent", "orchestrator"),
                    "step_index": i,
                    "output": ev.get("message", ""),
                    "tokens_used": 0,
                    "duration_ms": 0,
                    "status": "completed",
                    "model": "",
                    "created_at": ev.get("ts"),
                }
                for i, ev in enumerate(events)
            ],
        }

    result = get_agent_run(db, run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@router.get("/runs")
def list_runs(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    """List Mentrix + legacy agent runs."""
    from app.models import MentrixRun
    from app.services.agent_orchestrator import list_agent_runs

    legacy = list_agent_runs(db, limit, offset)
    mentrix_rows = db.query(MentrixRun).order_by(MentrixRun.id.desc()).limit(limit).all()
    mentrix = [
        {
            "id": r.id,
            "run_id": f"mentrix-{r.id}",
            "task": (r.goal or "")[:200],
            "status": r.status,
            "engine": "mentrix",
            "mode": r.mode,
            "current_agent": r.current_agent,
            "stages": [],
            "model": "",
            "steps": [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in mentrix_rows
    ]
    # Prefer Mentrix runs first
    return mentrix + (legacy if isinstance(legacy, list) else [])


@router.delete("/run/{run_id}")
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    """Cancel a running or paused agent run."""
    from app.models import AgentRun
    run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = "cancelled"
    db.commit()
    return {"status": "cancelled", "run_id": run_id}

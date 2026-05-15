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
    """Start a new autonomous agent run."""
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
    """Get agent run details with all steps."""
    from app.services.agent_orchestrator import get_agent_run
    result = get_agent_run(db, run_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@router.get("/runs")
def list_runs(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    """List all agent runs."""
    from app.services.agent_orchestrator import list_agent_runs
    return list_agent_runs(db, limit, offset)


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

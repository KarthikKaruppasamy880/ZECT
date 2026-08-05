"""Agent Mode API — autonomous multi-step execution via Mentrix."""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal

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
    # Real disk workspace so Build writes files (not free-text paste)
    workspace: str = ""
    project_key: str = ""
    repo_id: int | None = None
    mode: str | None = None  # optional override: deliver|upgrade|bugfix|chat|review_only


class AgentResumeRequest(BaseModel):
    model: str | None = None


def _resolve_mode(req: AgentRunRequest) -> str:
    """Map Agent Mode stages → Mentrix mode that can actually generate code.

    Previously always used ``deliver``, whose builder is a guidance stub and
    never calls ``run_build_from_plan`` — so Agent Mode appeared to "run"
    without writing any files. When ``build`` is selected (default), use
    ``upgrade`` so Scout→Plan→Build writes to the workspace.
    """
    if req.mode and req.mode.strip():
        return req.mode.strip()
    stages = req.stages or ["ask", "plan", "build", "review", "deploy"]
    if stages == ["review"] or (len(stages) == 1 and stages[0] == "review"):
        return "review_only"
    if stages in (["ask"], ["plan"]) or set(stages).issubset({"ask", "plan"}):
        return "chat"
    if "build" in stages or "deploy" in stages:
        return "upgrade"
    return "deliver"


def _serialize_mentrix_run(run, *, task: str, stages: list[str], model: str) -> dict:
    events = json.loads(run.events_json or "[]")
    result = json.loads(run.result_json or "{}")
    builder = result.get("builder") or {}
    files_written = builder.get("files_written") or (
        [builder["file_path"]] if builder.get("file_path") else []
    )
    return {
        "id": run.id,
        "run_id": f"mentrix-{run.id}",
        "task": task,
        "status": run.status,
        "engine": "mentrix",
        "mode": run.mode,
        "current_agent": run.current_agent,
        "stages": stages,
        "model": model,
        "auto_advance": True,
        "current_stage_index": max(0, len(stages) - 1) if run.status == "completed" else 0,
        "total_tokens": int(result.get("tokens_used") or 0),
        "workspace": result.get("workspace") or "",
        "files_written": files_written,
        "events": events,
        "result": result,
        "gates": json.loads(run.gates_json or "{}"),
        "steps": [
            {
                "id": i,
                "stage": ev.get("agent", "orchestrator"),
                "step_index": i,
                "output": ev.get("message", ""),
                "tokens_used": 0,
                "duration_ms": 0,
                "status": "completed",
                "model": model,
                "created_at": ev.get("ts"),
            }
            for i, ev in enumerate(events)
        ],
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if getattr(run, "completed_at", None) else None,
    }


@router.post("/run")
def start_agent_run(req: AgentRunRequest, db: Session = Depends(get_db)):
    """Start a Mentrix-powered autonomous run (legacy agent shell preserved)."""
    stages = req.stages or ["ask", "plan", "build", "review", "deploy"]

    if os.getenv("MENTRIX_ENABLED", "true").lower() not in ("0", "false"):
        from app.services.forge_loop.orchestrator import run_mentrix

        mode = _resolve_mode(req)
        workspace = (req.workspace or "").strip()
        project_key = (req.project_key or "").strip()
        # Back-compat: if UI still only sends repo_context, treat a path-looking
        # value as workspace and otherwise as project_key.
        ctx = (req.repo_context or "").strip()
        if not workspace and ctx and (os.path.isdir(ctx) or "\\" in ctx or "/" in ctx):
            workspace = ctx
        elif not project_key and ctx and len(ctx) < 200 and "\n" not in ctx:
            project_key = ctx

        if mode == "upgrade" and not workspace and req.repo_id is None:
            # Still allow run (LLM can draft), but warn — no disk write without path
            pass

        run = run_mentrix(
            db,
            goal=req.task,
            mode=mode,
            project_key=project_key,
            workspace=workspace,
            repo_id=req.repo_id,
            created_by="agent-mode",
        )
        payload = _serialize_mentrix_run(run, task=req.task, stages=stages, model=req.model)
        if mode == "upgrade" and not workspace and req.repo_id is None:
            payload["warning"] = (
                "No workspace path or repo_id — Mentrix ran upgrade mode but "
                "cannot write generated files to disk. Set Workspace path from "
                "Repo Workspace (zect_mentrix_workspace) and re-run."
            )
        return payload

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
    if run_id.startswith("mentrix-"):
        raise HTTPException(
            status_code=400,
            detail="Mentrix runs are not resumable mid-pipeline — start a new Agent Mode run.",
        )
    from app.services.agent_orchestrator import resume_agent_run

    result = resume_agent_run(db, run_id, req.model)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/run/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get agent run details with all steps (legacy or Mentrix)."""
    from app.models import MentrixRun
    from app.services.agent_orchestrator import get_agent_run

    if run_id.startswith("mentrix-"):
        mid = int(run_id.split("-", 1)[1])
        run = db.query(MentrixRun).filter(MentrixRun.id == mid).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return _serialize_mentrix_run(
            run,
            task=run.goal or "",
            stages=["ask", "plan", "build", "review", "deploy"],
            model="",
        )

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
            "stages": ["ask", "plan", "build", "review", "deploy"],
            "model": "",
            "steps": [],
            "total_tokens": 0,
            "current_stage_index": 0,
            "auto_advance": True,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in mentrix_rows
    ]
    return mentrix + (legacy if isinstance(legacy, list) else [])


@router.delete("/run/{run_id}")
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    """Cancel a running or paused agent run (legacy or Mentrix)."""
    from app.models import AgentRun, MentrixRun

    if run_id.startswith("mentrix-"):
        mid = int(run_id.split("-", 1)[1])
        run = db.query(MentrixRun).filter(MentrixRun.id == mid).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        run.status = "cancelled"
        db.commit()
        return {"status": "cancelled", "run_id": run_id}

    run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = "cancelled"
    db.commit()
    return {"status": "cancelled", "run_id": run_id}

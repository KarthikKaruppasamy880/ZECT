"""Agent Mode API — autonomous multi-step execution via Mentrix."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal

# Modes that actually write files to disk (see _resolve_mode's docstring --
# "deliver"'s builder is a guidance stub, "chat"/"review_only" never touch a
# repo). Only these, with a real workspace path, are routed to the canonical
# coding_engine Mission/Harness instead of forge_loop.orchestrator -- so a
# read-only Ask/Plan-style legacy submission is left exactly as it was.
_MISSION_BACKED_MODES = ("upgrade", "bugfix")

_MISSION_RUN_PREFIX = "mission-"

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


_MISSION_STATUS = {
    "running": "running",
    "completed": "completed",
    "blocked": "blocked",
    "recoverable": "paused",
    "stopped": "stopped",
}

_EVENT_STAGE_PREFIXES = (
    ("explore_", "explore"),
    ("diagnose_", "debugger"),
    ("browser_verify_", "tester"),
    ("native_implement", "coder"),
    ("evidence_verify_", "reviewer"),
    ("review", "reviewer"),
)


def _mission_event_stage(event_name: str) -> str:
    for prefix, stage in _EVENT_STAGE_PREFIXES:
        if event_name.startswith(prefix):
            return stage
    return "orchestrator"


def _serialize_mission_as_agent_run(mission: dict[str, Any], *, task: str, model: str, workspace: str) -> dict:
    """Translate a real coding_engine Mission (see coding_engine/lifecycle.py)
    into the legacy AgentModeRun JSON shape the frontend already parses, so
    the redirect requires zero frontend changes. ``result.mission`` carries
    the full, untranslated mission so opening a run always resolves to the
    same canonical Mission -- not a lossy summary standing in for it.
    """
    mission_id = str(mission.get("id") or "")
    events = list(mission.get("events") or [])
    execution_state = str(mission.get("execution_state") or "")
    status = _MISSION_STATUS.get(execution_state, execution_state or "running")
    if mission.get("phase") == "cancelled" or mission.get("status") == "cancelled":
        status = "cancelled"
    elif mission.get("phase") == "awaiting_plan_approval" and not mission.get("plan_approved"):
        # A file-writing mission must never look "running"/"stopped" while it
        # is actually just sitting there waiting for a human to read the PLAN
        # and approve it -- see the governance fix in start_agent_run() below.
        status = "awaiting_approval"
    steps = [
        {
            "id": i,
            "stage": _mission_event_stage(str(ev.get("event") or "")),
            "step_index": i,
            "output": str(ev.get("message") or ""),
            "tokens_used": 0,
            "duration_ms": 0,
            "status": "completed",
            "model": model,
            "created_at": ev.get("at"),
        }
        for i, ev in enumerate(events)
    ]
    return {
        "id": mission_id,
        "run_id": f"{_MISSION_RUN_PREFIX}{mission_id}",
        "task": task,
        "status": status,
        "engine": "coding_engine_mission",
        "mode": mission.get("mode") or "",
        "current_agent": (mission.get("agents") or [None])[-1],
        "stages": ["explore", "coder", "debugger", "tester", "reviewer"],
        "model": model,
        "auto_advance": True,
        "current_stage_index": 0 if status == "running" else max(0, len(steps) - 1),
        "total_tokens": 0,
        "workspace": workspace,
        "files_written": list(mission.get("files") or []),
        "events": events,
        "result": {"mission": mission},
        "gates": {},
        "steps": steps,
        "created_at": mission.get("started_at"),
        "completed_at": mission.get("updated_at") if status in ("completed", "blocked", "cancelled") else None,
        "warning": "; ".join(mission.get("blockers") or []) or None,
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

        if mode in _MISSION_BACKED_MODES and workspace and os.path.isdir(workspace):
            # File-writing legacy submissions must not run on a second,
            # independent coding engine (forge_loop.orchestrator writes
            # files with no worktree isolation, no commit, no Ultra Review,
            # no EvidenceVerifier). Hand off to the same canonical
            # coding_engine Mission/Harness Developer Workspace uses.
            #
            # The mission is returned in its "awaiting_plan_approval" phase
            # and deliberately NOT auto-approved here: worktree isolation and
            # every file edit only happen after a human reads the PLAN and
            # calls POST /api/coding-agent/missions/{id}/approve-plan (the
            # same gate the canonical Mission panel uses). Auto-approving on
            # the caller's behalf would let a file-writing agent run execute
            # with zero human confirmation.
            from app.services.coding_engine.lifecycle import start_mission

            label = Path(workspace).name or "workspace"
            mission = start_mission(
                goal=req.task,
                roots=[{"id": req.repo_id or 1, "label": label, "path": workspace}],
                propose_if_empty=True,
                mode=mode,
                source="legacy_agent_mode",
            )
            return _serialize_mission_as_agent_run(mission, task=req.task, model=req.model, workspace=workspace)

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
    if run_id.startswith(_MISSION_RUN_PREFIX):
        from app.services.coding_engine.lifecycle import get_mission, resume_mission_in_background

        mid = run_id[len(_MISSION_RUN_PREFIX) :]
        try:
            base = get_mission(mid)
        except KeyError:
            raise HTTPException(status_code=404, detail="Run not found") from None
        mission = resume_mission_in_background(mid)
        return _serialize_mission_as_agent_run(
            mission, task=base.get("goal") or "", model=req.model or "", workspace=""
        )
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
    """Get agent run details with all steps (legacy, Mentrix, or Mission-backed).

    Mission-backed ids resolve straight to lifecycle.get_mission() -- the
    same durable Mission read Developer Workspace uses -- so opening a run
    from History reconnects to the live/actual mission, never re-executes
    or approximates it.
    """
    from app.models import MentrixRun
    from app.services.agent_orchestrator import get_agent_run

    if run_id.startswith(_MISSION_RUN_PREFIX):
        from app.services.coding_engine.lifecycle import get_mission

        mid = run_id[len(_MISSION_RUN_PREFIX) :]
        try:
            mission = get_mission(mid)
        except KeyError:
            raise HTTPException(status_code=404, detail="Run not found") from None
        return _serialize_mission_as_agent_run(mission, task=mission.get("goal") or "", model="", workspace="")

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
    """List Mentrix + legacy + Mission-backed agent runs as one chronologically
    merged, correctly paginated projection.

    Mission-backed entries are a live projection of the canonical Mission
    JSON store (lifecycle.list_missions) -- not a second history table --
    per the migration direction: legacy route -> canonical Mission ->
    Mission/Event persistence -> Runs projection/UI. The other two engines
    (legacy agent_orchestrator, ForgeLoop's MentrixRun) remain genuinely
    separate execution paths for non-Mission-backed asks (see
    ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase D) -- this
    endpoint's job is only to present all three as one truthful, correctly
    paginated, chronologically-ordered list, not to eliminate the other two.

    Each source is queried for `offset + limit` rows (enough candidates to
    merge-sort correctly across all three before paginating) -- the
    previous version queried each source for `limit` independently and
    concatenated them, which could return up to 3x the requested page size
    with no cross-source ordering (a legacy/Mentrix row newer than every
    Mission row would still sort after all of them).
    """
    from app.models import MentrixRun
    from app.services.agent_orchestrator import list_agent_runs
    from app.services.coding_engine.lifecycle import list_missions

    fetch = offset + limit
    legacy = list_agent_runs(db, fetch, 0)
    mentrix_rows = db.query(MentrixRun).order_by(MentrixRun.id.desc()).limit(fetch).all()
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
    missions = [
        _serialize_mission_as_agent_run(m, task=m.get("goal") or "", model="", workspace="")
        for m in list_missions(limit=fetch, offset=0)
    ]
    combined = missions + mentrix + (legacy if isinstance(legacy, list) else [])
    combined.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return combined[offset : offset + limit]


@router.delete("/run/{run_id}")
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    """Cancel a running or paused agent run (legacy, Mentrix, or Mission-backed)."""
    from app.models import AgentRun, MentrixRun

    if run_id.startswith(_MISSION_RUN_PREFIX):
        from app.services.coding_engine.lifecycle import cancel_mission

        mid = run_id[len(_MISSION_RUN_PREFIX) :]
        try:
            cancel_mission(mid)
        except KeyError:
            raise HTTPException(status_code=404, detail="Run not found") from None
        return {"status": "cancelled", "run_id": run_id}

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

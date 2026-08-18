"""Mentrix agent API — ForgeLoop + human approve → create PR."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import time

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.coding_runtime import selected_coding_engine
from app.domains.audit.audit_trail import log_audit
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import SessionLocal, get_db
from app.models import FineTuneSample, MentrixRun
from app.services.forge_loop.orchestrator import (
    AGENT_ROLES,
    MODE_PIPELINE,
    continue_mentrix_after_batch,
    continue_mentrix_after_plan,
    gates_allow_approve,
    gates_allow_create_pr,
    validate_context_pack,
)
from app.workers.mentrix_worker import run_mentrix_in_background

router = APIRouter(prefix="/api/mentrix", tags=["mentrix"])

# Mentrix Delivery state set (Phase 1). Upgrade.md also lists queued/provisioning/validating —
# those map onto Mentrix phases inside events; top-level status stays product-facing.
MENTRIX_TERMINAL = frozenset({"completed", "failed", "cancelled", "pr_created", "approved"})
RETRYABLE_STATUSES = frozenset({"failed", "cancelled", "needs_human"})


def _json_dict(raw: str | None) -> dict[str, Any]:
    try:
        val = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return val if isinstance(val, dict) else {}


def _json_list(raw: str | None) -> list[Any]:
    try:
        val = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return val if isinstance(val, list) else []


class StartRunRequest(BaseModel):
    goal: str
    mode: str = "chat"
    project_key: str = ""
    project_id: int | None = None
    workspace: str = ""
    source_lang: str = ""
    target_lang: str = ""
    repo_id: int | None = None


class FineTuneSampleRequest(BaseModel):
    agent_role: str = "builder"
    prompt_context: str
    preferred_output: str
    rejected_output: str = ""
    accepted: bool = True


class ApproveRequest(BaseModel):
    acknowledge_issues: bool = False
    acknowledge_reason: str = ""


class CreatePRRequest(BaseModel):
    title: str = ""
    body: str = ""
    repo_path: str = ""
    owner: str = ""
    repo_name: str = ""
    head_branch: str = ""
    base_branch: str = "main"
    dry_run: bool | None = None


class PlanPatchRequest(BaseModel):
    summary: str | None = None
    plan: str | None = None
    phases: list[Any] | None = None
    steps: list[dict[str, Any]] | None = None


class ConfirmPlanRequest(BaseModel):
    summary: str | None = None
    plan: str | None = None
    phases: list[Any] | None = None
    steps: list[dict[str, Any]] | None = None
    files_expected: list[str] | None = None


def _normalize_events(raw: Any) -> list[dict[str, Any]]:
    """Ensure every event has a stable 1-based sequence_id for SSE reconnect."""
    events = raw if isinstance(raw, list) else []
    out: list[dict[str, Any]] = []
    for i, item in enumerate(events):
        if not isinstance(item, dict):
            continue
        ev = dict(item)
        if "sequence_id" not in ev:
            ev["sequence_id"] = i + 1
        out.append(ev)
    return out


def _append_event(run: MentrixRun, event: dict[str, Any]) -> list[dict[str, Any]]:
    events = _normalize_events(_json_list(run.events_json))
    next_seq = (events[-1]["sequence_id"] if events else 0) + 1
    payload = dict(event)
    payload.setdefault("sequence_id", next_seq)
    payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
    events.append(payload)
    run.events_json = json.dumps(events)
    return events


def _artifacts_from_run(run: MentrixRun, result: dict[str, Any], files_written: list) -> list[dict[str, Any]]:
    arts: list[dict[str, Any]] = []
    for path in files_written:
        arts.append({"kind": "file", "path": path})
    if run.pr_url:
        arts.append({"kind": "pr", "url": run.pr_url})
    for key in ("plan", "ask", "ultra_review", "api_eval", "builder"):
        if result.get(key):
            arts.append({"kind": "result", "name": key})
    return arts


def _run_to_dict(run: MentrixRun) -> dict:
    result = _json_dict(run.result_json)
    builder = result.get("builder") if isinstance(result.get("builder"), dict) else {}
    files_written = builder.get("files_written") or result.get("files_written") or []
    if not isinstance(files_written, list):
        files_written = []
    events = _normalize_events(_json_list(run.events_json))
    gates = _json_dict(run.gates_json)
    terminal_lines = [
        f"[{e.get('phase') or e.get('agent') or 'mentrix'}] {e.get('message') or e.get('event') or ''}"
        for e in events
        if e.get("message") or e.get("event")
    ]
    return {
        "id": run.id,
        "status": run.status,
        "mode": run.mode,
        "goal": run.goal,
        "current_agent": run.current_agent,
        "events": events,
        "result": result,
        "gates": gates,
        "next_step": run.next_step or "",
        "approved_at": run.approved_at.isoformat() if run.approved_at else None,
        "approved_by": run.approved_by or "",
        "pr_url": run.pr_url or "",
        "files_written": files_written,
        "batch_index": result.get("batch_index"),
        "batch_total": result.get("batch_total"),
        "batch_files": result.get("batch_files") or [],
        "files_expected": (result.get("plan") if isinstance(result.get("plan"), dict) else {}).get("files_expected")
        or (result.get("builder") if isinstance(result.get("builder"), dict) else {}).get("files_expected")
        or [],
        "artifacts": _artifacts_from_run(run, result, files_written),
        "terminal": terminal_lines[-80:],
        "test_results": {
            "lint_ok": gates.get("lint_ok"),
            "sandbox_ready": gates.get("sandbox_ready"),
            "api_eval_ok": gates.get("api_eval_ok"),
            "review_ok": gates.get("review_ok"),
            "incomplete_ok": gates.get("incomplete_ok"),
            "sast_ok": gates.get("sast_ok"),
        },
        "event_cursor": events[-1]["sequence_id"] if events else 0,
        "engine_provider": (result.get("context") or {}).get("engine_provider")
        if isinstance(result.get("context"), dict)
        else None,
        "workspace_id": (result.get("context") or {}).get("workspace_id")
        if isinstance(result.get("context"), dict)
        else None,
        "engine_run_id": (result.get("context") or {}).get("engine_run_id")
        if isinstance(result.get("context"), dict)
        else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/agents")
def list_agents(_user: CurrentUser = Depends(get_current_user)):
    return {
        "user_facing": "Mentrix",
        "roles": list(AGENT_ROLES),
        "pipelines": MODE_PIPELINE,
        "wake_phrases": ["Mentrix", "Hey Mentrix", "Mentrix engage"],
        "engine": "forge_loop",
        "coding_engine": selected_coding_engine(),
        "langgraph": False,
    }


@router.get("/eval/golden")
def eval_golden(_user: CurrentUser = Depends(get_current_user)):
    """Non-blocking Mentrix golden eval suite (observability seed)."""
    from app.services.quality.eval_harness import run_golden_suite

    return run_golden_suite()


@router.post("/runs")
def start_run(
    req: StartRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.security.emergency_stop import require_not_emergency_stopped

    require_not_emergency_stopped(db)
    if not req.goal.strip():
        raise HTTPException(status_code=400, detail="goal is required")
    if req.mode not in MODE_PIPELINE:
        raise HTTPException(status_code=400, detail=f"Unknown mode. Use one of {list(MODE_PIPELINE)}")
    pack_errors = validate_context_pack(
        workspace=req.workspace or "",
        project_key=req.project_key or "",
        mode=req.mode,
    )
    if pack_errors:
        raise HTTPException(status_code=400, detail="; ".join(pack_errors))

    run = MentrixRun(
        project_id=req.project_id,
        mode=req.mode,
        goal=req.goal.strip(),
        status="running",
        current_agent="orchestrator",
        events_json="[]",
        gates_json="{}",
        result_json=json.dumps(
            {
                "context": {
                    "project_key": req.project_key or "",
                    "workspace": req.workspace or "",
                    "source_lang": req.source_lang or "",
                    "target_lang": req.target_lang or "",
                    "repo_id": req.repo_id,
                }
            }
        ),
        next_step="",
        created_by=user.email,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    log_audit(
        db,
        action="mentrix_run_start",
        resource_type="mentrix_run",
        resource_id=run.id,
        resource_name=(req.goal or "")[:120],
        details=json.dumps({"mode": req.mode, "project_key": req.project_key or ""}),
        user_id=getattr(user, "id", None) if isinstance(getattr(user, "id", None), int) else None,
    )

    background_tasks.add_task(
        run_mentrix_in_background,
        run.id,
        goal=req.goal.strip(),
        mode=req.mode,
        project_key=req.project_key,
        project_id=req.project_id,
        created_by=user.email,
        workspace=req.workspace,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        repo_id=req.repo_id,
    )
    return _run_to_dict(run)


@router.get("/runs/{run_id}/plan")
def get_run_plan(run_id: int, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    result = _json_dict(run.result_json)
    plan = result.get("plan") if isinstance(result.get("plan"), dict) else {}
    return {
        "run_id": run.id,
        "status": run.status,
        "plan_confirmed": bool(_json_dict(run.gates_json).get("plan_confirmed")),
        "plan": plan,
        "root_cause": result.get("root_cause"),
    }


@router.patch("/runs/{run_id}/plan")
def patch_run_plan(
    run_id: int,
    req: PlanPatchRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_plan_confirm":
        raise HTTPException(status_code=400, detail="Plan can only be edited while awaiting_plan_confirm")
    result = _json_dict(run.result_json)
    raw_plan = result.get("plan")
    plan = dict(raw_plan) if isinstance(raw_plan, dict) else {}
    if req.summary is not None:
        plan["summary"] = req.summary
    if req.plan is not None:
        plan["summary"] = req.plan
    if req.phases is not None:
        plan["phases"] = req.phases
    if req.steps is not None:
        plan["steps"] = req.steps
    result["plan"] = plan
    cp = result.get("_checkpoint") if isinstance(result.get("_checkpoint"), dict) else {}
    if isinstance(cp.get("plan"), dict):
        inner = dict(cp["plan"])
        if req.steps is not None:
            inner["steps"] = req.steps
        if req.summary is not None or req.plan is not None:
            inner["plan"] = req.summary or req.plan or ""
        if req.phases is not None:
            inner["phases"] = req.phases
        cp["plan"] = inner
        result["_checkpoint"] = cp
    run.result_json = json.dumps(result)
    db.commit()
    db.refresh(run)
    return {"run_id": run.id, "plan": plan}


@router.post("/runs/{run_id}/confirm-plan")
def confirm_run_plan(
    run_id: int,
    req: ConfirmPlanRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_plan_confirm":
        raise HTTPException(status_code=400, detail="Run is not awaiting plan confirmation")
    patch: dict[str, Any] = {}
    if req.summary is not None:
        patch["summary"] = req.summary
    if req.plan is not None:
        patch["plan"] = req.plan
    if req.phases is not None:
        patch["phases"] = req.phases
    if req.steps is not None:
        patch["steps"] = req.steps
    if req.files_expected is not None:
        patch["files_expected"] = req.files_expected
    try:
        run = continue_mentrix_after_plan(
            db,
            run,
            plan_patch=patch or None,
            confirmed_by=user.email or user.username or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _run_to_dict(run)


@router.post("/runs/{run_id}/confirm-batch")
def confirm_run_batch(
    run_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Human confirms a Build file batch — continue next batch or remaining gates."""
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_batch_confirm":
        raise HTTPException(status_code=400, detail="Run is not awaiting batch confirmation")
    try:
        run = continue_mentrix_after_batch(
            db,
            run,
            confirmed_by=user.email or user.username or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _run_to_dict(run)


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_dict(run)


@router.delete("/runs/{run_id}")
def cancel_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Cancel an in-flight Mentrix run (parity with Agent Mode DELETE /api/agent/run/{id})."""
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in ("approved", "pr_created", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a run in status={run.status}",
        )
    if run.status != "cancelled":
        run.status = "cancelled"
        run.next_step = f"Cancelled by {user.email or user.username or 'user'}"
        _append_event(
            run,
            {
                "agent": "orchestrator",
                "phase": "cancel",
                "event": "cancelled",
                "message": run.next_step,
            },
        )
        db.commit()
        db.refresh(run)
        log_audit(
            db,
            action="mentrix_run_cancel",
            resource_type="mentrix_run",
            resource_id=run.id,
            resource_name=(run.goal or "")[:120],
            details=json.dumps({"status": run.status}),
            user_id=getattr(user, "id", None) if isinstance(getattr(user, "id", None), int) else None,
        )
    return _run_to_dict(run)


@router.post("/runs/{run_id}/retry")
def retry_run(
    run_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Retry a failed/cancelled/needs_human run by starting a fresh Mentrix run (same goal/mode)."""
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in RETRYABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry a run in status={run.status}",
        )
    result = _json_dict(run.result_json)
    ctx = result.get("context") if isinstance(result.get("context"), dict) else {}
    goal = (run.goal or "").strip()
    mode = run.mode or "deliver"
    project_key = ctx.get("project_key") or ""
    workspace = ctx.get("workspace") or ""
    source_lang = ctx.get("source_lang") or ""
    target_lang = ctx.get("target_lang") or ""
    repo_id = ctx.get("repo_id")
    project_id = run.project_id

    new_run = MentrixRun(
        project_id=project_id,
        mode=mode,
        goal=goal,
        status="running",
        current_agent="orchestrator",
        events_json=json.dumps(
            [
                {
                    "sequence_id": 1,
                    "agent": "orchestrator",
                    "phase": "retry",
                    "event": "retry",
                    "message": f"Retry of run #{run_id}",
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            ]
        ),
        gates_json="{}",
        next_step="",
        created_by=user.email,
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    log_audit(
        db,
        action="mentrix_run_retry",
        resource_type="mentrix_run",
        resource_id=new_run.id,
        resource_name=goal[:120],
        details=json.dumps({"retried_from": run_id, "mode": mode}),
        user_id=getattr(user, "id", None) if isinstance(getattr(user, "id", None), int) else None,
    )
    background_tasks.add_task(
        run_mentrix_in_background,
        new_run.id,
        goal=goal,
        mode=mode,
        project_key=project_key,
        project_id=project_id,
        created_by=user.email,
        workspace=workspace,
        source_lang=source_lang,
        target_lang=target_lang,
        repo_id=repo_id if isinstance(repo_id, int) else None,
    )
    return _run_to_dict(new_run)


@router.get("/runs/{run_id}/events/stream")
def stream_run_events(
    run_id: int,
    after: int = Query(0, ge=0, description="Resume after this sequence_id"),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """SSE of Mentrix run events with sequence_id; reconnect with ?after=<last_seq>."""
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    def gen():
        cursor = after
        idle_rounds = 0
        # Bound the stream so tests and proxies don't hang forever.
        while idle_rounds < 40:
            session = SessionLocal()
            try:
                row = session.query(MentrixRun).filter(MentrixRun.id == run_id).first()
                if not row:
                    yield f"event: error\ndata: {json.dumps({'error': 'not_found'})}\n\n"
                    return
                events = _normalize_events(_json_list(row.events_json))
                new_events = [e for e in events if int(e.get("sequence_id") or 0) > cursor]
                for ev in new_events:
                    cursor = int(ev["sequence_id"])
                    yield f"id: {cursor}\nevent: mentrix_event\ndata: {json.dumps(ev)}\n\n"
                    idle_rounds = 0
                payload = {
                    "run_id": run_id,
                    "status": row.status,
                    "event_cursor": cursor,
                }
                yield f"event: status\ndata: {json.dumps(payload)}\n\n"
                if row.status != "running" and not new_events:
                    idle_rounds += 1
                    if row.status in MENTRIX_TERMINAL or row.status in (
                        "awaiting_plan_confirm",
                        "awaiting_approval",
                        "needs_human",
                    ):
                        # Pause states: emit once more then close so clients reconnect on action.
                        if idle_rounds >= 2:
                            yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                            return
                else:
                    idle_rounds += 1
            finally:
                session.close()
            time.sleep(0.25)
        yield f"event: done\ndata: {json.dumps({'run_id': run_id, 'event_cursor': cursor, 'reason': 'timeout'})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs")
def list_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    rows = db.query(MentrixRun).order_by(MentrixRun.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "status": r.status,
            "mode": r.mode,
            "goal": (r.goal or "")[:120],
            "current_agent": r.current_agent,
            "next_step": r.next_step or "",
            "pr_url": r.pr_url or "",
        }
        for r in rows
    ]


@router.post("/runs/{run_id}/approve")
def approve_run(
    run_id: int,
    req: ApproveRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Human approve after lint/sandbox/review gates — required before create-pr."""
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in ("pr_created",):
        raise HTTPException(status_code=400, detail="PR already created for this run")

    gates = _json_dict(run.gates_json)
    result = _json_dict(run.result_json)

    # Security / secrets critical findings are never waiveable
    if gates.get("security_critical") and req.acknowledge_issues:
        raise HTTPException(
            status_code=403,
            detail="Cannot acknowledge security/secrets critical findings — fix required",
        )

    waived: list[str] = []
    if req.acknowledge_issues:
        gates["acknowledge_issues"] = True
        if not gates.get("sandbox_ready"):
            waived.append("sandbox_ready")
            gates["sandbox_ready"] = True
        if not gates.get("review_ok") and not gates.get("security_critical"):
            waived.append("review_ok")
            gates["review_ok"] = True
        if gates.get("api_eval_ok") is False:
            waived.append("api_eval_ok")
            gates["api_eval_ok"] = True

    ok, blockers = gates_allow_approve(gates, acknowledge=req.acknowledge_issues)
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=f"Gates not green — cannot approve: {', '.join(blockers)}",
        )

    run.approved_at = datetime.now(timezone.utc)
    run.approved_by = user.email or user.username
    run.status = "approved"
    run.next_step = "create_pr"
    run.gates_json = json.dumps(gates)
    _append_event(
        run,
        {
            "agent": "orchestrator",
            "message": f"Human approved by {run.approved_by}",
            "event": "approve",
            "next_step": "create_pr",
        },
    )
    if req.acknowledge_issues:
        reason = (req.acknowledge_reason or "").strip() or "human override of non-security gates"
        waiver_event = {
            "agent": "orchestrator",
            "message": f"Acknowledge waiver by {run.approved_by}: {reason}",
            "event": "acknowledge_waiver",
            "waived_gates": waived,
            "reason": reason,
            "actor": run.approved_by,
        }
        events = _append_event(run, waiver_event)
        result["acknowledge_waiver"] = {
            "waived_gates": waived,
            "reason": reason,
            "actor": run.approved_by,
            "ts": events[-1].get("ts"),
        }
        run.result_json = json.dumps(result)
    db.commit()
    db.refresh(run)
    log_audit(
        db,
        action="mentrix_run_approve",
        resource_type="mentrix_run",
        resource_id=run.id,
        resource_name=(run.goal or "")[:120],
        details=json.dumps({"acknowledge_issues": bool(req.acknowledge_issues), "waived": waived}),
        user_id=getattr(user, "id", None) if isinstance(getattr(user, "id", None), int) else None,
    )
    return _run_to_dict(run)


@router.post("/runs/{run_id}/create-pr")
def create_pr_for_run(
    run_id: int,
    req: CreatePRRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Create GitHub PR only after human approve. No silent ship."""
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.approved_at:
        raise HTTPException(
            status_code=403,
            detail="Human approve required before create-pr (POST /api/mentrix/runs/{id}/approve)",
        )
    if run.pr_url:
        return {**_run_to_dict(run), "status": "already_created"}

    # Hard completion backstop — re-check gates; no silent partial ship
    gates = _json_dict(run.gates_json)
    result = _json_dict(run.result_json)
    # Strip acknowledge for create-pr hard check on incomplete/contract/grounding
    hard_gates = dict(gates)
    hard_gates["acknowledge_issues"] = False
    ok_pr, pr_blockers = gates_allow_create_pr(hard_gates)
    if not ok_pr:
        raise HTTPException(
            status_code=403,
            detail=f"Hard completion gate — cannot create PR: {', '.join(pr_blockers)}",
        )
    if result.get("rejected_files") or gates.get("rejected_files"):
        raise HTTPException(
            status_code=403,
            detail=f"Rejected/unverified files block PR: {result.get('rejected_files') or gates.get('rejected_files')}",
        )

    dry = req.dry_run
    if dry is None:
        dry = os.getenv("MENTRIX_PR_DRY_RUN", "false").lower() in ("1", "true", "yes")

    title = req.title or f"Mentrix: {(run.goal or '')[:72]}"
    waiver = result.get("acknowledge_waiver") or {}
    waiver_md = ""
    if waiver:
        waiver_md = (
            f"\n### Acknowledge waivers\n"
            f"- Actor: {waiver.get('actor')}\n"
            f"- Reason: {waiver.get('reason')}\n"
            f"- Waived: {', '.join(waiver.get('waived_gates') or [])}\n"
        )
    body = req.body or (
        f"## Mentrix delivery\n\n{run.goal}\n\n"
        f"Approved by: {run.approved_by}\n"
        f"Gates: `{run.gates_json}`\n"
        f"{waiver_md}"
    )

    if dry:
        pr_url = f"https://github.com/example/zect/pull/dry-run-{run.id}"
        pr_meta = {"dry_run": True, "number": run.id, "html_url": pr_url}
    else:
        repo_path = req.repo_path or os.getenv("MENTRIX_WORKSPACE", "")
        if not repo_path:
            raise HTTPException(
                status_code=400,
                detail="repo_path required (or set MENTRIX_WORKSPACE) when MENTRIX_PR_DRY_RUN is false",
            )
        try:
            from app.domains.repository.git_ops import CreatePRRequest as GitPRReq
            from app.domains.repository.git_ops import create_pull_request as git_create_pr

            pr_meta = git_create_pr(
                GitPRReq(
                    repo_path=repo_path,
                    title=title,
                    body=body,
                    owner=req.owner or None,
                    repo_name=req.repo_name or None,
                    head_branch=req.head_branch or None,
                    base_branch=req.base_branch or "main",
                )
            )
            pr_url = pr_meta.get("pr_url") or pr_meta.get("html_url") or ""
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"PR create failed: {exc}") from exc

    run.pr_url = pr_url
    run.status = "pr_created"
    run.next_step = "done"
    _append_event(
        run,
        {
            "agent": "integrator",
            "message": f"PR created: {pr_url}",
            "event": "create_pr",
            "pr_url": pr_url,
            "by": user.email,
        },
    )
    result = _json_dict(run.result_json)
    result["pr"] = pr_meta if not dry else {"dry_run": True, "html_url": pr_url}

    # Semgrep / GitHub Checks SAST after PR exists (never blocks pre-check create).
    owner = (req.owner or "").strip()
    repo_name = (req.repo_name or "").strip()
    ref = (req.head_branch or "").strip() or "HEAD"
    if not dry and owner and repo_name:
        try:
            from app.github_service import sast_checks_ok, sast_required

            sast = sast_checks_ok(owner, repo_name, ref)
            gates["sast_required"] = bool(sast.get("required", sast_required()))
            gates["sast_checked"] = True
            gates["sast_ok"] = bool(sast.get("ok"))
            gates["sast_detail"] = {
                "note": sast.get("note"),
                "matched": sast.get("matched") or [],
                "pending": sast.get("pending"),
                "error": sast.get("error"),
                "ref": ref,
                "owner": owner,
                "repo": repo_name,
            }
            result["sast"] = gates["sast_detail"]
            _append_event(
                run,
                {
                    "agent": "integrator",
                    "message": f"SAST check: ok={gates['sast_ok']} ({sast.get('note') or ''})",
                    "event": "sast_check",
                },
            )
            if gates["sast_required"] and not gates["sast_ok"]:
                run.status = "awaiting_sast"
                run.next_step = "await_sast"
                _append_event(
                    run,
                    {
                        "agent": "integrator",
                        "message": "Awaiting Semgrep/GitHub SAST success — use POST /refresh-sast",
                        "event": "awaiting_sast",
                    },
                )
        except Exception as exc:
            gates["sast_checked"] = True
            gates["sast_ok"] = False if gates.get("sast_required") else True
            gates["sast_detail"] = {"error": str(exc)[:300]}
            if gates.get("sast_required"):
                run.status = "awaiting_sast"
                run.next_step = "await_sast"

    run.gates_json = json.dumps(gates)
    run.result_json = json.dumps(result)
    db.commit()
    db.refresh(run)
    log_audit(
        db,
        action="mentrix_run_create_pr",
        resource_type="mentrix_run",
        resource_id=run.id,
        resource_name=(run.goal or "")[:120],
        details=json.dumps({"pr_url": pr_url, "dry_run": bool(dry)}),
        user_id=getattr(user, "id", None) if isinstance(getattr(user, "id", None), int) else None,
    )
    return _run_to_dict(run)


@router.post("/runs/{run_id}/refresh-sast")
def refresh_sast_for_run(
    run_id: int,
    owner: str = "",
    repo: str = "",
    ref: str = "",
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Re-poll GitHub Check Runs for Semgrep/SAST and update gates."""
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    gates = _json_dict(run.gates_json)
    result = _json_dict(run.result_json)
    detail = gates.get("sast_detail") or result.get("sast") or {}
    owner = (owner or detail.get("owner") or "").strip()
    repo = (repo or detail.get("repo") or "").strip()
    ref = (ref or detail.get("ref") or "").strip() or "HEAD"
    if not owner or not repo:
        raise HTTPException(
            status_code=400,
            detail="owner and repo required (query params or prior sast_detail on run)",
        )
    try:
        from app.github_service import sast_checks_ok, sast_required

        sast = sast_checks_ok(owner, repo, ref)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SAST refresh failed: {exc}") from exc

    gates["sast_required"] = bool(sast.get("required", sast_required()))
    gates["sast_checked"] = True
    gates["sast_ok"] = bool(sast.get("ok"))
    gates["sast_detail"] = {
        "note": sast.get("note"),
        "matched": sast.get("matched") or [],
        "pending": sast.get("pending"),
        "error": sast.get("error"),
        "ref": ref,
        "owner": owner,
        "repo": repo,
    }
    result["sast"] = gates["sast_detail"]
    result["gates"] = gates
    events = _json_list(run.events_json)
    events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": "integrator",
        "message": f"SAST refresh: ok={gates['sast_ok']} ({sast.get('note') or ''})",
        "event": "refresh_sast",
        "by": user.email,
    })
    if gates.get("sast_required") and not gates["sast_ok"]:
        run.status = "awaiting_sast"
        run.next_step = "await_sast"
    elif run.pr_url:
        run.status = "pr_created"
        run.next_step = "done"
    run.gates_json = json.dumps(gates)
    run.result_json = json.dumps(result)
    run.events_json = json.dumps(events)
    db.commit()
    db.refresh(run)
    return {**_run_to_dict(run), "sast": gates["sast_detail"]}


@router.post("/fine-tune/samples")
def add_fine_tune_sample(
    req: FineTuneSampleRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    row = FineTuneSample(
        agent_role=req.agent_role,
        prompt_context=req.prompt_context,
        preferred_output=req.preferred_output,
        rejected_output=req.rejected_output,
        accepted=req.accepted,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": "stored", "fine_tune_enabled": False}


@router.get("/fine-tune/samples")
def list_fine_tune_samples(
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    rows = db.query(FineTuneSample).order_by(FineTuneSample.id.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "samples": [
            {
                "id": r.id,
                "agent_role": r.agent_role,
                "accepted": r.accepted,
                "prompt_preview": (r.prompt_context or "")[:160],
            }
            for r in rows
        ],
        "note": "Phase 9: export these samples for LoRA after Mentrix quality bar is green.",
    }


@router.get("/fine-tune/export")
def export_fine_tune_dataset(
    limit: int = 500,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    rows = db.query(FineTuneSample).order_by(FineTuneSample.id.desc()).limit(limit).all()
    samples = [
        {
            "agent_role": r.agent_role,
            "prompt": r.prompt_context,
            "chosen": r.preferred_output,
            "rejected": r.rejected_output or "",
            "accepted": bool(r.accepted),
        }
        for r in rows
    ]
    return {
        "count": len(samples),
        "samples": samples,
        "format": "preference_pairs",
        "fine_tune_enabled": os.getenv("FINE_TUNE_ENABLED", "false").lower() in ("1", "true"),
        "note": "Train LoRA only after RAG quality bar is green.",
    }


# ---------------------------------------------------------------------------
# Mentrix Companion — personal company agent
# ---------------------------------------------------------------------------


class CompanionTurnRequest(BaseModel):
    message: str
    project_key: str = ""
    project_id: int | None = None
    confirmed_tools: list[str] = []
    history: list[dict] = []
    agent_context: str = ""
    skill_id: int | None = None
    model: str | None = None
    repository_ids: list[int] = []
    work_item_id: int | None = None
    workspace_id: str = ""


class OrgPolicyImportRequest(BaseModel):
    pack: dict
    replace: bool = False


@router.get("/companion/scope")
def companion_scope(
    project_id: int | None = None,
    work_item_id: int | None = None,
    workspace_id: str = "",
    repository_ids: str = "",
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """Active Project / authorized roots / WorkItem envelope for HUD + dock."""
    from app.services.mentrix.companion_scope import build_companion_scope

    ids: list[int] = []
    for part in (repository_ids or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return build_companion_scope(
        db,
        project_id=project_id,
        repository_ids=ids or None,
        work_item_id=work_item_id,
        workspace_id=workspace_id,
        created_by=getattr(_user, "email", "") or "",
    )


@router.get("/companion/agent-context")
def companion_agent_context(
    skill_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """Skills + staged Dream lessons for Mentrix turns (empty text when none)."""
    from app.services.mentrix.companion import build_agent_context

    text = build_agent_context(db, skill_id=skill_id, project_id=project_id)
    return {"ok": True, "text": text}


class NoteCreate(BaseModel):
    text: str
    tags: list[str] | None = None


@router.get("/notes")
def list_mentrix_notes(
    limit: int = 200,
    _user: CurrentUser = Depends(get_current_user),
):
    """Browse notes — manual (note_add trigger phrases) and auto-logged
    Companion exchanges alike. Was previously only viewable ephemerally by
    asking Companion "list my notes" inline, once, per conversation."""
    from app.services.mentrix.notes import list_notes

    return {"notes": list_notes(limit=min(max(limit, 1), 500))}


@router.post("/notes")
def create_mentrix_note(
    req: NoteCreate,
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.notes import add_note

    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    return add_note(text, tags=req.tags)


@router.delete("/notes/{note_id}")
def delete_mentrix_note(
    note_id: str,
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.notes import delete_note

    if not delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"deleted": True, "id": note_id}


class LogExchangeRequest(BaseModel):
    user_message: str
    assistant_reply: str


@router.post("/companion/log-exchange")
def companion_log_exchange(
    req: LogExchangeRequest,
    _user: CurrentUser = Depends(get_current_user),
):
    """Auto-log a completed Realtime-voice exchange to Mentrix Notes — the
    text-chat path (iter_companion_events) already does this on every turn
    via _auto_log_exchange; the voice path has no equivalent server-side
    turn function to hook into, so the frontend calls this once per
    finished cloned-voice reply instead."""
    from app.services.mentrix.companion import _auto_log_exchange

    _auto_log_exchange(req.user_message, req.assistant_reply)
    return {"ok": True}


@router.post("/companion/turn")
def companion_turn(
    req: CompanionTurnRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.companion import run_companion_turn
    from app.services.mentrix.org_policy import ensure_companion_rules

    if not (req.message or "").strip():
        raise HTTPException(status_code=400, detail="message required")
    ensure_companion_rules(db)
    uid = getattr(user, "id", None)
    return run_companion_turn(
        db,
        req.message.strip(),
        project_key=req.project_key or "",
        project_id=req.project_id,
        user_id=uid if isinstance(uid, int) else None,
        created_by=getattr(user, "email", "") or "",
        confirmed_tools=req.confirmed_tools or [],
        history=req.history or [],
        agent_context=req.agent_context or "",
        skill_id=req.skill_id,
        model=req.model,
        repository_ids=req.repository_ids or None,
        work_item_id=req.work_item_id,
        workspace_id=req.workspace_id or "",
    )


class CompanionStreamResumeRequest(BaseModel):
    turn_id: str
    confirmed_tools: list[str] = []
    project_key: str = ""


@router.get("/companion/stream")
def companion_stream(
    message: str = Query(..., min_length=1),
    project_key: str = "",
    project_id: int | None = None,
    confirmed_tools: str = "",
    agent_context: str = "",
    skill_id: int | None = None,
    model: str | None = None,
    repository_ids: str = "",
    work_item_id: int | None = None,
    workspace_id: str = "",
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """SSE stream: thinking → tool_start → artifact → token → done."""
    from app.services.mentrix.companion import iter_companion_events, sse_pack
    from app.services.mentrix.org_policy import ensure_companion_rules

    ensure_companion_rules(db)
    uid = getattr(user, "id", None)
    confirmed = [t.strip() for t in confirmed_tools.split(",") if t.strip()]
    repo_ids: list[int] = []
    for part in (repository_ids or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            repo_ids.append(int(part))
        except ValueError:
            continue

    def gen():
        try:
            for ev in iter_companion_events(
                db,
                message.strip(),
                project_key=project_key or "",
                project_id=project_id,
                user_id=uid if isinstance(uid, int) else None,
                created_by=getattr(user, "email", "") or "",
                confirmed_tools=confirmed,
                agent_context=agent_context or "",
                skill_id=skill_id,
                model=model,
                repository_ids=repo_ids or None,
                work_item_id=work_item_id,
                workspace_id=workspace_id or "",
            ):
                yield sse_pack(ev)
        except Exception as exc:  # noqa: BLE001
            yield sse_pack({"event": "error", "data": {"error": str(exc)}})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/companion/stream/resume")
def companion_stream_resume(
    req: CompanionStreamResumeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.companion import resume_companion_turn, sse_pack
    from app.services.mentrix.org_policy import ensure_companion_rules

    if not req.turn_id.strip():
        raise HTTPException(status_code=400, detail="turn_id required")
    ensure_companion_rules(db)

    def gen():
        try:
            for ev in resume_companion_turn(
                db,
                req.turn_id.strip(),
                req.confirmed_tools or [],
                created_by=getattr(user, "email", "") or "",
            ):
                yield sse_pack(ev)
        except Exception as exc:  # noqa: BLE001
            yield sse_pack({"event": "error", "data": {"error": str(exc)}})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/companion/policy")
def companion_policy_export(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.org_policy import export_org_policy

    return export_org_policy(db)


@router.post("/companion/policy/import")
def companion_policy_import(
    req: OrgPolicyImportRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.org_policy import import_org_policy

    try:
        return import_org_policy(db, req.pack, replace=req.replace)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/companion/tools")
def companion_tools(_user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.permission_broker import ALWAYS_CONFIRM_TOOLS, TOOL_ACTIONS

    return {
        "tools": sorted(TOOL_ACTIONS.keys()),
        "always_confirm": sorted(ALWAYS_CONFIRM_TOOLS),
        "packs": [
            "research",
            "content_ads",
            "reporting",
            "internal_docs",
            "comms",
            "delivery",
            "desktop",
            "media",
            "browser",
        ],
    }


class PreferredNameBody(BaseModel):
    preferred_name: str = ""


@router.get("/companion/preferred-name")
def companion_get_preferred_name(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.preferred_name import resolve_preferred_name

    uid = getattr(user, "id", None)
    email = getattr(user, "email", "") or ""
    name = resolve_preferred_name(db, user_id=uid if isinstance(uid, int) else None, email=email)
    return {"preferred_name": name, "email": email}


@router.put("/companion/preferred-name")
def companion_set_preferred_name(
    body: PreferredNameBody,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.preferred_name import set_preferred_name

    uid = getattr(user, "id", None)
    if not isinstance(uid, int):
        raise HTTPException(status_code=400, detail="user id required")
    return set_preferred_name(db, uid, (body.preferred_name or "").strip())


@router.get("/companion/desktop-bridge/status")
def desktop_bridge_status(
    agent_id: str = "electron",
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.desktop_bridge import agent_status

    return agent_status(getattr(user, "email", "") or "", agent_id)


@router.post("/companion/desktop-bridge/heartbeat")
def desktop_bridge_heartbeat(
    agent_id: str = "electron",
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.desktop_bridge import heartbeat

    return heartbeat(getattr(user, "email", "") or "", agent_id)


class DesktopBridgeEnqueue(BaseModel):
    command: dict = {}
    agent_id: str = "electron"


@router.post("/companion/desktop-bridge/enqueue")
def desktop_bridge_enqueue(
    body: DesktopBridgeEnqueue,
    user: CurrentUser = Depends(get_current_user),
):
    """Mobile/thin client queues desktop work for the linked Electron agent."""
    from app.services.mentrix.desktop_bridge import enqueue

    out = enqueue(getattr(user, "email", "") or "", body.command or {}, body.agent_id or "electron")
    if not out.get("ok"):
        raise HTTPException(status_code=503, detail=out.get("hint") or out.get("error") or "desktop_offline")
    return out


@router.get("/companion/desktop-bridge/poll")
def desktop_bridge_poll(
    agent_id: str = "electron",
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.desktop_bridge import poll

    return poll(getattr(user, "email", "") or "", agent_id)


class DesktopBridgeAck(BaseModel):
    id: str
    agent_id: str = "electron"
    result: dict = {}


@router.post("/companion/desktop-bridge/ack")
def desktop_bridge_ack(
    body: DesktopBridgeAck,
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.desktop_bridge import ack

    return ack(getattr(user, "email", "") or "", body.id, body.agent_id or "electron", body.result)


@router.get("/companion/integrations")
def companion_integrations_status(_user: CurrentUser = Depends(get_current_user)):
    """Non-secret readiness for Mentrix tools (env-backed Slack/Jira). Never returns tokens."""
    import os

    from app.services.mentrix.presentation.service import PresentationService

    slack = bool((os.getenv("SLACK_BOT_TOKEN") or "").strip())
    jira = bool(
        (os.getenv("MCP_JIRA_URL") or os.getenv("JIRA_BASE_URL") or "").strip()
        and (os.getenv("JIRA_EMAIL") or "").strip()
        and (os.getenv("JIRA_API_TOKEN") or "").strip()
    )
    openai = bool((os.getenv("OPENAI_API_KEY") or "").strip())
    from app.adapters.llm.openai_compat import mentrix_local_llm_configured, probe_mentrix_local_llm

    local_probe = probe_mentrix_local_llm() if mentrix_local_llm_configured() else {
        "configured": False,
        "online": False,
        "label": "Mentrix Local LLM not configured",
    }
    datadog = bool(
        (os.getenv("DATADOG_API_KEY") or "").strip() and (os.getenv("DATADOG_APP_KEY") or "").strip()
    )
    github = bool((os.getenv("GITHUB_TOKEN") or "").strip())
    zoom_join = (os.getenv("ZOOM_DEFAULT_JOIN_URL") or "").strip()
    from app.services.browser.runtime import get_browser_runtime

    browser = get_browser_runtime().status()
    uid = getattr(_user, "user_id", None) or getattr(_user, "username", "anon")
    present_status = PresentationService().status(user_id=str(uid))
    is_presenton = str(present_status.get("provider") or "") == "presenton"
    presenton_online = bool(
        is_presenton and present_status.get("configured") and present_status.get("reachable")
    )
    return {
        "slack": slack,
        "jira": jira,
        "openai": openai,
        "mentrix_local": bool(local_probe.get("online")),
        "mentrix_local_configured": bool(local_probe.get("configured")),
        "mentrix_local_label": local_probe.get("label") or "",
        "datadog": datadog,
        "github": github,
        "browser": bool(browser.get("online")),
        "browser_label": browser.get("label") or "Browser automation",
        "browser_hint": browser.get("hint") or "",
        "browser_provider": browser.get("provider") or "playwright",
        "presenton": presenton_online,
        "presenton_configured": bool(is_presenton and present_status.get("configured")),
        "presenton_reachable": bool(is_presenton and present_status.get("reachable")),
        "presenton_base_url": str(present_status.get("base_url") or ""),
        "presentation_provider": present_status.get("provider") or "presenton",
        "zinnia_presenton_template_id": "",
        "zoom_join_url_configured": bool(zoom_join),
        "zoom_desktop_path_configured": bool((os.getenv("ZOOM_DESKTOP_PATH") or "").strip()),
        "slack_channel": (os.getenv("SLACK_DEFAULT_CHANNEL") or "#engineering") if slack else "",
    }


class PresentonGenerateRequest(BaseModel):
    content: str
    n_slides: int = 6
    template: str = "general"
    # UI gallery id (e.g. zinnia-exec) — preferred for honest zinnia_verified resolution
    ui_template_choice: str = ""
    custom_id: str = ""
    instructions: str = ""
    filename: str = ""
    asset_ids: list[str] = []
    fast_basic: bool = False
    require_llm: bool = False


@router.get("/presenton/status")
def presenton_status(_user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.presentation.service import PresentationService

    uid = getattr(_user, "user_id", None) or getattr(_user, "username", "anon")
    return PresentationService().status(user_id=str(uid))


@router.get("/presenton/templates")
def presenton_templates(_user: CurrentUser = Depends(get_current_user)):
    """List engine templates via PresentationService (Presenton remains default)."""
    from app.services.mentrix.presentation.service import PresentationService

    return PresentationService().list_engine_templates()


@router.post("/presenton/generate")
def presenton_generate(
    req: PresentonGenerateRequest,
    _user: CurrentUser = Depends(get_current_user),
):
    """Generate a PPTX through PresentationService (Presenton default until S8C)."""
    from app.services.mentrix.presentation.provider import PresentationGenerateRequest
    from app.services.mentrix.presentation.service import PresentationService

    uid = getattr(_user, "user_id", None) or getattr(_user, "username", "anon")
    out = PresentationService().generate(
        PresentationGenerateRequest(
            content=req.content,
            n_slides=req.n_slides,
            template=req.template,
            ui_template_choice=req.ui_template_choice,
            custom_id=req.custom_id,
            instructions=req.instructions,
            filename=req.filename,
            user_id=str(uid),
            asset_ids=list(req.asset_ids or []),
            require_llm=bool(req.require_llm),
            fast_basic=bool(req.fast_basic),
        )
    )
    if not out.get("ok"):
        http_status = int(out.get("http_status") or 502)
        if http_status < 400:
            http_status = 502
        raise HTTPException(
            status_code=http_status,
            detail={
                "error": out.get("error") or "presenton_failed",
                "hint": out.get("hint") or "",
                "detail": out.get("detail") or "",
                "template_sent": out.get("template_sent"),
                "ui_template_choice": out.get("ui_template_choice"),
                "zinnia_verified": out.get("zinnia_verified"),
                "zinnia_note": out.get("zinnia_note"),
                "lifecycle": out.get("lifecycle"),
                "canonical_id": out.get("canonical_id"),
                "mapping_source": out.get("mapping_source"),
                "blocked_external": bool(out.get("blocked_external")),
                "block_code": out.get("block_code") or out.get("error") or "",
                "retries": out.get("retries"),
                "provider": out.get("provider"),
                "planner_mode": out.get("planner_mode"),
                "fallback": out.get("fallback"),
                "fallback_reason": out.get("fallback_reason"),
                "degraded": out.get("degraded"),
                "final_quality_status": out.get("final_quality_status"),
                "repair_attempts": out.get("repair_attempts"),
                "overlap_count": out.get("overlap_count"),
                "ungrounded_fact_count": out.get("ungrounded_fact_count"),
            },
        )
    return out


@router.post("/present/parse-pptx")
async def present_parse_pptx(
    file: UploadFile = File(...),
    _user: CurrentUser = Depends(get_current_user),
):
    """Parse uploaded .pptx into slide text + speaker notes for browser Present narration."""
    from app.services.pptx_parse import parse_pptx_bytes

    name = (file.filename or "").lower()
    if not name.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Upload a .pptx file")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 40_000_000:
        raise HTTPException(status_code=400, detail="PPTX too large (max 40MB)")
    try:
        slides = parse_pptx_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse PPTX: {e}") from e
    if not slides:
        raise HTTPException(status_code=400, detail="No slides found in that .pptx")
    return {"ok": True, "count": len(slides), "slides": slides, "filename": file.filename or "deck.pptx"}


class PresentPathIn(BaseModel):
    path: str
    slides: list[dict[str, Any]] | None = None


def _pptx_from_request(path_str: str):
    from app.services.pptx_paths import resolve_allowlisted_pptx

    try:
        return resolve_allowlisted_pptx(path_str)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="pptx_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="path_not_allowlisted") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/present/pptx")
def present_download_pptx(
    path: str,
    accept_warnings: bool = Query(False),
    _user: CurrentUser = Depends(get_current_user),
):
    """Download a generated PPTX from an allowlisted user folder (ZECT UI export)."""
    pptx = _pptx_from_request(path)
    from app.services.mentrix.presentation.deck_catalog import quality_gate_for_path

    gate = quality_gate_for_path(str(pptx))
    if gate.get("export_blocked") or gate.get("hard_blocked"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "export_blocked_critical_quality",
                "hint": "Critical quality findings cannot be accepted. Repair collisions, duplicates, clipping, or broken assets.",
                "hard_findings": gate.get("hard_findings") or [],
            },
        )
    return FileResponse(
        path=str(pptx),
        filename=pptx.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.get("/present/decks")
def present_list_decks(_user: CurrentUser = Depends(get_current_user), limit: int = Query(24, ge=1, le=80)):
    from app.services.mentrix.presentation.deck_catalog import list_recent_decks

    return {"ok": True, "items": list_recent_decks(limit=limit)}


@router.post("/present/blank")
def present_blank_deck(_user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.presentation.deck_catalog import create_blank_pptx

    dest = create_blank_pptx()
    return {"ok": True, "path": str(dest), "filename": dest.name}


@router.post("/present/import")
async def present_import_deck(
    file: UploadFile = File(...),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.presentation.deck_catalog import import_pptx_bytes

    name = (file.filename or "imported.pptx").lower()
    if not name.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Upload a .pptx file")
    data = await file.read()
    if not data or len(data) > 40_000_000:
        raise HTTPException(status_code=400, detail="invalid_pptx")
    dest = import_pptx_bytes(data, filename=file.filename or "imported.pptx")
    return {"ok": True, "path": str(dest), "filename": dest.name}


@router.get("/present/slide-preview")
def present_slide_preview(
    path: str,
    index: int = 0,
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.mentrix.presentation.slide_preview import cache_slide_preview

    pptx = _pptx_from_request(path)
    png = cache_slide_preview(pptx, max(0, index))
    return FileResponse(path=str(png), media_type="image/png", filename=png.name)


@router.get("/present/quality-gate")
def present_quality_gate(path: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.presentation.deck_catalog import quality_gate_for_path

    try:
        return quality_gate_for_path(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="pptx_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="path_not_allowlisted") from exc


@router.get("/present/template-cover/{template_id}")
def present_template_cover(template_id: str, _user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.presentation.template_definition import ensure_template_cover

    cover = ensure_template_cover(template_id)
    if cover is None or not cover.is_file():
        raise HTTPException(status_code=404, detail="cover_not_ready")
    return FileResponse(path=str(cover), media_type="image/png", filename=cover.name)


@router.post("/present/parse-pptx-path")
def present_parse_pptx_path(body: PresentPathIn, _user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.presentation.document import inspect_pptx_visuals, merge_sidecar_slides
    from app.services.pptx_parse import parse_pptx_bytes
    from app.services.pptx_paths import notes_sidecar_for_pptx

    pptx = _pptx_from_request(body.path)
    data = pptx.read_bytes()
    slides = parse_pptx_bytes(data)
    if not slides:
        raise HTTPException(status_code=400, detail="No slides found in that .pptx")
    sidecar_slides = None
    try:
        sidecar = notes_sidecar_for_pptx(pptx)
        if sidecar.is_file():
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("slides"), list):
                sidecar_slides = payload["slides"]
    except (PermissionError, OSError, ValueError, json.JSONDecodeError):
        sidecar_slides = None
    slides = merge_sidecar_slides(slides, sidecar_slides)
    return {
        "ok": True,
        "count": len(slides),
        "slides": slides,
        "filename": pptx.name,
        "path": str(pptx),
        "visuals": inspect_pptx_visuals(data),
    }


@router.post("/present/save-notes")
def present_save_notes(body: PresentPathIn, _user: CurrentUser = Depends(get_current_user)):
    """Persist speaker notes sidecar and round-trip notes/text into OOXML when possible."""
    pptx = _pptx_from_request(body.path)
    from app.services.pptx_paths import notes_sidecar_for_pptx, write_notes_sidecar

    try:
        sidecar = notes_sidecar_for_pptx(pptx)
        payload = {
            "path": str(pptx),
            "slides": body.slides or [],
        }
        write_notes_sidecar(sidecar, json.dumps(payload, indent=2))
        ooxml = False
        ooxml_error = ""
        try:
            from app.services.mentrix.presentation.document_io import apply_document_to_pptx

            apply_document_to_pptx(pptx, body.slides or [], user_id=str(getattr(_user, "user_id", None) or getattr(_user, "username", "anon")))
            ooxml = True
        except Exception as exc:  # noqa: BLE001 — sidecar already saved
            ooxml_error = str(exc)[:200]
        return {
            "ok": True,
            "notes_path": str(sidecar),
            "count": len(body.slides or []),
            "ooxml_roundtrip": ooxml,
            "ooxml_error": ooxml_error,
        }
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc) or "sidecar_rejected") from exc


@router.post("/companion/realtime/session")
def companion_realtime_session(
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mint OpenAI Realtime ephemeral client secret (API key never leaves server)."""
    from app.services.mentrix.realtime import mint_realtime_session

    return mint_realtime_session(db=db, user_id=_user.user_id)


class RealtimeToolRequest(BaseModel):
    tool: str
    args: dict = {}
    confirmed: bool = False
    project_key: str = ""
    project_id: int | None = None


@router.post("/companion/realtime/tool")
def companion_realtime_tool(
    req: RealtimeToolRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Execute a Realtime function call through Mentrix permission broker."""
    from app.services.mentrix.org_policy import ensure_companion_rules
    from app.services.mentrix.realtime import run_realtime_tool

    if not (req.tool or "").strip():
        raise HTTPException(status_code=400, detail="tool required")
    ensure_companion_rules(db)
    uid = getattr(user, "user_id", None) or getattr(user, "id", None)
    return run_realtime_tool(
        db,
        req.tool.strip(),
        req.args or {},
        user_id=uid if isinstance(uid, int) else None,
        project_id=req.project_id,
        project_key=req.project_key or "",
        created_by=getattr(user, "email", "") or "",
        user_confirmed=bool(req.confirmed),
    )


@router.get("/companion/media")
def companion_media_list(_user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.media_board import list_media

    return {"items": list_media()}


@router.get("/companion/media/{number}")
def companion_media_file(number: int, _user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.media_board import get_media_file

    path = get_media_file(number)
    if not path:
        raise HTTPException(status_code=404, detail="media not found")
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.websocket("/companion/realtime")
async def companion_realtime_ws(websocket: WebSocket, token: str = Query("")):
    """
    Authenticated Mentrix↔OpenAI Realtime relay.
    Client sends JSON control messages; audio frames forwarded to OpenAI when session active.
    For browser convenience, prefer ephemeral client_secret from /realtime/session and
    connect to OpenAI directly; this relay is available when proxying is preferred.
    """
    from app.infrastructure.auth.session_store import get_token_row
    from app.infrastructure.database import SessionLocal
    from app.services.mentrix.realtime import mint_realtime_session, realtime_enabled

    if not token:
        await websocket.close(code=4401)
        return
    db = SessionLocal()
    try:
        row = get_token_row(db, token)
        if not row:
            await websocket.close(code=4401)
            return
        user_id = row.user_id
    finally:
        db.close()

    await websocket.accept()
    if not realtime_enabled():
        await websocket.send_json({"event": "error", "data": {"error": "realtime_disabled", "fallback": "stt_sse"}})
        await websocket.close()
        return

    mint_db = SessionLocal()
    try:
        session = mint_realtime_session(db=mint_db, user_id=user_id)
    finally:
        mint_db.close()
    if not session.get("ok"):
        await websocket.send_json({"event": "error", "data": session})
        await websocket.close()
        return

    await websocket.send_json(
        {
            "event": "session",
            "data": {
                "realtime_enabled": True,
                "model": session.get("model"),
                "openai_ws_url": session.get("openai_ws_url"),
                "client_secret": session.get("client_secret"),
                "expires_at": session.get("expires_at"),
                "note": "Use client_secret to open OpenAI Realtime WS; tools via POST /companion/realtime/tool",
            },
        }
    )

    try:
        while True:
            msg = await websocket.receive_json()
            # Control channel: client reports orb state / tool results; relay echoes mentrix events
            if msg.get("type") == "ping":
                await websocket.send_json({"event": "pong"})
            elif msg.get("type") == "orb":
                await websocket.send_json({"event": "orb", "data": msg.get("data") or {}})
            else:
                await websocket.send_json({"event": "ack", "data": {"type": msg.get("type")}})
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass

"""Mentrix agent API — ForgeLoop + human approve → create PR."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.database import get_db
from app.models import FineTuneSample, MentrixRun
from app.services.forge_loop.orchestrator import (
    AGENT_ROLES,
    MODE_PIPELINE,
    continue_mentrix_after_plan,
    gates_allow_approve,
    gates_allow_create_pr,
    run_mentrix,
    validate_context_pack,
)

router = APIRouter(prefix="/api/mentrix", tags=["mentrix"])


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


def _run_to_dict(run: MentrixRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "mode": run.mode,
        "goal": run.goal,
        "current_agent": run.current_agent,
        "events": json.loads(run.events_json or "[]"),
        "result": json.loads(run.result_json or "{}"),
        "gates": json.loads(run.gates_json or "{}"),
        "next_step": run.next_step or "",
        "approved_at": run.approved_at.isoformat() if run.approved_at else None,
        "approved_by": run.approved_by or "",
        "pr_url": run.pr_url or "",
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
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
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
    run = run_mentrix(
        db,
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
    result = json.loads(run.result_json or "{}")
    plan = result.get("plan") or {}
    return {
        "run_id": run.id,
        "status": run.status,
        "plan_confirmed": bool(json.loads(run.gates_json or "{}").get("plan_confirmed")),
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
    result = json.loads(run.result_json or "{}")
    plan = dict(result.get("plan") or {})
    if req.summary is not None:
        plan["summary"] = req.summary
    if req.plan is not None:
        plan["summary"] = req.plan
    if req.phases is not None:
        plan["phases"] = req.phases
    if req.steps is not None:
        plan["steps"] = req.steps
    result["plan"] = plan
    cp = result.get("_checkpoint") or {}
    if cp.get("plan") is not None:
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


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_dict(run)


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

    gates = json.loads(run.gates_json or "{}")
    result = json.loads(run.result_json or "{}")

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
    events = json.loads(run.events_json or "[]")
    events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": "orchestrator",
        "message": f"Human approved by {run.approved_by}",
        "event": "approve",
        "next_step": "create_pr",
    })
    if req.acknowledge_issues:
        reason = (req.acknowledge_reason or "").strip() or "human override of non-security gates"
        waiver_event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "message": f"Acknowledge waiver by {run.approved_by}: {reason}",
            "event": "acknowledge_waiver",
            "waived_gates": waived,
            "reason": reason,
            "actor": run.approved_by,
        }
        events.append(waiver_event)
        result["acknowledge_waiver"] = {
            "waived_gates": waived,
            "reason": reason,
            "actor": run.approved_by,
            "ts": waiver_event["ts"],
        }
        run.result_json = json.dumps(result)
    run.events_json = json.dumps(events)
    db.commit()
    db.refresh(run)
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
    gates = json.loads(run.gates_json or "{}")
    result = json.loads(run.result_json or "{}")
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
            from app.routers.git_ops import CreatePRRequest as GitPRReq
            from app.routers.git_ops import create_pull_request as git_create_pr

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
    events = json.loads(run.events_json or "[]")
    events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": "integrator",
        "message": f"PR created: {pr_url}",
        "event": "create_pr",
        "pr_url": pr_url,
        "by": user.email,
    })
    run.events_json = json.dumps(events)
    result = json.loads(run.result_json or "{}")
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
            events.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "agent": "integrator",
                "message": f"SAST check: ok={gates['sast_ok']} ({sast.get('note') or ''})",
                "event": "sast_check",
            })
            run.events_json = json.dumps(events)
            if gates["sast_required"] and not gates["sast_ok"]:
                run.status = "awaiting_sast"
                run.next_step = "await_sast"
                events.append({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "agent": "integrator",
                    "message": "Awaiting Semgrep/GitHub SAST success — use POST /refresh-sast",
                    "event": "awaiting_sast",
                })
                run.events_json = json.dumps(events)
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
    gates = json.loads(run.gates_json or "{}")
    result = json.loads(run.result_json or "{}")
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
    events = json.loads(run.events_json or "[]")
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


class OrgPolicyImportRequest(BaseModel):
    pack: dict
    replace: bool = False


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
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """SSE stream: thinking → tool_start → artifact → token → done."""
    from app.services.mentrix.companion import iter_companion_events, sse_pack
    from app.services.mentrix.org_policy import ensure_companion_rules

    ensure_companion_rules(db)
    uid = getattr(user, "id", None)
    confirmed = [t.strip() for t in confirmed_tools.split(",") if t.strip()]

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
        ],
    }


@router.get("/companion/integrations")
def companion_integrations_status(_user: CurrentUser = Depends(get_current_user)):
    """Non-secret readiness for Mentrix tools (env-backed Slack/Jira). Never returns tokens."""
    import os

    from app.services.presenton_client import presenton_configured

    slack = bool((os.getenv("SLACK_BOT_TOKEN") or "").strip())
    jira = bool(
        (os.getenv("MCP_JIRA_URL") or os.getenv("JIRA_BASE_URL") or "").strip()
        and (os.getenv("JIRA_EMAIL") or "").strip()
        and (os.getenv("JIRA_API_TOKEN") or "").strip()
    )
    openai = bool((os.getenv("OPENAI_API_KEY") or "").strip())
    datadog = bool(
        (os.getenv("DATADOG_API_KEY") or "").strip() and (os.getenv("DATADOG_APP_KEY") or "").strip()
    )
    github = bool((os.getenv("GITHUB_TOKEN") or "").strip())
    zoom_join = (os.getenv("ZOOM_DEFAULT_JOIN_URL") or "").strip()
    return {
        "slack": slack,
        "jira": jira,
        "openai": openai,
        "datadog": datadog,
        "github": github,
        "presenton": presenton_configured(),
        "presenton_base_url": (os.getenv("PRESENTON_BASE_URL") or "").strip() or "",
        "zoom_join_url_configured": bool(zoom_join),
        "zoom_desktop_path_configured": bool((os.getenv("ZOOM_DESKTOP_PATH") or "").strip()),
        "slack_channel": (os.getenv("SLACK_DEFAULT_CHANNEL") or "#engineering") if slack else "",
    }


class PresentonGenerateRequest(BaseModel):
    content: str
    n_slides: int = 6
    template: str = "general"
    instructions: str = ""
    filename: str = ""


@router.get("/presenton/status")
def presenton_status(_user: CurrentUser = Depends(get_current_user)):
    from app.services.presenton_client import presenton_base_url, presenton_configured

    return {
        "configured": presenton_configured(),
        "base_url": presenton_base_url() or "",
    }


@router.post("/presenton/generate")
def presenton_generate(
    req: PresentonGenerateRequest,
    _user: CurrentUser = Depends(get_current_user),
):
    """Proxy Presenton generate → save PPTX under Documents/Desktop for Present Deck."""
    from app.services.presenton_client import generate_presentation

    out = generate_presentation(
        req.content,
        n_slides=req.n_slides,
        template=req.template or None,
        instructions=req.instructions or None,
        filename=req.filename or None,
    )
    if not out.get("ok"):
        raise HTTPException(
            status_code=502,
            detail=out.get("detail") or out.get("hint") or out.get("error") or "presenton_failed",
        )
    return out


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
    from app.core.auth.session_store import get_token_row
    from app.database import SessionLocal
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

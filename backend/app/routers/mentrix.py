"""Mentrix agent API — ForgeLoop + human approve → create PR."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.database import get_db
from app.models import FineTuneSample, MentrixRun
from app.services.forge_loop.orchestrator import (
    AGENT_ROLES,
    MODE_PIPELINE,
    gates_allow_approve,
    gates_allow_create_pr,
    run_mentrix,
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
    run.result_json = json.dumps(result)
    db.commit()
    db.refresh(run)
    return _run_to_dict(run)


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

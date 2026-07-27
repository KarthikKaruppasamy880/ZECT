"""Deployment Phase — Deployment orchestration, checklist management, and
real GitHub Actions triggering.

/checklist and /runbook only ever generated advice text — nothing here
actually deployed anything. /trigger-workflow is the first thing that does:
it fires a real workflow_dispatch run, gated by the Permissions Protocol's
deploy_.* -> require_approval rule (seeded in permissions.py but previously
enforced by nothing, since nothing in ZECT deployed anything to gate)."""

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openai import OpenAI, APIError
from app.core.auth.deps import CurrentUser, get_current_user
from app.database import get_db
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/deploy", tags=["deploy"])


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DeployChecklistRequest(BaseModel):
    project_name: str
    tech_stack: str | None = None
    environment: str = "production"  # staging, production
    deployment_type: str = "standard"  # standard, canary, blue-green


class ChecklistItem(BaseModel):
    category: str
    task: str
    critical: bool
    automated: bool


class DeployChecklistResponse(BaseModel):
    checklist: list[ChecklistItem]
    runbook: str
    rollback_plan: str
    model: str
    tokens_used: int


class DeployRunbookRequest(BaseModel):
    project_name: str
    tech_stack: str | None = None
    infrastructure: str | None = None  # AWS, GCP, Azure, on-prem
    services: list[str] = []


class DeployRunbookResponse(BaseModel):
    runbook: str
    estimated_downtime: str
    risk_level: str
    model: str
    tokens_used: int


class DeployTriggerRequest(BaseModel):
    owner: str
    repo: str
    workflow_file: str  # e.g. "deploy.yml", or the numeric workflow id as a string
    ref: str = "main"
    environment: str = "production"
    inputs: dict[str, str] = {}
    audit_id: int | None = None  # set when retrying after the approval step below granted it


class DeployTriggerResponse(BaseModel):
    status: str  # "dispatched", "pending_approval"
    audit_id: int | None = None
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/checklist", response_model=DeployChecklistResponse)
def generate_checklist(req: DeployChecklistRequest):
    """Generate a deployment checklist with runbook and rollback plan."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI Deployment Orchestrator. Generate a comprehensive deployment "
        "checklist for the given project. Include:\n"
        "1. Pre-deployment checks (tests, security scan, approvals)\n"
        "2. Deployment steps\n"
        "3. Post-deployment verification\n"
        "4. Rollback procedure\n\n"
        "Respond in this exact JSON format:\n"
        "{\n"
        '  "checklist": [\n'
        '    {"category": "<pre-deploy|deploy|post-deploy|monitoring>", '
        '"task": "<description>", "critical": <true|false>, "automated": <true|false>}\n'
        "  ],\n"
        '  "runbook": "<step-by-step deployment runbook in markdown>",\n'
        '  "rollback_plan": "<rollback procedure in markdown>"\n'
        "}\n"
        "Only return valid JSON."
    )

    user_content = (
        f"Project: {req.project_name}\n"
        f"Environment: {req.environment}\n"
        f"Deployment Type: {req.deployment_type}"
    )
    if req.tech_stack:
        user_content += f"\nTech Stack: {req.tech_stack}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=3000,
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0

        import json
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            data = {"checklist": [], "runbook": "Unable to generate.", "rollback_plan": ""}

        checklist = [
            ChecklistItem(
                category=item.get("category", "deploy"),
                task=item.get("task", ""),
                critical=item.get("critical", False),
                automated=item.get("automated", False),
            )
            for item in data.get("checklist", [])
        ]

        log_tokens(
            action="deploy_checklist",
            feature="deploy_phase",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )

        return DeployChecklistResponse(
            checklist=checklist,
            runbook=data.get("runbook", ""),
            rollback_plan=data.get("rollback_plan", ""),
            model="gpt-4o-mini",
            tokens_used=tokens,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.post("/runbook", response_model=DeployRunbookResponse)
def generate_runbook(req: DeployRunbookRequest):
    """Generate a detailed deployment runbook."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI Deployment Expert. Generate a detailed deployment runbook "
        "for the specified project and infrastructure. Include:\n"
        "- Prerequisites and environment setup\n"
        "- Step-by-step deployment commands\n"
        "- Health check verification steps\n"
        "- Monitoring and alerting setup\n"
        "- Rollback procedure with commands\n"
        "- Communication templates for stakeholders\n\n"
        "Format as clean markdown. Also assess:\n"
        "- Estimated downtime (e.g., '0 minutes', '5-10 minutes')\n"
        "- Risk level (low, medium, high)\n\n"
        "Start your response with:\n"
        "DOWNTIME: <estimate>\n"
        "RISK: <level>\n"
        "---\n"
        "<runbook content>"
    )

    user_content = f"Project: {req.project_name}"
    if req.tech_stack:
        user_content += f"\nTech Stack: {req.tech_stack}"
    if req.infrastructure:
        user_content += f"\nInfrastructure: {req.infrastructure}"
    if req.services:
        user_content += f"\nServices: {', '.join(req.services)}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=3000,
            temperature=0.3,
        )
        content = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0

        downtime = "Unknown"
        risk = "medium"
        runbook = content

        for line in content.split("\n"):
            if line.startswith("DOWNTIME:"):
                downtime = line.replace("DOWNTIME:", "").strip()
            elif line.startswith("RISK:"):
                risk = line.replace("RISK:", "").strip().lower()

        if "---" in content:
            runbook = content.split("---", 1)[1].strip()

        log_tokens(
            action="deploy_runbook",
            feature="deploy_phase",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )

        return DeployRunbookResponse(
            runbook=runbook,
            estimated_downtime=downtime,
            risk_level=risk,
            model="gpt-4o-mini",
            tokens_used=tokens,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.post("/trigger-workflow", response_model=DeployTriggerResponse)
def trigger_workflow(
    req: DeployTriggerRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fire a real GitHub Actions deployment run — gated by the deploy_.*
    permission rule. First call (no audit_id) checks policy: allowed rules
    dispatch immediately, require_approval rules come back pending with an
    audit_id to approve via POST /api/permissions/audits/{id}/approve, then
    retry this call with that audit_id."""
    from app.models import PermissionAudit
    from app.routers.audit_trail import log_audit
    from app.routers.permissions import PermissionCheck, check_permission

    action = f"deploy_{req.environment}"

    if req.audit_id is not None:
        audit = db.query(PermissionAudit).filter(PermissionAudit.id == req.audit_id).first()
        if not audit or audit.action != action or audit.result != "granted":
            raise HTTPException(
                status_code=403,
                detail="Approval not found or not granted for this deploy request — approve it first via /api/permissions/audits/{id}/approve",
            )
    else:
        check = check_permission(PermissionCheck(action=action, user_id=current_user.user_id), db=db)
        if check["result"] == "denied":
            raise HTTPException(status_code=403, detail=f"Deploy denied by policy: {action}")
        if check["result"] == "pending_approval":
            return DeployTriggerResponse(
                status="pending_approval",
                audit_id=check["audit_id"],
                message=(
                    f"Deploy requires approval — POST /api/permissions/audits/{check['audit_id']}/approve, "
                    "then retry this call with that audit_id."
                ),
            )

    from app import github_service

    try:
        result = github_service.trigger_workflow_dispatch(
            req.owner, req.repo, req.workflow_file, req.ref, req.inputs
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub Actions dispatch failed: {e}")

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="deploy_trigger_workflow",
        resource_type="deploy",
        details={"owner": req.owner, "repo": req.repo, "workflow": req.workflow_file, "ref": req.ref},
    )

    return DeployTriggerResponse(
        status="dispatched", audit_id=req.audit_id, message=result.get("message", "Workflow dispatched")
    )

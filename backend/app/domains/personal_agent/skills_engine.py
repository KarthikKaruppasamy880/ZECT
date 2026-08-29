"""Zinnia Skills Engine — skill registry, trigger matching, and seed skills.

Also the sole home of the "template" concept (a freeform reusable
prompt/snippet a skill carries) and the AI pattern-detector, both merged in
from the standalone Skill Library page/router — that page duplicated this
one's purpose with a thinner data model (no versioning, no trigger
matching, no execution tracking) and was never wired into anything beyond
itself except Mentrix's "Active Skill" picker, which now reads from here.
A skill's template lives in manifest["template"] rather than its own column
— no schema change needed, and every other skill attribute (inputs/outputs/
config for the seed skills) already lives in manifest too.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import SkillDefinition, SkillExecutionLog

router = APIRouter(prefix="/api/skills-engine", tags=["skills-engine"])


# ── Pydantic schemas ────────────────────────────────────────────────

class SkillCreate(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    category: str = "general"
    trigger_pattern: str = ""
    manifest: dict = {}
    template: str = ""
    tags: list[str] = []
    script_body: str = ""
    project_id: Optional[int] = None
    is_seed: bool = False
    owner: str = ""
    provenance: str = "local"
    approval_required: bool = True
    timeout_seconds: int = 300
    required_capabilities: list[str] = []
    allowed_tools: list[str] = []
    input_schema: dict = {}
    output_schema: dict = {}
    test_cases: list = []


class SkillUpdate(BaseModel):
    description: Optional[str] = None
    version: Optional[str] = None
    trigger_pattern: Optional[str] = None
    manifest: Optional[dict] = None
    template: Optional[str] = None
    tags: Optional[list[str]] = None
    script_body: Optional[str] = None
    is_active: Optional[bool] = None
    owner: Optional[str] = None
    provenance: Optional[str] = None
    approval_required: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    required_capabilities: Optional[list[str]] = None
    allowed_tools: Optional[list[str]] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    test_cases: Optional[list] = None


class SkillExecLog(BaseModel):
    skill_id: int
    project_id: Optional[int] = None
    input_data: dict = {}
    output_data: dict = {}
    success: bool = True
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    approved: bool = False  # required when skill.approval_required
    requested_tools: list[str] = []


class DetectSkillRequest(BaseModel):
    code: str
    context: Optional[str] = None


class DetectSkillResponse(BaseModel):
    detected_patterns: list[dict]
    suggested_skills: list[dict]
    model: str
    tokens_used: int


class TriggerMatch(BaseModel):
    intent: str
    project_id: Optional[int] = None


# ── Seed skill definitions ─────────────────────────────────────────

SEED_SKILLS = [
    {
        "name": "zinnia-code-review",
        "version": "1.0.0",
        "description": "Automated code review with configurable rulesets, severity levels, and auto-fix suggestions",
        "category": "quality",
        "trigger_pattern": "code.review|pull_request|lint|quality",
        "manifest": {
            "inputs": ["repo_url", "branch", "file_patterns"],
            "outputs": ["findings", "severity_summary", "auto_fix_patches"],
            "config": {"max_files": 100, "severity_threshold": "warning"},
        },
        "is_seed": True,
    },
    {
        "name": "zinnia-debug",
        "version": "1.0.0",
        "description": "Structured debugging: reproduce, hypothesize, instrument, verify, and document root cause",
        "category": "debugging",
        "trigger_pattern": "debug|error|exception|traceback|bug|investigate",
        "manifest": {
            "inputs": ["error_description", "stack_trace", "repo_context"],
            "outputs": ["root_cause", "fix_suggestion", "prevention_steps"],
            "config": {"max_depth": 5, "timeout_seconds": 300},
        },
        "is_seed": True,
    },
    {
        "name": "zinnia-deploy",
        "version": "1.0.0",
        "description": "Deployment checklist: pre-flight checks, rollout steps, smoke tests, rollback plan",
        "category": "deployment",
        "trigger_pattern": "deploy|release|rollout|ship|publish",
        "manifest": {
            "inputs": ["environment", "version", "changelog"],
            "outputs": ["deploy_plan", "rollback_plan", "smoke_test_results"],
            "config": {"environments": ["staging", "production"], "requires_approval": True},
        },
        "is_seed": True,
    },
    {
        "name": "zinnia-git-safety",
        "version": "1.0.0",
        "description": "Git safety guardrails: prevent force push, validate branch naming, check merge conflicts",
        "category": "git",
        "trigger_pattern": "git|branch|merge|push|commit",
        "manifest": {
            "inputs": ["git_operation", "branch_name", "target_branch"],
            "outputs": ["is_safe", "warnings", "suggested_alternatives"],
            "config": {"block_force_push": True, "branch_pattern": "^(feature|fix|hotfix)/.*"},
        },
        "is_seed": True,
    },
    {
        "name": "zinnia-memory-manager",
        "version": "1.0.0",
        "description": "Memory lifecycle: archive stale workspaces, promote lessons, run dream cycles",
        "category": "memory",
        "trigger_pattern": "memory|learn|recall|forget|archive",
        "manifest": {
            "inputs": ["operation", "project_id"],
            "outputs": ["result", "affected_count"],
            "config": {"auto_archive_days": 2, "dream_cycle_hours": 6},
        },
        "is_seed": True,
    },
    {
        "name": "zinnia-skillforge",
        "version": "1.0.0",
        "description": "Meta-skill: create, test, and register new skills from natural language descriptions",
        "category": "meta",
        "trigger_pattern": "create.skill|new.skill|skill.forge|build.skill",
        "manifest": {
            "inputs": ["skill_description", "trigger_patterns", "examples"],
            "outputs": ["skill_manifest", "test_results", "registration_status"],
            "config": {"auto_register": False, "test_required": True},
        },
        "is_seed": True,
    },
    {
        "name": "zinnia-blueprint",
        "version": "1.0.0",
        "description": "Generate architectural blueprints from requirements with component diagrams and API specs",
        "category": "architecture",
        "trigger_pattern": "blueprint|architecture|design|diagram|spec",
        "manifest": {
            "inputs": ["requirements", "tech_stack", "constraints"],
            "outputs": ["blueprint_doc", "component_diagram", "api_spec"],
            "config": {"format": "markdown", "include_diagrams": True},
        },
        "is_seed": True,
    },
    {
        "name": "zinnia-project-scaffold",
        "version": "1.0.0",
        "description": "Scaffold a new ZECT project from a stack template — name, description, starter Mentrix prompts, and folder conventions",
        "category": "project_scaffold",
        "trigger_pattern": "new.project|scaffold|bootstrap|create.project|greenfield",
        "manifest": {
            "template": (
                "Create a new project named {{project_name}} using stack {{stack}}. "
                "Follow ZECT conventions: Projects → Developer Workspace → Index/Lattice → Mentrix. "
                "Starter folders: src/, docs/, tests/. First Mentrix goal: bootstrap README and CI."
            ),
            "inputs": ["project_name", "stack", "description"],
            "outputs": ["project_fields", "starter_prompts", "folder_layout"],
            "config": {
                "stacks": ["python-fastapi", "react-vite", "full-stack"],
                "default_stack": "full-stack",
                "scaffold": True,
            },
            "scaffold": {
                "default_name": "New Mentrix Project",
                "default_description": "Scaffolded via Skills Engine — Mentrix delivery ready.",
                "starter_prompts": [
                    "Index the repo and summarize architecture",
                    "Propose Ask → Plan → Build milestones",
                ],
            },
        },
        "is_seed": True,
    },
]


def _seed_if_empty(db: Session):
    """Ensure default seed skills exist (insert any missing by name)."""
    now = datetime.now(timezone.utc)
    existing = {r[0] for r in db.query(SkillDefinition.name).all()}
    added = False
    for s in SEED_SKILLS:
        if s["name"] in existing:
            continue
        skill = SkillDefinition(
            name=s["name"],
            version=s["version"],
            description=s["description"],
            category=s["category"],
            trigger_pattern=s["trigger_pattern"],
            manifest=s["manifest"],
            script_body="",
            project_id=None,
            is_seed=s["is_seed"],
            is_active=True,
            execution_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(skill)
        added = True
    if added:
        db.commit()


def _skill_to_dict(skill: SkillDefinition) -> dict:
    """Convert a SkillDefinition ORM object to a JSON-friendly dict."""
    manifest = skill.manifest or {}
    return {
        "id": skill.id,
        "name": skill.name,
        "version": skill.version,
        "description": skill.description,
        "category": skill.category,
        "trigger_pattern": skill.trigger_pattern,
        "manifest": manifest,
        "template": manifest.get("template", ""),
        "tags": manifest.get("tags", []),
        "script_body": skill.script_body or "",
        "project_id": skill.project_id,
        "is_seed": skill.is_seed,
        "is_active": skill.is_active,
        "execution_count": skill.execution_count,
        "last_executed_at": skill.last_executed_at.isoformat() if skill.last_executed_at else None,
        "owner": getattr(skill, "owner", "") or "",
        "provenance": getattr(skill, "provenance", None) or ("seed" if skill.is_seed else "local"),
        "approval_required": bool(getattr(skill, "approval_required", True)),
        "timeout_seconds": int(getattr(skill, "timeout_seconds", None) or 300),
        "required_capabilities": getattr(skill, "required_capabilities", None) or [],
        "allowed_tools": getattr(skill, "allowed_tools", None) or [],
        "input_schema": getattr(skill, "input_schema", None) or {},
        "output_schema": getattr(skill, "output_schema", None) or {},
        "test_cases": getattr(skill, "test_cases", None) or [],
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
    }


def _log_to_dict(log: SkillExecutionLog) -> dict:
    """Convert a SkillExecutionLog ORM object to a JSON-friendly dict."""
    return {
        "id": log.id,
        "skill_id": log.skill_id,
        "skill_name": log.skill_name,
        "project_id": log.project_id,
        "input_data": log.input_data or {},
        "output_data": log.output_data or {},
        "success": log.success,
        "duration_seconds": log.duration_seconds,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/skills")
def list_skills(
    category: Optional[str] = None,
    active_only: bool = True,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List all registered skills with optional filters."""
    _seed_if_empty(db)
    query = db.query(SkillDefinition)
    if active_only:
        query = query.filter(SkillDefinition.is_active == True)
    if category:
        query = query.filter(SkillDefinition.category == category)
    if project_id is not None:
        query = query.filter(
            (SkillDefinition.project_id == None) | (SkillDefinition.project_id == project_id)
        )
    skills = query.order_by(SkillDefinition.id).all()
    return [_skill_to_dict(s) for s in skills]


@router.get("/skills/{skill_id}")
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    """Get a specific skill by ID."""
    _seed_if_empty(db)
    skill = db.query(SkillDefinition).filter(SkillDefinition.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _skill_to_dict(skill)


@router.post("/skills")
def create_skill(body: SkillCreate, db: Session = Depends(get_db)):
    """Register a new skill."""
    _seed_if_empty(db)
    existing = db.query(SkillDefinition).filter(
        SkillDefinition.name == body.name,
        SkillDefinition.is_active == True,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Skill '{body.name}' already exists")

    now = datetime.now(timezone.utc)
    manifest = dict(body.manifest or {})
    if body.template:
        manifest["template"] = body.template
    if body.tags:
        manifest["tags"] = body.tags
    skill = SkillDefinition(
        name=body.name,
        version=body.version,
        description=body.description,
        category=body.category,
        trigger_pattern=body.trigger_pattern,
        manifest=manifest,
        script_body=body.script_body,
        project_id=body.project_id,
        is_seed=body.is_seed,
        is_active=True,
        execution_count=0,
        owner=body.owner or "",
        provenance=body.provenance or ("seed" if body.is_seed else "local"),
        approval_required=body.approval_required,
        timeout_seconds=body.timeout_seconds,
        required_capabilities=body.required_capabilities or [],
        allowed_tools=body.allowed_tools or [],
        input_schema=body.input_schema or {},
        output_schema=body.output_schema or {},
        test_cases=body.test_cases or [],
        created_at=now,
        updated_at=now,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill)


@router.put("/skills/{skill_id}")
def update_skill(skill_id: int, body: SkillUpdate, db: Session = Depends(get_db)):
    """Update an existing skill."""
    _seed_if_empty(db)
    skill = db.query(SkillDefinition).filter(SkillDefinition.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if body.description is not None:
        skill.description = body.description
    if body.version is not None:
        skill.version = body.version
    if body.trigger_pattern is not None:
        skill.trigger_pattern = body.trigger_pattern
    manifest = dict(body.manifest) if body.manifest is not None else dict(skill.manifest or {})
    if body.template is not None:
        manifest["template"] = body.template
    if body.tags is not None:
        manifest["tags"] = body.tags
    if body.manifest is not None or body.template is not None or body.tags is not None:
        skill.manifest = manifest
    if body.script_body is not None:
        skill.script_body = body.script_body
    if body.is_active is not None:
        skill.is_active = body.is_active
    if body.owner is not None:
        skill.owner = body.owner
    if body.provenance is not None:
        skill.provenance = body.provenance
    if body.approval_required is not None:
        skill.approval_required = body.approval_required
    if body.timeout_seconds is not None:
        skill.timeout_seconds = body.timeout_seconds
    if body.required_capabilities is not None:
        skill.required_capabilities = body.required_capabilities
    if body.allowed_tools is not None:
        skill.allowed_tools = body.allowed_tools
    if body.input_schema is not None:
        skill.input_schema = body.input_schema
    if body.output_schema is not None:
        skill.output_schema = body.output_schema
    if body.test_cases is not None:
        skill.test_cases = body.test_cases
    skill.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill)


@router.delete("/skills/{skill_id}")
def deactivate_skill(skill_id: int, db: Session = Depends(get_db)):
    """Deactivate a skill (soft delete)."""
    _seed_if_empty(db)
    skill = db.query(SkillDefinition).filter(SkillDefinition.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.is_active = False
    skill.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "deactivated", "skill_id": skill_id}


@router.post("/match")
def match_skills(body: TriggerMatch, db: Session = Depends(get_db)):
    """Match skills by intent against trigger patterns."""
    _seed_if_empty(db)
    query = db.query(SkillDefinition).filter(
        SkillDefinition.is_active == True,
        SkillDefinition.trigger_pattern != "",
    )
    if body.project_id is not None:
        query = query.filter(
            (SkillDefinition.project_id == None) | (SkillDefinition.project_id == body.project_id)
        )
    all_skills = query.all()

    intent_lower = body.intent.lower()
    matches = []
    for s in all_skills:
        patterns = s.trigger_pattern.split("|")
        score = 0
        for p in patterns:
            p_clean = p.strip().replace(".", " ").lower()
            if p_clean in intent_lower:
                score += 2
            elif any(w in intent_lower for w in p_clean.split()):
                score += 1
        if score > 0:
            matches.append({
                "skill": _skill_to_dict(s),
                "score": score,
                "trigger_pattern": s.trigger_pattern,
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {
        "intent": body.intent,
        "matches": matches[:5],
        "total_matches": len(matches),
    }


@router.post("/execute/{skill_id}")
def log_execution(skill_id: int, body: SkillExecLog, db: Session = Depends(get_db)):
    """Gate + log a skill execution (never auto-runs untrusted script_body)."""
    _seed_if_empty(db)
    skill = db.query(SkillDefinition).filter(SkillDefinition.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if not skill.is_active:
        raise HTTPException(status_code=403, detail="Skill is inactive")

    approval_required = bool(getattr(skill, "approval_required", True))
    if approval_required and not body.approved:
        raise HTTPException(
            status_code=403,
            detail="Skill requires explicit approval before execution logging",
        )

    from app.services.mentrix.skill_governance import (
        normalize_manifest,
        tool_allowed,
        validate_manifest,
    )

    governed = normalize_manifest(skill.manifest if isinstance(skill.manifest, dict) else {}, skill_row=skill)
    manifest_errors = validate_manifest(governed)
    if manifest_errors and (os.getenv("MENTRIX_SKILL_MANIFEST_STRICT") or "1").strip() not in (
        "0",
        "false",
        "off",
    ):
        # Soft-enforce: require prohibited_ops at minimum; missing keys get filled by normalize
        hard = [e for e in manifest_errors if e.startswith("must_prohibit:")]
        if hard:
            raise HTTPException(status_code=403, detail=f"Skill manifest policy: {hard}")

    allowed = list(getattr(skill, "allowed_tools", None) or []) or list(governed.get("allowed_tools") or [])
    if body.requested_tools:
        for t in body.requested_tools:
            ok_t, reason = tool_allowed(governed, t)
            if not ok_t:
                raise HTTPException(status_code=403, detail=f"Tool '{t}' blocked: {reason}")
        if allowed:
            disallowed = [t for t in body.requested_tools if t not in allowed and "*" not in allowed]
            if disallowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Tools not allowed for this skill: {disallowed}",
                )

    timeout = int(getattr(skill, "timeout_seconds", None) or 300)
    if body.duration_seconds and body.duration_seconds > timeout:
        raise HTTPException(
            status_code=408,
            detail=f"Skill exceeded timeout_seconds={timeout}",
        )

    # Untrusted skills never auto-execute script_body — Stage B only records gated runs.
    if (skill.script_body or "").strip() and (getattr(skill, "provenance", "") or "") == "imported":
        if not body.approved:
            raise HTTPException(status_code=403, detail="Imported skills require approval")

    now = datetime.now(timezone.utc)
    skill.execution_count = (skill.execution_count or 0) + 1
    skill.last_executed_at = now

    log_entry = SkillExecutionLog(
        skill_id=skill_id,
        skill_name=skill.name,
        project_id=body.project_id,
        input_data=body.input_data,
        output_data={
            **(body.output_data or {}),
            "_gate": {
                "approved": body.approved,
                "timeout_seconds": timeout,
                "allowed_tools": allowed,
                "script_executed": False,
            },
        },
        success=body.success,
        duration_seconds=body.duration_seconds,
        error_message=body.error_message,
        created_at=now,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return _log_to_dict(log_entry)


@router.get("/executions")
def list_executions(
    skill_id: Optional[int] = None,
    project_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List skill execution logs."""
    query = db.query(SkillExecutionLog)
    if skill_id is not None:
        query = query.filter(SkillExecutionLog.skill_id == skill_id)
    if project_id is not None:
        query = query.filter(SkillExecutionLog.project_id == project_id)
    logs = query.order_by(desc(SkillExecutionLog.id)).limit(limit).all()
    return [_log_to_dict(l) for l in logs]


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """List all skill categories with counts."""
    _seed_if_empty(db)
    rows = (
        db.query(SkillDefinition.category, func.count(SkillDefinition.id))
        .filter(SkillDefinition.is_active == True)
        .group_by(SkillDefinition.category)
        .order_by(SkillDefinition.category)
        .all()
    )
    return [{"category": cat, "count": cnt} for cat, cnt in rows]


@router.get("/stats")
def skill_stats(db: Session = Depends(get_db)):
    """Get skills engine statistics."""
    _seed_if_empty(db)
    total = db.query(func.count(SkillDefinition.id)).filter(SkillDefinition.is_active == True).scalar() or 0
    seeds = db.query(func.count(SkillDefinition.id)).filter(SkillDefinition.is_active == True, SkillDefinition.is_seed == True).scalar() or 0
    total_execs = db.query(func.count(SkillExecutionLog.id)).scalar() or 0
    success_execs = db.query(func.count(SkillExecutionLog.id)).filter(SkillExecutionLog.success == True).scalar() or 0
    cat_count = db.query(func.count(func.distinct(SkillDefinition.category))).filter(SkillDefinition.is_active == True).scalar() or 0
    return {
        "total_skills": total,
        "seed_skills": seeds,
        "custom_skills": total - seeds,
        "total_executions": total_execs,
        "successful_executions": success_execs,
        "categories": cat_count,
    }


# ── AI pattern detection (merged in from the standalone Skill Library) ─

def _get_openai_client():
    from openai import OpenAI

    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


@router.post("/detect", response_model=DetectSkillResponse)
def detect_patterns(req: DetectSkillRequest):
    """Detect reusable patterns in code and suggest skills to register."""
    import json

    from openai import APIError

    from app.token_tracker import log_tokens

    client = _get_openai_client()

    system_prompt = (
        "You are ZECT AI Skills Detector. Analyze the provided code and identify "
        "reusable patterns that could be saved as skills/templates for future use. "
        "Look for:\n"
        "- Common design patterns (singleton, factory, observer, etc.)\n"
        "- Boilerplate code that could be templated\n"
        "- Testing patterns\n"
        "- API endpoint patterns\n"
        "- Error handling patterns\n"
        "- Configuration patterns\n\n"
        "Respond in JSON format:\n"
        "{\n"
        '  "detected_patterns": [\n'
        '    {"name": "<pattern name>", "type": "<design|boilerplate|testing|api|config>", '
        '"description": "<what it does>", "lines": "<line range>"}\n'
        "  ],\n"
        '  "suggested_skills": [\n'
        '    {"name": "<skill name>", "category": "<category>", '
        '"description": "<what it does>", "template": "<templated version>"}\n'
        "  ]\n"
        "}\nOnly return valid JSON."
    )

    user_content = f"Code:\n```\n{req.code[:6000]}\n```"
    if req.context:
        user_content += f"\nContext: {req.context[:1000]}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=2000,
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            data = {"detected_patterns": [], "suggested_skills": []}

        log_tokens(
            action="skills_detect",
            feature="skills_engine",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )

        return DetectSkillResponse(
            detected_patterns=data.get("detected_patterns", []),
            suggested_skills=data.get("suggested_skills", []),
            model="gpt-4o-mini",
            tokens_used=tokens,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")

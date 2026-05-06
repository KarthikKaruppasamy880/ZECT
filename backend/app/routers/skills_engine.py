"""Zinnia Skills Engine — skill registry, trigger matching, and seed skills."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
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
    script_body: str = ""
    project_id: Optional[int] = None
    is_seed: bool = False


class SkillUpdate(BaseModel):
    description: Optional[str] = None
    version: Optional[str] = None
    trigger_pattern: Optional[str] = None
    manifest: Optional[dict] = None
    script_body: Optional[str] = None
    is_active: Optional[bool] = None


class TriggerMatch(BaseModel):
    intent: str
    project_id: Optional[int] = None


class SkillExecLog(BaseModel):
    skill_id: int
    project_id: Optional[int] = None
    input_data: dict = {}
    output_data: dict = {}
    success: bool = True
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


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
        "name": "zinnia-migration",
        "version": "1.0.0",
        "description": "Database and API migration planner with rollback scripts and data validation",
        "category": "migration",
        "trigger_pattern": "migrate|migration|schema.change|database.update",
        "manifest": {
            "inputs": ["source_schema", "target_schema", "data_constraints"],
            "outputs": ["migration_plan", "rollback_script", "validation_queries"],
            "config": {"auto_rollback": True, "dry_run_first": True},
        },
        "is_seed": True,
    },
]


def _seed_if_empty(db: Session):
    """Seed the database with default skills if empty."""
    count = db.query(func.count(SkillDefinition.id)).scalar()
    if count > 0:
        return
    now = datetime.now(timezone.utc)
    for s in SEED_SKILLS:
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
    db.commit()


def _skill_to_dict(skill: SkillDefinition) -> dict:
    """Convert a SkillDefinition ORM object to a JSON-friendly dict."""
    return {
        "id": skill.id,
        "name": skill.name,
        "version": skill.version,
        "description": skill.description,
        "category": skill.category,
        "trigger_pattern": skill.trigger_pattern,
        "manifest": skill.manifest or {},
        "script_body": skill.script_body or "",
        "project_id": skill.project_id,
        "is_seed": skill.is_seed,
        "is_active": skill.is_active,
        "execution_count": skill.execution_count,
        "last_executed_at": skill.last_executed_at.isoformat() if skill.last_executed_at else None,
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
    skill = SkillDefinition(
        name=body.name,
        version=body.version,
        description=body.description,
        category=body.category,
        trigger_pattern=body.trigger_pattern,
        manifest=body.manifest,
        script_body=body.script_body,
        project_id=body.project_id,
        is_seed=body.is_seed,
        is_active=True,
        execution_count=0,
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
    if body.manifest is not None:
        skill.manifest = body.manifest
    if body.script_body is not None:
        skill.script_body = body.script_body
    if body.is_active is not None:
        skill.is_active = body.is_active
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
    """Log a skill execution result."""
    _seed_if_empty(db)
    skill = db.query(SkillDefinition).filter(SkillDefinition.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    now = datetime.now(timezone.utc)
    skill.execution_count = (skill.execution_count or 0) + 1
    skill.last_executed_at = now

    log_entry = SkillExecutionLog(
        skill_id=skill_id,
        skill_name=skill.name,
        project_id=body.project_id,
        input_data=body.input_data,
        output_data=body.output_data,
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

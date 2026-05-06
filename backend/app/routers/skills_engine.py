"""Zinnia Skills Engine — skill registry, trigger matching, and seed skills."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db

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


# ── In-memory skill store (backed by DB when available) ─────────────

# We keep an in-memory registry so skills work even without the
# SkillDefinition / SkillExecutionLog models being present in models.py.
# If they exist we persist; otherwise we use this dict.

_skill_registry: list[dict] = []
_exec_logs: list[dict] = []
_next_id = 1
_next_log_id = 1


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


def _seed_if_empty():
    """Seed the in-memory registry with default skills if empty."""
    global _next_id
    if len(_skill_registry) > 0:
        return
    for s in SEED_SKILLS:
        _skill_registry.append({
            "id": _next_id,
            "name": s["name"],
            "version": s["version"],
            "description": s["description"],
            "category": s["category"],
            "trigger_pattern": s["trigger_pattern"],
            "manifest": s["manifest"],
            "script_body": "",
            "project_id": None,
            "is_seed": s["is_seed"],
            "is_active": True,
            "execution_count": 0,
            "last_executed_at": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        })
        _next_id += 1


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/skills")
def list_skills(
    category: Optional[str] = None,
    active_only: bool = True,
    project_id: Optional[int] = None,
):
    """List all registered skills with optional filters."""
    _seed_if_empty()
    results = _skill_registry
    if active_only:
        results = [s for s in results if s["is_active"]]
    if category:
        results = [s for s in results if s["category"] == category]
    if project_id is not None:
        results = [s for s in results if s["project_id"] is None or s["project_id"] == project_id]
    return results


@router.get("/skills/{skill_id}")
def get_skill(skill_id: int):
    """Get a specific skill by ID."""
    _seed_if_empty()
    for s in _skill_registry:
        if s["id"] == skill_id:
            return s
    raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/skills")
def create_skill(body: SkillCreate):
    """Register a new skill."""
    global _next_id
    _seed_if_empty()
    # Check duplicate name
    for s in _skill_registry:
        if s["name"] == body.name and s["is_active"]:
            raise HTTPException(status_code=409, detail=f"Skill '{body.name}' already exists")

    skill = {
        "id": _next_id,
        "name": body.name,
        "version": body.version,
        "description": body.description,
        "category": body.category,
        "trigger_pattern": body.trigger_pattern,
        "manifest": body.manifest,
        "script_body": body.script_body,
        "project_id": body.project_id,
        "is_seed": body.is_seed,
        "is_active": True,
        "execution_count": 0,
        "last_executed_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _next_id += 1
    _skill_registry.append(skill)
    return skill


@router.put("/skills/{skill_id}")
def update_skill(skill_id: int, body: SkillUpdate):
    """Update an existing skill."""
    _seed_if_empty()
    for s in _skill_registry:
        if s["id"] == skill_id:
            if body.description is not None:
                s["description"] = body.description
            if body.version is not None:
                s["version"] = body.version
            if body.trigger_pattern is not None:
                s["trigger_pattern"] = body.trigger_pattern
            if body.manifest is not None:
                s["manifest"] = body.manifest
            if body.script_body is not None:
                s["script_body"] = body.script_body
            if body.is_active is not None:
                s["is_active"] = body.is_active
            s["updated_at"] = datetime.utcnow().isoformat()
            return s
    raise HTTPException(status_code=404, detail="Skill not found")


@router.delete("/skills/{skill_id}")
def deactivate_skill(skill_id: int):
    """Deactivate a skill (soft delete)."""
    _seed_if_empty()
    for s in _skill_registry:
        if s["id"] == skill_id:
            s["is_active"] = False
            s["updated_at"] = datetime.utcnow().isoformat()
            return {"status": "deactivated", "skill_id": skill_id}
    raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/match")
def match_skills(body: TriggerMatch):
    """Match skills by intent against trigger patterns."""
    import re
    _seed_if_empty()
    intent_lower = body.intent.lower()
    matches = []
    for s in _skill_registry:
        if not s["is_active"]:
            continue
        if body.project_id is not None and s["project_id"] is not None and s["project_id"] != body.project_id:
            continue
        if not s["trigger_pattern"]:
            continue
        # Check if any trigger pattern word matches
        patterns = s["trigger_pattern"].split("|")
        score = 0
        for p in patterns:
            p_clean = p.strip().replace(".", " ").lower()
            if p_clean in intent_lower:
                score += 2
            elif any(w in intent_lower for w in p_clean.split()):
                score += 1
        if score > 0:
            matches.append({"skill": s, "score": score, "trigger_pattern": s["trigger_pattern"]})

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {
        "intent": body.intent,
        "matches": matches[:5],
        "total_matches": len(matches),
    }


@router.post("/execute/{skill_id}")
def log_execution(skill_id: int, body: SkillExecLog):
    """Log a skill execution result."""
    global _next_log_id
    _seed_if_empty()

    # Find skill
    skill = None
    for s in _skill_registry:
        if s["id"] == skill_id:
            skill = s
            break
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Update skill stats
    skill["execution_count"] = skill.get("execution_count", 0) + 1
    skill["last_executed_at"] = datetime.utcnow().isoformat()

    log_entry = {
        "id": _next_log_id,
        "skill_id": skill_id,
        "skill_name": skill["name"],
        "project_id": body.project_id,
        "input_data": body.input_data,
        "output_data": body.output_data,
        "success": body.success,
        "duration_seconds": body.duration_seconds,
        "error_message": body.error_message,
        "created_at": datetime.utcnow().isoformat(),
    }
    _next_log_id += 1
    _exec_logs.append(log_entry)
    return log_entry


@router.get("/executions")
def list_executions(
    skill_id: Optional[int] = None,
    project_id: Optional[int] = None,
    limit: int = 50,
):
    """List skill execution logs."""
    results = _exec_logs
    if skill_id is not None:
        results = [l for l in results if l["skill_id"] == skill_id]
    if project_id is not None:
        results = [l for l in results if l.get("project_id") == project_id]
    return sorted(results, key=lambda x: x["id"], reverse=True)[:limit]


@router.get("/categories")
def list_categories():
    """List all skill categories with counts."""
    _seed_if_empty()
    cats: dict[str, int] = {}
    for s in _skill_registry:
        if s["is_active"]:
            cats[s["category"]] = cats.get(s["category"], 0) + 1
    return [{"category": k, "count": v} for k, v in sorted(cats.items())]


@router.get("/stats")
def skill_stats():
    """Get skills engine statistics."""
    _seed_if_empty()
    active = [s for s in _skill_registry if s["is_active"]]
    return {
        "total_skills": len(active),
        "seed_skills": len([s for s in active if s.get("is_seed")]),
        "custom_skills": len([s for s in active if not s.get("is_seed")]),
        "total_executions": len(_exec_logs),
        "successful_executions": len([l for l in _exec_logs if l["success"]]),
        "categories": len(set(s["category"] for s in active)),
    }

"""Skills — Pattern detection, auto-save, and skill library management."""

import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Skill
from openai import OpenAI, APIError
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/skills", tags=["skills"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SkillCreate(BaseModel):
    name: str
    description: str
    category: str = "general"  # general, testing, deployment, review, architecture
    template: str  # The actual skill content/template
    trigger_pattern: str | None = None  # Regex or keyword pattern that triggers this skill
    tags: list[str] = []
    repo_id: int | None = None  # null = global skill, set to scope to a repo
    scope: str = "global"  # global, repo


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    template: str | None = None
    trigger_pattern: str | None = None
    tags: list[str] | None = None
    repo_id: int | None = None
    scope: str | None = None


class SkillResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    template: str
    trigger_pattern: str | None
    tags: list[str]
    usage_count: int
    repo_id: int | None
    scope: str
    repo_name: str | None = None
    created_at: str
    updated_at: str


class DetectSkillRequest(BaseModel):
    code: str
    context: str | None = None


class DetectSkillResponse(BaseModel):
    detected_patterns: list[dict]
    suggested_skills: list[dict]
    model: str
    tokens_used: int


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------

def _skill_to_response(s: Skill) -> SkillResponse:
    """Convert a Skill ORM object to a SkillResponse."""
    repo_name = None
    if s.repo:
        repo_name = f"{s.repo.owner}/{s.repo.repo_name}"
    return SkillResponse(
        id=s.id,
        name=s.name,
        description=s.description,
        category=s.category,
        template=s.template,
        trigger_pattern=s.trigger_pattern,
        tags=json.loads(s.tags) if s.tags else [],
        usage_count=s.usage_count,
        repo_id=s.repo_id,
        scope=s.scope or "global",
        repo_name=repo_name,
        created_at=s.created_at.isoformat() if s.created_at else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else "",
    )


@router.get("", response_model=list[SkillResponse])
@router.get("/", response_model=list[SkillResponse])
def list_skills(category: str | None = None, repo_id: int | None = None, scope: str | None = None, db: Session = Depends(get_db)):
    """List all skills, optionally filtered by category, repo_id, or scope."""
    try:
        query = db.query(Skill)
        if category:
            query = query.filter(Skill.category == category)
        if repo_id is not None:
            query = query.filter(Skill.repo_id == repo_id)
        if scope:
            query = query.filter(Skill.scope == scope)
        skills = query.order_by(Skill.usage_count.desc()).all()
        return [_skill_to_response(s) for s in skills]
    except Exception as exc:
        print(f"[ZECT SKILLS] Error listing skills: {exc}")
        return []


@router.post("", response_model=SkillResponse)
@router.post("/", response_model=SkillResponse)
def create_skill(req: SkillCreate, db: Session = Depends(get_db)):
    """Create a new skill."""
    skill = Skill(
        name=req.name,
        description=req.description,
        category=req.category,
        template=req.template,
        trigger_pattern=req.trigger_pattern,
        tags=json.dumps(req.tags),
        repo_id=req.repo_id,
        scope=req.scope if req.repo_id else "global",
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _skill_to_response(skill)


@router.get("/{skill_id}", response_model=SkillResponse)
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    """Get a skill by ID."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _skill_to_response(skill)


@router.put("/{skill_id}", response_model=SkillResponse)
def update_skill(skill_id: int, req: SkillUpdate, db: Session = Depends(get_db)):
    """Update a skill."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if req.name is not None:
        skill.name = req.name
    if req.description is not None:
        skill.description = req.description
    if req.category is not None:
        skill.category = req.category
    if req.template is not None:
        skill.template = req.template
    if req.trigger_pattern is not None:
        skill.trigger_pattern = req.trigger_pattern
    if req.tags is not None:
        skill.tags = json.dumps(req.tags)
    if req.repo_id is not None:
        skill.repo_id = req.repo_id
        skill.scope = "repo"
    if req.scope is not None:
        skill.scope = req.scope
        if req.scope == "global":
            skill.repo_id = None
    skill.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(skill)
    return _skill_to_response(skill)


@router.delete("/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    """Delete a skill."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(skill)
    db.commit()
    return {"deleted": True}


@router.post("/{skill_id}/use")
def use_skill(skill_id: int, db: Session = Depends(get_db)):
    """Increment usage count for a skill."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.usage_count += 1
    db.commit()
    return {"usage_count": skill.usage_count}


# ---------------------------------------------------------------------------
# AI-Powered Endpoints
# ---------------------------------------------------------------------------

@router.post("/detect", response_model=DetectSkillResponse)
def detect_patterns(req: DetectSkillRequest):
    """Detect reusable patterns in code and suggest skills to save."""
    client = _get_client()

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
            feature="skills",
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

"""Zinnia Transfer & Onboarding — brain state export/import + onboarding wizard."""

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    TransferBundle, OnboardingResponse, UserPreference,
    Lesson, Decision, EpisodicMemory, Skill,
)

router = APIRouter(prefix="/api/transfer", tags=["transfer"])

# Secret patterns to detect before export
SECRET_PATTERNS = [
    re.compile(r"(?:api[_-]?key|secret|token|password|credential|auth)[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    project_id: int
    user_id: Optional[int] = None
    bundle_type: str = "full"  # full, memory_only, skills_only, lessons_only
    include_preferences: bool = False


class ImportRequest(BaseModel):
    target_project_id: int
    user_id: Optional[int] = None
    bundle_data: dict
    merge_strategy: str = "skip_duplicates"  # skip_duplicates, overwrite, merge


class OnboardingAnswer(BaseModel):
    user_id: int
    project_id: Optional[int] = None
    question_key: str
    answer: dict


class OnboardingComplete(BaseModel):
    user_id: int
    project_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.post("/export")
def export_bundle(data: ExportRequest, db: Session = Depends(get_db)):
    """Export brain state as a verified bundle."""
    bundle = {"version": "1.0", "exported_at": datetime.now(timezone.utc).isoformat(), "type": data.bundle_type}

    if data.bundle_type in ("full", "memory_only", "lessons_only"):
        lessons = db.query(Lesson).filter(
            Lesson.project_id == data.project_id,
            Lesson.status.in_(["accepted", "provisional"]),
        ).all()
        bundle["lessons"] = [
            {"claim": l.claim, "conditions": l.conditions or [], "rationale": l.rationale,
             "status": l.status, "confidence": l.confidence, "evidence_count": l.evidence_count}
            for l in lessons
        ]

    if data.bundle_type in ("full", "memory_only"):
        decisions = db.query(Decision).filter(
            Decision.project_id == data.project_id,
            Decision.status == "active",
        ).all()
        bundle["decisions"] = [
            {"title": d.title, "decision": d.decision, "rationale": d.rationale,
             "alternatives": d.alternatives, "status": d.status}
            for d in decisions
        ]

        episodes = db.query(EpisodicMemory).filter(
            EpisodicMemory.project_id == data.project_id,
            EpisodicMemory.is_decayed == False,
        ).order_by(EpisodicMemory.created_at.desc()).limit(100).all()
        bundle["episodes"] = [
            {"action": e.action, "outcome": e.outcome, "success": e.success,
             "importance": e.importance, "reflection": e.reflection, "harness": e.harness}
            for e in episodes
        ]

    if data.bundle_type in ("full", "skills_only"):
        skills = db.query(Skill).filter(
            Skill.scope == "global",
        ).all()
        bundle["skills"] = [
            {"name": s.name, "description": s.description, "category": s.category,
             "template": s.template, "trigger_pattern": s.trigger_pattern, "tags": s.tags}
            for s in skills
        ]

    if data.include_preferences and data.user_id:
        pref = db.query(UserPreference).filter(UserPreference.user_id == data.user_id).first()
        if pref:
            bundle["preferences"] = {
                "code_style": pref.code_style or {}, "workflow": pref.workflow or {},
                "constraints": pref.constraints or {}, "communication": pref.communication or {},
            }

    # Security check — scan for secrets
    bundle_json = json.dumps(bundle)
    for pat in SECRET_PATTERNS:
        if pat.search(bundle_json):
            raise HTTPException(400, "Bundle contains potential secrets — export blocked for security. Remove sensitive data and retry.")

    # Compute checksum
    checksum = hashlib.sha256(bundle_json.encode()).hexdigest()

    # Save export record
    record = TransferBundle(
        user_id=data.user_id,
        source_project_id=data.project_id,
        bundle_type=data.bundle_type,
        direction="export",
        status="completed",
        lessons_count=len(bundle.get("lessons", [])),
        decisions_count=len(bundle.get("decisions", [])),
        episodes_count=len(bundle.get("episodes", [])),
        skills_count=len(bundle.get("skills", [])),
        preferences_included=data.include_preferences,
        checksum=checksum,
        bundle_data=bundle,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "bundle_id": record.id,
        "checksum": checksum,
        "bundle": bundle,
        "counts": {
            "lessons": len(bundle.get("lessons", [])),
            "decisions": len(bundle.get("decisions", [])),
            "episodes": len(bundle.get("episodes", [])),
            "skills": len(bundle.get("skills", [])),
        },
    }


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

@router.post("/import")
def import_bundle(data: ImportRequest, db: Session = Depends(get_db)):
    """Import a brain state bundle into a project."""
    bundle = data.bundle_data
    imported = {"lessons": 0, "decisions": 0, "episodes": 0, "skills": 0}

    # Import lessons
    for l_data in bundle.get("lessons", []):
        if data.merge_strategy == "skip_duplicates":
            existing = db.query(Lesson).filter(
                Lesson.project_id == data.target_project_id,
                Lesson.claim == l_data["claim"],
            ).first()
            if existing:
                continue

        lesson = Lesson(
            project_id=data.target_project_id,
            user_id=data.user_id,
            claim=l_data["claim"],
            conditions=l_data.get("conditions", []),
            rationale=l_data.get("rationale", "Imported from transfer bundle"),
            status=l_data.get("status", "accepted"),
            confidence=l_data.get("confidence", 0.5),
            evidence_count=l_data.get("evidence_count", 1),
            accepted_at=datetime.now(timezone.utc),
        )
        db.add(lesson)
        imported["lessons"] += 1

    # Import decisions
    for d_data in bundle.get("decisions", []):
        if data.merge_strategy == "skip_duplicates":
            existing = db.query(Decision).filter(
                Decision.project_id == data.target_project_id,
                Decision.title == d_data["title"],
            ).first()
            if existing:
                continue

        decision = Decision(
            project_id=data.target_project_id,
            user_id=data.user_id,
            title=d_data["title"],
            decision=d_data["decision"],
            rationale=d_data.get("rationale", ""),
            alternatives=d_data.get("alternatives", ""),
        )
        db.add(decision)
        imported["decisions"] += 1

    # Import episodes (as read-only history)
    for e_data in bundle.get("episodes", []):
        ep = EpisodicMemory(
            project_id=data.target_project_id,
            user_id=data.user_id,
            action=e_data.get("action", ""),
            outcome=e_data.get("outcome", ""),
            success=e_data.get("success", True),
            importance=e_data.get("importance", 5),
            reflection=e_data.get("reflection", ""),
            harness=e_data.get("harness", "imported"),
        )
        db.add(ep)
        imported["episodes"] += 1

    # Import skills
    for s_data in bundle.get("skills", []):
        if data.merge_strategy == "skip_duplicates":
            existing = db.query(Skill).filter(Skill.name == s_data["name"]).first()
            if existing:
                continue

        skill = Skill(
            name=s_data["name"],
            description=s_data.get("description", ""),
            category=s_data.get("category", "general"),
            template=s_data.get("template", ""),
            trigger_pattern=s_data.get("trigger_pattern"),
            tags=s_data.get("tags", "[]"),
        )
        db.add(skill)
        imported["skills"] += 1

    # Save import record
    record = TransferBundle(
        user_id=data.user_id,
        target_project_id=data.target_project_id,
        bundle_type=bundle.get("type", "full"),
        direction="import",
        status="completed",
        lessons_count=imported["lessons"],
        decisions_count=imported["decisions"],
        episodes_count=imported["episodes"],
        skills_count=imported["skills"],
        bundle_data={"source": "import", "merge_strategy": data.merge_strategy},
        completed_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"bundle_id": record.id, "imported": imported}


@router.get("/bundles")
def list_bundles(
    user_id: Optional[int] = None,
    direction: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(TransferBundle)
    if user_id:
        q = q.filter(TransferBundle.user_id == user_id)
    if direction:
        q = q.filter(TransferBundle.direction == direction)
    bundles = q.order_by(TransferBundle.created_at.desc()).limit(limit).all()
    return [_serialize_bundle(b) for b in bundles]


# ---------------------------------------------------------------------------
# Onboarding Wizard
# ---------------------------------------------------------------------------

ONBOARDING_QUESTIONS = [
    {
        "key": "code_style",
        "question": "What code style do you prefer?",
        "options": [
            {"value": "minimal", "label": "Minimal — fewer comments, concise"},
            {"value": "verbose", "label": "Verbose — detailed comments, explicit"},
            {"value": "standard", "label": "Standard — follow project conventions"},
        ],
    },
    {
        "key": "testing_approach",
        "question": "How do you approach testing?",
        "options": [
            {"value": "tdd", "label": "TDD — write tests first"},
            {"value": "post_implementation", "label": "Test after implementation"},
            {"value": "minimal", "label": "Minimal — only critical paths"},
        ],
    },
    {
        "key": "git_workflow",
        "question": "What's your preferred git workflow?",
        "options": [
            {"value": "feature_branch", "label": "Feature branches + PR review"},
            {"value": "trunk_based", "label": "Trunk-based development"},
            {"value": "gitflow", "label": "Gitflow (develop/release/hotfix)"},
        ],
    },
    {
        "key": "review_strictness",
        "question": "How strict should code reviews be?",
        "options": [
            {"value": "strict", "label": "Strict — enforce all rules, block on issues"},
            {"value": "moderate", "label": "Moderate — warn on issues, block on critical"},
            {"value": "lenient", "label": "Lenient — advisory only, never block"},
        ],
    },
    {
        "key": "deploy_preference",
        "question": "What's your deployment preference?",
        "options": [
            {"value": "manual_approval", "label": "Manual approval for all deploys"},
            {"value": "auto_staging", "label": "Auto-deploy to staging, manual for production"},
            {"value": "full_auto", "label": "Full automation with rollback capabilities"},
        ],
    },
    {
        "key": "communication_style",
        "question": "How should ZECT communicate with you?",
        "options": [
            {"value": "concise", "label": "Concise — brief updates, just the facts"},
            {"value": "detailed", "label": "Detailed — full explanations with context"},
            {"value": "conversational", "label": "Conversational — friendly and collaborative"},
        ],
    },
]

FEATURE_TOGGLES = [
    {"key": "dream_cycle", "label": "Dream Cycle — auto-extract patterns from work history", "default": True},
    {"key": "data_flywheel", "label": "Data Flywheel — build training artifacts from approved runs", "default": False},
    {"key": "permission_enforcement", "label": "Permission Enforcement — enforce action permissions", "default": True},
    {"key": "auto_memory", "label": "Auto Memory — automatically log actions to episodic memory", "default": True},
    {"key": "skill_self_rewrite", "label": "Skill Self-Rewrite — skills improve themselves over time", "default": False},
]


@router.get("/onboarding/questions")
def get_onboarding_questions():
    return {"questions": ONBOARDING_QUESTIONS, "feature_toggles": FEATURE_TOGGLES}


@router.post("/onboarding/answer")
def save_onboarding_answer(data: OnboardingAnswer, db: Session = Depends(get_db)):
    existing = db.query(OnboardingResponse).filter(
        OnboardingResponse.user_id == data.user_id,
        OnboardingResponse.question_key == data.question_key,
    ).first()
    if existing:
        existing.answer = data.answer
        existing.project_id = data.project_id
    else:
        resp = OnboardingResponse(
            user_id=data.user_id,
            project_id=data.project_id,
            question_key=data.question_key,
            answer=data.answer,
        )
        db.add(resp)
    db.commit()
    return {"status": "saved", "question_key": data.question_key}


@router.post("/onboarding/complete")
def complete_onboarding(data: OnboardingComplete, db: Session = Depends(get_db)):
    """Complete onboarding — generate UserPreference from answers."""
    answers = db.query(OnboardingResponse).filter(
        OnboardingResponse.user_id == data.user_id,
    ).all()

    # Build preference from answers
    prefs = {}
    feature_flags = {}
    for a in answers:
        if a.question_key.startswith("toggle_"):
            feature_flags[a.question_key.replace("toggle_", "")] = a.answer.get("enabled", False)
        else:
            prefs[a.question_key] = a.answer

    # Create or update preferences
    pref = db.query(UserPreference).filter(UserPreference.user_id == data.user_id).first()
    if not pref:
        pref = UserPreference(user_id=data.user_id)
        db.add(pref)

    pref.code_style = prefs.get("code_style", {})
    pref.workflow = {k: v for k, v in prefs.items() if k in ("testing_approach", "git_workflow", "deploy_preference")}
    pref.constraints = prefs.get("review_strictness", {})
    pref.communication = prefs.get("communication_style", {})
    pref.feature_flags = feature_flags

    # Mark all as completed
    for a in answers:
        a.completed = True

    db.commit()
    db.refresh(pref)

    return {
        "status": "completed",
        "user_id": data.user_id,
        "preferences_created": True,
        "answers_count": len(answers),
    }


@router.get("/onboarding/status/{user_id}")
def onboarding_status(user_id: int, db: Session = Depends(get_db)):
    answers = db.query(OnboardingResponse).filter(
        OnboardingResponse.user_id == user_id,
    ).all()
    answered_keys = {a.question_key for a in answers}
    all_keys = {q["key"] for q in ONBOARDING_QUESTIONS}
    completed = all_keys.issubset(answered_keys)
    return {
        "user_id": user_id,
        "completed": completed,
        "answered": len(answered_keys),
        "total": len(all_keys),
        "remaining": list(all_keys - answered_keys),
    }


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_bundle(b: TransferBundle) -> dict:
    return {
        "id": b.id, "user_id": b.user_id,
        "source_project_id": b.source_project_id,
        "target_project_id": b.target_project_id,
        "bundle_type": b.bundle_type, "direction": b.direction,
        "status": b.status, "lessons_count": b.lessons_count,
        "decisions_count": b.decisions_count, "episodes_count": b.episodes_count,
        "skills_count": b.skills_count,
        "preferences_included": b.preferences_included,
        "checksum": b.checksum,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "completed_at": b.completed_at.isoformat() if b.completed_at else None,
    }

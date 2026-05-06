"""Zinnia Memory System — 4-layer memory API (working, episodic, semantic, personal)."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    WorkingMemory, EpisodicMemory, Lesson, Decision,
    UserPreference, AuditLog,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class WorkingMemoryCreate(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    task_name: str = ""
    open_files: list = Field(default_factory=list)
    hypotheses: list = Field(default_factory=list)
    checkpoints: list = Field(default_factory=list)
    next_step: str = ""


class EpisodicReflect(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    skill_name: str = ""
    action: str
    outcome: str = ""
    success: bool = True
    importance: int = 5
    confidence: float = 0.5
    pain_score: int = 2
    reflection: str = ""
    harness: str = "zect"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_estimate_usd: float = 0.0


class LessonStage(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    claim: str
    conditions: list = Field(default_factory=list)
    confidence: float = 0.5
    evidence_count: int = 1


class LessonGraduate(BaseModel):
    rationale: str
    reviewer: str = "user"
    provisional: bool = False


class LessonReject(BaseModel):
    reason: str
    reviewer: str = "user"


class LearnOneShot(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    claim: str
    conditions: list = Field(default_factory=list)
    rationale: str = ""
    reviewer: str = "user"


class RecallRequest(BaseModel):
    intent: str
    project_id: Optional[int] = None
    top_k: int = 5


class DecisionCreate(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    title: str
    decision: str
    rationale: str = ""
    alternatives: str = ""


class PreferenceUpdate(BaseModel):
    code_style: dict = Field(default_factory=dict)
    workflow: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    communication: dict = Field(default_factory=dict)
    feature_flags: dict = Field(default_factory=dict)


class MemorySearch(BaseModel):
    query: str
    project_id: Optional[int] = None
    layers: list = Field(default_factory=lambda: ["episodic", "semantic", "working"])
    limit: int = 20


# ---------------------------------------------------------------------------
# Working Memory (Layer 1)
# ---------------------------------------------------------------------------

@router.get("/working/{project_id}")
def get_working_memory(project_id: int, db: Session = Depends(get_db)):
    entries = db.query(WorkingMemory).filter(
        WorkingMemory.project_id == project_id,
        WorkingMemory.status == "active",
    ).order_by(WorkingMemory.updated_at.desc()).all()
    return [_serialize_working(e) for e in entries]


@router.post("/working")
def upsert_working_memory(data: WorkingMemoryCreate, db: Session = Depends(get_db)):
    existing = None
    if data.project_id:
        existing = db.query(WorkingMemory).filter(
            WorkingMemory.project_id == data.project_id,
            WorkingMemory.status == "active",
        ).first()

    if existing:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _serialize_working(existing)

    entry = WorkingMemory(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize_working(entry)


@router.post("/working/{entry_id}/archive")
def archive_working_memory(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(WorkingMemory).filter(WorkingMemory.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Working memory entry not found")
    entry.status = "archived"
    entry.archived_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "archived", "id": entry_id}


# ---------------------------------------------------------------------------
# Episodic Memory (Layer 2) — reflect / log events
# ---------------------------------------------------------------------------

@router.get("/episodic/{project_id}")
def list_episodes(
    project_id: int,
    limit: int = 50,
    include_decayed: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(EpisodicMemory).filter(EpisodicMemory.project_id == project_id)
    if not include_decayed:
        q = q.filter(EpisodicMemory.is_decayed == False)
    entries = q.order_by(EpisodicMemory.created_at.desc()).limit(limit).all()
    return [_serialize_episodic(e) for e in entries]


@router.post("/episodic/reflect")
def reflect(data: EpisodicReflect, db: Session = Depends(get_db)):
    salience = min(1.0, (data.importance / 10.0 + data.confidence) / 2)
    entry = EpisodicMemory(
        **data.model_dump(),
        salience=salience,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize_episodic(entry)


# ---------------------------------------------------------------------------
# Semantic Memory (Layer 3) — lessons + decisions
# ---------------------------------------------------------------------------

@router.get("/lessons/{project_id}")
def list_lessons(
    project_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Lesson).filter(Lesson.project_id == project_id)
    if status:
        q = q.filter(Lesson.status == status)
    entries = q.order_by(Lesson.created_at.desc()).all()
    return [_serialize_lesson(e) for e in entries]


@router.get("/lessons/{project_id}/pending")
def list_pending_lessons(project_id: int, db: Session = Depends(get_db)):
    entries = db.query(Lesson).filter(
        Lesson.project_id == project_id,
        Lesson.status == "staged",
    ).order_by(Lesson.canonical_salience.desc()).all()
    return [_serialize_lesson(e) for e in entries]


@router.post("/lessons/stage")
def stage_lesson(data: LessonStage, db: Session = Depends(get_db)):
    # Idempotent: same claim + conditions → same lesson
    existing = db.query(Lesson).filter(
        Lesson.project_id == data.project_id,
        Lesson.claim == data.claim,
        Lesson.status.in_(["staged", "accepted", "provisional"]),
    ).first()
    if existing:
        existing.evidence_count += 1
        existing.cluster_size += 1
        db.commit()
        db.refresh(existing)
        return _serialize_lesson(existing)

    lesson = Lesson(
        **data.model_dump(),
        canonical_salience=data.confidence,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return _serialize_lesson(lesson)


@router.post("/lessons/{lesson_id}/graduate")
def graduate_lesson(lesson_id: int, data: LessonGraduate, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    if lesson.status not in ("staged", "provisional"):
        raise HTTPException(400, f"Cannot graduate lesson with status '{lesson.status}'")

    now = datetime.now(timezone.utc)
    lesson.status = "provisional" if data.provisional else "accepted"
    lesson.rationale = data.rationale
    lesson.reviewer = data.reviewer
    lesson.accepted_at = now
    history = lesson.decision_history or []
    history.append({
        "action": "graduate",
        "rationale": data.rationale,
        "reviewer": data.reviewer,
        "at": now.isoformat(),
    })
    lesson.decision_history = history
    db.commit()
    db.refresh(lesson)
    return _serialize_lesson(lesson)


@router.post("/lessons/{lesson_id}/reject")
def reject_lesson(lesson_id: int, data: LessonReject, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    now = datetime.now(timezone.utc)
    lesson.status = "rejected"
    lesson.rejection_reason = data.reason
    lesson.rejection_count = (lesson.rejection_count or 0) + 1
    lesson.reviewer = data.reviewer
    lesson.rejected_at = now
    history = lesson.decision_history or []
    history.append({
        "action": "reject",
        "reason": data.reason,
        "reviewer": data.reviewer,
        "at": now.isoformat(),
    })
    lesson.decision_history = history
    db.commit()
    db.refresh(lesson)
    return _serialize_lesson(lesson)


@router.post("/lessons/{lesson_id}/reopen")
def reopen_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    now = datetime.now(timezone.utc)
    lesson.status = "staged"
    history = lesson.decision_history or []
    history.append({"action": "reopen", "at": now.isoformat()})
    lesson.decision_history = history
    db.commit()
    db.refresh(lesson)
    return _serialize_lesson(lesson)


@router.post("/learn")
def learn_one_shot(data: LearnOneShot, db: Session = Depends(get_db)):
    """Stage + graduate in one call — equivalent to learn.py."""
    # Check for existing
    existing = db.query(Lesson).filter(
        Lesson.project_id == data.project_id,
        Lesson.claim == data.claim,
        Lesson.status.in_(["staged", "accepted", "provisional"]),
    ).first()
    if existing:
        existing.evidence_count += 1
        db.commit()
        db.refresh(existing)
        return _serialize_lesson(existing)

    now = datetime.now(timezone.utc)
    lesson = Lesson(
        project_id=data.project_id,
        user_id=data.user_id,
        claim=data.claim,
        conditions=data.conditions,
        rationale=data.rationale,
        status="accepted",
        confidence=0.8,
        evidence_count=1,
        cluster_size=1,
        canonical_salience=0.8,
        reviewer=data.reviewer,
        accepted_at=now,
        decision_history=[{
            "action": "learn_one_shot",
            "rationale": data.rationale,
            "reviewer": data.reviewer,
            "at": now.isoformat(),
        }],
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return _serialize_lesson(lesson)


@router.post("/recall")
def recall_lessons(data: RecallRequest, db: Session = Depends(get_db)):
    """Recall lessons relevant to an intent — lexical overlap scoring."""
    q = db.query(Lesson).filter(Lesson.status.in_(["accepted", "provisional"]))
    if data.project_id:
        q = q.filter(Lesson.project_id == data.project_id)
    all_lessons = q.all()

    query_words = set(data.intent.lower().split())
    scored = []
    for lesson in all_lessons:
        claim_words = set(lesson.claim.lower().split())
        cond_words = set()
        for c in (lesson.conditions or []):
            cond_words.update(c.lower().split())

        claim_hits = len(query_words & claim_words)
        cond_hits = len(query_words & cond_words)
        total = len(query_words) * 3 if query_words else 1
        score = (claim_hits + 2 * cond_hits) / total
        if score > 0:
            scored.append((_serialize_lesson(lesson), score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [{"lesson": s[0], "relevance_score": round(s[1], 3)} for s in scored[:data.top_k]]


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

@router.get("/decisions/{project_id}")
def list_decisions(project_id: int, db: Session = Depends(get_db)):
    entries = db.query(Decision).filter(
        Decision.project_id == project_id,
    ).order_by(Decision.created_at.desc()).all()
    return [_serialize_decision(e) for e in entries]


@router.post("/decisions")
def create_decision(data: DecisionCreate, db: Session = Depends(get_db)):
    entry = Decision(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize_decision(entry)


@router.put("/decisions/{decision_id}")
def update_decision(decision_id: int, data: DecisionCreate, db: Session = Depends(get_db)):
    entry = db.query(Decision).filter(Decision.id == decision_id).first()
    if not entry:
        raise HTTPException(404, "Decision not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return _serialize_decision(entry)


@router.post("/decisions/{decision_id}/supersede")
def supersede_decision(decision_id: int, new_decision_id: int, db: Session = Depends(get_db)):
    entry = db.query(Decision).filter(Decision.id == decision_id).first()
    if not entry:
        raise HTTPException(404, "Decision not found")
    entry.status = "superseded"
    entry.superseded_by = new_decision_id
    db.commit()
    return {"status": "superseded", "superseded_by": new_decision_id}


# ---------------------------------------------------------------------------
# Personal Memory (Layer 4) — user preferences
# ---------------------------------------------------------------------------

@router.get("/preferences/{user_id}")
def get_preferences(user_id: int, db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not pref:
        return {"user_id": user_id, "code_style": {}, "workflow": {}, "constraints": {}, "communication": {}, "feature_flags": {}}
    return _serialize_preference(pref)


@router.put("/preferences/{user_id}")
def update_preferences(user_id: int, data: PreferenceUpdate, db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not pref:
        pref = UserPreference(user_id=user_id, **data.model_dump())
        db.add(pref)
    else:
        for k, v in data.model_dump(exclude_unset=True).items():
            if v:  # only update non-empty values
                setattr(pref, k, v)
    db.commit()
    db.refresh(pref)
    return _serialize_preference(pref)


# ---------------------------------------------------------------------------
# Brain State Dashboard
# ---------------------------------------------------------------------------

@router.get("/brain-state/{project_id}")
def brain_state(project_id: int, db: Session = Depends(get_db)):
    """Full brain state dashboard — all memory layers at a glance."""
    working = db.query(WorkingMemory).filter(
        WorkingMemory.project_id == project_id,
        WorkingMemory.status == "active",
    ).count()

    episodes_total = db.query(EpisodicMemory).filter(
        EpisodicMemory.project_id == project_id,
    ).count()
    episodes_active = db.query(EpisodicMemory).filter(
        EpisodicMemory.project_id == project_id,
        EpisodicMemory.is_decayed == False,
    ).count()

    lessons_staged = db.query(Lesson).filter(
        Lesson.project_id == project_id,
        Lesson.status == "staged",
    ).count()
    lessons_accepted = db.query(Lesson).filter(
        Lesson.project_id == project_id,
        Lesson.status.in_(["accepted", "provisional"]),
    ).count()
    lessons_rejected = db.query(Lesson).filter(
        Lesson.project_id == project_id,
        Lesson.status == "rejected",
    ).count()

    decisions_active = db.query(Decision).filter(
        Decision.project_id == project_id,
        Decision.status == "active",
    ).count()

    # Recent episodes for preview
    recent_episodes = db.query(EpisodicMemory).filter(
        EpisodicMemory.project_id == project_id,
        EpisodicMemory.is_decayed == False,
    ).order_by(EpisodicMemory.created_at.desc()).limit(5).all()

    # Pending review
    pending_lessons = db.query(Lesson).filter(
        Lesson.project_id == project_id,
        Lesson.status == "staged",
    ).order_by(Lesson.canonical_salience.desc()).limit(5).all()

    return {
        "project_id": project_id,
        "summary": {
            "working_tasks": working,
            "episodes_total": episodes_total,
            "episodes_active": episodes_active,
            "lessons_staged": lessons_staged,
            "lessons_accepted": lessons_accepted,
            "lessons_rejected": lessons_rejected,
            "decisions_active": decisions_active,
        },
        "recent_episodes": [_serialize_episodic(e) for e in recent_episodes],
        "pending_review": [_serialize_lesson(l) for l in pending_lessons],
    }


# ---------------------------------------------------------------------------
# Full-Text Search
# ---------------------------------------------------------------------------

@router.post("/search")
def search_memory(data: MemorySearch, db: Session = Depends(get_db)):
    """Full-text search across memory layers."""
    results = []
    query_lower = data.query.lower()

    if "episodic" in data.layers:
        q = db.query(EpisodicMemory)
        if data.project_id:
            q = q.filter(EpisodicMemory.project_id == data.project_id)
        for ep in q.order_by(EpisodicMemory.created_at.desc()).limit(200).all():
            text = f"{ep.action} {ep.outcome} {ep.reflection}".lower()
            if query_lower in text:
                results.append({"layer": "episodic", "data": _serialize_episodic(ep)})

    if "semantic" in data.layers:
        q = db.query(Lesson)
        if data.project_id:
            q = q.filter(Lesson.project_id == data.project_id)
        for lesson in q.all():
            text = f"{lesson.claim} {' '.join(lesson.conditions or [])}".lower()
            if query_lower in text:
                results.append({"layer": "semantic", "data": _serialize_lesson(lesson)})

    if "working" in data.layers:
        q = db.query(WorkingMemory).filter(WorkingMemory.status == "active")
        if data.project_id:
            q = q.filter(WorkingMemory.project_id == data.project_id)
        for wm in q.all():
            text = f"{wm.task_name} {wm.next_step}".lower()
            if query_lower in text:
                results.append({"layer": "working", "data": _serialize_working(wm)})

    return results[:data.limit]


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_working(e: WorkingMemory) -> dict:
    return {
        "id": e.id, "project_id": e.project_id, "user_id": e.user_id,
        "task_name": e.task_name, "open_files": e.open_files or [],
        "hypotheses": e.hypotheses or [], "checkpoints": e.checkpoints or [],
        "next_step": e.next_step, "status": e.status,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        "archived_at": e.archived_at.isoformat() if e.archived_at else None,
    }


def _serialize_episodic(e: EpisodicMemory) -> dict:
    return {
        "id": e.id, "project_id": e.project_id, "user_id": e.user_id,
        "skill_name": e.skill_name, "action": e.action, "outcome": e.outcome,
        "success": e.success, "importance": e.importance, "salience": e.salience,
        "confidence": e.confidence, "pain_score": e.pain_score,
        "evidence_ids": e.evidence_ids or [], "reflection": e.reflection,
        "harness": e.harness, "tokens_in": e.tokens_in, "tokens_out": e.tokens_out,
        "cost_estimate_usd": e.cost_estimate_usd, "is_decayed": e.is_decayed,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _serialize_lesson(e: Lesson) -> dict:
    return {
        "id": e.id, "project_id": e.project_id, "user_id": e.user_id,
        "claim": e.claim, "conditions": e.conditions or [],
        "rationale": e.rationale, "status": e.status,
        "confidence": e.confidence, "evidence_count": e.evidence_count,
        "cluster_size": e.cluster_size, "canonical_salience": e.canonical_salience,
        "reviewer": e.reviewer, "rejection_reason": e.rejection_reason,
        "rejection_count": e.rejection_count,
        "decision_history": e.decision_history or [],
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "accepted_at": e.accepted_at.isoformat() if e.accepted_at else None,
        "rejected_at": e.rejected_at.isoformat() if e.rejected_at else None,
    }


def _serialize_decision(e: Decision) -> dict:
    return {
        "id": e.id, "project_id": e.project_id, "user_id": e.user_id,
        "title": e.title, "decision": e.decision, "rationale": e.rationale,
        "alternatives": e.alternatives, "status": e.status,
        "superseded_by": e.superseded_by,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


def _serialize_preference(e: UserPreference) -> dict:
    return {
        "id": e.id, "user_id": e.user_id,
        "code_style": e.code_style or {}, "workflow": e.workflow or {},
        "constraints": e.constraints or {}, "communication": e.communication or {},
        "feature_flags": e.feature_flags or {},
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }

"""Zinnia Data Flywheel — approved runs → traces → context cards → eval cases."""

from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FlywheelTrace, FlywheelContextCard, FlywheelEvalCase

router = APIRouter(prefix="/api/flywheel", tags=["data-flywheel"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TraceCreate(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    source_type: str  # review, build, plan, ask, deploy
    source_id: Optional[int] = None
    input_redacted: str = ""
    output_redacted: str = ""
    model_used: str = ""
    tokens_used: int = 0
    quality_score: Optional[float] = None


class TraceApprove(BaseModel):
    approved_by: str = "user"


class ContextCardCreate(BaseModel):
    project_id: Optional[int] = None
    title: str
    pattern_description: str = ""
    trace_ids: list = Field(default_factory=list)
    frequency: int = 1


class EvalCaseCreate(BaseModel):
    project_id: Optional[int] = None
    context_card_id: Optional[int] = None
    input_text: str
    expected_output: str
    model_tested: str = ""
    notes: str = ""


class EvalCaseResult(BaseModel):
    actual_output: str
    pass_fail: str  # pass, fail


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------

@router.post("/traces")
def create_trace(data: TraceCreate, db: Session = Depends(get_db)):
    trace = FlywheelTrace(**data.model_dump())
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return _serialize_trace(trace)


@router.get("/traces")
def list_traces(
    project_id: Optional[int] = None,
    approved_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(FlywheelTrace)
    if project_id:
        q = q.filter(FlywheelTrace.project_id == project_id)
    if approved_only:
        q = q.filter(FlywheelTrace.is_approved == True)
    traces = q.order_by(FlywheelTrace.created_at.desc()).limit(limit).all()
    return [_serialize_trace(t) for t in traces]


@router.post("/traces/{trace_id}/approve")
def approve_trace(trace_id: int, data: TraceApprove, db: Session = Depends(get_db)):
    trace = db.query(FlywheelTrace).filter(FlywheelTrace.id == trace_id).first()
    if not trace:
        raise HTTPException(404, "Trace not found")
    trace.is_approved = True
    trace.approved_by = data.approved_by
    trace.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trace)
    return _serialize_trace(trace)


@router.post("/traces/{trace_id}/rate")
def rate_trace(trace_id: int, score: float, db: Session = Depends(get_db)):
    trace = db.query(FlywheelTrace).filter(FlywheelTrace.id == trace_id).first()
    if not trace:
        raise HTTPException(404, "Trace not found")
    if score < 1 or score > 5:
        raise HTTPException(400, "Score must be between 1 and 5")
    trace.quality_score = score
    db.commit()
    return {"id": trace_id, "quality_score": score}


# ---------------------------------------------------------------------------
# Context Cards
# ---------------------------------------------------------------------------

@router.post("/context-cards")
def create_context_card(data: ContextCardCreate, db: Session = Depends(get_db)):
    card = FlywheelContextCard(**data.model_dump())
    # Calculate avg quality from traces
    if data.trace_ids:
        traces = db.query(FlywheelTrace).filter(
            FlywheelTrace.id.in_(data.trace_ids),
        ).all()
        scores = [t.quality_score for t in traces if t.quality_score]
        card.avg_quality = sum(scores) / len(scores) if scores else 0.0
    db.add(card)
    db.commit()
    db.refresh(card)
    return _serialize_card(card)


@router.get("/context-cards")
def list_context_cards(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(FlywheelContextCard)
    if project_id:
        q = q.filter(FlywheelContextCard.project_id == project_id)
    if status:
        q = q.filter(FlywheelContextCard.status == status)
    cards = q.order_by(FlywheelContextCard.created_at.desc()).limit(limit).all()
    return [_serialize_card(c) for c in cards]


@router.post("/context-cards/{card_id}/approve")
def approve_context_card(card_id: int, db: Session = Depends(get_db)):
    card = db.query(FlywheelContextCard).filter(FlywheelContextCard.id == card_id).first()
    if not card:
        raise HTTPException(404, "Context card not found")
    card.status = "approved"
    db.commit()
    return {"id": card_id, "status": "approved"}


# ---------------------------------------------------------------------------
# Eval Cases
# ---------------------------------------------------------------------------

@router.post("/eval-cases")
def create_eval_case(data: EvalCaseCreate, db: Session = Depends(get_db)):
    case = FlywheelEvalCase(**data.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return _serialize_eval(case)


@router.get("/eval-cases")
def list_eval_cases(
    project_id: Optional[int] = None,
    context_card_id: Optional[int] = None,
    pass_fail: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(FlywheelEvalCase)
    if project_id:
        q = q.filter(FlywheelEvalCase.project_id == project_id)
    if context_card_id:
        q = q.filter(FlywheelEvalCase.context_card_id == context_card_id)
    if pass_fail:
        q = q.filter(FlywheelEvalCase.pass_fail == pass_fail)
    cases = q.order_by(FlywheelEvalCase.created_at.desc()).limit(limit).all()
    return [_serialize_eval(c) for c in cases]


@router.put("/eval-cases/{case_id}/result")
def update_eval_result(case_id: int, data: EvalCaseResult, db: Session = Depends(get_db)):
    case = db.query(FlywheelEvalCase).filter(FlywheelEvalCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Eval case not found")
    case.actual_output = data.actual_output
    case.pass_fail = data.pass_fail
    db.commit()
    db.refresh(case)
    return _serialize_eval(case)


# ---------------------------------------------------------------------------
# Flywheel Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def flywheel_stats(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Overall flywheel readiness metrics."""
    tq = db.query(FlywheelTrace)
    cq = db.query(FlywheelContextCard)
    eq = db.query(FlywheelEvalCase)
    if project_id:
        tq = tq.filter(FlywheelTrace.project_id == project_id)
        cq = cq.filter(FlywheelContextCard.project_id == project_id)
        eq = eq.filter(FlywheelEvalCase.project_id == project_id)

    total_traces = tq.count()
    approved_traces = tq.filter(FlywheelTrace.is_approved == True).count()
    total_cards = cq.count()
    approved_cards = cq.filter(FlywheelContextCard.status == "approved").count()
    total_evals = eq.count()
    passing_evals = eq.filter(FlywheelEvalCase.pass_fail == "pass").count()

    # Readiness heuristic
    if approved_traces >= 500:
        readiness = "adapter_candidate"
    elif approved_traces >= 100:
        readiness = "compression_ready"
    elif approved_traces >= 25:
        readiness = "eval_set_ready"
    elif approved_traces >= 10:
        readiness = "first_context_card"
    else:
        readiness = "collecting"

    return {
        "traces": {"total": total_traces, "approved": approved_traces},
        "context_cards": {"total": total_cards, "approved": approved_cards},
        "eval_cases": {"total": total_evals, "passing": passing_evals},
        "readiness_level": readiness,
        "readiness_thresholds": {
            "first_context_card": 10,
            "eval_set_ready": 25,
            "compression_ready": 100,
            "adapter_candidate": 500,
        },
    }


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_trace(t: FlywheelTrace) -> dict:
    return {
        "id": t.id, "project_id": t.project_id, "user_id": t.user_id,
        "source_type": t.source_type, "source_id": t.source_id,
        "input_redacted": t.input_redacted, "output_redacted": t.output_redacted,
        "model_used": t.model_used, "tokens_used": t.tokens_used,
        "quality_score": t.quality_score, "is_approved": t.is_approved,
        "approved_by": t.approved_by,
        "approved_at": t.approved_at.isoformat() if t.approved_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_card(c: FlywheelContextCard) -> dict:
    return {
        "id": c.id, "project_id": c.project_id,
        "title": c.title, "pattern_description": c.pattern_description,
        "trace_ids": c.trace_ids or [], "frequency": c.frequency,
        "avg_quality": c.avg_quality, "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_eval(e: FlywheelEvalCase) -> dict:
    return {
        "id": e.id, "project_id": e.project_id,
        "context_card_id": e.context_card_id,
        "input_text": e.input_text, "expected_output": e.expected_output,
        "actual_output": e.actual_output, "pass_fail": e.pass_fail,
        "model_tested": e.model_tested, "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }

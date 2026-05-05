"""Generated Outputs — History of all AI-generated code, plans, reviews."""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import GeneratedOutput

router = APIRouter(prefix="/api/outputs", tags=["outputs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OutputCreate(BaseModel):
    output_type: str  # code, plan, review, checklist, runbook, blueprint
    feature: str = ""
    title: str = ""
    prompt_used: str = ""
    output_content: str = ""
    language: str = ""
    file_path: str = ""
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    session_id: int | None = None
    user_id: int | None = None


class OutputOut(BaseModel):
    id: int
    user_id: int | None
    session_id: int | None
    output_type: str
    feature: str
    title: str
    prompt_used: str
    output_content: str
    language: str
    file_path: str
    model_used: str
    tokens_used: int
    cost_usd: float
    quality_score: float | None
    was_accepted: bool | None
    created_at: str


class OutputRating(BaseModel):
    quality_score: float  # 1-5
    was_accepted: bool | None = None


class OutputStats(BaseModel):
    total_outputs: int
    by_type: dict[str, int]
    by_feature: dict[str, int]
    total_tokens: int
    total_cost_usd: float
    avg_quality: float | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[OutputOut])
@router.get("/", response_model=list[OutputOut])
def list_outputs(
    output_type: str | None = None,
    feature: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List generated outputs with optional filters."""
    query = db.query(GeneratedOutput)
    if output_type:
        query = query.filter(GeneratedOutput.output_type == output_type)
    if feature:
        query = query.filter(GeneratedOutput.feature == feature)
    outputs = query.order_by(GeneratedOutput.created_at.desc()).offset(offset).limit(limit).all()
    return [_output_out(o) for o in outputs]


@router.post("", response_model=OutputOut)
@router.post("/", response_model=OutputOut)
def create_output(req: OutputCreate, db: Session = Depends(get_db)):
    """Store a generated output."""
    output = GeneratedOutput(
        user_id=req.user_id,
        session_id=req.session_id,
        output_type=req.output_type,
        feature=req.feature,
        title=req.title,
        prompt_used=req.prompt_used,
        output_content=req.output_content,
        language=req.language,
        file_path=req.file_path,
        model_used=req.model_used,
        tokens_used=req.tokens_used,
        cost_usd=req.cost_usd,
    )
    db.add(output)
    db.commit()
    db.refresh(output)
    return _output_out(output)


@router.get("/stats", response_model=OutputStats)
def output_stats(db: Session = Depends(get_db)):
    """Get statistics about generated outputs."""
    from sqlalchemy import func

    total = db.query(GeneratedOutput).count()
    by_type = dict(
        db.query(GeneratedOutput.output_type, func.count(GeneratedOutput.id))
        .group_by(GeneratedOutput.output_type).all()
    )
    by_feature = dict(
        db.query(GeneratedOutput.feature, func.count(GeneratedOutput.id))
        .group_by(GeneratedOutput.feature).all()
    )
    total_tokens = db.query(func.sum(GeneratedOutput.tokens_used)).scalar() or 0
    total_cost = db.query(func.sum(GeneratedOutput.cost_usd)).scalar() or 0.0
    avg_quality = db.query(func.avg(GeneratedOutput.quality_score)).filter(
        GeneratedOutput.quality_score.isnot(None)
    ).scalar()

    return OutputStats(
        total_outputs=total,
        by_type=by_type,
        by_feature=by_feature,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 4),
        avg_quality=round(avg_quality, 2) if avg_quality else None,
    )


@router.get("/{output_id}", response_model=OutputOut)
def get_output(output_id: int, db: Session = Depends(get_db)):
    """Get a specific generated output."""
    output = db.query(GeneratedOutput).filter(GeneratedOutput.id == output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="Output not found")
    return _output_out(output)


@router.post("/{output_id}/rate", response_model=OutputOut)
def rate_output(output_id: int, req: OutputRating, db: Session = Depends(get_db)):
    """Rate a generated output (quality score 1-5)."""
    output = db.query(GeneratedOutput).filter(GeneratedOutput.id == output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="Output not found")
    output.quality_score = max(1.0, min(5.0, req.quality_score))
    if req.was_accepted is not None:
        output.was_accepted = req.was_accepted
    db.commit()
    db.refresh(output)
    return _output_out(output)


@router.delete("/{output_id}")
def delete_output(output_id: int, db: Session = Depends(get_db)):
    """Delete a generated output."""
    output = db.query(GeneratedOutput).filter(GeneratedOutput.id == output_id).first()
    if not output:
        raise HTTPException(status_code=404, detail="Output not found")
    db.delete(output)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _output_out(o: GeneratedOutput) -> OutputOut:
    return OutputOut(
        id=o.id, user_id=o.user_id, session_id=o.session_id,
        output_type=o.output_type, feature=o.feature or "",
        title=o.title or "", prompt_used=o.prompt_used or "",
        output_content=o.output_content or "", language=o.language or "",
        file_path=o.file_path or "", model_used=o.model_used or "",
        tokens_used=o.tokens_used, cost_usd=o.cost_usd,
        quality_score=o.quality_score, was_accepted=o.was_accepted,
        created_at=o.created_at.isoformat() if o.created_at else "",
    )

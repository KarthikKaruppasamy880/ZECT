"""Session Insights — analytics, cost tracking, quality metrics."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserSession, TokenLog, GeneratedOutput, ReviewSession

router = APIRouter(prefix="/api/session-insights", tags=["session-insights"])


@router.get("/overview")
def get_overview(days: int = 30, db: Session = Depends(get_db)):
    """Get high-level session insights overview."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Session stats
        total_sessions = db.query(func.count(UserSession.id)).filter(
            UserSession.started_at >= cutoff
        ).scalar() or 0
        active_sessions = db.query(func.count(UserSession.id)).filter(
            UserSession.status == "active"
        ).scalar() or 0

        # Token/cost stats
        token_row = db.query(
            func.sum(TokenLog.total_tokens),
            func.sum(TokenLog.estimated_cost_usd),
            func.count(TokenLog.id),
        ).filter(TokenLog.created_at >= cutoff).first()
        total_tokens = token_row[0] or 0
        total_cost = round(token_row[1] or 0, 4)
        total_requests = token_row[2] or 0

        # Quality stats
        avg_quality = db.query(func.avg(GeneratedOutput.quality_score)).filter(
            GeneratedOutput.quality_score.isnot(None),
            GeneratedOutput.created_at >= cutoff,
        ).scalar()

        # Review stats
        review_row = db.query(
            func.count(ReviewSession.id),
            func.sum(ReviewSession.total_findings),
            func.avg(ReviewSession.overall_score),
        ).filter(ReviewSession.created_at >= cutoff).first()

        return {
            "period_days": days,
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
            },
            "tokens": {
                "total": total_tokens,
                "total_cost_usd": total_cost,
                "total_requests": total_requests,
                "avg_tokens_per_request": round(total_tokens / max(total_requests, 1)),
                "avg_cost_per_request": round(total_cost / max(total_requests, 1), 4),
            },
            "quality": {
                "avg_output_rating": round(avg_quality or 0, 2),
                "reviews_completed": review_row[0] or 0,
                "total_findings": review_row[1] or 0,
                "avg_review_score": round(review_row[2] or 0, 1),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-breakdown")
def daily_breakdown(days: int = 14, db: Session = Depends(get_db)):
    """Get daily token/cost breakdown."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(
            func.date(TokenLog.created_at).label("date"),
            func.sum(TokenLog.total_tokens).label("tokens"),
            func.sum(TokenLog.estimated_cost_usd).label("cost"),
            func.count(TokenLog.id).label("requests"),
        ).filter(
            TokenLog.created_at >= cutoff
        ).group_by(func.date(TokenLog.created_at)).order_by(func.date(TokenLog.created_at)).all()

        return [
            {
                "date": str(r.date),
                "tokens": r.tokens or 0,
                "cost_usd": round(r.cost or 0, 4),
                "requests": r.requests or 0,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-usage")
def model_usage(days: int = 30, db: Session = Depends(get_db)):
    """Get usage breakdown by model."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(
            TokenLog.model,
            func.count(TokenLog.id).label("requests"),
            func.sum(TokenLog.total_tokens).label("tokens"),
            func.sum(TokenLog.estimated_cost_usd).label("cost"),
            func.avg(TokenLog.latency_ms).label("avg_latency"),
        ).filter(
            TokenLog.created_at >= cutoff,
            TokenLog.model != "",
        ).group_by(TokenLog.model).order_by(func.sum(TokenLog.total_tokens).desc()).all()

        return [
            {
                "model": r.model,
                "requests": r.requests,
                "tokens": r.tokens or 0,
                "cost_usd": round(r.cost or 0, 4),
                "avg_latency_ms": round(r.avg_latency or 0),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feature-usage")
def feature_usage(days: int = 30, db: Session = Depends(get_db)):
    """Get usage breakdown by feature."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(
            TokenLog.feature,
            func.count(TokenLog.id).label("requests"),
            func.sum(TokenLog.total_tokens).label("tokens"),
            func.sum(TokenLog.estimated_cost_usd).label("cost"),
        ).filter(
            TokenLog.created_at >= cutoff,
            TokenLog.feature != "",
        ).group_by(TokenLog.feature).order_by(func.sum(TokenLog.total_tokens).desc()).all()

        return [
            {
                "feature": r.feature,
                "requests": r.requests,
                "tokens": r.tokens or 0,
                "cost_usd": round(r.cost or 0, 4),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
def list_sessions(
    status: Optional[str] = None,
    session_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List sessions with insights."""
    try:
        q = db.query(UserSession)
        if status:
            q = q.filter(UserSession.status == status)
        if session_type:
            q = q.filter(UserSession.session_type == session_type)
        total = q.count()
        items = q.order_by(UserSession.started_at.desc()).offset(skip).limit(limit).all()
        return {
            "items": [
                {
                    "id": s.id,
                    "user_id": s.user_id,
                    "project_id": s.project_id,
                    "session_type": s.session_type,
                    "title": s.title,
                    "status": s.status,
                    "total_tokens_used": s.total_tokens_used,
                    "total_cost_usd": s.total_cost_usd,
                    "models_used": s.models_used,
                    "messages_count": s.messages_count,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "last_activity": s.last_activity.isoformat() if s.last_activity else None,
                }
                for s in items
            ],
            "total": total,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

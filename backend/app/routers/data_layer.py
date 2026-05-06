"""Zinnia Data Layer — cross-agent monitoring, KPIs, dashboards, daily reports."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import AgentEvent, DailyReport

router = APIRouter(prefix="/api/data-layer", tags=["data-layer"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AgentEventCreate(BaseModel):
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    harness: str = "zect"
    event_type: str
    category: str = "general"
    description: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    model: str = ""
    duration_seconds: int = 0
    success: bool = True
    metadata: dict = Field(default_factory=dict)


class DashboardQuery(BaseModel):
    project_id: Optional[int] = None
    days: int = 7
    harness: Optional[str] = None
    category: Optional[str] = None


class DailyReportRequest(BaseModel):
    project_id: Optional[int] = None
    date: Optional[str] = None  # YYYY-MM-DD, defaults to today


# ---------------------------------------------------------------------------
# Agent Events
# ---------------------------------------------------------------------------

@router.post("/events")
def log_event(data: AgentEventCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    payload["event_metadata"] = payload.pop("metadata", {})
    event = AgentEvent(**payload)
    db.add(event)
    db.commit()
    db.refresh(event)
    return _serialize_event(event)


@router.get("/events")
def list_events(
    project_id: Optional[int] = None,
    harness: Optional[str] = None,
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(AgentEvent).filter(AgentEvent.created_at >= cutoff)
    if project_id:
        q = q.filter(AgentEvent.project_id == project_id)
    if harness:
        q = q.filter(AgentEvent.harness == harness)
    if category:
        q = q.filter(AgentEvent.category == category)
    if event_type:
        q = q.filter(AgentEvent.event_type == event_type)
    events = q.order_by(AgentEvent.created_at.desc()).limit(limit).all()
    return [_serialize_event(e) for e in events]


# ---------------------------------------------------------------------------
# Analytics Dashboard
# ---------------------------------------------------------------------------

@router.post("/dashboard")
def get_dashboard(data: DashboardQuery, db: Session = Depends(get_db)):
    """Full analytics dashboard — KPIs, breakdowns, trends."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=data.days)
    q = db.query(AgentEvent).filter(AgentEvent.created_at >= cutoff)
    if data.project_id:
        q = q.filter(AgentEvent.project_id == data.project_id)
    if data.harness:
        q = q.filter(AgentEvent.harness == data.harness)
    if data.category:
        q = q.filter(AgentEvent.category == data.category)

    events = q.all()

    # KPIs
    total_events = len(events)
    total_tokens = sum(e.tokens_used for e in events)
    total_cost = sum(e.cost_usd for e in events)
    successes = sum(1 for e in events if e.success)
    success_rate = (successes / total_events * 100) if total_events else 0
    avg_duration = (sum(e.duration_seconds for e in events) / total_events) if total_events else 0

    # Harness breakdown
    harness_data = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0, "successes": 0})
    for e in events:
        h = harness_data[e.harness]
        h["count"] += 1
        h["tokens"] += e.tokens_used
        h["cost"] += e.cost_usd
        if e.success:
            h["successes"] += 1

    # Category breakdown
    category_data = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0})
    for e in events:
        c = category_data[e.category]
        c["count"] += 1
        c["tokens"] += e.tokens_used
        c["cost"] += e.cost_usd

    # Model breakdown
    model_data = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0})
    for e in events:
        if e.model:
            m = model_data[e.model]
            m["count"] += 1
            m["tokens"] += e.tokens_used
            m["cost"] += e.cost_usd

    # Daily trends
    daily_trends = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0, "successes": 0})
    for e in events:
        day = e.created_at.strftime("%Y-%m-%d") if e.created_at else "unknown"
        d = daily_trends[day]
        d["count"] += 1
        d["tokens"] += e.tokens_used
        d["cost"] += e.cost_usd
        if e.success:
            d["successes"] += 1

    return {
        "period_days": data.days,
        "kpis": {
            "total_events": total_events,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "success_rate": round(success_rate, 1),
            "avg_duration_seconds": round(avg_duration, 1),
            "throughput_per_day": round(total_events / max(data.days, 1), 1),
        },
        "harness_breakdown": {k: v for k, v in harness_data.items()},
        "category_breakdown": {k: v for k, v in category_data.items()},
        "model_breakdown": {k: v for k, v in model_data.items()},
        "daily_trends": [
            {"date": k, **v}
            for k, v in sorted(daily_trends.items())
        ],
    }


# ---------------------------------------------------------------------------
# Daily Reports
# ---------------------------------------------------------------------------

@router.post("/daily-report")
def generate_daily_report(data: DailyReportRequest, db: Session = Depends(get_db)):
    """Generate or fetch a daily summary report."""
    if data.date:
        report_date = datetime.strptime(data.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        report_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if report already exists
    existing = db.query(DailyReport).filter(
        DailyReport.report_date == report_date,
        DailyReport.project_id == data.project_id,
    ).first()
    if existing:
        return _serialize_daily_report(existing)

    # Generate new report
    start = report_date
    end = start + timedelta(days=1)
    q = db.query(AgentEvent).filter(
        AgentEvent.created_at >= start,
        AgentEvent.created_at < end,
    )
    if data.project_id:
        q = q.filter(AgentEvent.project_id == data.project_id)
    events = q.all()

    total_events = len(events)
    total_tokens = sum(e.tokens_used for e in events)
    total_cost = sum(e.cost_usd for e in events)
    successes = sum(1 for e in events if e.success)
    success_rate = (successes / total_events * 100) if total_events else 0

    # Breakdowns
    harness_breakdown = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0})
    category_breakdown = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0})
    model_breakdown = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0})

    for e in events:
        h = harness_breakdown[e.harness]
        h["count"] += 1; h["tokens"] += e.tokens_used; h["cost"] += e.cost_usd
        c = category_breakdown[e.category]
        c["count"] += 1; c["tokens"] += e.tokens_used; c["cost"] += e.cost_usd
        if e.model:
            m = model_breakdown[e.model]
            m["count"] += 1; m["tokens"] += e.tokens_used; m["cost"] += e.cost_usd

    # Generate markdown
    md = f"# Daily Report — {report_date.strftime('%Y-%m-%d')}\n\n"
    md += f"## Summary\n- Events: {total_events}\n- Tokens: {total_tokens:,}\n"
    md += f"- Cost: ${total_cost:.4f}\n- Success Rate: {success_rate:.1f}%\n\n"
    md += f"## Harness Breakdown\n"
    for h, d in harness_breakdown.items():
        md += f"- **{h}**: {d['count']} events, {d['tokens']:,} tokens, ${d['cost']:.4f}\n"
    md += f"\n## Category Breakdown\n"
    for c, d in category_breakdown.items():
        md += f"- **{c}**: {d['count']} events, {d['tokens']:,} tokens, ${d['cost']:.4f}\n"

    report = DailyReport(
        project_id=data.project_id,
        report_date=report_date,
        total_events=total_events,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 4),
        success_rate=round(success_rate, 1),
        harness_breakdown=dict(harness_breakdown),
        category_breakdown=dict(category_breakdown),
        model_breakdown=dict(model_breakdown),
        kpi_summary={
            "throughput": total_events,
            "reliability": round(success_rate, 1),
            "avg_cost_per_event": round(total_cost / max(total_events, 1), 6),
        },
        report_markdown=md,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _serialize_daily_report(report)


@router.get("/daily-reports")
def list_daily_reports(
    project_id: Optional[int] = None,
    limit: int = 30,
    db: Session = Depends(get_db),
):
    q = db.query(DailyReport)
    if project_id:
        q = q.filter(DailyReport.project_id == project_id)
    reports = q.order_by(DailyReport.report_date.desc()).limit(limit).all()
    return [_serialize_daily_report(r) for r in reports]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.get("/export/csv")
def export_csv(
    project_id: Optional[int] = None,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Export agent events as CSV-compatible JSON."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(AgentEvent).filter(AgentEvent.created_at >= cutoff)
    if project_id:
        q = q.filter(AgentEvent.project_id == project_id)
    events = q.order_by(AgentEvent.created_at.asc()).all()
    return {
        "format": "csv",
        "columns": ["id", "harness", "event_type", "category", "tokens_used", "cost_usd", "model", "success", "created_at"],
        "rows": [
            [e.id, e.harness, e.event_type, e.category, e.tokens_used, e.cost_usd, e.model, e.success,
             e.created_at.isoformat() if e.created_at else ""]
            for e in events
        ],
        "total_rows": len(events),
    }


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_event(e: AgentEvent) -> dict:
    return {
        "id": e.id, "project_id": e.project_id, "user_id": e.user_id,
        "harness": e.harness, "event_type": e.event_type, "category": e.category,
        "description": e.description, "tokens_used": e.tokens_used,
        "cost_usd": e.cost_usd, "model": e.model,
        "duration_seconds": e.duration_seconds, "success": e.success,
        "metadata": e.event_metadata or {},
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _serialize_daily_report(r: DailyReport) -> dict:
    return {
        "id": r.id, "project_id": r.project_id,
        "report_date": r.report_date.isoformat() if r.report_date else None,
        "total_events": r.total_events, "total_tokens": r.total_tokens,
        "total_cost_usd": r.total_cost_usd, "success_rate": r.success_rate,
        "harness_breakdown": r.harness_breakdown or {},
        "category_breakdown": r.category_breakdown or {},
        "model_breakdown": r.model_breakdown or {},
        "top_skills": r.top_skills or [],
        "kpi_summary": r.kpi_summary or {},
        "report_markdown": r.report_markdown,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }

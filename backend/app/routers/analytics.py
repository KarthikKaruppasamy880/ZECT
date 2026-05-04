from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Project, Repo
from app.schemas import AnalyticsOverview
from app.token_tracker import get_usage_summary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/token-dashboard")
def token_dashboard(db: Session = Depends(get_db)):
    """Aggregated token usage for the dashboard control panel."""
    return get_usage_summary(db)


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    total = len(projects)
    active = sum(1 for p in projects if p.status == "active")
    completed = sum(1 for p in projects if p.status == "completed")
    avg_completion = round(sum(p.completion_percent for p in projects) / total, 1) if total else 0
    avg_savings = round(sum(p.token_savings for p in projects) / total, 1) if total else 0
    total_alerts = sum(p.risk_alerts for p in projects)
    total_repos = db.query(Repo).count()

    stages = {"ask": 0, "plan": 0, "build": 0, "review": 0, "deploy": 0}
    for p in projects:
        if p.current_stage in stages:
            stages[p.current_stage] += 1

    return AnalyticsOverview(
        total_projects=total,
        active_projects=active,
        completed_projects=completed,
        avg_completion=avg_completion,
        avg_token_savings=avg_savings,
        total_risk_alerts=total_alerts,
        total_repos=total_repos,
        stage_distribution=stages,
    )

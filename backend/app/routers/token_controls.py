"""Token Limit Controls — Dashboard model/budget controls with per-user tracking."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import SessionLocal
from app.models import TokenLog, TokenBudget, User, UserSession, GeneratedOutput
from app.token_tracker import get_usage_summary
from datetime import datetime, timezone, timedelta
from typing import Optional

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class TokenUsageSummary(BaseModel):
    total_calls: int
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    by_feature: dict
    by_model: dict
    recent: list[dict]


class BudgetConfig(BaseModel):
    daily_token_limit: int = 0  # 0 = unlimited
    monthly_token_limit: int = 0
    daily_cost_limit_usd: float = 0.0
    monthly_cost_limit_usd: float = 0.0
    alert_threshold_percent: int = 80
    preferred_model: str = "gpt-4o-mini"
    allowed_models: list[str] = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
    enforce_limits: bool = False


class BudgetStatus(BaseModel):
    daily_tokens_used: int
    daily_tokens_limit: int
    daily_cost_used: float
    daily_cost_limit: float
    monthly_tokens_used: int
    monthly_tokens_limit: int
    monthly_cost_used: float
    monthly_cost_limit: float
    alert_triggered: bool
    alert_message: str
    preferred_model: str
    allowed_models: list[str]


class ModelUsageBreakdown(BaseModel):
    model: str
    calls: int
    tokens: int
    cost: float
    percentage: float


class UserActivity(BaseModel):
    user_id: int
    email: str
    name: str
    team: str
    role: str
    total_calls: int
    total_tokens: int
    total_cost: float
    models_used: list[str]
    features_used: list[str]
    last_active: Optional[str] = None
    sessions_count: int


class UserActivityDetail(BaseModel):
    user_id: int
    email: str
    name: str
    team: str
    total_tokens: int
    total_cost: float
    daily_tokens: int
    daily_cost: float
    monthly_tokens: int
    monthly_cost: float
    top_models: list[dict]
    top_features: list[dict]
    recent_activity: list[dict]
    sessions: list[dict]


class TeamUsageSummary(BaseModel):
    team: str
    members: int
    total_tokens: int
    total_cost: float
    top_model: str
    top_feature: str


# ---------------------------------------------------------------------------
# Core Token Endpoints
# ---------------------------------------------------------------------------

@router.get("/usage", response_model=TokenUsageSummary)
def get_token_usage(db: Session = Depends(get_db)):
    """Get full token usage summary with breakdowns."""
    summary = get_usage_summary(db)
    return TokenUsageSummary(**summary)


@router.get("/budget", response_model=BudgetStatus)
def get_budget_status(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get current budget status including limits and alerts."""
    # Get budget config (user-specific or global)
    budget = None
    if user_id:
        budget = db.query(TokenBudget).filter(TokenBudget.user_id == user_id).first()
    if not budget:
        budget = db.query(TokenBudget).filter(TokenBudget.user_id == None).first()  # noqa: E711
    if not budget:
        budget = TokenBudget()
        db.add(budget)
        db.commit()
        db.refresh(budget)

    # Calculate daily usage
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_query = db.query(TokenLog).filter(TokenLog.created_at >= today_start)
    if user_id:
        daily_query = daily_query.filter(TokenLog.user_id == user_id)
    daily_logs = daily_query.all()
    daily_tokens = sum(log.total_tokens for log in daily_logs)
    daily_cost = sum(log.estimated_cost_usd for log in daily_logs)

    # Calculate monthly usage
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_query = db.query(TokenLog).filter(TokenLog.created_at >= month_start)
    if user_id:
        monthly_query = monthly_query.filter(TokenLog.user_id == user_id)
    monthly_logs = monthly_query.all()
    monthly_tokens = sum(log.total_tokens for log in monthly_logs)
    monthly_cost = sum(log.estimated_cost_usd for log in monthly_logs)

    # Check alerts
    alert_triggered = False
    alert_message = ""

    if budget.daily_token_limit > 0:
        pct = (daily_tokens / budget.daily_token_limit) * 100
        if pct >= budget.alert_threshold_percent:
            alert_triggered = True
            alert_message = f"Daily token usage at {pct:.0f}% of limit"

    if budget.monthly_token_limit > 0:
        pct = (monthly_tokens / budget.monthly_token_limit) * 100
        if pct >= budget.alert_threshold_percent:
            alert_triggered = True
            alert_message = f"Monthly token usage at {pct:.0f}% of limit"

    if budget.monthly_cost_limit_usd > 0:
        pct = (monthly_cost / budget.monthly_cost_limit_usd) * 100
        if pct >= budget.alert_threshold_percent:
            alert_triggered = True
            alert_message = f"Monthly cost at {pct:.0f}% of budget (${monthly_cost:.4f}/${budget.monthly_cost_limit_usd:.2f})"

    allowed_models = budget.allowed_models.split(",") if budget.allowed_models else ["gpt-4o-mini"]

    return BudgetStatus(
        daily_tokens_used=daily_tokens,
        daily_tokens_limit=budget.daily_token_limit,
        daily_cost_used=round(daily_cost, 6),
        daily_cost_limit=budget.daily_cost_limit_usd,
        monthly_tokens_used=monthly_tokens,
        monthly_tokens_limit=budget.monthly_token_limit,
        monthly_cost_used=round(monthly_cost, 6),
        monthly_cost_limit=budget.monthly_cost_limit_usd,
        alert_triggered=alert_triggered,
        alert_message=alert_message,
        preferred_model=budget.preferred_model or "gpt-4o-mini",
        allowed_models=allowed_models,
    )


@router.put("/budget")
def update_budget(config: BudgetConfig, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Update budget configuration (global or per-user)."""
    if user_id:
        budget = db.query(TokenBudget).filter(TokenBudget.user_id == user_id).first()
        if not budget:
            budget = TokenBudget(user_id=user_id, scope="user")
            db.add(budget)
    else:
        budget = db.query(TokenBudget).filter(TokenBudget.user_id == None).first()  # noqa: E711
        if not budget:
            budget = TokenBudget(scope="global")
            db.add(budget)

    budget.daily_token_limit = config.daily_token_limit
    budget.monthly_token_limit = config.monthly_token_limit
    budget.daily_cost_limit_usd = config.daily_cost_limit_usd
    budget.monthly_cost_limit_usd = config.monthly_cost_limit_usd
    budget.alert_threshold_percent = config.alert_threshold_percent
    budget.preferred_model = config.preferred_model
    budget.allowed_models = ",".join(config.allowed_models)
    budget.enforce_limits = config.enforce_limits

    db.commit()
    return {"updated": True}


@router.get("/models", response_model=list[ModelUsageBreakdown])
def get_model_breakdown(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get per-model usage breakdown for analytics."""
    query = db.query(TokenLog)
    if user_id:
        query = query.filter(TokenLog.user_id == user_id)
    logs = query.all()
    total_tokens = sum(log.total_tokens for log in logs) or 1

    models: dict[str, dict] = {}
    for log in logs:
        key = log.model or "unknown"
        if key not in models:
            models[key] = {"calls": 0, "tokens": 0, "cost": 0.0}
        models[key]["calls"] += 1
        models[key]["tokens"] += log.total_tokens
        models[key]["cost"] += log.estimated_cost_usd

    return [
        ModelUsageBreakdown(
            model=name,
            calls=data["calls"],
            tokens=data["tokens"],
            cost=round(data["cost"], 6),
            percentage=round((data["tokens"] / total_tokens) * 100, 1),
        )
        for name, data in sorted(models.items(), key=lambda x: x[1]["tokens"], reverse=True)
    ]


# ---------------------------------------------------------------------------
# Per-User Activity Tracking (SSO-ready)
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserActivity])
def get_all_user_activity(db: Session = Depends(get_db)):
    """Get activity summary for all users — admin dashboard view."""
    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    result = []

    for user in users:
        logs = db.query(TokenLog).filter(TokenLog.user_id == user.id).all()
        sessions = db.query(UserSession).filter(UserSession.user_id == user.id).all()

        models_used = list(set(log.model for log in logs if log.model))
        features_used = list(set(log.feature for log in logs if log.feature))
        last_log = db.query(TokenLog).filter(TokenLog.user_id == user.id).order_by(desc(TokenLog.created_at)).first()

        result.append(UserActivity(
            user_id=user.id,
            email=user.email,
            name=user.name,
            team=user.team or "",
            role=user.role or "developer",
            total_calls=len(logs),
            total_tokens=sum(log.total_tokens for log in logs),
            total_cost=round(sum(log.estimated_cost_usd for log in logs), 6),
            models_used=models_used[:5],
            features_used=features_used[:5],
            last_active=last_log.created_at.isoformat() if last_log and last_log.created_at else None,
            sessions_count=len(sessions),
        ))

    result.sort(key=lambda x: x.total_tokens, reverse=True)
    return result


@router.get("/users/{user_id}", response_model=UserActivityDetail)
def get_user_activity_detail(user_id: int, db: Session = Depends(get_db)):
    """Get detailed activity for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logs = db.query(TokenLog).filter(TokenLog.user_id == user_id).all()
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()

    # Daily stats
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_logs = [log for log in logs if log.created_at and log.created_at >= today_start]

    # Monthly stats
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_logs = [log for log in logs if log.created_at and log.created_at >= month_start]

    # Top models
    model_stats: dict[str, dict] = {}
    for log in logs:
        key = log.model or "unknown"
        if key not in model_stats:
            model_stats[key] = {"model": key, "calls": 0, "tokens": 0, "cost": 0.0}
        model_stats[key]["calls"] += 1
        model_stats[key]["tokens"] += log.total_tokens
        model_stats[key]["cost"] += log.estimated_cost_usd
    top_models = sorted(model_stats.values(), key=lambda x: x["tokens"], reverse=True)[:5]

    # Top features
    feature_stats: dict[str, dict] = {}
    for log in logs:
        key = log.feature or "other"
        if key not in feature_stats:
            feature_stats[key] = {"feature": key, "calls": 0, "tokens": 0}
        feature_stats[key]["calls"] += 1
        feature_stats[key]["tokens"] += log.total_tokens
    top_features = sorted(feature_stats.values(), key=lambda x: x["tokens"], reverse=True)[:5]

    # Recent activity (last 20)
    recent_logs = sorted(logs, key=lambda x: x.created_at or datetime.min, reverse=True)[:20]
    recent_activity = [
        {
            "id": log.id,
            "action": log.action,
            "feature": log.feature,
            "model": log.model,
            "tokens": log.total_tokens,
            "cost": round(log.estimated_cost_usd, 6),
            "status": log.status or "success",
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in recent_logs
    ]

    # Sessions summary
    sessions_data = [
        {
            "id": s.id,
            "type": s.session_type,
            "title": s.title or f"{s.session_type} session",
            "status": s.status,
            "tokens": s.total_tokens_used,
            "cost": round(s.total_cost_usd, 6),
            "messages": s.messages_count,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        }
        for s in sorted(sessions, key=lambda x: x.started_at or datetime.min, reverse=True)[:10]
    ]

    return UserActivityDetail(
        user_id=user.id,
        email=user.email,
        name=user.name,
        team=user.team or "",
        total_tokens=sum(log.total_tokens for log in logs),
        total_cost=round(sum(log.estimated_cost_usd for log in logs), 6),
        daily_tokens=sum(log.total_tokens for log in daily_logs),
        daily_cost=round(sum(log.estimated_cost_usd for log in daily_logs), 6),
        monthly_tokens=sum(log.total_tokens for log in monthly_logs),
        monthly_cost=round(sum(log.estimated_cost_usd for log in monthly_logs), 6),
        top_models=top_models,
        top_features=top_features,
        recent_activity=recent_activity,
        sessions=sessions_data,
    )


@router.get("/teams", response_model=list[TeamUsageSummary])
def get_team_usage(db: Session = Depends(get_db)):
    """Get token usage grouped by team."""
    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    teams: dict[str, dict] = {}

    for user in users:
        team = user.team or "Unassigned"
        if team not in teams:
            teams[team] = {"members": set(), "tokens": 0, "cost": 0.0, "models": {}, "features": {}}
        teams[team]["members"].add(user.id)

        logs = db.query(TokenLog).filter(TokenLog.user_id == user.id).all()
        for log in logs:
            teams[team]["tokens"] += log.total_tokens
            teams[team]["cost"] += log.estimated_cost_usd
            model = log.model or "unknown"
            teams[team]["models"][model] = teams[team]["models"].get(model, 0) + log.total_tokens
            feature = log.feature or "other"
            teams[team]["features"][feature] = teams[team]["features"].get(feature, 0) + log.total_tokens

    result = []
    for team_name, data in teams.items():
        top_model = max(data["models"], key=data["models"].get) if data["models"] else "none"
        top_feature = max(data["features"], key=data["features"].get) if data["features"] else "none"
        result.append(TeamUsageSummary(
            team=team_name,
            members=len(data["members"]),
            total_tokens=data["tokens"],
            total_cost=round(data["cost"], 6),
            top_model=top_model,
            top_feature=top_feature,
        ))

    result.sort(key=lambda x: x.total_tokens, reverse=True)
    return result


@router.get("/trends")
def get_usage_trends(days: int = 30, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get daily usage trends for the last N days."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(TokenLog).filter(TokenLog.created_at >= start_date)
    if user_id:
        query = query.filter(TokenLog.user_id == user_id)
    logs = query.all()

    # Group by date
    daily: dict[str, dict] = {}
    for log in logs:
        if not log.created_at:
            continue
        date_key = log.created_at.strftime("%Y-%m-%d")
        if date_key not in daily:
            daily[date_key] = {"tokens": 0, "cost": 0.0, "calls": 0}
        daily[date_key]["tokens"] += log.total_tokens
        daily[date_key]["cost"] += log.estimated_cost_usd
        daily[date_key]["calls"] += 1

    # Fill in missing dates
    result = []
    for i in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        data = daily.get(date, {"tokens": 0, "cost": 0.0, "calls": 0})
        result.append({
            "date": date,
            "tokens": data["tokens"],
            "cost": round(data["cost"], 6),
            "calls": data["calls"],
        })

    return result


# ---------------------------------------------------------------------------
# Budget Enforcement Check
# ---------------------------------------------------------------------------

@router.get("/check-limit")
def check_token_limit(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Check if a user/global has hit their token limit. Call before making LLM requests."""
    # Get applicable budget
    budget = None
    if user_id:
        budget = db.query(TokenBudget).filter(TokenBudget.user_id == user_id).first()
    if not budget:
        budget = db.query(TokenBudget).filter(TokenBudget.user_id == None).first()  # noqa: E711

    if not budget or not budget.enforce_limits:
        return {"allowed": True, "reason": "No limits enforced"}

    # Check daily limit
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_query = db.query(TokenLog).filter(TokenLog.created_at >= today_start)
    if user_id:
        daily_query = daily_query.filter(TokenLog.user_id == user_id)
    daily_tokens = sum(log.total_tokens for log in daily_query.all())

    if budget.daily_token_limit > 0 and daily_tokens >= budget.daily_token_limit:
        return {
            "allowed": False,
            "reason": f"Daily token limit reached ({daily_tokens:,}/{budget.daily_token_limit:,})",
            "limit_type": "daily_tokens",
        }

    # Check monthly limit
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_query = db.query(TokenLog).filter(TokenLog.created_at >= month_start)
    if user_id:
        monthly_query = monthly_query.filter(TokenLog.user_id == user_id)
    monthly_logs = monthly_query.all()
    monthly_tokens = sum(log.total_tokens for log in monthly_logs)
    monthly_cost = sum(log.estimated_cost_usd for log in monthly_logs)

    if budget.monthly_token_limit > 0 and monthly_tokens >= budget.monthly_token_limit:
        return {
            "allowed": False,
            "reason": f"Monthly token limit reached ({monthly_tokens:,}/{budget.monthly_token_limit:,})",
            "limit_type": "monthly_tokens",
        }

    if budget.monthly_cost_limit_usd > 0 and monthly_cost >= budget.monthly_cost_limit_usd:
        return {
            "allowed": False,
            "reason": f"Monthly cost limit reached (${monthly_cost:.4f}/${budget.monthly_cost_limit_usd:.2f})",
            "limit_type": "monthly_cost",
        }

    return {"allowed": True, "reason": "Within limits"}

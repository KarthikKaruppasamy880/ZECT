"""Token Limit Controls — Dashboard model/budget controls."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import TokenLog, TokenBudget
from app.token_tracker import get_usage_summary
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Models
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
    alert_threshold_percent: int = 80  # Alert when usage hits this % of limit
    preferred_model: str = "gpt-4o-mini"
    allowed_models: list[str] = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/usage", response_model=TokenUsageSummary)
def get_token_usage(db: Session = Depends(get_db)):
    """Get full token usage summary with breakdowns."""
    summary = get_usage_summary(db)
    return TokenUsageSummary(**summary)


@router.get("/budget", response_model=BudgetStatus)
def get_budget_status(db: Session = Depends(get_db)):
    """Get current budget status including limits and alerts."""
    # Get budget config
    budget = db.query(TokenBudget).first()
    if not budget:
        budget = TokenBudget()
        db.add(budget)
        db.commit()
        db.refresh(budget)

    # Calculate daily usage
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_logs = db.query(TokenLog).filter(TokenLog.created_at >= today_start).all()
    daily_tokens = sum(l.total_tokens for l in daily_logs)
    daily_cost = sum(l.estimated_cost_usd for l in daily_logs)

    # Calculate monthly usage
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_logs = db.query(TokenLog).filter(TokenLog.created_at >= month_start).all()
    monthly_tokens = sum(l.total_tokens for l in monthly_logs)
    monthly_cost = sum(l.estimated_cost_usd for l in monthly_logs)

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
def update_budget(config: BudgetConfig, db: Session = Depends(get_db)):
    """Update budget configuration."""
    budget = db.query(TokenBudget).first()
    if not budget:
        budget = TokenBudget()
        db.add(budget)

    budget.daily_token_limit = config.daily_token_limit
    budget.monthly_token_limit = config.monthly_token_limit
    budget.daily_cost_limit_usd = config.daily_cost_limit_usd
    budget.monthly_cost_limit_usd = config.monthly_cost_limit_usd
    budget.alert_threshold_percent = config.alert_threshold_percent
    budget.preferred_model = config.preferred_model
    budget.allowed_models = ",".join(config.allowed_models)

    db.commit()
    return {"updated": True}


@router.get("/models", response_model=list[ModelUsageBreakdown])
def get_model_breakdown(db: Session = Depends(get_db)):
    """Get per-model usage breakdown for analytics."""
    logs = db.query(TokenLog).all()
    total_tokens = sum(l.total_tokens for l in logs) or 1

    models: dict[str, dict] = {}
    for l in logs:
        key = l.model or "unknown"
        if key not in models:
            models[key] = {"calls": 0, "tokens": 0, "cost": 0.0}
        models[key]["calls"] += 1
        models[key]["tokens"] += l.total_tokens
        models[key]["cost"] += l.estimated_cost_usd

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

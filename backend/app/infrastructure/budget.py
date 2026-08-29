"""Token budget enforcement — the missing link between TokenBudget config and actual LLM calls.

check_token_limit() in routers/token_controls.py already computes daily/monthly
usage against a user's TokenBudget row, but nothing called it before spending
tokens — enforce_limits had no effect. This module wires that check in as a
FastAPI dependency so LLM-calling endpoints can require it directly.
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import get_current_user, CurrentUser
from app.infrastructure.database import get_db
from app.models import TokenBudget, TokenLog


class BudgetExceeded(HTTPException):
    """Raised when a user has hit their configured token/cost budget."""

    def __init__(self, message: str, limit_type: str):
        super().__init__(status_code=429, detail={"message": message, "limit_type": limit_type})


def _get_budget(db: Session, user_id: int) -> TokenBudget | None:
    budget = db.query(TokenBudget).filter(TokenBudget.user_id == user_id).first()
    if not budget:
        budget = db.query(TokenBudget).filter(TokenBudget.user_id == None).first()  # noqa: E711
    return budget


def check_budget(db: Session, user_id: int) -> None:
    """Raise BudgetExceeded if the user (or the global default) is over budget.

    No-op if no budget row exists or enforce_limits is False — budgets are
    opt-in per org/user, not a silent default-deny.
    """
    budget = _get_budget(db, user_id)
    if not budget or not budget.enforce_limits:
        return

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    daily_tokens = sum(
        log.total_tokens
        for log in db.query(TokenLog).filter(TokenLog.user_id == user_id, TokenLog.created_at >= today_start)
    )
    if budget.daily_token_limit > 0 and daily_tokens >= budget.daily_token_limit:
        raise BudgetExceeded(
            f"Daily token limit reached ({daily_tokens:,}/{budget.daily_token_limit:,})",
            "daily_tokens",
        )

    monthly_logs = db.query(TokenLog).filter(TokenLog.user_id == user_id, TokenLog.created_at >= month_start).all()
    monthly_tokens = sum(log.total_tokens for log in monthly_logs)
    monthly_cost = sum(log.estimated_cost_usd for log in monthly_logs)

    if budget.monthly_token_limit > 0 and monthly_tokens >= budget.monthly_token_limit:
        raise BudgetExceeded(
            f"Monthly token limit reached ({monthly_tokens:,}/{budget.monthly_token_limit:,})",
            "monthly_tokens",
        )
    if budget.monthly_cost_limit_usd > 0 and monthly_cost >= budget.monthly_cost_limit_usd:
        raise BudgetExceeded(
            f"Monthly cost limit reached (${monthly_cost:.4f}/${budget.monthly_cost_limit_usd:.2f})",
            "monthly_cost",
        )


def enforce_token_budget(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """FastAPI dependency: 429s before an LLM call if the user is over budget.

    Usage: add `current_user: CurrentUser = Depends(enforce_token_budget)` to
    any endpoint that spends tokens, then pass current_user.user_id into log_tokens().
    """
    check_budget(db, current_user.user_id)
    return current_user

"""Centralized token tracking — persists every operation to the token_logs table."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import TokenLog

# Pricing per 1M tokens (gpt-4o-mini as of 2025)
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "github-api": {"input": 0.0, "output": 0.0},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING.get(model, {"input": 0.15, "output": 0.60})
    cost = (prompt_tokens / 1_000_000) * rates["input"] + (completion_tokens / 1_000_000) * rates["output"]
    return round(cost, 6)


def log_tokens(
    action: str,
    feature: str,
    model: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> None:
    """Persist a token usage record to the database.

    This function is fail-safe: if the database write fails for any reason
    (missing table, connection error, etc.), it logs the error to stdout
    but does NOT raise — token tracking must never crash the main request.
    """
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens
    cost = _estimate_cost(model, prompt_tokens, completion_tokens)
    try:
        db = SessionLocal()
        try:
            entry = TokenLog(
                action=action,
                feature=feature,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost,
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[ZECT TOKEN TRACKER] Failed to log tokens: {e}")


def get_usage_summary(db: Session) -> dict:
    """Return aggregate token usage stats."""
    logs = db.query(TokenLog).all()
    total_calls = len(logs)
    total_tokens = sum(l.total_tokens for l in logs)
    total_cost = round(sum(l.estimated_cost_usd for l in logs), 6)
    total_prompt = sum(l.prompt_tokens for l in logs)
    total_completion = sum(l.completion_tokens for l in logs)

    # Breakdown by feature
    features: dict[str, dict] = {}
    for l in logs:
        key = l.feature or "other"
        if key not in features:
            features[key] = {"calls": 0, "tokens": 0, "cost": 0.0}
        features[key]["calls"] += 1
        features[key]["tokens"] += l.total_tokens
        features[key]["cost"] = round(features[key]["cost"] + l.estimated_cost_usd, 6)

    # Breakdown by model
    models: dict[str, dict] = {}
    for l in logs:
        key = l.model or "unknown"
        if key not in models:
            models[key] = {"calls": 0, "tokens": 0, "cost": 0.0}
        models[key]["calls"] += 1
        models[key]["tokens"] += l.total_tokens
        models[key]["cost"] = round(models[key]["cost"] + l.estimated_cost_usd, 6)

    # Recent entries (last 50)
    recent = sorted(logs, key=lambda x: x.created_at or datetime.min, reverse=True)[:50]

    return {
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_cost_usd": total_cost,
        "by_feature": features,
        "by_model": models,
        "recent": [
            {
                "id": r.id,
                "action": r.action,
                "feature": r.feature,
                "model": r.model,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in recent
        ],
    }

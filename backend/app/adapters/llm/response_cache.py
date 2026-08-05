"""Exact-match LLM response cache — cost-tree lever #10 ("cache exact
responses: same input -> instant hit"). Re-running an unchanged review is a
real, common case (user clicks Review again without editing anything) that
previously always re-hit the API for a response that would come back
identical."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session


def cache_key_for(*parts: str) -> str:
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def get_cached(db: Session | None, cache_key: str) -> dict[str, Any] | None:
    """Best-effort — a lookup/parse failure must never break the caller;
    it's treated the same as a cache miss."""
    if db is None:
        return None
    from app.models import LLMResponseCache

    try:
        row = db.query(LLMResponseCache).filter(LLMResponseCache.cache_key == cache_key).first()
        if not row:
            return None
        return json.loads(row.response_json)
    except Exception:
        return None


def store_cached(db: Session | None, cache_key: str, response: dict[str, Any], *, model: str = "", tokens_used: int = 0) -> None:
    """Best-effort — a cache-write failure must never break the response the
    caller already has in hand."""
    if db is None:
        return
    from app.models import LLMResponseCache

    try:
        payload = json.dumps(response)
        existing = db.query(LLMResponseCache).filter(LLMResponseCache.cache_key == cache_key).first()
        if existing:
            existing.response_json = payload
            existing.model = model
            existing.tokens_used = tokens_used
        else:
            db.add(LLMResponseCache(cache_key=cache_key, response_json=payload, model=model, tokens_used=tokens_used))
        db.commit()
    except Exception:
        db.rollback()

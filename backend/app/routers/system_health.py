"""System Health + P3 security/model readiness routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/system", tags=["system-health"])


@router.get("/health")
def system_health(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.system_health import build_system_health

    return build_system_health(db)


@router.get("/model-readiness")
def model_readiness(_user: CurrentUser = Depends(get_current_user)):
    """P3: local/cloud model gateway readiness (no secrets)."""
    from app.adapters.llm.openai_compat import (
        mentrix_local_llm_configured,
        openai_compat_available,
        mentrix_llm_chat_model,
    )
    from app.services.work_items.fallback_policy import resolve_model_route
    import os

    local_ok = mentrix_local_llm_configured()
    cloud_ok = bool((os.getenv("OPENAI_API_KEY") or "").strip()) or openai_compat_available()
    route = resolve_model_route(
        local_configured=local_ok,
        cloud_configured=cloud_ok,
        local_model=mentrix_llm_chat_model(),
    )
    return {
        "local_configured": local_ok,
        "cloud_configured": cloud_ok,
        "model": mentrix_llm_chat_model(),
        "route": {
            "provider": route.provider,
            "blocked": route.blocked,
            "fallback_used": route.fallback_used,
            "fallback_reason": route.fallback_reason,
        },
    }


class SecurityScanIn(BaseModel):
    target: str = ""
    context: Optional[dict[str, Any]] = None


@router.post("/security-scan")
def security_scan(
    body: SecurityScanIn,
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.security_scanner import get_default_security_scanner

    return get_default_security_scanner().scan(target=body.target, context=body.context)


@router.get("/skills-fs")
def skills_filesystem(
    limit: int = Query(50, ge=1, le=200),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.skills_fs import list_filesystem_skills

    return {"skills": list_filesystem_skills(limit=limit)}

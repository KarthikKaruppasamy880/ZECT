"""System Health + P3 security/model/skills/desktop readiness routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
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
    """Local/cloud model gateway readiness + surface matrix (no secrets)."""
    from app.adapters.llm.openai_compat import (
        mentrix_local_llm_configured,
        openai_compat_available,
        mentrix_llm_chat_model,
    )
    from app.services.work_items.fallback_policy import resolve_model_route
    from app.services.local_model_matrix import build_local_model_matrix
    import os

    local_ok = mentrix_local_llm_configured()
    cloud_ok = bool((os.getenv("OPENAI_API_KEY") or "").strip()) or openai_compat_available()
    route = resolve_model_route(
        local_configured=local_ok,
        cloud_configured=cloud_ok,
        local_model=mentrix_llm_chat_model(),
    )
    base_url = (
        os.getenv("ZECT_LLM_BASE_URL")
        or os.getenv("MENTRIX_LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or ""
    ).strip()
    optimizations: list[str] = []
    if local_ok:
        optimizations.append("prefer_local_for_coding")
        optimizations.append("cache_identical_prompts")
    if cloud_ok and not local_ok:
        optimizations.append("configure_local_llm_for_lower_latency")
    if not local_ok and not cloud_ok:
        optimizations.append("set_ZECT_LLM_BASE_URL_or_OPENAI_API_KEY")
    return {
        "local_configured": local_ok,
        "cloud_configured": cloud_ok,
        "model": mentrix_llm_chat_model(),
        "base_url_configured": bool(base_url),
        "optimizations": optimizations,
        "route": {
            "provider": route.provider,
            "blocked": route.blocked,
            "fallback_used": route.fallback_used,
            "fallback_reason": route.fallback_reason,
        },
        "matrix": build_local_model_matrix(),
    }


class SecurityScanIn(BaseModel):
    target: str = ""
    context: Optional[dict[str, Any]] = None


@router.post("/security-scan")
def security_scan(
    body: SecurityScanIn,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.security_scanner import get_default_security_scanner

    return get_default_security_scanner().scan(target=body.target, context=body.context, db=db)


@router.get("/skills-fs")
def skills_filesystem(
    limit: int = Query(50, ge=1, le=200),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.skills_fs import list_filesystem_skills

    return {"skills": list_filesystem_skills(limit=limit)}


class SkillsSyncIn(BaseModel):
    direction: str = Field(default="bidirectional")  # fs_to_db | db_to_fs | bidirectional


@router.post("/skills-fs/sync")
def skills_filesystem_sync(
    body: SkillsSyncIn | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """Bidirectional Skills sync: FS packs ↔ SkillDefinition (DB remains execution SoT)."""
    from fastapi import HTTPException
    from app.services.skills_fs import (
        sync_db_skills_to_filesystem,
        sync_filesystem_skills_to_db,
        sync_skills_bidirectional,
    )

    direction = ((body.direction if body else None) or "bidirectional").strip().lower()
    if direction == "fs_to_db":
        return sync_filesystem_skills_to_db(db, limit=limit)
    if direction == "db_to_fs":
        return sync_db_skills_to_filesystem(db, limit=limit)
    if direction in ("bidirectional", "both", "bi"):
        return sync_skills_bidirectional(db, limit=limit)
    raise HTTPException(status_code=400, detail="direction must be fs_to_db|db_to_fs|bidirectional")


@router.get("/desktop-readiness")
def desktop_readiness(_user: CurrentUser = Depends(get_current_user)):
    """Electron / Computer Mode readiness surface (no new desktop agent)."""
    from app.services.desktop_readiness import build_desktop_readiness

    return build_desktop_readiness()

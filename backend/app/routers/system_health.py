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
    """Local/cloud model gateway readiness + per-profile matrix (no secrets)."""
    from app.adapters.llm.openai_compat import mentrix_llm_chat_model
    from app.services.local_model_matrix import build_local_model_matrix
    from app.services.model_gateway import MODEL_PROFILES, build_gateway_audit

    audit = build_gateway_audit()
    default_route = audit["profiles"].get("QUALITY") or next(iter(audit["profiles"].values()), {})
    optimizations: list[str] = []
    if audit.get("local_configured"):
        optimizations.append("prefer_local_for_coding")
        optimizations.append("cache_identical_prompts")
    if audit.get("cloud_configured") and not audit.get("local_configured"):
        optimizations.append("configure_local_llm_for_lower_latency")
    if not audit.get("local_configured") and not audit.get("cloud_configured"):
        optimizations.append("set_ZECT_LLM_BASE_URL_or_OPENAI_API_KEY")
    if audit.get("duplicate_config_warning"):
        optimizations.append("resolve_duplicate_ZECT_vs_MENTRIX_LLM_BASE_URL")
    return {
        "local_configured": audit["local_configured"],
        "cloud_configured": audit["cloud_configured"],
        "model": mentrix_llm_chat_model(),
        "base_url_configured": audit["canonical_base_url_configured"],
        "canonical_env": audit["canonical_env"],
        "alias_envs": audit["alias_envs"],
        "duplicate_config_warning": audit["duplicate_config_warning"],
        "model_profiles": list(MODEL_PROFILES),
        "profiles": audit["profiles"],
        "optimizations": optimizations,
        "route": {
            "provider": default_route.get("provider"),
            "blocked": default_route.get("blocked"),
            "fallback_used": default_route.get("fallback_used"),
            "fallback_reason": default_route.get("fallback_reason"),
            "requested_model": default_route.get("requested_model"),
            "actual_model": default_route.get("actual_model"),
            "local_or_cloud": default_route.get("local_or_cloud"),
        },
        "matrix": build_local_model_matrix(),
        "gateway_audit": audit,
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

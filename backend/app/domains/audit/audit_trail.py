"""Audit Trail — Full CRUD audit logging for all operations."""

import json
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.infrastructure.database import SessionLocal
from app.models import AuditLog
from app.infrastructure.auth.deps import get_current_user, CurrentUser
from app.infrastructure.auth.rbac import require_authentication

router = APIRouter(prefix="/api/audit", tags=["audit"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: int | None
    resource_name: str
    details: str
    ip_address: str | None
    user_agent: str | None
    created_at: str


class AuditStats(BaseModel):
    total_entries: int
    actions: dict[str, int]
    resource_types: dict[str, int]
    recent_24h: int


# ---------------------------------------------------------------------------
# Helper: write an audit entry from any router
# ---------------------------------------------------------------------------

def log_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    resource_name: str = "",
    details: str | dict | None = "",
    user_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """Canonical audit writer (Phase 5 Stage A). Soft-fails so ops never break on audit errors."""
    try:
        if details is None:
            details_value = ""
        elif isinstance(details, str):
            details_value = details
        else:
            details_value = json.dumps(details, default=str)
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type or "unknown",
            resource_id=resource_id,
            resource_name=resource_name or "",
            details=details_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entry)
        db.commit()
        return entry
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[audit] logging failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AuditLogResponse])
@router.get("/", response_model=list[AuditLogResponse])
@require_authentication  # ✅ RBAC: Authentication required
def list_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit log entries with optional filters (authentication required)."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [
        AuditLogResponse(
            id=e.id,
            user_id=e.user_id,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            resource_name=e.resource_name or "",
            details=e.details or "",
            ip_address=e.ip_address,
            user_agent=e.user_agent,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in entries
    ]


@router.get("/stats", response_model=AuditStats)
@require_authentication  # ✅ RBAC: Authentication required
def audit_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit trail statistics (authentication required)."""
    from sqlalchemy import func
    from datetime import timedelta

    total = db.query(AuditLog).count()
    now = datetime.now(timezone.utc)
    recent = db.query(AuditLog).filter(AuditLog.created_at >= now - timedelta(hours=24)).count()

    action_counts = dict(
        db.query(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
        .all()
    )
    resource_counts = dict(
        db.query(AuditLog.resource_type, func.count(AuditLog.id))
        .group_by(AuditLog.resource_type)
        .all()
    )

    return AuditStats(
        total_entries=total,
        actions=action_counts,
        resource_types=resource_counts,
        recent_24h=recent,
    )

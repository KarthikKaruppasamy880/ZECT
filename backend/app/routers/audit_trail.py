"""Audit Trail — Full CRUD audit logging for all operations."""

import json
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import AuditLog

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
    details: str = "",
    user_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        details=details if isinstance(details, str) else json.dumps(details),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    db.commit()
    return entry


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AuditLogResponse])
@router.get("/", response_model=list[AuditLogResponse])
def list_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List audit log entries with optional filters."""
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
def audit_stats(db: Session = Depends(get_db)):
    """Get audit trail statistics."""
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

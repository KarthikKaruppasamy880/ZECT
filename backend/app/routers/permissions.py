"""Zinnia Permissions Protocol — allow/require-approval/never-allowed enforcement."""

import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PermissionRule, PermissionAudit

router = APIRouter(prefix="/api/permissions", tags=["permissions"])

# Default permission rules — seeded on first access
DEFAULT_RULES = [
    # Always allowed
    {"action_pattern": "read_file", "permission_level": "allow", "category": "file", "description": "Read any file in the workspace"},
    {"action_pattern": "run_tests", "permission_level": "allow", "category": "testing", "description": "Run test suites"},
    {"action_pattern": "create_branch", "permission_level": "allow", "category": "git", "description": "Create new branches"},
    {"action_pattern": "write_memory", "permission_level": "allow", "category": "memory", "description": "Write to memory layers"},
    {"action_pattern": "draft_pr", "permission_level": "allow", "category": "git", "description": "Create draft pull requests"},
    {"action_pattern": "search_code", "permission_level": "allow", "category": "file", "description": "Search code and files"},
    # Requires approval
    {"action_pattern": "merge_pr", "permission_level": "require_approval", "category": "git", "description": "Merge pull requests to main/develop"},
    {"action_pattern": "deploy_.*", "permission_level": "require_approval", "category": "deploy", "description": "Deploy to any environment"},
    {"action_pattern": "delete_file", "permission_level": "require_approval", "category": "file", "description": "Delete files from workspace"},
    {"action_pattern": "install_dependency", "permission_level": "require_approval", "category": "package", "description": "Install new dependencies"},
    {"action_pattern": "modify_ci", "permission_level": "require_approval", "category": "ci", "description": "Modify CI/CD pipelines"},
    {"action_pattern": "run_migration", "permission_level": "require_approval", "category": "database", "description": "Run database migrations"},
    {"action_pattern": "modify_permissions", "permission_level": "require_approval", "category": "admin", "description": "Modify permission rules"},
    # Never allowed
    {"action_pattern": "force_push_main", "permission_level": "never", "category": "git", "description": "Force push to main/master branches"},
    {"action_pattern": "access_secrets", "permission_level": "never", "category": "security", "description": "Directly access secrets/credentials"},
    {"action_pattern": "disable_hooks", "permission_level": "never", "category": "git", "description": "Disable pre-commit hooks"},
    {"action_pattern": "delete_memory", "permission_level": "never", "category": "memory", "description": "Delete memory entries permanently"},
    {"action_pattern": "external_network_.*", "permission_level": "never", "category": "network", "description": "Access unapproved external domains"},
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PermissionRuleCreate(BaseModel):
    project_id: Optional[int] = None
    action_pattern: str
    permission_level: str  # allow, require_approval, never
    category: str = "general"
    description: str = ""
    requires_mfa: bool = False


class PermissionRuleUpdate(BaseModel):
    permission_level: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    requires_mfa: Optional[bool] = None
    is_active: Optional[bool] = None


class PermissionCheck(BaseModel):
    action: str
    project_id: Optional[int] = None
    user_id: Optional[int] = None


class ApprovalAction(BaseModel):
    approved: bool
    approved_by: str = "admin"
    reason: str = ""


# ---------------------------------------------------------------------------
# Rules CRUD
# ---------------------------------------------------------------------------

@router.get("/rules")
def list_rules(
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    permission_level: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(PermissionRule).filter(PermissionRule.is_active == True)
    if project_id is not None:
        q = q.filter(PermissionRule.project_id == project_id)
    if category:
        q = q.filter(PermissionRule.category == category)
    if permission_level:
        q = q.filter(PermissionRule.permission_level == permission_level)
    rules = q.order_by(PermissionRule.category, PermissionRule.action_pattern).all()

    # Seed defaults if empty
    if not rules and project_id is None:
        for d in DEFAULT_RULES:
            rule = PermissionRule(**d)
            db.add(rule)
        db.commit()
        rules = db.query(PermissionRule).filter(PermissionRule.is_active == True).all()

    return [_serialize_rule(r) for r in rules]


@router.post("/rules")
def create_rule(data: PermissionRuleCreate, db: Session = Depends(get_db)):
    if data.permission_level not in ("allow", "require_approval", "never"):
        raise HTTPException(400, "permission_level must be: allow, require_approval, or never")
    rule = PermissionRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _serialize_rule(rule)


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, data: PermissionRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(PermissionRule).filter(PermissionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return _serialize_rule(rule)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(PermissionRule).filter(PermissionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.is_active = False
    db.commit()
    return {"status": "deactivated", "id": rule_id}


# ---------------------------------------------------------------------------
# Permission Check — the core enforcement endpoint
# ---------------------------------------------------------------------------

@router.post("/check")
def check_permission(data: PermissionCheck, db: Session = Depends(get_db)):
    """Check if an action is allowed, requires approval, or is blocked."""
    # Get all active rules (project-specific + global)
    rules = db.query(PermissionRule).filter(
        PermissionRule.is_active == True,
    ).all()

    # Find matching rules (most restrictive wins)
    matching = []
    for rule in rules:
        # Only match project-specific rules if project matches, or global rules (project_id=None)
        if rule.project_id is not None and rule.project_id != data.project_id:
            continue
        try:
            if re.fullmatch(rule.action_pattern, data.action):
                matching.append(rule)
        except re.error:
            if rule.action_pattern == data.action:
                matching.append(rule)

    if not matching:
        # Default: allow if no rule matches
        result = "granted"
        level = "allow"
    else:
        # Most restrictive wins: never > require_approval > allow
        levels = [r.permission_level for r in matching]
        if "never" in levels:
            result = "denied"
            level = "never"
        elif "require_approval" in levels:
            result = "pending_approval"
            level = "require_approval"
        else:
            result = "granted"
            level = "allow"

    # Log the check
    audit = PermissionAudit(
        user_id=data.user_id,
        project_id=data.project_id,
        action=data.action,
        permission_level=level,
        result=result,
        rule_id=matching[0].id if matching else None,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    return {
        "action": data.action,
        "result": result,
        "permission_level": level,
        "matching_rules": [_serialize_rule(r) for r in matching],
        "audit_id": audit.id,
    }


# ---------------------------------------------------------------------------
# Approval Workflow
# ---------------------------------------------------------------------------

@router.post("/audits/{audit_id}/approve")
def approve_action(audit_id: int, data: ApprovalAction, db: Session = Depends(get_db)):
    audit = db.query(PermissionAudit).filter(PermissionAudit.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit entry not found")
    if audit.result != "pending_approval":
        raise HTTPException(400, "This action is not pending approval")

    audit.approval_status = "approved" if data.approved else "rejected"
    audit.approved_by = data.approved_by
    audit.reason = data.reason
    audit.result = "granted" if data.approved else "denied"
    db.commit()
    db.refresh(audit)
    return _serialize_audit(audit)


@router.get("/audits")
def list_audits(
    project_id: Optional[int] = None,
    result: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(PermissionAudit)
    if project_id:
        q = q.filter(PermissionAudit.project_id == project_id)
    if result:
        q = q.filter(PermissionAudit.result == result)
    audits = q.order_by(PermissionAudit.created_at.desc()).limit(limit).all()
    return [_serialize_audit(a) for a in audits]


@router.get("/audits/pending")
def list_pending_approvals(db: Session = Depends(get_db)):
    audits = db.query(PermissionAudit).filter(
        PermissionAudit.result == "pending_approval",
    ).order_by(PermissionAudit.created_at.desc()).all()
    return [_serialize_audit(a) for a in audits]


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_rule(r: PermissionRule) -> dict:
    return {
        "id": r.id, "project_id": r.project_id,
        "action_pattern": r.action_pattern,
        "permission_level": r.permission_level,
        "category": r.category, "description": r.description,
        "requires_mfa": r.requires_mfa, "is_active": r.is_active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_audit(a: PermissionAudit) -> dict:
    return {
        "id": a.id, "user_id": a.user_id, "project_id": a.project_id,
        "action": a.action, "permission_level": a.permission_level,
        "result": a.result, "rule_id": a.rule_id,
        "approval_status": a.approval_status,
        "approved_by": a.approved_by, "reason": a.reason,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }

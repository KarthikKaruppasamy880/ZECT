"""Zinnia Permissions Protocol — allow/require-approval/never-allowed enforcement."""

import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import PermissionRule, PermissionAudit, CapabilityGrant
from app.infrastructure.auth.deps import get_current_user, CurrentUser
from app.infrastructure.auth.rbac import (
    require_role,
    require_authentication,
    log_audit,
    get_user_from_current_user,
    PermissionDenied,
)
from app.domains.permissions.capability_grants import (
    CAPABILITY_TO_ACTIONS,
    apply_grant_override,
    find_active_grants_for_action,
    serialize_grant,
)

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
    {"action_pattern": "delete_file", "permission_level": "never", "category": "file", "description": "Delete files from workspace — never allowed"},
    {"action_pattern": "companion_desktop_delete", "permission_level": "never", "category": "desktop", "description": "Delete OS desktop files — never allowed"},
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
    # Mentrix Companion — company personal agent
    {"action_pattern": "companion_navigate", "permission_level": "allow", "category": "companion", "description": "Navigate ZECT UI"},
    {"action_pattern": "companion_delivery_status", "permission_level": "allow", "category": "companion", "description": "Read Mentrix Delivery status"},
    {"action_pattern": "companion_lattice_query", "permission_level": "allow", "category": "companion", "description": "Query Lattice graph"},
    {"action_pattern": "companion_research", "permission_level": "allow", "category": "companion", "description": "Research and news fetch"},
    {"action_pattern": "companion_content", "permission_level": "allow", "category": "companion", "description": "Content and ads briefs"},
    {"action_pattern": "companion_report", "permission_level": "allow", "category": "companion", "description": "Draft reports on Mentrix Board"},
    {"action_pattern": "companion_docs_read", "permission_level": "allow", "category": "companion", "description": "Search internal docs"},
    {"action_pattern": "companion_docs_write", "permission_level": "require_approval", "category": "companion", "description": "Publish internal doc drafts"},
    {"action_pattern": "companion_slack_read", "permission_level": "allow", "category": "companion", "description": "Slack channel digest"},
    {"action_pattern": "companion_slack_send", "permission_level": "require_approval", "category": "companion", "description": "Send Slack messages"},
    {"action_pattern": "companion_email_read", "permission_level": "allow", "category": "companion", "description": "Email inbox digest"},
    {"action_pattern": "companion_email_send", "permission_level": "require_approval", "category": "companion", "description": "Send email"},
    {"action_pattern": "companion_image_gen", "permission_level": "require_approval", "category": "companion", "description": "Generate avatar/images from user photo"},
    {"action_pattern": "companion_delivery_start", "permission_level": "require_approval", "category": "companion", "description": "Start Mentrix Delivery run"},
    {"action_pattern": "companion_delivery_approve", "permission_level": "require_approval", "category": "companion", "description": "Approve Mentrix Delivery run"},
    {"action_pattern": "companion_create_pr", "permission_level": "require_approval", "category": "companion", "description": "Create pull request"},
    {"action_pattern": "companion_desktop_read", "permission_level": "require_approval", "category": "desktop", "description": "Read allowlisted desktop paths"},
    {"action_pattern": "companion_desktop_screenshot", "permission_level": "require_approval", "category": "desktop", "description": "Capture screenshot"},
    {"action_pattern": "companion_desktop_write", "permission_level": "require_approval", "category": "desktop", "description": "Write allowlisted Desktop/Documents note files"},
    {"action_pattern": "companion_desktop_delete", "permission_level": "never", "category": "desktop", "description": "Delete OS desktop files — never allowed"},
    {"action_pattern": "companion_computer_open", "permission_level": "require_approval", "category": "desktop", "description": "Open allowlisted apps"},
    {"action_pattern": "companion_computer_control", "permission_level": "require_approval", "category": "desktop", "description": "Computer Mode click/type"},
    {"action_pattern": "companion_diagnose", "permission_level": "allow", "category": "companion", "description": "Diagnose and fix planning"},
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
    subject_type: Optional[str] = None  # user | agent | tool | workspace
    subject_id: Optional[str] = None
    workspace: Optional[str] = None


class CapabilityGrantCreate(BaseModel):
    capability: str
    subject_type: str = "user"
    subject_id: str = ""
    project_id: Optional[int] = None
    permission_level: str = "allow"
    reason: str = ""
    expires_at: datetime  # required — temporary grants only


class ApprovalAction(BaseModel):
    approved: bool
    approved_by: str = "admin"
    reason: str = ""


# ---------------------------------------------------------------------------
# Rules CRUD
# ---------------------------------------------------------------------------

@router.get("/rules")
@require_authentication
def list_rules(
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    permission_level: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
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
@require_role("admin")  # ✅ RBAC: Only admins can create rules
def create_rule(
    data: PermissionRuleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new permission rule (admin only)."""
    if data.permission_level not in ("allow", "require_approval", "never"):
        raise HTTPException(400, "permission_level must be: allow, require_approval, or never")
    rule = PermissionRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # ✅ Audit logging
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="create_permission_rule",
        resource_id=rule.id,
        resource_type="permission_rule",
        details={"action_pattern": rule.action_pattern, "permission_level": rule.permission_level}
    )

    return _serialize_rule(rule)


@router.put("/rules/{rule_id}")
@require_role("admin")  # ✅ RBAC: Only admins can update rules
def update_rule(
    rule_id: int,
    data: PermissionRuleUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a permission rule (admin only)."""
    rule = db.query(PermissionRule).filter(PermissionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(rule, k, v)
    db.commit()
    db.refresh(rule)

    # ✅ Audit logging
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="update_permission_rule",
        resource_id=rule.id,
        resource_type="permission_rule",
        details={"action_pattern": rule.action_pattern, "permission_level": rule.permission_level}
    )

    return _serialize_rule(rule)


@router.delete("/rules/{rule_id}")
@require_role("admin")  # ✅ RBAC: Only admins can delete rules
def delete_rule(
    rule_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a permission rule (admin only)."""
    rule = db.query(PermissionRule).filter(PermissionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.is_active = False
    db.commit()

    # ✅ Audit logging
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="delete_permission_rule",
        resource_id=rule_id,
        resource_type="permission_rule",
        details={"action_pattern": rule.action_pattern}
    )

    return {"status": "deactivated", "id": rule_id}


# ---------------------------------------------------------------------------
# Permission Check — the core enforcement endpoint
# ---------------------------------------------------------------------------

@router.post("/check")
@require_authentication
def check_permission(
    data: PermissionCheck,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if an action is allowed, requires approval, or is blocked."""
    # Prefer authenticated identity when body omits user_id
    if not data.user_id:
        try:
            db_user = get_user_from_current_user(current_user, db)
            if db_user:
                data.user_id = db_user.id
        except Exception:
            pass

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

    grants = find_active_grants_for_action(
        db,
        data.action,
        user_id=data.user_id,
        project_id=data.project_id,
        subject_type=data.subject_type,
        subject_id=data.subject_id or (str(data.user_id) if data.user_id else None),
        workspace=data.workspace,
    )
    result, level, grant = apply_grant_override(result, level, grants)

    # Log the check
    audit = PermissionAudit(
        user_id=data.user_id,
        project_id=data.project_id,
        action=data.action,
        permission_level=level,
        result=result,
        rule_id=matching[0].id if matching else None,
        reason=f"grant:{grant.id}" if grant else "",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    return {
        "action": data.action,
        "result": result,
        "permission_level": level,
        "matching_rules": [_serialize_rule(r) for r in matching],
        "active_grants": [serialize_grant(g) for g in grants],
        "grant_applied": serialize_grant(grant) if grant else None,
        "audit_id": audit.id,
    }


# ---------------------------------------------------------------------------
# Approval Workflow
# ---------------------------------------------------------------------------

@router.post("/audits/{audit_id}/approve")
@require_role("admin", "lead")  # ✅ RBAC: Only admins/leads can approve
def approve_action(
    audit_id: int,
    data: ApprovalAction,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve or reject a pending action (admin/lead only)."""
    audit = db.query(PermissionAudit).filter(PermissionAudit.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit entry not found")
    if audit.result != "pending_approval":
        raise HTTPException(400, "This action is not pending approval")

    audit.approval_status = "approved" if data.approved else "rejected"
    audit.approved_by = data.approved_by or current_user.email
    audit.reason = data.reason
    audit.result = "granted" if data.approved else "denied"
    db.commit()
    db.refresh(audit)

    # ✅ Audit logging
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="approve_action",
        resource_id=audit_id,
        resource_type="permission_audit",
        details={
            "action": audit.action,
            "approval_status": audit.approval_status,
            "reason": audit.reason
        }
    )

    return _serialize_audit(audit)


@router.get("/audits")
@require_authentication
def list_audits(
    project_id: Optional[int] = None,
    result: Optional[str] = None,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
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
@require_authentication
def list_pending_approvals(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    audits = db.query(PermissionAudit).filter(
        PermissionAudit.result == "pending_approval",
    ).order_by(PermissionAudit.created_at.desc()).all()
    return [_serialize_audit(a) for a in audits]


# ---------------------------------------------------------------------------
# Temporary capability grants (Phase 5 Stage B)
# ---------------------------------------------------------------------------

@router.get("/capabilities")
@require_authentication
def list_capability_aliases(current_user: CurrentUser = Depends(get_current_user)):
    """Upgrade.md capability → existing action-pattern map."""
    return {"capabilities": CAPABILITY_TO_ACTIONS}


@router.get("/grants")
@require_authentication
def list_grants(
    project_id: Optional[int] = None,
    active_only: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(CapabilityGrant)
    if project_id is not None:
        q = q.filter(CapabilityGrant.project_id == project_id)
    rows = q.order_by(CapabilityGrant.created_at.desc()).limit(200).all()
    out = [serialize_grant(g) for g in rows]
    if active_only:
        out = [g for g in out if g.get("active")]
    return out


@router.post("/grants")
@require_role("admin", "lead")
def create_grant(
    data: CapabilityGrantCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.permission_level not in ("allow", "require_approval", "never"):
        raise HTTPException(400, "permission_level must be: allow, require_approval, or never")
    if data.subject_type not in ("user", "agent", "tool", "workspace"):
        raise HTTPException(400, "subject_type must be: user, agent, tool, or workspace")
    exp = data.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= datetime.now(timezone.utc):
        raise HTTPException(400, "expires_at must be in the future")

    granter_id = None
    try:
        u = get_user_from_current_user(current_user, db)
        if u:
            granter_id = u.id
    except Exception:
        granter_id = getattr(current_user, "user_id", None)

    subject_id = (data.subject_id or "").strip()
    if data.subject_type == "user" and not subject_id and granter_id:
        subject_id = str(granter_id)

    grant = CapabilityGrant(
        capability=data.capability.strip(),
        subject_type=data.subject_type,
        subject_id=subject_id,
        project_id=data.project_id,
        permission_level=data.permission_level,
        reason=data.reason or "",
        granted_by=granter_id,
        expires_at=exp,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    log_audit(
        db=db,
        user_id=granter_id or 0,
        action="create_capability_grant",
        resource_id=grant.id,
        resource_type="capability_grant",
        details={"capability": grant.capability, "expires_at": exp.isoformat(), "subject_type": grant.subject_type},
    )
    return serialize_grant(grant)


@router.post("/grants/{grant_id}/revoke")
@require_role("admin", "lead")
def revoke_grant(
    grant_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    grant = db.query(CapabilityGrant).filter(CapabilityGrant.id == grant_id).first()
    if not grant:
        raise HTTPException(404, "Grant not found")
    if grant.revoked_at is None:
        grant.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(grant)
    granter_id = getattr(current_user, "user_id", None) or 0
    try:
        u = get_user_from_current_user(current_user, db)
        if u:
            granter_id = u.id
    except Exception:
        pass
    log_audit(
        db=db,
        user_id=granter_id or 0,
        action="revoke_capability_grant",
        resource_id=grant_id,
        resource_type="capability_grant",
        details={"capability": grant.capability},
    )
    return serialize_grant(grant)


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

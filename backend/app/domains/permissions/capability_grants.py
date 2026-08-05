"""Phase 5 Stage B — temporary capability grants + Upgrade.md capability aliases.

Reuses PermissionRule / permission_broker evaluation: an active non-expired grant
can override the baseline rule result for matching actions.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import CapabilityGrant

# Upgrade.md capability names → existing PermissionRule / broker action patterns
CAPABILITY_TO_ACTIONS: dict[str, list[str]] = {
    "repository:read": ["read_file", "search_code", "companion_docs_read", "companion_lattice_query"],
    "repository:search": ["search_code", "companion_docs_read"],
    "repository:edit_workspace": ["write_memory", "companion_notes_write"],
    "branch:push": ["create_branch", "companion_create_pr"],
    "pull_request:create": ["draft_pr", "companion_create_pr"],
    "pull_request:merge": ["merge_pr"],
    "deploy:execute": ["deploy_.*"],
    "desktop:view": ["companion_desktop_read", "companion_desktop_screenshot", "companion_computer_inspect"],
    "desktop:control": ["companion_computer_control", "companion_computer_open", "companion_desktop_write"],
    "filesystem:scan": ["search_code", "companion_desktop_read"],
    "filesystem:move": ["companion_desktop_write"],
    "email:read": ["companion_email_read"],
    "email:draft": ["companion_email_send"],
    "email:send": ["companion_email_send"],
    "slack:read": ["companion_slack_read"],
    "slack:send": ["companion_slack_send"],
    "jira:read": ["companion_jira_read"],
    "jira:create": ["companion_jira_write"],
    "jira:update": ["companion_jira_write"],
    "security:read_alert": ["companion_security_scan"],
    "security:collect_evidence": ["companion_security_scan"],
    # Phase 9 capabilities listed for mapping only — default rules should keep them never/require_approval
    "security:contain_endpoint": ["companion_security_contain"],
    "secret:use_reference": ["access_secrets", "secret:use_reference"],
}


def capabilities_covering_action(action: str) -> set[str]:
    """Return Upgrade capability names (plus raw action) that cover this action."""
    out: set[str] = {action}
    for cap, patterns in CAPABILITY_TO_ACTIONS.items():
        for pat in patterns:
            try:
                if re.fullmatch(pat, action):
                    out.add(cap)
                    break
            except re.error:
                if pat == action:
                    out.add(cap)
                    break
    return out


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_grant_active(grant: CapabilityGrant, *, now: datetime | None = None) -> bool:
    now = _normalize_dt(now) or _utcnow()
    if grant.revoked_at is not None:
        return False
    exp = _normalize_dt(grant.expires_at)
    if exp is None or exp <= now:
        return False
    return True


def _subject_matches(
    grant: CapabilityGrant,
    *,
    user_id: int | None,
    subject_type: str | None,
    subject_id: str | None,
    workspace: str | None,
) -> bool:
    st = (grant.subject_type or "user").lower()
    sid = (grant.subject_id or "").strip()

    if st == "user":
        if user_id is None:
            return False
        return sid == "" or sid == str(user_id)
    if st == "workspace":
        if not workspace:
            return False
        return sid == "" or sid == workspace
    if st in ("agent", "tool"):
        if subject_type and subject_type.lower() != st:
            # still allow if subject_id matches explicitly
            pass
        want = (subject_id or "").strip()
        if not want:
            return False
        return sid == "" or sid == want
    # Unknown subject_type: require exact id match when provided
    if subject_id is not None:
        return sid == str(subject_id)
    return False


def find_active_grants_for_action(
    db: Session,
    action: str,
    *,
    user_id: int | None = None,
    project_id: int | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    workspace: str | None = None,
    now: datetime | None = None,
) -> list[CapabilityGrant]:
    now = _normalize_dt(now) or _utcnow()
    caps = capabilities_covering_action(action)
    rows = db.query(CapabilityGrant).filter(CapabilityGrant.revoked_at.is_(None)).all()
    matched: list[CapabilityGrant] = []
    for g in rows:
        if not is_grant_active(g, now=now):
            continue
        if g.project_id is not None and project_id is not None and g.project_id != project_id:
            continue
        if g.project_id is not None and project_id is None:
            continue
        if g.capability not in caps and g.capability != action:
            # Also allow grant.capability to be a regex/action pattern matching the action
            try:
                if not re.fullmatch(g.capability, action):
                    continue
            except re.error:
                continue
        if not _subject_matches(
            g,
            user_id=user_id,
            subject_type=subject_type,
            subject_id=subject_id,
            workspace=workspace,
        ):
            continue
        matched.append(g)
    return matched


def apply_grant_override(
    baseline_result: str,
    baseline_level: str,
    grants: list[CapabilityGrant],
) -> tuple[str, str, CapabilityGrant | None]:
    """Active grants override baseline. Most restrictive grant wins among grants;
    but an `allow` grant upgrades require_approval → granted. `never` grant always denies.
    """
    if not grants:
        return baseline_result, baseline_level, None

    levels = [g.permission_level for g in grants]
    if "never" in levels:
        chosen = next(g for g in grants if g.permission_level == "never")
        return "denied", "never", chosen
    if "require_approval" in levels and "allow" not in levels:
        chosen = next(g for g in grants if g.permission_level == "require_approval")
        return "pending_approval", "require_approval", chosen
    if "allow" in levels:
        chosen = next(g for g in grants if g.permission_level == "allow")
        # Temporary allow overrides baseline deny/pending (except we already handled never grants)
        if baseline_level == "never" and chosen.permission_level == "allow":
            # Explicit temporary allow can open a normally-never action (admin-issued)
            return "granted", "allow", chosen
        return "granted", "allow", chosen
    return baseline_result, baseline_level, None


def serialize_grant(g: CapabilityGrant) -> dict[str, Any]:
    return {
        "id": g.id,
        "capability": g.capability,
        "subject_type": g.subject_type,
        "subject_id": g.subject_id,
        "project_id": g.project_id,
        "permission_level": g.permission_level,
        "reason": g.reason or "",
        "granted_by": g.granted_by,
        "expires_at": g.expires_at.isoformat() if g.expires_at else None,
        "revoked_at": g.revoked_at.isoformat() if g.revoked_at else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "active": is_grant_active(g),
        "covers_actions": CAPABILITY_TO_ACTIONS.get(g.capability, [g.capability]),
    }

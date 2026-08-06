"""Mentrix Companion permission broker — gates every tool via Permissions Protocol."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import PermissionAudit, PermissionRule
from app.domains.audit.audit_trail import log_audit
from app.domains.permissions.capability_grants import (
    apply_grant_override,
    find_active_grants_for_action,
)

# Companion tool → permission action mapping
TOOL_ACTIONS: dict[str, str] = {
    "navigate": "companion_navigate",
    "go_back": "companion_navigate",
    "delivery_status": "companion_delivery_status",
    "lattice_query": "companion_lattice_query",
    "research_news": "companion_research",
    "summarize_topic": "companion_research",
    "weather_report": "companion_weather",
    "content_brief": "companion_content",
    "ads_copy": "companion_content",
    "report_draft": "companion_report",
    "docs_search": "companion_docs_read",
    "docs_draft": "companion_docs_write",
    "slack_digest": "companion_slack_read",
    "slack_send": "companion_slack_send",
    "email_digest": "companion_email_read",
    "email_send": "companion_email_send",
    "image_avatar": "companion_image_gen",
    "media_generate": "companion_image_gen",
    "media_edit": "companion_image_gen",
    "media_list": "companion_image_list",
    "start_delivery": "companion_delivery_start",
    "approve_delivery": "companion_delivery_approve",
    "create_pr": "companion_create_pr",
    "desktop_read": "companion_desktop_read",
    "desktop_screenshot": "companion_desktop_screenshot",
    "desktop_write_note": "companion_desktop_write",
    "desktop_delete": "companion_desktop_delete",
    "desktop_open_presentation": "companion_computer_open",
    "computer_open_app": "companion_computer_open",
    "computer_click": "companion_computer_control",
    "computer_type": "companion_computer_control",
    "browser_navigate": "companion_browser",
    "browser_snapshot": "companion_browser",
    "browser_fill": "companion_browser",
    "computer_scroll": "companion_computer_control",
    "computer_ui_inspect": "companion_computer_inspect",
    "diagnose_fix": "companion_diagnose",
    "note_add": "companion_notes_write",
    "note_list": "companion_notes_read",
    "jira_get_issue": "companion_jira_read",
    "jira_search_incidents": "companion_jira_read",
    "datadog_query_logs": "companion_datadog_read",
    "jira_comment_pr": "companion_jira_write",
    "scan_for_anomalies": "companion_security_scan",
    "file_security_ticket": "companion_jira_write",
}

ALWAYS_CONFIRM_TOOLS = {
    "slack_send",
    "email_send",
    "docs_draft",
    "image_avatar",
    "media_generate",
    "media_edit",
    "start_delivery",
    "approve_delivery",
    "create_pr",
    "desktop_read",
    "desktop_screenshot",
    "desktop_write_note",
    "desktop_open_presentation",
    "computer_open_app",
    "computer_click",
    "computer_type",
    "computer_scroll",
    "computer_ui_inspect",
    "jira_comment_pr",
    "file_security_ticket",
    "browser_navigate",
    "browser_snapshot",
    "browser_fill",
}


def check_tool_permission(
    db: Session,
    tool_name: str,
    *,
    user_id: int | None = None,
    project_id: int | None = None,
    user_confirmed: bool = False,
) -> dict[str, Any]:
    """Return {result, action, needs_confirm, audit_id, permission_level}."""
    action = TOOL_ACTIONS.get(tool_name, f"companion_{tool_name}")
    rules = (
        db.query(PermissionRule)
        .filter(PermissionRule.is_active == True)  # noqa: E712
        .all()
    )
    matching: list[PermissionRule] = []
    for rule in rules:
        if rule.project_id is not None and rule.project_id != project_id:
            continue
        try:
            if re.fullmatch(rule.action_pattern, action):
                matching.append(rule)
        except re.error:
            if rule.action_pattern == action:
                matching.append(rule)

    if not matching:
        result, level = "granted", "allow"
    else:
        levels = [r.permission_level for r in matching]
        if "never" in levels:
            result, level = "denied", "never"
        elif "require_approval" in levels:
            result, level = "pending_approval", "require_approval"
        else:
            result, level = "granted", "allow"

    grants = find_active_grants_for_action(
        db,
        action,
        user_id=user_id,
        project_id=project_id,
        subject_type="user" if user_id else "agent",
        subject_id=str(user_id) if user_id else "mentrix",
    )
    result, level, grant = apply_grant_override(result, level, grants)

    needs_confirm = tool_name in ALWAYS_CONFIRM_TOOLS or result == "pending_approval"
    if needs_confirm and user_confirmed and result == "pending_approval":
        result = "granted"
    elif needs_confirm and user_confirmed and result == "granted":
        pass
    elif needs_confirm and not user_confirmed and result != "denied":
        result = "pending_approval"

    audit = PermissionAudit(
        user_id=user_id,
        project_id=project_id,
        action=action,
        permission_level=level,
        result=result,
        rule_id=matching[0].id if matching else None,
        reason=f"grant:{grant.id}" if grant else "",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    return {
        "tool": tool_name,
        "action": action,
        "result": result,
        "permission_level": level,
        "needs_confirm": needs_confirm and not user_confirmed and result != "denied",
        "audit_id": audit.id,
        "grant_id": grant.id if grant else None,
    }


def log_mentrix_tool(
    db: Session,
    tool_name: str,
    *,
    args: dict | None = None,
    result: str = "ok",
    user_id: int | None = None,
) -> None:
    from app.security.redact import redact_mapping

    redacted = redact_mapping(args or {})
    log_audit(
        db,
        action=f"mentrix_tool_{tool_name}",
        resource_type="mentrix_companion",
        resource_name=tool_name,
        details=json.dumps({"args": redacted, "result": result})[:4000],
        user_id=user_id,
    )

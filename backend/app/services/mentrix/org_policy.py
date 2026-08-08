"""Org policy pack — shareable Mentrix Companion rules for company installs."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import PermissionRule

POLICY_VERSION = 1

COMPANION_SEED_RULES = [
    {"action_pattern": "companion_navigate", "permission_level": "allow", "category": "companion", "description": "Navigate ZECT UI"},
    {"action_pattern": "companion_delivery_status", "permission_level": "allow", "category": "companion", "description": "Read Mentrix Delivery status"},
    {"action_pattern": "companion_lattice_query", "permission_level": "allow", "category": "companion", "description": "Query Lattice graph"},
    {"action_pattern": "companion_research", "permission_level": "allow", "category": "companion", "description": "Research and news fetch"},
    {"action_pattern": "companion_weather", "permission_level": "allow", "category": "companion", "description": "Mentrix weather report (Open-Meteo)"},
    {"action_pattern": "companion_content", "permission_level": "allow", "category": "companion", "description": "Content and ads briefs"},
    {"action_pattern": "companion_report", "permission_level": "allow", "category": "companion", "description": "Draft reports on Mentrix Board"},
    {"action_pattern": "companion_docs_read", "permission_level": "allow", "category": "companion", "description": "Search internal docs"},
    {"action_pattern": "companion_docs_write", "permission_level": "require_approval", "category": "companion", "description": "Publish internal doc drafts"},
    {"action_pattern": "companion_slack_read", "permission_level": "allow", "category": "companion", "description": "Slack channel digest"},
    {"action_pattern": "companion_slack_send", "permission_level": "require_approval", "category": "companion", "description": "Send Slack messages"},
    {"action_pattern": "companion_email_read", "permission_level": "allow", "category": "companion", "description": "Email inbox digest"},
    {"action_pattern": "companion_email_send", "permission_level": "require_approval", "category": "companion", "description": "Send email"},
    {"action_pattern": "companion_image_gen", "permission_level": "require_approval", "category": "companion", "description": "Generate Mentrix images/thumbnails"},
    {"action_pattern": "companion_image_list", "permission_level": "allow", "category": "companion", "description": "List Mentrix Image board"},
    {"action_pattern": "companion_delivery_start", "permission_level": "require_approval", "category": "companion", "description": "Start Mentrix Delivery run"},
    {"action_pattern": "companion_delivery_approve", "permission_level": "require_approval", "category": "companion", "description": "Approve Mentrix Delivery run"},
    {"action_pattern": "companion_create_pr", "permission_level": "require_approval", "category": "companion", "description": "Create pull request"},
    {"action_pattern": "companion_desktop_read", "permission_level": "require_approval", "category": "desktop", "description": "Read allowlisted desktop paths"},
    {"action_pattern": "companion_desktop_screenshot", "permission_level": "require_approval", "category": "desktop", "description": "Capture screenshot"},
    {"action_pattern": "companion_desktop_write", "permission_level": "require_approval", "category": "desktop", "description": "Write allowlisted Desktop/Documents note files"},
    {"action_pattern": "companion_desktop_delete", "permission_level": "never", "category": "desktop", "description": "Delete OS desktop files — never allowed"},
    {"action_pattern": "companion_computer_open", "permission_level": "require_approval", "category": "desktop", "description": "Open allowlisted apps"},
    {"action_pattern": "companion_computer_control", "permission_level": "require_approval", "category": "desktop", "description": "Computer Mode click/type/scroll"},
    {"action_pattern": "companion_computer_inspect", "permission_level": "require_approval", "category": "desktop", "description": "Computer Mode UI inspect"},
    {"action_pattern": "companion_diagnose", "permission_level": "allow", "category": "companion", "description": "Diagnose and fix planning"},
    {"action_pattern": "companion_notes_read", "permission_level": "allow", "category": "companion", "description": "List Mentrix notes"},
    {"action_pattern": "companion_notes_write", "permission_level": "allow", "category": "companion", "description": "Add Mentrix notes"},
    {"action_pattern": "companion_jira_read", "permission_level": "allow", "category": "companion", "description": "Read Jira issues and search incidents"},
    {"action_pattern": "companion_jira_write", "permission_level": "require_approval", "category": "companion", "description": "Comment on Jira issues (e.g. PR link)"},
    {"action_pattern": "companion_datadog_read", "permission_level": "allow", "category": "companion", "description": "Query Datadog logs for incidents"},
    {"action_pattern": "delete_file", "permission_level": "never", "category": "file", "description": "Delete files from workspace — never allowed"},
]


def ensure_companion_rules(db: Session) -> int:
    """Idempotently seed Mentrix Companion permission rules."""
    added = 0
    for d in COMPANION_SEED_RULES:
        exists = (
            db.query(PermissionRule)
            .filter(PermissionRule.action_pattern == d["action_pattern"])
            .first()
        )
        if exists:
            continue
        db.add(PermissionRule(**d, is_active=True))
        added += 1
    if added:
        db.commit()
    return added


# Default allowlisted apps / folders for Computer Mode (Windows)
DEFAULT_DESKTOP_POLICY = {
    "computer_mode_default": False,
    "max_tier": 4,
    "allowlisted_apps_windows": [
        "notepad.exe",
        "notepad++.exe",
        "code.exe",
        "explorer.exe",
        "msedge.exe",
        "chrome.exe",
        "calc.exe",
        "Slack.exe",
        "POWERPNT.EXE",
        "Zoom.exe",
        "outlook.exe",
        "ms-teams.exe",
        "teams.exe",
    ],
    "allowlisted_apps_macos": [
        "TextEdit",
        "Finder",
        "Safari",
        "Google Chrome",
        "Visual Studio Code",
        "Calculator",
        "Microsoft PowerPoint",
        "zoom.us",
        "Notepad++",
    ],
    "allowlisted_apps": [
        "notepad.exe",
        "notepad++.exe",
        "code.exe",
        "explorer.exe",
        "msedge.exe",
        "chrome.exe",
        "Slack.exe",
        "POWERPNT.EXE",
        "Zoom.exe",
        "outlook.exe",
        "ms-teams.exe",
    ],
    "allowlisted_folders": [],
    "deny_globs": ["**/.env", "**/.env.*", "**/id_rsa", "**/*.pem", "**/credentials*"],
    "enabled_connectors": ["slack", "email", "news", "confluence"],
}


def export_org_policy(db: Session) -> dict[str, Any]:
    rules = (
        db.query(PermissionRule)
        .filter(PermissionRule.is_active == True)  # noqa: E712
        .all()
    )
    return {
        "version": POLICY_VERSION,
        "agent": "Mentrix",
        "desktop": DEFAULT_DESKTOP_POLICY,
        "rules": [
            {
                "action_pattern": r.action_pattern,
                "permission_level": r.permission_level,
                "category": r.category,
                "description": r.description or "",
                "requires_mfa": bool(r.requires_mfa),
            }
            for r in rules
        ],
    }


def import_org_policy(db: Session, pack: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
    if not isinstance(pack, dict) or pack.get("agent") not in (None, "Mentrix"):
        raise ValueError("Invalid Mentrix org policy pack")
    rules_in = pack.get("rules") or []
    if replace:
        for r in db.query(PermissionRule).all():
            r.is_active = False
        db.commit()
    created = 0
    for d in rules_in:
        pattern = d.get("action_pattern")
        level = d.get("permission_level")
        if not pattern or level not in ("allow", "require_approval", "never"):
            continue
        existing = (
            db.query(PermissionRule)
            .filter(PermissionRule.action_pattern == pattern, PermissionRule.is_active == True)  # noqa: E712
            .first()
        )
        if existing:
            existing.permission_level = level
            existing.category = d.get("category") or existing.category
            existing.description = d.get("description") or existing.description
        else:
            db.add(
                PermissionRule(
                    action_pattern=pattern,
                    permission_level=level,
                    category=d.get("category") or "companion",
                    description=d.get("description") or "",
                    requires_mfa=bool(d.get("requires_mfa")),
                    is_active=True,
                )
            )
            created += 1
    db.commit()
    desktop = {**DEFAULT_DESKTOP_POLICY, **(pack.get("desktop") or {})}
    return {"imported_rules": len(rules_in), "created": created, "desktop": desktop}


def policy_json_dumps(pack: dict) -> str:
    return json.dumps(pack, indent=2)

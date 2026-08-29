"""PA-9 skill manifest governance — validate and enforce declared contracts."""

from __future__ import annotations

from typing import Any


REQUIRED_MANIFEST_KEYS = (
    "allowed_tools",
    "prohibited_ops",
    "approval_points",
)

DEFAULT_PROHIBITED = (
    "delete",
    "desktop_delete",
    "delete_file",
    "empty_trash",
    "rmdir",
    "unlink",
)


def normalize_manifest(raw: dict[str, Any] | None, *, skill_row: Any = None) -> dict[str, Any]:
    m = dict(raw or {})
    allowed_tools = m.get("allowed_tools")
    if not isinstance(allowed_tools, list):
        allowed_tools = list(getattr(skill_row, "allowed_tools", None) or [])
    prohibited = m.get("prohibited_ops")
    if not isinstance(prohibited, list) or not prohibited:
        prohibited = list(DEFAULT_PROHIBITED)
    approval_points = m.get("approval_points")
    if not isinstance(approval_points, list):
        approval_points = ["before_side_effect"] if getattr(skill_row, "approval_required", True) else []
    resources = m.get("allowed_resources")
    if not isinstance(resources, list):
        resources = []
    retry = m.get("retry_policy") if isinstance(m.get("retry_policy"), dict) else {
        "max_attempts": 1,
        "backoff_seconds": 0,
    }
    verification = m.get("verification") if isinstance(m.get("verification"), dict) else {
        "require_provider_id": False,
        "require_hash": False,
    }
    return {
        "allowed_tools": [str(t) for t in allowed_tools],
        "prohibited_ops": [str(t) for t in prohibited],
        "approval_points": [str(t) for t in approval_points],
        "allowed_resources": [str(t) for t in resources],
        "retry_policy": retry,
        "verification": verification,
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            errors.append(f"missing:{key}")
    for op in DEFAULT_PROHIBITED:
        if op not in (manifest.get("prohibited_ops") or []):
            errors.append(f"must_prohibit:{op}")
    return errors


def tool_allowed(manifest: dict[str, Any], tool_name: str) -> tuple[bool, str]:
    name = (tool_name or "").strip()
    prohibited = set(manifest.get("prohibited_ops") or [])
    if name in prohibited or any(p in name for p in ("delete", "unlink", "rmdir")):
        return False, "prohibited_op"
    allowed = manifest.get("allowed_tools") or []
    if allowed and name not in allowed and "*" not in allowed:
        return False, "tool_not_in_allowed_tools"
    return True, "ok"


def schedule_grants_from_config(task_config: dict[str, Any] | None) -> dict[str, Any]:
    """PA-9: schedules carry separate limited grants inside task_config.grants."""
    cfg = task_config or {}
    grants = cfg.get("grants") if isinstance(cfg.get("grants"), dict) else {}
    return {
        "allowed_tools": list(grants.get("allowed_tools") or cfg.get("allowed_tools") or []),
        "allowed_resources": list(grants.get("allowed_resources") or []),
        "max_side_effects": int(grants.get("max_side_effects") or 1),
        "require_approval": bool(grants.get("require_approval", True)),
    }


def schedule_tool_permitted(grants: dict[str, Any], tool_name: str) -> tuple[bool, str]:
    name = (tool_name or "").strip()
    if "delete" in name:
        return False, "schedule_delete_forbidden"
    allowed = grants.get("allowed_tools") or []
    if allowed and name not in allowed and "*" not in allowed:
        return False, "schedule_tool_not_granted"
    return True, "ok"

"""Single authoritative deck quality verdict across inspector, plan critic, document critic."""

from __future__ import annotations

from typing import Any


def _status(row: dict[str, Any] | None) -> str:
    if not row or not isinstance(row, dict):
        return ""
    return str(
        row.get("final_quality_status")
        or row.get("deck_status")
        or row.get("status")
        or ""
    ).upper()


def unified_quality_verdict(
    *,
    inspector: dict[str, Any] | None = None,
    plan_critic: dict[str, Any] | None = None,
    document_critic: dict[str, Any] | None = None,
) -> str:
    statuses = [_status(inspector), _status(plan_critic), _status(document_critic)]
    statuses = [s for s in statuses if s]
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s in {"NEEDS_REVIEW", "REPAIRABLE", "DEGRADED_PASS"} for s in statuses):
        return "NEEDS_REVIEW"
    return "PASS"


def merge_quality_reports(
    *,
    inspector: dict[str, Any] | None = None,
    plan_critic: dict[str, Any] | None = None,
    document_critic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verdict = unified_quality_verdict(
        inspector=inspector,
        plan_critic=plan_critic,
        document_critic=document_critic,
    )
    hard: list[str] = []
    for row in (inspector, plan_critic, document_critic):
        if not row:
            continue
        for item in list(row.get("hard_findings") or []):
            if item and item not in hard:
                hard.append(str(item))
        if _status(row) == "FAIL" and "quality_critic_fail" not in hard:
            if row is document_critic or row is plan_critic:
                hard.append("quality_critic_fail")
    blocked = verdict == "FAIL" or bool(hard) or bool((inspector or {}).get("export_blocked"))
    return {
        "final_quality_status": verdict,
        "export_blocked": blocked,
        "hard_blocked": blocked,
        "hard_findings": hard,
        "quality_passed": verdict == "PASS",
        "subchecks": {
            "inspector": _status(inspector) or "n/a",
            "plan_critic": _status(plan_critic) or "n/a",
            "document_critic": _status(document_critic) or "n/a",
        },
    }


__all__ = ["merge_quality_reports", "unified_quality_verdict"]

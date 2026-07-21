"""Shared Mentrix gate approve / create-pr policy (no DB imports)."""

from __future__ import annotations

from typing import Any


def gates_allow_approve(gates: dict[str, Any], acknowledge: bool = False) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if gates.get("security_critical"):
        blockers.append("security_critical=true (never waive — human must fix)")
    if not gates.get("lint_ok"):
        blockers.append("lint_ok=false")
    if not gates.get("sandbox_ready") and not acknowledge:
        blockers.append("sandbox_ready=false (set acknowledge_issues to override)")
    if not gates.get("review_ok") and not acknowledge:
        blockers.append("review_ok=false / Mentrix Ultra Review critical (set acknowledge_issues to override)")
    if gates.get("incomplete_ok") is False:
        blockers.append("incomplete_ok=false (refuse incomplete files)")
    if gates.get("grounding_ok") is False:
        blockers.append("grounding_ok=false (invented API — refuse)")
    if gates.get("contract_ok") is False:
        blockers.append("contract_ok=false (design contract — refuse)")
    if gates.get("acceptance_ok") is False:
        blockers.append("acceptance_ok=false (criteria unsatisfied — refuse)")
    if gates.get("api_eval_ok") is False and not acknowledge:
        blockers.append("api_eval_ok=false (set acknowledge_issues to override)")
    if gates.get("rejected_files"):
        blockers.append(f"rejected_files={gates.get('rejected_files')}")
    if int(gates.get("ultra_review_critical") or 0) > 0 and not acknowledge:
        if "review_ok=false" not in " ".join(blockers):
            blockers.append("Mentrix Ultra Review critical findings block approve")
    return len(blockers) == 0, blockers


def gates_allow_create_pr(gates: dict[str, Any]) -> tuple[bool, list[str]]:
    """Hard completion — no acknowledge override at create-pr time."""
    return gates_allow_approve(gates, acknowledge=False)

"""Ultra Review closed-loop finding router — 6-class routing + MERGE_ELIGIBLE gates.

Reuses Phase-4 ReviewFindingSpec; does not replace Ultra Review / ForgeLoop engines.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RouteClass(str, Enum):
    LOCAL_FIX = "LOCAL_FIX"
    TEST_GAP = "TEST_GAP"
    SECURITY = "SECURITY"
    PLAN_REVISION = "PLAN_REVISION"
    SCOPE_CHANGE = "SCOPE_CHANGE"
    ARCHITECTURE_CHANGE = "ARCHITECTURE_CHANGE"


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"  # model suspicion only
    VERIFIED = "VERIFIED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INVALIDATED = "INVALIDATED"


class ClosedLoopFinding(BaseModel):
    finding_id: str
    run_id: str = ""
    work_item_id: int | None = None
    pr_id: str | None = None
    repository_id: int | None = None
    commit_sha: str = ""
    severity: Severity = Severity.MEDIUM
    category: str = "code_quality"
    file: str | None = None
    line: int | None = None
    claim: str = ""
    evidence: str = ""
    requirement_id: str | None = None
    security_policy_id: str | None = None
    plan_impact: bool = False
    architecture_impact: bool = False
    recommended_action: RouteClass = RouteClass.LOCAL_FIX
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    created_at: str = ""
    resolved_at: str | None = None
    title: str = ""
    fingerprint: str = ""
    blocks_ship: bool = False
    merge_eligible: bool = True


_SECURITY_RE = re.compile(
    r"\b(auth\s*bypass|idor|ssrf|path\s*traversal|command\s*injection|secret|api[_ ]?key|"
    r"password|token\s*leak|prompt[- ]injection|sql\s*injection|xss|rce|privilege\s*escalat)\b",
    re.I,
)
_TEST_GAP_RE = re.compile(r"\b(missing\s*test|no\s*test|untested|test\s*coverage|add\s*a\s*test)\b", re.I)
_PLAN_RE = re.compile(r"\b(plan\s*revision|violates\s*plan|out\s*of\s*plan|requirements?\s*mismatch)\b", re.I)
_SCOPE_RE = re.compile(r"\b(scope\s*creep|out\s*of\s*scope|scope\s*change|expand(?:s|ed)?\s*scope)\b", re.I)
_ARCH_RE = re.compile(
    r"\b(architecture|redesign|new\s*service|cross[- ]cutting|blueprint\s*change|schema\s*migration)\b",
    re.I,
)


def _norm_severity(raw: str | None) -> Severity:
    s = (raw or "medium").strip().upper()
    aliases = {
        "INFO": Severity.INFO,
        "LOW": Severity.LOW,
        "MEDIUM": Severity.MEDIUM,
        "MED": Severity.MEDIUM,
        "HIGH": Severity.HIGH,
        "CRITICAL": Severity.CRITICAL,
        "CRIT": Severity.CRITICAL,
    }
    return aliases.get(s, Severity.MEDIUM)


def classify_finding(raw: dict[str, Any]) -> RouteClass:
    """Map a review finding dict → canonical route class (deterministic heuristics)."""
    blob = " ".join(
        str(raw.get(k) or "")
        for k in ("title", "claim", "description", "explanation", "category", "message", "suggested_fix", "evidence")
    )
    cat = str(raw.get("category") or "").lower()
    if cat in ("security", "secrets", "vulnerability") or _SECURITY_RE.search(blob):
        return RouteClass.SECURITY
    if raw.get("architecture_impact") or _ARCH_RE.search(blob):
        return RouteClass.ARCHITECTURE_CHANGE
    if raw.get("plan_impact") or _PLAN_RE.search(blob):
        return RouteClass.PLAN_REVISION
    if _SCOPE_RE.search(blob):
        return RouteClass.SCOPE_CHANGE
    if cat in ("test", "testing", "coverage") or _TEST_GAP_RE.search(blob):
        return RouteClass.TEST_GAP
    return RouteClass.LOCAL_FIX


def normalize_closed_loop_finding(
    raw: dict[str, Any],
    *,
    run_id: str = "",
    work_item_id: int | None = None,
    pr_id: str | None = None,
    repository_id: int | None = None,
    commit_sha: str = "",
) -> ClosedLoopFinding:
    title = str(raw.get("title") or raw.get("message") or "")[:200]
    claim = str(raw.get("claim") or raw.get("explanation") or raw.get("description") or title)
    evidence = str(raw.get("evidence") or raw.get("code_snippet") or "")
    file_path = raw.get("file") or raw.get("file_path")
    line = raw.get("line") or raw.get("start_line") or raw.get("line_start")
    route = classify_finding(raw)
    sev = _norm_severity(raw.get("severity"))
    verified = bool(raw.get("is_verified") or raw.get("verification_status") in ("verified", "VERIFIED", "validated"))
    line_int: int | None = None
    if isinstance(line, int):
        line_int = line
    elif line is not None and str(line).isdigit():
        line_int = int(line)
    fp = raw.get("fingerprint") or hashlib.sha256(
        f"{route.value}|{file_path}|{line_int}|{title}".encode()
    ).hexdigest()[:32]
    now = datetime.now(timezone.utc).isoformat()
    security_suspicion = route == RouteClass.SECURITY and sev in (Severity.HIGH, Severity.CRITICAL)
    blocks = security_suspicion
    return ClosedLoopFinding(
        finding_id=str(raw.get("finding_id") or raw.get("id") or f"f-{uuid.uuid4().hex[:12]}"),
        run_id=run_id,
        work_item_id=work_item_id,
        pr_id=pr_id,
        repository_id=repository_id,
        commit_sha=commit_sha or str(raw.get("commit_sha") or ""),
        severity=sev,
        category=str(raw.get("category") or "code_quality"),
        file=str(file_path) if file_path else None,
        line=line_int,
        claim=claim,
        evidence=evidence,
        requirement_id=raw.get("requirement_id"),
        security_policy_id=raw.get("security_policy_id") or ("SEC-BLOCK" if route == RouteClass.SECURITY else None),
        plan_impact=route in (RouteClass.PLAN_REVISION, RouteClass.SCOPE_CHANGE, RouteClass.ARCHITECTURE_CHANGE),
        architecture_impact=route == RouteClass.ARCHITECTURE_CHANGE,
        recommended_action=route,
        verification_status=VerificationStatus.VERIFIED if verified else VerificationStatus.UNVERIFIED,
        created_at=str(raw.get("created_at") or now),
        resolved_at=raw.get("resolved_at"),
        title=title,
        fingerprint=fp,
        blocks_ship=blocks,
        merge_eligible=not blocks,
    )


def _counts(findings: list[ClosedLoopFinding]) -> dict[str, int]:
    out: dict[str, int] = {r.value: 0 for r in RouteClass}
    for f in findings:
        out[f.recommended_action.value] = out.get(f.recommended_action.value, 0) + 1
    return out


def gate_from_findings(findings: list[ClosedLoopFinding]) -> dict[str, Any]:
    """Compute READY_TO_SHIP / MERGE_ELIGIBLE from classified findings."""
    active = [
        f
        for f in findings
        if f.verification_status
        not in (
            VerificationStatus.RESOLVED,
            VerificationStatus.FALSE_POSITIVE,
            VerificationStatus.INVALIDATED,
        )
    ]
    security_blockers = [
        f
        for f in active
        if f.recommended_action == RouteClass.SECURITY
        and f.severity in (Severity.HIGH, Severity.CRITICAL)
    ]
    needs_plan = any(
        f.recommended_action
        in (RouteClass.PLAN_REVISION, RouteClass.SCOPE_CHANGE, RouteClass.ARCHITECTURE_CHANGE)
        and f.verification_status == VerificationStatus.VERIFIED
        for f in active
    )
    unresolved_high = [
        f
        for f in active
        if f.verification_status == VerificationStatus.VERIFIED
        and f.severity in (Severity.HIGH, Severity.CRITICAL)
    ]

    merge_eligible = len(security_blockers) == 0 and not needs_plan
    ready_to_ship = merge_eligible and len(unresolved_high) == 0

    return {
        "READY_TO_SHIP": ready_to_ship,
        "MERGE_ELIGIBLE": merge_eligible,
        "security_blockers": [f.finding_id for f in security_blockers],
        "needs_plan_revision": needs_plan,
        "open_blocking_count": len(security_blockers),
        "routing_counts": _counts(findings),
        "unresolved_high_critical": [f.finding_id for f in unresolved_high],
    }


def route_target(route: RouteClass) -> dict[str, Any]:
    """Which existing agent should handle this route (reuse, do not invent new agents)."""
    if route == RouteClass.LOCAL_FIX:
        return {"agent": "coding_agent", "then": "test_agent", "planner": False}
    if route == RouteClass.TEST_GAP:
        return {"agent": "test_agent", "then": "coding_agent", "planner": False}
    if route == RouteClass.SECURITY:
        return {
            "agent": "permission_security_gate",
            "then": "coding_agent_or_planner",
            "planner": "if_design_change",
            "force": {"READY_TO_SHIP": False, "MERGE_ELIGIBLE": False},
        }
    if route == RouteClass.PLAN_REVISION:
        return {"agent": "planner", "then": "human_approval", "planner": True}
    if route == RouteClass.SCOPE_CHANGE:
        return {"agent": "planner", "then": "human_approval", "planner": True}
    return {"agent": "planner", "then": "blueprint_review", "planner": True}

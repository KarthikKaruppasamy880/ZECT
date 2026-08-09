"""Ultra Review 3-lane merger — classifies existing findings (no second LLM engine)."""

from __future__ import annotations

from typing import Any


_REQ = ("requirement", "acceptance", "spec", "story", "ac ", "traceab")
_SEC = ("security", "auth", "secret", "xss", "injection", "csrf", "crypto", "permission", "vulnerability")
_ENG = ("bug", "code", "lint", "type", "perf", "performance", "refactor", "test", "api", "error")


def _lane_for_finding(finding: dict[str, Any]) -> str:
    blob = " ".join(
        str(finding.get(k) or "")
        for k in ("category", "severity", "title", "message", "claim", "rule_id", "type")
    ).lower()
    if any(t in blob for t in _SEC):
        return "security"
    if any(t in blob for t in _REQ):
        return "requirements"
    if any(t in blob for t in _ENG):
        return "engineering"
    # default engineering for code review findings
    return "engineering"


def merge_ultrareview_lanes(findings: list[dict[str, Any]]) -> dict[str, Any]:
    lanes = {
        "requirements": [],
        "engineering": [],
        "security": [],
    }
    for f in findings:
        lane = _lane_for_finding(f if isinstance(f, dict) else {})
        item = dict(f) if isinstance(f, dict) else {"raw": f}
        item["lane"] = lane
        item.setdefault("verification_status", item.get("verification_status") or "unverified")
        lanes[lane].append(item)
    return {
        "engine": "review_service",
        "lanes": lanes,
        "counts": {k: len(v) for k, v in lanes.items()},
        "total": sum(len(v) for v in lanes.values()),
    }

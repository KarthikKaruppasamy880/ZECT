"""Blind CodeRabbit vs Mentrix Ultra Review comparison harness.

Mentrix findings must be produced BEFORE CodeRabbit findings are loaded.
Does not claim Mentrix is better without metrics evidence.
"""

from __future__ import annotations

from typing import Any

from app.services.ultra_review.finding_router import ClosedLoopFinding, normalize_closed_loop_finding


def _key(f: ClosedLoopFinding) -> str:
    return f"{(f.file or '').replace(chr(92), '/').lower()}|{f.line or ''}|{(f.title or f.claim)[:80].lower()}"


def normalize_coderabbit_findings(raw: list[dict[str, Any]]) -> list[ClosedLoopFinding]:
    out: list[ClosedLoopFinding] = []
    for item in raw:
        mapped = {
            "title": item.get("title") or item.get("body") or item.get("summary") or "",
            "severity": item.get("severity") or item.get("priority") or "medium",
            "category": item.get("category") or item.get("type") or "code_quality",
            "file": item.get("file") or item.get("path") or item.get("filename"),
            "line": item.get("line") or item.get("start_line"),
            "evidence": item.get("evidence") or item.get("diff") or "",
            "description": item.get("description") or item.get("body") or "",
            "is_verified": bool(item.get("is_verified", False)),
        }
        out.append(normalize_closed_loop_finding(mapped, run_id="coderabbit"))
    return out


def compare_blind(
    mentrix_raw: list[dict[str, Any]],
    coderabbit_raw: list[dict[str, Any]],
    *,
    mentrix_ran_first: bool,
) -> dict[str, Any]:
    """Compare normalized finding sets. Requires mentrix_ran_first=True for valid blind run."""
    if not mentrix_ran_first:
        return {
            "ok": False,
            "error": "blind_protocol_violated",
            "detail": "Mentrix Ultra Review must complete before CodeRabbit findings are loaded",
        }

    mentrix = [normalize_closed_loop_finding(f, run_id="mentrix") for f in mentrix_raw]
    rabbit = normalize_coderabbit_findings(coderabbit_raw)
    m_keys = {_key(f): f for f in mentrix}
    r_keys = {_key(f): f for f in rabbit}

    shared = sorted(set(m_keys) & set(r_keys))
    mentrix_only = sorted(set(m_keys) - set(r_keys))
    rabbit_only = sorted(set(r_keys) - set(m_keys))

    def _sev_count(items: list[ClosedLoopFinding], sev: str) -> int:
        return sum(1 for f in items if f.severity.value == sev)

    return {
        "ok": True,
        "blind": True,
        "mentrix_ran_first": True,
        "counts": {
            "mentrix": len(mentrix),
            "coderabbit": len(rabbit),
            "shared": len(shared),
            "mentrix_only": len(mentrix_only),
            "coderabbit_only": len(rabbit_only),
        },
        "severity": {
            "mentrix_critical": _sev_count(mentrix, "CRITICAL"),
            "mentrix_high": _sev_count(mentrix, "HIGH"),
            "coderabbit_critical": _sev_count(rabbit, "CRITICAL"),
            "coderabbit_high": _sev_count(rabbit, "HIGH"),
        },
        "shared_keys": shared,
        "mentrix_only_keys": mentrix_only,
        "coderabbit_only_keys": rabbit_only,
        "claim": "No superiority claim — metrics only",
        "rows": [
            {
                "key": k,
                "mentrix": True,
                "coderabbit": True,
                "severity_mentrix": m_keys[k].severity.value,
                "severity_coderabbit": r_keys[k].severity.value,
                "route_mentrix": m_keys[k].recommended_action.value,
            }
            for k in shared
        ]
        + [
            {
                "key": k,
                "mentrix": True,
                "coderabbit": False,
                "severity_mentrix": m_keys[k].severity.value,
                "route_mentrix": m_keys[k].recommended_action.value,
            }
            for k in mentrix_only
        ]
        + [
            {
                "key": k,
                "mentrix": False,
                "coderabbit": True,
                "severity_coderabbit": r_keys[k].severity.value,
                "route_coderabbit": r_keys[k].recommended_action.value,
            }
            for k in rabbit_only
        ],
    }

"""Mentrix Ultra Review — orchestrator-facing wrapper.

Used to run its own standalone OpenAI call with its own JSON schema — a 4th
copy of the same reviewer alongside the three consolidated in review_service.py
(review_phase.py, code_review.py, ultrareview.py), and the only one whose runs
were never persisted to ReviewSession/ReviewFinding (the orchestrator has no
history of its own Ultra Review gates). Now delegates to the same canonical
review_code_snippet(), so orchestrator-driven reviews persist like every other
entry point, and adapts its response back to this function's existing
score/passed/critical_findings contract so orchestrator.py needs no changes
beyond threading db/user_id through.
"""

from __future__ import annotations

import re
from typing import Any

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

# Assignment-style pattern, not a bare substring — mirrors transfer.py's
# SECRET_PATTERNS. A bare "api_key" substring match previously false-
# positived on the offline build stub's OWN comment ("Generated without
# OPENAI_API_KEY — replace in live runs"), which contains "api_key" as a
# substring of "OPENAI_API_KEY" — meaning every upgrade/deliver run with no
# LLM key configured got a critical, non-waiveable "credential handling"
# finding purely from the placeholder explaining that no key was configured.
_HARDCODED_CREDENTIAL_RE = re.compile(
    r"(?:api[_-]?key|secret|password|credential|token)\s*[:=]\s*['\"]\S",
    re.IGNORECASE,
)


def run_ultra_review(
    code: str,
    *,
    language: str = "python",
    context: str = "",
    severity_threshold: str = "medium",
    goal: str = "",
    db: Any = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Best-in-class Mentrix Ultra Review (ZECT-branded)."""
    if not code.strip() and goal:
        code = f"# Goal context for review\n# {goal[:2000]}\n"
    if context:
        code = f"# Context: {context[:2000]}\n\n{code}"

    from app.review_service import review_code_snippet

    try:
        result = review_code_snippet(code=code, language=language, user_id=user_id, db=db)
    except ValueError:
        # No LLM configured — offline heuristic, same signals the old
        # standalone implementation used, kept for zero-config environments.
        # Only scans the generated code, not the goal text — a goal like
        # "add password reset flow" describes a legitimate feature, not a
        # hardcoded credential, and shouldn't trip this on its own.
        findings: list[dict[str, Any]] = []
        if _HARDCODED_CREDENTIAL_RE.search(code):
            findings.append({
                "severity": "critical",
                "category": "security",
                "line": None,
                "message": "Possible credential handling in upgrade scope",
                "suggestion": "Use secrets manager; never hardcode credentials.",
            })
        if re.search(r"\bTODO\b|\bFIXME\b|\.\.\.\s*$|NotImplementedError", code):
            findings.append({
                "severity": "high",
                "category": "maintainability",
                "line": None,
                "message": "Incomplete markers in generated code",
                "suggestion": "Complete implementation before approve.",
            })
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        score = 90 if not findings else (35 if critical else 65)
        return {
            "brand": "Mentrix Ultra Review",
            "passed": critical == 0,
            "score": score,
            "quality_score": score,
            "findings": findings,
            "summary": "Mentrix Ultra Review (offline heuristics).",
            "critical_findings": critical,
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
        }

    threshold_idx = (
        _SEVERITY_ORDER.index(severity_threshold) if severity_threshold in _SEVERITY_ORDER else 2
    )
    findings = []
    for f in result.get("findings", []):
        sev = f.get("severity", "info")
        if sev in _SEVERITY_ORDER and _SEVERITY_ORDER.index(sev) <= threshold_idx:
            title = f.get("title", "")
            description = f.get("description", "")
            findings.append({
                "severity": sev,
                "category": f.get("category", "code_quality"),
                "line": f.get("line"),
                "message": f"{title} — {description}" if title and description else (title or description),
                "suggestion": f.get("suggestion", ""),
            })
    critical = sum(1 for f in findings if f.get("severity") == "critical")
    score = int(result.get("quality_score", 50))
    return {
        "brand": "Mentrix Ultra Review",
        "passed": critical == 0 and score >= 70,
        "score": score,
        "quality_score": score,
        "findings": findings,
        "summary": result.get("summary", ""),
        "critical_findings": critical,
        "model": result.get("model", "gpt-4o-mini"),
        "tokens_used": result.get("tokens_used", 0),
        "review_session_id": result.get("review_session_id"),
        "offline": False,
    }

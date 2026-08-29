"""Classify Mentrix gate/build errors for smarter Fixer recovery."""

from __future__ import annotations

import re
from typing import Any

Category = str  # SYNTAX | LOGIC | VALIDATION | TIMEOUT | SECURITY


def classify_error(
    error: str = "",
    *,
    gate: str = "",
    findings: list[dict] | None = None,
) -> dict[str, Any]:
    blob = f"{error} {gate}".lower()
    findings = findings or []

    for f in findings:
        sev = (f.get("severity") or "").lower()
        cat = (f.get("category") or "").lower()
        msg = (f.get("message") or "").lower()
        if sev == "critical" and cat in ("security", "secrets") or "secret" in msg or "password" in msg:
            return {
                "category": "SECURITY",
                "next_step": "await_human",
                "model_tier": "same",
                "deterministic_fix": False,
                "auto_waive": False,
                "feedback": "Security finding — human required; never auto-waive",
            }

    if any(k in blob for k in ("timeout", "timed out", "connection reset", "429", "rate limit")):
        return {
            "category": "TIMEOUT",
            "next_step": "re_build",
            "model_tier": "same",
            "deterministic_fix": False,
            "auto_waive": False,
            "feedback": "Transient/timeout — retry same tier with backoff",
        }

    if any(
        k in blob
        for k in (
            "syntax",
            "brace",
            "ast_syntax",
            "indent",
            "parse",
            "truncated",
            "finish_reason",
            "incomplete",
            "deny_placeholder",
        )
    ) or gate in ("incomplete", "incomplete_files", "lint"):
        return {
            "category": "SYNTAX",
            "next_step": "re_build",
            "model_tier": "same",
            "deterministic_fix": True,
            "auto_waive": False,
            "feedback": "Syntax/structure — cheap deterministic fix then re_build",
        }

    if any(k in blob for k in ("invented_api", "grounding", "missing_mention", "criteria_unsatisfied", "contract")):
        return {
            "category": "VALIDATION",
            "next_step": "re_build",
            "model_tier": "escalate",
            "deterministic_fix": False,
            "auto_waive": False,
            "feedback": "Validation/grounding failure — escalate prompt detail",
        }

    if any(k in blob for k in ("logic", "sandbox", "review", "quality", "api_eval")):
        return {
            "category": "LOGIC",
            "next_step": "re_review" if "review" in blob else "re_build",
            "model_tier": "escalate",
            "deterministic_fix": False,
            "auto_waive": False,
            "feedback": "Logic/review failure — escalate model tier hint",
        }

    return {
        "category": "LOGIC",
        "next_step": "re_build",
        "model_tier": "escalate",
        "deterministic_fix": False,
        "auto_waive": False,
        "feedback": "Unclassified — treat as logic with escalate hint",
    }


def classify_from_blockers(blockers: list[str] | None, gate: str = "") -> dict[str, Any]:
    return classify_error("; ".join(blockers or []), gate=gate)

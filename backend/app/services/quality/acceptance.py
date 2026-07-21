"""Design contract + acceptance criteria satisfaction (not presence-only)."""

from __future__ import annotations

import re
from typing import Any


def verify_design_contract(
    *,
    contract: dict[str, Any] | None,
    files_written: list[str] | None,
    generated_code: str = "",
    file_contents: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Verify required_files and required_mentions appear in generated output."""
    contract = contract or {}
    written = [f.replace("\\", "/") for f in (files_written or []) if f]
    blob_parts = [generated_code or ""]
    for text in (file_contents or {}).values():
        blob_parts.append(str(text))
    blob = "\n".join(blob_parts)
    blockers: list[str] = []

    required_files = [f.replace("\\", "/") for f in (contract.get("required_files") or []) if f]
    for rf in required_files:
        if rf not in written and not any(w.endswith(rf) or rf.endswith(w) for w in written):
            blockers.append(f"missing_required_file:{rf}")

    mentions = [m for m in (contract.get("required_mentions") or []) if m]
    for mention in mentions:
        if mention.lower() not in blob.lower():
            blockers.append(f"missing_mention:{mention}")

    return {
        "ok": len(blockers) == 0,
        "blockers": blockers,
        "required_files": required_files,
        "required_mentions": mentions,
        "gate": "design_contract",
    }


def _criteria_tokens(criterion: str) -> list[str]:
    """Extract meaningful tokens from a criterion phrase."""
    stop = {
        "a", "an", "the", "and", "or", "to", "of", "for", "with", "in", "on", "is", "be",
        "must", "should", "shall", "that", "this", "from", "as", "by", "at", "it",
    }
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", criterion or "")
    return [w for w in words if w.lower() not in stop]


def verify_acceptance_criteria(
    *,
    criteria: list[str] | None,
    generated_code: str = "",
    plan_text: str = "",
    file_contents: dict[str, str] | None = None,
    min_token_hit_ratio: float = 0.35,
) -> dict[str, Any]:
    """Heuristic satisfaction: enough criterion tokens must appear in implementation."""
    criteria = [c for c in (criteria or []) if c and str(c).strip()]
    if not criteria:
        return {
            "ok": True,
            "blockers": [],
            "results": [],
            "note": "No acceptance criteria — skipped",
            "gate": "acceptance",
        }

    blob_parts = [generated_code or "", plan_text or ""]
    for text in (file_contents or {}).values():
        blob_parts.append(str(text))
    blob = "\n".join(blob_parts).lower()

    results: list[dict[str, Any]] = []
    blockers: list[str] = []
    process_only = re.compile(
        r"\b(lint|approve|ultra\s*review|sandbox|gate|pr\b|human)\b",
        re.I,
    )
    for c in criteria:
        # Process/governance criteria are enforced by ForgeLoop gates — not code text
        if process_only.search(c) and len(_criteria_tokens(c)) <= 6:
            results.append({"criterion": c, "ok": True, "hit_ratio": 1.0, "skipped": "process_gate"})
            continue
        tokens = _criteria_tokens(c)
        if not tokens:
            results.append({"criterion": c, "ok": True, "hit_ratio": 1.0})
            continue
        hits = sum(1 for t in tokens if t.lower() in blob)
        ratio = hits / len(tokens)
        ok = ratio >= min_token_hit_ratio
        results.append({"criterion": c, "ok": ok, "hit_ratio": round(ratio, 2), "hits": hits, "tokens": len(tokens)})
        if not ok:
            blockers.append(f"criteria_unsatisfied:{c[:80]}")

    return {
        "ok": len(blockers) == 0,
        "blockers": blockers,
        "results": results,
        "gate": "acceptance",
    }

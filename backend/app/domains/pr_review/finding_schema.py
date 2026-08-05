"""Canonical Phase 4 ReviewFinding schema (Upgrade.md).

Normalizers map legacy LLM/DB shapes onto the spec without requiring a DB migration
in Stage A — fingerprint / validation_status / source / confidence are computed at
the API boundary.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    unvalidated = "unvalidated"
    validated = "validated"
    false_positive = "false_positive"
    invalidated = "invalidated"


class FindingSource(str, Enum):
    ai = "ai"
    deterministic = "deterministic"
    rules_engine = "rules_engine"
    unknown = "unknown"


class ReviewFindingSpec(BaseModel):
    """Upgrade.md ReviewFinding fields (plus stable id when from DB)."""

    id: Optional[int] = None
    category: str = "code_quality"
    severity: str = "info"
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    title: str = ""
    explanation: str = ""
    repository: Optional[str] = None
    commit_sha: Optional[str] = None
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    evidence: Optional[str] = None
    suggested_fix: Optional[str] = None
    validation_status: ValidationStatus = ValidationStatus.unvalidated
    source: FindingSource = FindingSource.ai
    fingerprint: str = ""

    # Compatibility aliases retained for existing UI consumers
    description: Optional[str] = None
    file_path: Optional[str] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    fixed_code: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None


def review_finding_fingerprint(
    *,
    category: str,
    file: str | None,
    start_line: int | None,
    title: str,
    source: str = "ai",
) -> str:
    """Stable SHA-256 fingerprint for dedupe (category|file|line|title|source)."""
    payload = "|".join(
        [
            (category or "").strip().lower(),
            (file or "").replace("\\", "/").strip().lower(),
            str(start_line if start_line is not None else ""),
            (title or "").strip().lower(),
            (source or "ai").strip().lower(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _validation_from_flags(is_verified: bool | None, is_false_positive: bool | None) -> ValidationStatus:
    if is_false_positive:
        return ValidationStatus.false_positive
    if is_verified:
        return ValidationStatus.validated
    return ValidationStatus.unvalidated


def normalize_from_llm(
    raw: dict[str, Any],
    *,
    repository: str | None = None,
    commit_sha: str | None = None,
    source: FindingSource = FindingSource.ai,
    default_confidence: float = 0.7,
) -> ReviewFindingSpec:
    """Map LLM /api/review finding dict → Upgrade.md shape."""
    file_path = raw.get("file") or raw.get("file_path")
    start = raw.get("start_line")
    if start is None:
        start = raw.get("line") or raw.get("line_start")
    end = raw.get("end_line") or raw.get("line_end") or start
    title = raw.get("title") or (raw.get("message") or "")[:120]
    explanation = raw.get("explanation") or raw.get("description") or raw.get("message") or ""
    evidence = raw.get("evidence") or raw.get("code_snippet")
    suggested = raw.get("suggested_fix") or raw.get("suggestion")
    category = raw.get("category") or "code_quality"
    severity = raw.get("severity") or "info"
    confidence = float(raw.get("confidence") if raw.get("confidence") is not None else default_confidence)
    src = FindingSource(raw.get("source") or source.value)
    fp = raw.get("fingerprint") or review_finding_fingerprint(
        category=category, file=file_path, start_line=start, title=title, source=src.value
    )
    return ReviewFindingSpec(
        category=category,
        severity=severity,
        confidence=max(0.0, min(1.0, confidence)),
        title=title,
        explanation=explanation,
        repository=repository or raw.get("repository"),
        commit_sha=commit_sha or raw.get("commit_sha"),
        file=file_path,
        start_line=int(start) if start is not None else None,
        end_line=int(end) if end is not None else None,
        evidence=evidence,
        suggested_fix=suggested,
        validation_status=ValidationStatus(raw.get("validation_status") or "unvalidated"),
        source=src,
        fingerprint=fp,
        description=explanation,
        file_path=file_path,
        suggestion=suggested,
        code_snippet=raw.get("code_snippet"),
        fixed_code=raw.get("fixed_code"),
        cwe_id=raw.get("cwe_id"),
        owasp_category=raw.get("owasp_category"),
    )


def normalize_from_db(
    row: Any,
    *,
    repository: str | None = None,
    commit_sha: str | None = None,
) -> ReviewFindingSpec:
    """Map SQLAlchemy ReviewFinding row → Upgrade.md shape."""
    file_path = getattr(row, "file_path", None)
    start = getattr(row, "line_start", None)
    end = getattr(row, "line_end", None) or start
    title = getattr(row, "title", "") or ""
    explanation = getattr(row, "description", "") or ""
    category = getattr(row, "category", "code_quality") or "code_quality"
    source_raw = getattr(row, "source", None) or "ai"
    try:
        src = FindingSource(source_raw)
    except ValueError:
        src = FindingSource.unknown
    stored_fp = getattr(row, "fingerprint", None)
    fp = stored_fp or review_finding_fingerprint(
        category=category, file=file_path, start_line=start, title=title, source=src.value
    )
    stored_vs = getattr(row, "validation_status", None)
    if stored_vs:
        try:
            vs = ValidationStatus(stored_vs)
        except ValueError:
            vs = _validation_from_flags(getattr(row, "is_verified", False), getattr(row, "is_false_positive", False))
    else:
        vs = _validation_from_flags(getattr(row, "is_verified", False), getattr(row, "is_false_positive", False))
    confidence = getattr(row, "confidence", None)
    if confidence is None:
        confidence = 0.7 if src == FindingSource.ai else 0.95
    return ReviewFindingSpec(
        id=getattr(row, "id", None),
        category=category,
        severity=getattr(row, "severity", "info") or "info",
        confidence=float(confidence),
        title=title,
        explanation=explanation,
        repository=repository,
        commit_sha=commit_sha,
        file=file_path,
        start_line=start,
        end_line=end,
        evidence=getattr(row, "code_snippet", None),
        suggested_fix=getattr(row, "suggestion", None),
        validation_status=vs,
        source=src,
        fingerprint=fp,
        description=explanation,
        file_path=file_path,
        suggestion=getattr(row, "suggestion", None),
        code_snippet=getattr(row, "code_snippet", None),
        fixed_code=getattr(row, "fixed_code", None),
        cwe_id=getattr(row, "cwe_id", None),
        owasp_category=getattr(row, "owasp_category", None),
    )


def normalize_from_rule(
    raw: dict[str, Any],
    *,
    repository: str | None = None,
    commit_sha: str | None = None,
) -> ReviewFindingSpec:
    """Map rules-engine / deterministic check hits → Upgrade.md shape."""
    return normalize_from_llm(
        raw,
        repository=repository,
        commit_sha=commit_sha,
        source=FindingSource.deterministic,
        default_confidence=0.95,
    )


def findings_to_jsonable(findings: list[ReviewFindingSpec]) -> list[dict[str, Any]]:
    return [json.loads(f.model_dump_json()) for f in findings]

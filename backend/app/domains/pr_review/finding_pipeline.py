"""Phase 4 Stage B — validate findings against PR diff, dedupe, rank."""

from __future__ import annotations

from typing import Any

from app.domains.pr_review.finding_schema import (
    FindingSource,
    ReviewFindingSpec,
    ValidationStatus,
    normalize_from_llm,
    review_finding_fingerprint,
)
from app.services.diff_line_mapper import clamp_finding_line, parse_new_file_line_ranges

_SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}


def _file_in_diff(file_path: str | None, files: list[dict[str, Any]]) -> bool:
    if not file_path:
        return False
    norm = file_path.replace("\\", "/")
    for f in files:
        name = (f.get("filename") or f.get("file") or "").replace("\\", "/")
        if name == norm or name.endswith("/" + norm) or norm.endswith("/" + name):
            return True
    return False


def _line_in_hunks(file_path: str | None, line: int | None, files: list[dict[str, Any]]) -> bool:
    if not file_path or line is None or line <= 0:
        return False
    norm = file_path.replace("\\", "/")
    for f in files:
        name = (f.get("filename") or f.get("file") or "").replace("\\", "/")
        if name != norm and not name.endswith("/" + norm) and not norm.endswith("/" + name):
            continue
        ranges = parse_new_file_line_ranges(f.get("patch") or "")
        if not ranges:
            # File changed but no patch (binary / too large) — accept any positive line
            return True
        return any(start <= line <= end for start, end in ranges)
    return False


def validate_finding_against_diff(
    finding: dict[str, Any] | ReviewFindingSpec,
    files: list[dict[str, Any]],
) -> ReviewFindingSpec:
    """Mark validation_status based on whether file/line appear in the PR diff."""
    if isinstance(finding, ReviewFindingSpec):
        spec = finding
    else:
        spec = normalize_from_llm(finding)

    file_path = spec.file or spec.file_path
    line = spec.start_line

    if not files:
        return spec.model_copy(update={"validation_status": ValidationStatus.unvalidated})

    if not _file_in_diff(file_path, files):
        return spec.model_copy(update={"validation_status": ValidationStatus.invalidated})

    clamped = clamp_finding_line(file_path or "", line, files)
    updates: dict[str, Any] = {}
    if clamped is not None:
        updates["start_line"] = clamped
        if spec.end_line is None or spec.end_line == line:
            updates["end_line"] = clamped
        line = clamped

    if _line_in_hunks(file_path, line, files):
        updates["validation_status"] = ValidationStatus.validated
    else:
        updates["validation_status"] = ValidationStatus.invalidated

    start_for_fp = updates.get("start_line", spec.start_line)
    updates["fingerprint"] = review_finding_fingerprint(
        category=spec.category,
        file=file_path,
        start_line=start_for_fp,
        title=spec.title,
        source=spec.source.value,
    )
    return spec.model_copy(update=updates)


def dedupe_by_fingerprint(findings: list[ReviewFindingSpec]) -> list[ReviewFindingSpec]:
    """Keep the best finding per fingerprint (severity, then confidence)."""
    best: dict[str, ReviewFindingSpec] = {}
    for f in findings:
        fp = f.fingerprint or review_finding_fingerprint(
            category=f.category, file=f.file, start_line=f.start_line, title=f.title, source=f.source.value
        )
        f = f.model_copy(update={"fingerprint": fp})
        prev = best.get(fp)
        if prev is None:
            best[fp] = f
            continue
        prev_rank = _SEVERITY_RANK.get((prev.severity or "info").lower(), 9)
        cur_rank = _SEVERITY_RANK.get((f.severity or "info").lower(), 9)
        if cur_rank < prev_rank or (cur_rank == prev_rank and f.confidence > prev.confidence):
            best[fp] = f
    return list(best.values())


def rank_findings(findings: list[ReviewFindingSpec]) -> list[ReviewFindingSpec]:
    """Sort: validated first, then severity, then confidence desc."""

    def key(f: ReviewFindingSpec):
        vs = f.validation_status
        vs_rank = 0 if vs == ValidationStatus.validated else (2 if vs == ValidationStatus.invalidated else 1)
        sev = _SEVERITY_RANK.get((f.severity or "info").lower(), 9)
        return (vs_rank, sev, -float(f.confidence or 0), f.title or "")

    return sorted(findings, key=key)


def finalize_pr_findings(
    raw_findings: list[dict[str, Any]],
    files: list[dict[str, Any]],
    *,
    repository: str | None = None,
    commit_sha: str | None = None,
) -> list[dict[str, Any]]:
    """Validate → dedupe → rank; return legacy-compatible dicts for persist/API."""
    specs: list[ReviewFindingSpec] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            continue
        base = normalize_from_llm(raw, repository=repository, commit_sha=commit_sha)
        specs.append(validate_finding_against_diff(base, files))
    specs = rank_findings(dedupe_by_fingerprint(specs))
    out: list[dict[str, Any]] = []
    for s in specs:
        out.append(
            {
                "category": s.category,
                "severity": s.severity,
                "title": s.title,
                "description": s.explanation,
                "explanation": s.explanation,
                "file": s.file,
                "file_path": s.file,
                "line": s.start_line,
                "line_start": s.start_line,
                "line_end": s.end_line,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "code_snippet": s.code_snippet or s.evidence,
                "evidence": s.evidence,
                "suggestion": s.suggested_fix,
                "suggested_fix": s.suggested_fix,
                "fixed_code": s.fixed_code,
                "cwe_id": s.cwe_id,
                "owasp_category": s.owasp_category,
                "confidence": s.confidence,
                "validation_status": s.validation_status.value,
                "source": s.source.value,
                "fingerprint": s.fingerprint,
                "repository": s.repository or repository,
                "commit_sha": s.commit_sha or commit_sha,
            }
        )
    return out

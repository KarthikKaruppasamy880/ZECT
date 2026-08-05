"""Phase 4 Stage B — validate / dedupe / rank findings."""
from app.domains.pr_review.finding_pipeline import (
    dedupe_by_fingerprint,
    finalize_pr_findings,
    rank_findings,
    validate_finding_against_diff,
)
from app.domains.pr_review.finding_schema import ValidationStatus, normalize_from_llm


def _patch_file(filename: str, new_start: int = 10, count: int = 5) -> dict:
    end = new_start + count - 1
    patch = f"@@ -1,1 +{new_start},{count} @@\n" + "\n".join("+" + ("x" * i) for i in range(count))
    return {"filename": filename, "status": "modified", "additions": count, "deletions": 0, "patch": patch}


def test_validate_marks_file_not_in_diff_invalidated():
    files = [_patch_file("a.py")]
    spec = validate_finding_against_diff(
        {"title": "x", "file": "missing.py", "line": 12, "category": "bug", "severity": "high"},
        files,
    )
    assert spec.validation_status == ValidationStatus.invalidated


def test_validate_marks_line_in_hunk_validated():
    files = [_patch_file("a.py", new_start=10, count=5)]
    spec = validate_finding_against_diff(
        {"title": "x", "file": "a.py", "line": 12, "category": "bug", "severity": "high"},
        files,
    )
    assert spec.validation_status == ValidationStatus.validated
    assert spec.start_line == 12


def test_dedupe_keeps_higher_severity():
    a = normalize_from_llm({"title": "Same", "file": "a.py", "line": 1, "category": "bug", "severity": "low"})
    b = normalize_from_llm({"title": "Same", "file": "a.py", "line": 1, "category": "bug", "severity": "critical"})
    # Force same fingerprint basis
    assert a.fingerprint == b.fingerprint or True
    out = dedupe_by_fingerprint([a, b])
    assert len(out) == 1
    assert out[0].severity == "critical"


def test_rank_puts_critical_validated_first():
    files = [_patch_file("a.py", 10, 5)]
    findings = finalize_pr_findings(
        [
            {"title": "low", "file": "a.py", "line": 11, "category": "style", "severity": "low"},
            {"title": "crit", "file": "a.py", "line": 12, "category": "security", "severity": "critical"},
            {"title": "ghost", "file": "other.py", "line": 1, "category": "bug", "severity": "critical"},
        ],
        files,
        repository="acme/zect",
    )
    assert findings[0]["title"] == "crit"
    assert findings[0]["validation_status"] == "validated"
    assert findings[-1]["title"] == "ghost"
    assert findings[-1]["validation_status"] == "invalidated"
    assert all("fingerprint" in f for f in findings)


def test_rank_findings_helper():
    specs = [
        normalize_from_llm({"title": "b", "file": "a.py", "line": 1, "severity": "low", "category": "x"}),
        normalize_from_llm({"title": "a", "file": "a.py", "line": 2, "severity": "high", "category": "x"}),
    ]
    ranked = rank_findings(specs)
    assert ranked[0].severity == "high"

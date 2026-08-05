"""Phase 4 Stage A — ReviewFinding canonical schema unit tests."""
from app.domains.pr_review.finding_schema import (
    FindingSource,
    ValidationStatus,
    normalize_from_db,
    normalize_from_llm,
    normalize_from_rule,
    review_finding_fingerprint,
)


def test_fingerprint_stable_and_distinct():
    a = review_finding_fingerprint(category="security", file="a.py", start_line=10, title="XSS")
    b = review_finding_fingerprint(category="security", file="a.py", start_line=10, title="XSS")
    c = review_finding_fingerprint(category="security", file="a.py", start_line=11, title="XSS")
    assert a == b
    assert a != c
    assert len(a) == 32


def test_normalize_from_llm_maps_legacy_fields():
    spec = normalize_from_llm(
        {
            "category": "security",
            "severity": "high",
            "title": "Hardcoded secret",
            "description": "API key in source",
            "file": "cfg.py",
            "line": 42,
            "suggestion": "Use env var",
            "code_snippet": "KEY = 'x'",
        },
        repository="acme/zect",
        commit_sha="abc123",
    )
    assert spec.file == "cfg.py"
    assert spec.start_line == 42
    assert spec.end_line == 42
    assert spec.explanation == "API key in source"
    assert spec.suggested_fix == "Use env var"
    assert spec.evidence == "KEY = 'x'"
    assert spec.repository == "acme/zect"
    assert spec.commit_sha == "abc123"
    assert spec.source == FindingSource.ai
    assert spec.validation_status == ValidationStatus.unvalidated
    assert spec.fingerprint
    assert spec.description == spec.explanation


def test_normalize_from_db_derives_validation_status():
    class Row:
        id = 1
        category = "bug"
        severity = "medium"
        title = "NPE"
        description = "May crash"
        file_path = "x.ts"
        line_start = 3
        line_end = 5
        code_snippet = "x!"
        suggestion = "null check"
        fixed_code = None
        cwe_id = None
        owasp_category = None
        is_verified = True
        is_false_positive = False

    spec = normalize_from_db(Row())
    assert spec.validation_status == ValidationStatus.validated
    assert spec.start_line == 3
    assert spec.end_line == 5
    assert spec.file == "x.ts"


def test_normalize_from_rule_is_deterministic():
    spec = normalize_from_rule({"title": "TODO", "file": "a.py", "line": 1, "category": "style"})
    assert spec.source == FindingSource.deterministic
    assert spec.confidence >= 0.9

"""Tranche I inventory: verdict docs cannot claim READY while blockers remain.

Skip / BLOCKED_EXTERNAL / CodeRabbit skip ≠ PASS. Architecture docs must not
claim pgvector/Chroma/FAISS/Qdrant/Redis as implemented.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

REQUIRED_BLOCKERS = [
    "CLEAN_WINDOWS_NSIS",
    "LIVE_POSTGRES",
    "LIVE_PRESENTON_GENERATE",
    "LIVE_VOICEBOX",
    "LIVE_PPT_COM",
    "LIVE_GITHUB_PR",
    "LIVE_CAMUNDA",
    "LIVE_JIRA_INGEST",
    "CODERABBIT_SKIPPED",
    "CI_ELECTRON_NOT_IN_CORE",
]

FORBIDDEN_IMPLEMENTED = (
    "pgvector is used",
    "Chroma is implemented",
    "FAISS is implemented",
    "Qdrant is implemented",
    "Redis is implemented",
)


def test_final_acceptance_is_partial_not_ready() -> None:
    text = (REPO / "ZECT_PRODUCTION_GRADE_FINAL_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "**ZECT_PRODUCTION_PARTIAL**" in text
    assert "**ZECT_PRODUCTION_READY**" not in text
    assert "ZECT_PRODUCTION_READY" in text
    assert "SKIPPED" in text
    assert "skip ≠ PASS" in text or "skip-review" in text.lower() or "never PASS" in text


def test_blocker_register_lists_open_externals() -> None:
    register = (REPO / "ZECT_PRODUCTION_GRADE_BLOCKER_REGISTER.md").read_text(encoding="utf-8")
    assert "**ZECT_PRODUCTION_PARTIAL**" in register
    for blocker_id in REQUIRED_BLOCKERS:
        assert blocker_id in register, blocker_id
    assert "BLOCKED_EXTERNAL" in register
    assert "CODERABBIT_SKIPPED" in register


def test_electron_full_release_not_in_ci_core() -> None:
    pkg = (REPO / "frontend" / "package.json").read_text(encoding="utf-8")
    assert "e2e/full-release-e2e-production.spec.ts" in pkg
    assert "e2e/full-release-e2e-electron.spec.ts" not in pkg


def test_architecture_does_not_claim_unbuilt_stores() -> None:
    for rel in (
        "ZECT_CANONICAL_ARCHITECTURE.md",
        "ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md",
    ):
        text = (REPO / rel).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "not implemented" in lowered or "**no.**" in lowered
        for phrase in FORBIDDEN_IMPLEMENTED:
            assert phrase.lower() not in lowered, (rel, phrase)
        assert "pgvector" in lowered
        assert "not" in lowered

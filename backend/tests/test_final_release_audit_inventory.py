"""Tranche I leftovers: architecture truth + electron not in ubuntu core.

Profile verdicts live in test_release_profile_inventory.py.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

FORBIDDEN_IMPLEMENTED = (
    "pgvector is used",
    "Chroma is implemented",
    "FAISS is implemented",
    "Qdrant is implemented",
    "Redis is implemented",
)


def test_monolith_ready_label_not_awarded() -> None:
    text = (REPO / "ZECT_PRODUCTION_GRADE_FINAL_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "**ZECT_PRODUCTION_READY**" not in text
    assert "ZECT_PRODUCTION_READY" in text


def test_electron_full_release_not_in_ci_core() -> None:
    pkg = (REPO / "frontend" / "package.json").read_text(encoding="utf-8")
    assert "e2e/full-release-e2e-production.spec.ts" in pkg
    core_line = next(line for line in pkg.splitlines() if '"test:e2e:core"' in line)
    assert "full-release-e2e-electron.spec.ts" not in core_line


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

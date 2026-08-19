"""Release-profile inventory: Core is not blocked by optional connectors.

PostgreSQL is mandatory only for server_postgres (DATABASE_URL postgres*).
desktop_sqlite is the Core / packaged Electron store. Skip ≠ PASS.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

OPTIONAL_CONNECTORS = ("GitHub", "Jira", "Camunda", "Presenton", "Voicebox")


def test_final_acceptance_has_profile_verdicts() -> None:
    text = (REPO / "ZECT_PRODUCTION_GRADE_FINAL_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "**ZECT_CORE_READY**" in text
    assert "**ZECT_DESKTOP_WINDOWS" in text
    assert "**ZECT_PRODUCTION_READY**" not in text
    assert "ZECT_PRODUCTION_READY" in text
    for name in OPTIONAL_CONNECTORS:
        assert name in text
    assert "BLOCKED_EXTERNAL" in text
    assert "skip ≠ PASS" in text or "never PASS" in text


def test_blocker_register_does_not_let_connectors_block_core() -> None:
    register = (REPO / "ZECT_PRODUCTION_GRADE_BLOCKER_REGISTER.md").read_text(encoding="utf-8")
    assert "does not block ZECT_CORE" in register or "do not block ZECT_CORE" in register
    assert "LIVE_POSTGRES" in register
    assert "server_postgres" in register
    assert "CLEAN_WINDOWS_NSIS" in register
    for name in (
        "LIVE_GITHUB_PR",
        "LIVE_JIRA_INGEST",
        "LIVE_CAMUNDA",
        "LIVE_PRESENTON_GENERATE",
        "LIVE_VOICEBOX",
    ):
        assert name in register


def test_electron_not_in_ubuntu_core_script() -> None:
    pkg = (REPO / "frontend" / "package.json").read_text(encoding="utf-8")
    assert "e2e/full-release-e2e-production.spec.ts" in pkg
    assert '"test:e2e:electron"' in pkg
    core_line = next(line for line in pkg.splitlines() if '"test:e2e:core"' in line)
    assert "full-release-e2e-electron.spec.ts" not in core_line


def test_ci_has_required_windows_electron_job() -> None:
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "e2e-electron:" in ci
    assert "windows-latest" in ci
    assert "ZECT_REQUIRE_ELECTRON" in ci
    assert "test:e2e:electron" in ci
    spec = (REPO / "frontend" / "e2e" / "full-release-e2e-electron.spec.ts").read_text(
        encoding="utf-8"
    )
    assert "ZECT_REQUIRE_ELECTRON" in spec


def test_postgres_is_mode_gated_not_core_default() -> None:
    database = (REPO / "backend" / "app" / "infrastructure" / "database.py").read_text(
        encoding="utf-8"
    )
    assert "desktop_sqlite" in database
    assert "server_postgres" in database
    assert "does not fall back to SQLite" in database
    db_url = (REPO / "backend" / "app" / "infrastructure" / "db_url.py").read_text(encoding="utf-8")
    assert "def is_postgres_url" in db_url
    example = (REPO / "backend" / ".env.example").read_text(encoding="utf-8")
    assert "DATABASE_URL=sqlite:///./zect.db" in example
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgresql+psycopg://" in compose


def test_architecture_does_not_claim_unbuilt_stores() -> None:
    for rel in (
        "ZECT_CANONICAL_ARCHITECTURE.md",
        "ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md",
    ):
        text = (REPO / rel).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "not implemented" in lowered or "**no.**" in lowered
        assert "pgvector" in lowered

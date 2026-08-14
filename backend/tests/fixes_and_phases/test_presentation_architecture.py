"""S2 architecture: domains and ZectPresent must not import Presenton client/types."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAINS = ROOT / "backend" / "app" / "domains"
ZECT_PRESENT = ROOT / "frontend" / "src" / "pages" / "ZectPresent.tsx"

FORBIDDEN_DOMAIN = (
    "from app.services.presenton_client",
    "import app.services.presenton_client",
    "from app.adapters.presentation.presenton_provider",
)
FORBIDDEN_UI = (
    "presenton_client",
    "PresentonProvider",
    "Presenton UI",
    "third-party Presenton",
    "ghcr.io/presenton",
)


def test_domains_do_not_import_presenton_client():
    hits: list[str] = []
    for path in DOMAINS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_DOMAIN:
            if needle in text:
                hits.append(f"{path.relative_to(ROOT)}: {needle}")
    assert hits == []


def test_zect_present_does_not_reference_presenton_types():
    text = ZECT_PRESENT.read_text(encoding="utf-8")
    hits = [needle for needle in FORBIDDEN_UI if needle in text]
    assert hits == []

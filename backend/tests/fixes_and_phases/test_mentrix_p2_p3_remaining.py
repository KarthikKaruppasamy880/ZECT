"""P2/P3 remaining + P3 deferred closeout — System Health, Skills FS sync, scanner, desktop."""

from __future__ import annotations

from app.services.desktop_readiness import build_desktop_readiness
from app.services.security_scanner import MentrixSecurityAgentScanner, get_default_security_scanner
from app.services.skills_fs import list_filesystem_skills, sync_filesystem_skills_to_db
from app.services.system_health import build_system_health
from app.services.work_items.ultra_review_lanes import merge_ultrareview_lanes


def test_system_health_components():
    h = build_system_health(db=None)
    assert h["status"] in ("ok", "degraded", "error")
    ids = {c["id"] for c in h["components"]}
    assert "api" in ids and "coding_engine" in ids and "model_gateway" in ids
    assert "desktop" in ids and "skills_fs" in ids


def test_skills_fs_lists_sample_pack():
    skills = list_filesystem_skills()
    names = {s["name"] for s in skills}
    assert "mentrix-smoke" in names


def test_skills_fs_sync_to_db(db_session=None):
    """Import FS pack into SkillDefinition when a session is available."""
    from app.infrastructure.database import SessionLocal
    from app.models import SkillDefinition

    db = db_session or SessionLocal()
    try:
        out = sync_filesystem_skills_to_db(db, limit=10)
        assert out["ok"] is True
        assert out["scanned"] >= 1
        assert "mentrix-smoke" in out["names"]
        row = (
            db.query(SkillDefinition)
            .filter(SkillDefinition.name == "mentrix-smoke", SkillDefinition.is_active == True)  # noqa: E712
            .first()
        )
        assert row is not None
        assert row.provenance == "imported"
        # idempotent second sync
        out2 = sync_filesystem_skills_to_db(db, limit=10)
        assert out2["updated"] >= 1
        assert out2["created"] == 0
    finally:
        if db_session is None:
            db.close()


def test_ultrareview_three_lanes():
    merged = merge_ultrareview_lanes(
        [
            {"category": "security", "title": "XSS risk", "severity": "high"},
            {"category": "requirement", "title": "Missing AC", "severity": "medium"},
            {"category": "bug", "title": "Null deref", "severity": "high"},
        ]
    )
    assert merged["engine"] == "review_service"
    assert merged["counts"]["security"] >= 1
    assert merged["counts"]["requirements"] >= 1
    assert merged["counts"]["engineering"] >= 1


def test_security_scanner_interface():
    scanner = get_default_security_scanner()
    assert isinstance(scanner, MentrixSecurityAgentScanner)
    out = scanner.scan(target="workspace")
    assert out["ok"] is True
    assert out["scanner"] == "mentrix_security_agent"
    assert out["route"] == "/security-incidents"
    assert "findings" in out


def test_security_scanner_with_db_findings():
    from app.infrastructure.database import SessionLocal
    from app.models import SecurityFinding
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        fp = f"p3-test-{datetime.now(timezone.utc).timestamp()}"
        db.add(
            SecurityFinding(
                fingerprint=fp,
                kind="malware",
                severity="high",
                status="open",
                title="P3 scanner fixture",
                description="test",
            )
        )
        db.commit()
        out = MentrixSecurityAgentScanner().scan(target="workspace", db=db)
        assert out["ok"] is True
        assert out["incident_count"] >= 0
        assert any(f.get("title") == "P3 scanner fixture" for f in out["findings"])
    finally:
        db.close()


def test_desktop_readiness_surface():
    d = build_desktop_readiness()
    assert d["ok"] is True
    assert "capabilities" in d
    assert "desktop_write_note" in d["capabilities"]
    assert isinstance(d["electron_main_present"], bool)

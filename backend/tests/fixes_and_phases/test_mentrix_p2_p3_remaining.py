"""P2/P3 + final closeout — System Health, Skills FS bi-sync, scanner, desktop, gates."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.desktop_readiness import build_desktop_readiness
from app.services.security_scanner import MentrixSecurityAgentScanner, get_default_security_scanner
from app.services.skills_fs import (
    list_filesystem_skills,
    primary_skills_fs_root,
    sync_db_skills_to_filesystem,
    sync_filesystem_skills_to_db,
    sync_skills_bidirectional,
)
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


def test_skills_fs_sync_to_db():
    from app.infrastructure.database import SessionLocal
    from app.models import SkillDefinition

    db = SessionLocal()
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
        out2 = sync_filesystem_skills_to_db(db, limit=10)
        assert out2["created"] == 0
    finally:
        db.close()


def test_skills_bidirectional_sync_roundtrip():
    from app.infrastructure.database import SessionLocal
    from app.models import SkillDefinition
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        name = "closeout-bidi-skill"
        now = datetime.now(timezone.utc)
        existing = db.query(SkillDefinition).filter(SkillDefinition.name == name).first()
        if existing:
            existing.script_body = "# closeout-bidi-skill\n\nDB authored body for export.\n"
            existing.is_active = True
            existing.provenance = "local"
            existing.updated_at = now
        else:
            db.add(
                SkillDefinition(
                    name=name,
                    version="1.0.0",
                    description="DB authored body for export.",
                    category="test",
                    script_body="# closeout-bidi-skill\n\nDB authored body for export.\n",
                    is_active=True,
                    provenance="local",
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()

        out = sync_skills_bidirectional(db, limit=50)
        assert out["ok"] is True
        assert out["direction"] == "bidirectional"
        assert out["db_to_fs"]["written"] >= 1 or out["db_to_fs"]["skipped"] >= 1

        path = primary_skills_fs_root() / name / "SKILL.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "DB authored body for export" in text or "closeout-bidi-skill" in text

        # Export-only path also works
        again = sync_db_skills_to_filesystem(db, limit=50)
        assert again["ok"] is True
        assert again["direction"] == "db_to_fs"
    finally:
        try:
            import shutil

            skill_dir = primary_skills_fs_root() / "closeout-bidi-skill"
            if skill_dir.exists():
                shutil.rmtree(skill_dir, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
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


def test_gate_statuses_require_evidence_allow_gate():
    from app.infrastructure.database import SessionLocal
    from app.domains.work_items.service import create_work_item, transition_status
    from app.domains.work_items.status import STATUS_READY_TO_SHIP, STATUS_DONE

    db = SessionLocal()
    try:
        wi = create_work_item(db, title="gate-block-closeout", description="must not skip verifier")
        with pytest.raises(HTTPException) as exc:
            transition_status(db, wi.id, STATUS_READY_TO_SHIP, allow_gate=False)
        assert exc.value.status_code == 403
        with pytest.raises(HTTPException) as exc2:
            transition_status(db, wi.id, STATUS_DONE, allow_gate=False)
        assert exc2.value.status_code == 403
    finally:
        db.close()

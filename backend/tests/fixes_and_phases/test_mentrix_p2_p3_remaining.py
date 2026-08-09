"""P2/P3 remaining — System Health, Skills FS, Ultra Review lanes, SecurityScanner."""

from __future__ import annotations

from app.services.security_scanner import MentrixSecurityAgentScanner, get_default_security_scanner
from app.services.skills_fs import list_filesystem_skills
from app.services.system_health import build_system_health
from app.services.work_items.ultra_review_lanes import merge_ultrareview_lanes


def test_system_health_components():
    h = build_system_health(db=None)
    assert h["status"] in ("ok", "degraded", "error")
    ids = {c["id"] for c in h["components"]}
    assert "api" in ids and "coding_engine" in ids and "model_gateway" in ids


def test_skills_fs_lists_sample_pack():
    skills = list_filesystem_skills()
    names = {s["name"] for s in skills}
    assert "mentrix-smoke" in names


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

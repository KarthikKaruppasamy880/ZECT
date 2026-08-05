"""Phase 9 — security finding fingerprint + persist smoke tests."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.models import PermissionAudit, SecurityFinding
from app.services.security.threat_detection import fingerprint_finding, run_anomaly_scan
from app.domains.security_incident.router import persist_normalized_findings
from app.adapters.detection_audit import AuditTrailDetectionProvider


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_fingerprint_stable():
    f = {"kind": "permission_denial_spike", "user_id": 1, "severity": "high", "actions": ["a"]}
    assert fingerprint_finding(f) == fingerprint_finding(dict(f))
    assert len(fingerprint_finding(f)) == 40


def test_scan_includes_fingerprint_and_persists():
    db = _session()
    for _ in range(6):
        db.add(
            PermissionAudit(
                user_id=9,
                action="companion_desktop_delete",
                permission_level="never",
                result="denied",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
    db.commit()

    result = run_anomaly_scan(db, lookback_hours=24)
    assert result["findings"]
    assert all("fingerprint" in f for f in result["findings"])

    provider = AuditTrailDetectionProvider()
    collected = provider.collect(db, lookback_hours=24)
    rows = persist_normalized_findings(db, collected["findings"])
    assert rows
    assert db.query(SecurityFinding).count() >= 1
    # Dedupe on second persist
    rows2 = persist_normalized_findings(db, collected["findings"])
    assert db.query(SecurityFinding).count() == len({r.fingerprint for r in rows2})

"""Anomaly detection over real audit data — PermissionAudit denial spikes,
AuditLog IP churn, sensitive-resource bursts, and off-hours access. Every
finding must trace back to actual rows already written elsewhere in the
app (permission_broker, core.auth.rbac.log_audit) — nothing here invents
telemetry that doesn't exist.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models import AuditLog, PermissionAudit
from app.services.security import threat_detection


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _perm_audit(db, *, user_id, result, action="companion_desktop_delete", minutes_ago=0):
    row = PermissionAudit(
        user_id=user_id,
        action=action,
        permission_level="never" if result == "denied" else "require_approval",
        result=result,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.add(row)
    return row


def _audit_log(db, *, user_id, resource_type, ip_address=None, action="read", minutes_ago=0, created_at=None):
    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        ip_address=ip_address,
        created_at=created_at or (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)),
    )
    db.add(row)
    return row


class TestDenialSpike:
    def test_flags_user_with_repeated_denials(self):
        db = _session()
        for _ in range(6):
            _perm_audit(db, user_id=1, result="denied")
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        kinds = [f["kind"] for f in result["findings"]]
        assert "permission_denial_spike" in kinds
        finding = next(f for f in result["findings"] if f["kind"] == "permission_denial_spike")
        assert finding["user_id"] == 1
        assert finding["severity"] == "high"
        assert finding["count"] == 6

    def test_below_threshold_does_not_flag(self):
        db = _session()
        _perm_audit(db, user_id=2, result="denied")
        _perm_audit(db, user_id=2, result="denied")
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        assert not any(f["kind"] == "permission_denial_spike" for f in result["findings"])

    def test_granted_results_are_never_counted(self):
        db = _session()
        for _ in range(10):
            _perm_audit(db, user_id=3, result="granted")
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        assert not any(f["kind"] == "permission_denial_spike" for f in result["findings"])

    def test_outside_lookback_window_is_excluded(self):
        db = _session()
        for _ in range(6):
            _perm_audit(db, user_id=4, result="denied", minutes_ago=60 * 48)
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        assert not any(f["kind"] == "permission_denial_spike" for f in result["findings"])


class TestIpChurn:
    def test_flags_user_active_from_many_ips(self):
        db = _session()
        for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
            _audit_log(db, user_id=5, resource_type="project", ip_address=ip)
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        finding = next(f for f in result["findings"] if f["kind"] == "ip_churn")
        assert finding["user_id"] == 5
        assert finding["count"] == 3

    def test_single_ip_does_not_flag(self):
        db = _session()
        for _ in range(5):
            _audit_log(db, user_id=6, resource_type="project", ip_address="9.9.9.9")
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        assert not any(f["kind"] == "ip_churn" for f in result["findings"])

    def test_rows_with_no_ip_are_ignored(self):
        db = _session()
        for _ in range(5):
            _audit_log(db, user_id=7, resource_type="project", ip_address=None)
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        assert not any(f["kind"] == "ip_churn" for f in result["findings"])


class TestSensitiveBurst:
    def test_flags_burst_on_sensitive_resource(self):
        db = _session()
        for _ in range(12):
            _audit_log(db, user_id=8, resource_type="secret", action="read")
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        finding = next(f for f in result["findings"] if f["kind"] == "sensitive_resource_burst")
        assert finding["user_id"] == 8
        assert finding["resource_types"] == ["secret"]

    def test_non_sensitive_resource_is_not_flagged(self):
        db = _session()
        for _ in range(20):
            _audit_log(db, user_id=9, resource_type="review", action="read")
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        assert not any(f["kind"] == "sensitive_resource_burst" for f in result["findings"])


class TestOffHoursAccess:
    def test_flags_sensitive_access_in_off_hours_window(self):
        db = _session()
        off_hours_ts = datetime.now(timezone.utc).replace(hour=3, minute=0, second=0, microsecond=0)
        _audit_log(db, user_id=10, resource_type="secret", action="read", created_at=off_hours_ts)
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24 * 7)

        assert any(f["kind"] == "off_hours_sensitive_access" and f["user_id"] == 10 for f in result["findings"])

    def test_daytime_sensitive_access_is_not_flagged(self):
        db = _session()
        daytime_ts = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0)
        _audit_log(db, user_id=11, resource_type="secret", action="read", created_at=daytime_ts)
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24 * 7)

        assert not any(f["kind"] == "off_hours_sensitive_access" and f["user_id"] == 11 for f in result["findings"])


class TestRunAnomalyScanShape:
    def test_returns_scanned_counts(self):
        db = _session()
        _perm_audit(db, user_id=1, result="denied")
        _audit_log(db, user_id=1, resource_type="project", ip_address="1.1.1.1")
        db.commit()

        result = threat_detection.run_anomaly_scan(db, lookback_hours=24)

        assert result["scanned"]["permission_audits"] == 1
        assert result["scanned"]["audit_logs"] == 1
        assert result["scanned"]["lookback_hours"] == 24

    def test_no_data_returns_empty_findings(self):
        db = _session()

        result = threat_detection.run_anomaly_scan(db)

        assert result["findings"] == []

"""Audit-trail Detection Provider — wraps existing threat_detection scan."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.adapters.detection_provider import normalize_finding
from app.services.security.threat_detection import fingerprint_finding, run_anomaly_scan


class AuditTrailDetectionProvider:
    name = "audit_trail"

    def collect(self, db: Session, *, lookback_hours: int = 24) -> dict[str, Any]:
        result = run_anomaly_scan(db, lookback_hours=lookback_hours)
        findings = []
        for f in result.get("findings") or []:
            nf = normalize_finding(
                {
                    **f,
                    "title": f.get("kind", "anomaly").replace("_", " ").title(),
                    "user": f.get("user_id"),
                    "rule_id": f.get("kind"),
                },
                source="audit_trail",
            )
            nf["fingerprint"] = fingerprint_finding(f)
            findings.append(nf)
        return {"findings": findings, "scanned": result.get("scanned") or {}, "provider": self.name}

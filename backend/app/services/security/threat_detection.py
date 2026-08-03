"""Anomaly detection over ZECT's own audit data — PermissionAudit (every
tool-permission check) and AuditLog (every CRUD/action record). No synthetic
telemetry: every finding traces back to real rows already written by
permission_broker.check_tool_permission() and core.auth.rbac.log_audit().
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, PermissionAudit

DENIAL_SPIKE_THRESHOLD = int(os.getenv("SECURITY_DENIAL_SPIKE_THRESHOLD", "5"))
IP_CHURN_THRESHOLD = int(os.getenv("SECURITY_IP_CHURN_THRESHOLD", "3"))
SENSITIVE_BURST_THRESHOLD = int(os.getenv("SECURITY_SENSITIVE_BURST_THRESHOLD", "10"))
OFF_HOURS_START = int(os.getenv("SECURITY_OFF_HOURS_START_UTC", "0"))  # inclusive, 24h UTC
OFF_HOURS_END = int(os.getenv("SECURITY_OFF_HOURS_END_UTC", "5"))  # inclusive

SENSITIVE_RESOURCE_TYPES = {"secret", "user", "permission", "jira_config", "mentrix_companion"}


def _is_off_hours(dt: datetime) -> bool:
    return OFF_HOURS_START <= dt.hour <= OFF_HOURS_END


def run_anomaly_scan(db: Session, *, lookback_hours: int = 24) -> dict[str, Any]:
    """Scan the last `lookback_hours` of PermissionAudit + AuditLog rows for
    known anomaly shapes. Returns {"findings": [...], "scanned": {...}}."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    perm_rows = db.query(PermissionAudit).filter(PermissionAudit.created_at >= cutoff).all()
    audit_rows = db.query(AuditLog).filter(AuditLog.created_at >= cutoff).all()

    findings: list[dict[str, Any]] = []
    findings.extend(_scan_denial_spikes(perm_rows))
    findings.extend(_scan_ip_churn(audit_rows))
    findings.extend(_scan_sensitive_bursts(audit_rows))
    findings.extend(_scan_off_hours_sensitive_access(audit_rows))

    return {
        "findings": findings,
        "scanned": {
            "permission_audits": len(perm_rows),
            "audit_logs": len(audit_rows),
            "lookback_hours": lookback_hours,
        },
    }


def _scan_denial_spikes(perm_rows: list[PermissionAudit]) -> list[dict[str, Any]]:
    by_user: dict[int | None, list[PermissionAudit]] = defaultdict(list)
    for row in perm_rows:
        if row.result in ("denied", "pending_approval"):
            by_user[row.user_id].append(row)

    findings = []
    for user_id, rows in by_user.items():
        if len(rows) < DENIAL_SPIKE_THRESHOLD:
            continue
        denied = [r for r in rows if r.result == "denied"]
        severity = "high" if len(denied) >= DENIAL_SPIKE_THRESHOLD else "medium"
        actions = sorted({r.action for r in rows})
        findings.append(
            {
                "kind": "permission_denial_spike",
                "severity": severity,
                "user_id": user_id,
                "count": len(rows),
                "actions": actions,
                "description": (
                    f"User {user_id} triggered {len(rows)} denied/pending-approval "
                    f"permission checks in the scan window across {len(actions)} action(s) "
                    f"({', '.join(actions[:5])}{'...' if len(actions) > 5 else ''}) — "
                    "consistent with probing for an accessible action or a compromised session."
                ),
                "evidence_ids": [r.id for r in rows[:20]],
            }
        )
    return findings


def _scan_ip_churn(audit_rows: list[AuditLog]) -> list[dict[str, Any]]:
    by_user: dict[int | None, set[str]] = defaultdict(set)
    rows_by_user: dict[int | None, list[AuditLog]] = defaultdict(list)
    for row in audit_rows:
        if row.user_id is None or not row.ip_address:
            continue
        by_user[row.user_id].add(row.ip_address)
        rows_by_user[row.user_id].append(row)

    findings = []
    for user_id, ips in by_user.items():
        if len(ips) < IP_CHURN_THRESHOLD:
            continue
        findings.append(
            {
                "kind": "ip_churn",
                "severity": "medium",
                "user_id": user_id,
                "count": len(ips),
                "ip_addresses": sorted(ips),
                "description": (
                    f"User {user_id} was active from {len(ips)} distinct IP addresses in the "
                    "scan window — possible credential sharing or session hijack."
                ),
                "evidence_ids": [r.id for r in rows_by_user[user_id][:20]],
            }
        )
    return findings


def _scan_sensitive_bursts(audit_rows: list[AuditLog]) -> list[dict[str, Any]]:
    by_user: dict[int | None, list[AuditLog]] = defaultdict(list)
    for row in audit_rows:
        if row.resource_type in SENSITIVE_RESOURCE_TYPES:
            by_user[row.user_id].append(row)

    findings = []
    for user_id, rows in by_user.items():
        if len(rows) < SENSITIVE_BURST_THRESHOLD:
            continue
        resource_types = sorted({r.resource_type for r in rows})
        findings.append(
            {
                "kind": "sensitive_resource_burst",
                "severity": "high",
                "user_id": user_id,
                "count": len(rows),
                "resource_types": resource_types,
                "description": (
                    f"User {user_id} touched sensitive resources ({', '.join(resource_types)}) "
                    f"{len(rows)} times in the scan window — check for mass export/deletion "
                    "or exfiltration."
                ),
                "evidence_ids": [r.id for r in rows[:20]],
            }
        )
    return findings


def _scan_off_hours_sensitive_access(audit_rows: list[AuditLog]) -> list[dict[str, Any]]:
    findings = []
    for row in audit_rows:
        if row.resource_type not in SENSITIVE_RESOURCE_TYPES:
            continue
        created_at = row.created_at
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if not _is_off_hours(created_at):
            continue
        findings.append(
            {
                "kind": "off_hours_sensitive_access",
                "severity": "low",
                "user_id": row.user_id,
                "count": 1,
                "resource_types": [row.resource_type],
                "description": (
                    f"User {row.user_id} performed '{row.action}' on {row.resource_type} "
                    f"at {created_at.isoformat()} UTC, outside normal working hours."
                ),
                "evidence_ids": [row.id],
            }
        )
    return findings

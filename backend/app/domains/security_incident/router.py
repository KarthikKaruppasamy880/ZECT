"""Phase 9 — Security findings, incidents, detection ingest, containment stubs."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.adapters.detection_audit import AuditTrailDetectionProvider
from app.adapters.detection_provider import normalize_finding
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import log_audit, require_authentication, require_role
from app.infrastructure.database import get_db
from app.models import SecurityFinding, SecurityIncident
from app.security.redact import redact_secrets

router = APIRouter(prefix="/api/security", tags=["security-incident"])

# In-memory replay / rate-limit (process-local; sufficient for Stage C spine)
_SEEN_EVENT_IDS: dict[str, float] = {}
_RATE_BUCKET: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_PER_MIN = int(os.getenv("SECURITY_INGEST_RATE_LIMIT", "60"))
_REPLAY_TTL_S = 3600


def _correlation_id() -> str:
    return uuid.uuid4().hex[:16]


def _prune_replay() -> None:
    now = time.time()
    dead = [k for k, ts in _SEEN_EVENT_IDS.items() if now - ts > _REPLAY_TTL_S]
    for k in dead:
        _SEEN_EVENT_IDS.pop(k, None)


def _rate_limit(key: str) -> None:
    now = time.time()
    bucket = _RATE_BUCKET[key]
    _RATE_BUCKET[key] = [t for t in bucket if now - t < 60]
    if len(_RATE_BUCKET[key]) >= _RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Detection ingest rate limit exceeded")
    _RATE_BUCKET[key].append(now)


def _serialize_finding(f: SecurityFinding) -> dict[str, Any]:
    return {
        "id": f.id,
        "fingerprint": f.fingerprint,
        "source": f.source,
        "kind": f.kind,
        "severity": f.severity,
        "status": f.status,
        "title": f.title,
        "description": f.description,
        "host": f.host,
        "user_ref": f.user_ref,
        "rule_id": f.rule_id,
        "indicators": f.indicators_json or {},
        "correlation_id": f.correlation_id,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _serialize_incident(i: SecurityIncident) -> dict[str, Any]:
    return {
        "id": i.id,
        "finding_id": i.finding_id,
        "status": i.status,
        "summary": i.summary,
        "severity": i.severity,
        "confidence": i.confidence,
        "jira_key": i.jira_key,
        "slack_ts": i.slack_ts,
        "approval_status": i.approval_status,
        "approved_by": i.approved_by,
        "timeline": i.timeline_json or [],
        "recommended_actions": i.recommended_actions_json or [],
        "correlation_id": i.correlation_id,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def persist_normalized_findings(db: Session, findings: list[dict[str, Any]]) -> list[SecurityFinding]:
    """Upsert by fingerprint — open findings are refreshed; duplicates skipped."""
    saved: list[SecurityFinding] = []
    for nf in findings:
        fp = nf.get("fingerprint") or hashlib.sha256(
            json.dumps(nf, sort_keys=True, default=str).encode()
        ).hexdigest()[:40]
        existing = (
            db.query(SecurityFinding)
            .filter(SecurityFinding.fingerprint == fp, SecurityFinding.status.in_(("open", "drafted")))
            .first()
        )
        if existing:
            saved.append(existing)
            continue
        row = SecurityFinding(
            fingerprint=fp,
            source=nf.get("source") or "detection_provider",
            kind=str(nf.get("kind") or "alert")[:120],
            severity=str(nf.get("severity") or "medium")[:32],
            status="open",
            title=str(nf.get("title") or "")[:250],
            description=str(redact_secrets(nf.get("description") or ""))[:8000],
            host=str(nf.get("host") or "")[:200],
            user_ref=str(nf.get("user_ref") or "")[:200],
            rule_id=str(nf.get("rule_id") or "")[:200],
            raw_event_json=json.dumps(nf.get("raw") or nf, default=str)[:20000],
            indicators_json=nf.get("indicators") or {},
            correlation_id=nf.get("correlation_id") or _correlation_id(),
        )
        db.add(row)
        saved.append(row)
    db.commit()
    for r in saved:
        db.refresh(r)
    return saved


# ---------------------------------------------------------------------------
# Scan / list
# ---------------------------------------------------------------------------

@router.post("/scan")
@require_authentication
def run_security_scan(
    lookback_hours: int = 24,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run Detection Provider (audit_trail) and persist findings."""
    provider = AuditTrailDetectionProvider()
    result = provider.collect(db, lookback_hours=lookback_hours)
    rows = persist_normalized_findings(db, result.get("findings") or [])
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="security_scan",
        resource_type="security_finding",
        details={"provider": provider.name, "new_or_open": len(rows), "scanned": result.get("scanned")},
    )
    return {
        "provider": provider.name,
        "scanned": result.get("scanned"),
        "findings": [_serialize_finding(r) for r in rows],
    }


@router.get("/findings")
@require_authentication
def list_findings(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(SecurityFinding)
    if status:
        q = q.filter(SecurityFinding.status == status)
    rows = q.order_by(SecurityFinding.created_at.desc()).limit(min(limit, 200)).all()
    return [_serialize_finding(r) for r in rows]


@router.get("/incidents")
@require_authentication
def list_incidents(
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(SecurityIncident).order_by(SecurityIncident.created_at.desc()).limit(min(limit, 200)).all()
    return [_serialize_incident(r) for r in rows]


# ---------------------------------------------------------------------------
# Stage B — draft / approve / Jira / Slack
# ---------------------------------------------------------------------------

class DraftIncidentRequest(BaseModel):
    finding_id: int
    summary: Optional[str] = None
    confidence: str = "medium"
    recommended_actions: list[str] = Field(default_factory=list)


@router.post("/incidents/draft")
@require_authentication
def draft_incident(
    req: DraftIncidentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    finding = db.query(SecurityFinding).filter(SecurityFinding.id == req.finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")
    summary = (req.summary or finding.title or finding.kind)[:250]
    description = redact_secrets(finding.description or "")
    incident = SecurityIncident(
        finding_id=finding.id,
        status="draft",
        summary=summary,
        severity=finding.severity,
        confidence=req.confidence,
        approval_status="pending",
        timeline_json=[{"at": datetime.now(timezone.utc).isoformat(), "event": "draft_created"}],
        recommended_actions_json=req.recommended_actions
        or [
            "Review audit evidence",
            "Confirm affected asset/user",
            "Approve Jira incident creation",
        ],
        correlation_id=finding.correlation_id or _correlation_id(),
    )
    finding.status = "drafted"
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return {
        "incident": _serialize_incident(incident),
        "finding": _serialize_finding(finding),
        "jira_preview": {
            "summary": f"[ZECT Security] {summary}",
            "description": description[:4000],
            "severity": finding.severity,
            "detection_source": finding.source,
            "rule_id": finding.rule_id,
            "host": finding.host,
            "correlation_id": incident.correlation_id,
        },
    }


class ApproveIncidentRequest(BaseModel):
    approved: bool = True
    create_jira: bool = True
    notify_slack: bool = True
    project_key: Optional[str] = None


@router.post("/incidents/{incident_id}/approve")
@require_role("admin", "lead")
def approve_incident(
    incident_id: int,
    req: ApproveIncidentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    incident = db.query(SecurityIncident).filter(SecurityIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(404, "Incident not found")
    finding = db.query(SecurityFinding).filter(SecurityFinding.id == incident.finding_id).first()
    if not req.approved:
        incident.approval_status = "rejected"
        incident.status = "closed"
        db.commit()
        return _serialize_incident(incident)

    incident.approval_status = "approved"
    incident.approved_by = getattr(current_user, "email", None) or "admin"
    timeline = list(incident.timeline_json or [])
    timeline.append({"at": datetime.now(timezone.utc).isoformat(), "event": "approved", "by": incident.approved_by})

    jira_key = ""
    if req.create_jira:
        from app.services.mcp.hub import execute_tool

        project_key = req.project_key or os.getenv("SECURITY_JIRA_PROJECT_KEY", "SEC")
        body = (
            f"*Severity:* {incident.severity}\n"
            f"*Confidence:* {incident.confidence}\n"
            f"*Detection source:* {finding.source if finding else ''}\n"
            f"*Rule:* {finding.rule_id if finding else ''}\n"
            f"*Host:* {finding.host if finding else ''}\n"
            f"*User:* {finding.user_ref if finding else ''}\n"
            f"*Correlation:* {incident.correlation_id}\n\n"
            f"{redact_secrets(finding.description if finding else '')}\n\n"
            f"*Recommended actions:*\n"
            + "\n".join(f"- {a}" for a in (incident.recommended_actions_json or []))
        )
        outcome = execute_tool(
            db,
            server_id="jira",
            tool_name="create_issue",
            arguments={
                "project": project_key,
                "summary": f"[ZECT Security] {incident.summary}"[:250],
                "type": os.getenv("SECURITY_JIRA_ISSUE_TYPE", "Bug"),
                "description": body[:8000],
            },
            user_email=incident.approved_by,
        )
        result = outcome.get("result") or {}
        jira_key = str(result.get("key") or "")
        if jira_key:
            incident.jira_key = jira_key
            incident.status = "created"
            timeline.append({"at": datetime.now(timezone.utc).isoformat(), "event": "jira_created", "key": jira_key})
            if finding:
                finding.status = "ticketed"

    slack_ts = ""
    if req.notify_slack and jira_key:
        channel = os.getenv("SECURITY_SLACK_CHANNEL", "").strip()
        if channel:
            from app.services.mcp.hub import execute_tool

            text = (
                f":shield: Security incident *{jira_key}* — {incident.summary} "
                f"(severity={incident.severity}, correlation={incident.correlation_id})"
            )
            outcome = execute_tool(
                db,
                server_id="slack",
                tool_name="send_message",
                arguments={"channel": channel.lstrip("#"), "text": text},
                user_email=incident.approved_by,
            )
            result = outcome.get("result") or {}
            slack_ts = str(result.get("ts") or result.get("id") or "")
            if slack_ts:
                incident.slack_ts = slack_ts
                incident.status = "notified"
                timeline.append({"at": datetime.now(timezone.utc).isoformat(), "event": "slack_notified"})

    incident.timeline_json = timeline
    db.commit()
    db.refresh(incident)
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="security_incident_approve",
        resource_type="security_incident",
        resource_id=incident.id,
        details={"jira_key": jira_key, "slack": bool(slack_ts)},
    )
    return _serialize_incident(incident)


# ---------------------------------------------------------------------------
# Stage C — external Detection Provider webhook
# ---------------------------------------------------------------------------

@router.post("/detection/ingest")
async def ingest_detection_event(
    request: Request,
    db: Session = Depends(get_db),
    x_zect_signature: str | None = Header(default=None, alias="X-ZECT-Signature"),
    x_event_id: str | None = Header(default=None, alias="X-ZECT-Event-Id"),
):
    """Ingest normalized detection events from an external Detection Provider.

    Requires SECURITY_DETECTION_WEBHOOK_SECRET. Signature: sha256=<hmac hex of body>.
    Never treats alert description as executable instructions.
    """
    secret = os.getenv("SECURITY_DETECTION_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(403, "Detection webhook secret not configured")

    body = await request.body()
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not x_zect_signature or not hmac.compare_digest(x_zect_signature, expected):
        raise HTTPException(403, "Invalid detection webhook signature")

    _prune_replay()
    event_id = x_event_id or hashlib.sha256(body).hexdigest()[:32]
    if event_id in _SEEN_EVENT_IDS:
        return {"status": "duplicate", "event_id": event_id}
    _rate_limit("detection_ingest")
    _SEEN_EVENT_IDS[event_id] = time.time()

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(400, "Invalid JSON") from e

    # Support single alert or {alerts: [...]}
    alerts = payload.get("alerts") if isinstance(payload, dict) else None
    if alerts is None:
        alerts = [payload]
    if not isinstance(alerts, list):
        raise HTTPException(400, "alerts must be a list")

    normalized = []
    for alert in alerts[:50]:
        if not isinstance(alert, dict):
            continue
        # Strip any instruction-like keys from being trusted as commands
        safe = {k: v for k, v in alert.items() if k.lower() not in ("command", "script", "shell", "contain")}
        nf = normalize_finding(safe, source="detection_provider")
        nf["fingerprint"] = hashlib.sha256(
            json.dumps(
                {"rule": nf["rule_id"], "host": nf["host"], "kind": nf["kind"], "title": nf["title"]},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:40]
        nf["correlation_id"] = _correlation_id()
        nf["raw"] = safe  # immutable original (sanitized keys only)
        normalized.append(nf)

    rows = persist_normalized_findings(db, normalized)
    return {
        "status": "accepted",
        "event_id": event_id,
        "finding_ids": [r.id for r in rows],
        "count": len(rows),
    }


# ---------------------------------------------------------------------------
# Stage D — containment stubs (disabled by default)
# ---------------------------------------------------------------------------

class ContainRequest(BaseModel):
    action: str  # quarantine_file | isolate_endpoint | kill_process | disable_account
    target: str = ""
    reason: str = ""
    confirm: bool = False


@router.post("/contain")
@require_role("admin")
def containment_stub(
    req: ContainRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Automatic response is disabled by default (Upgrade.md Phase 9).

    Set SECURITY_AUTO_CONTAIN=1 and confirm=true only after policy validation —
    this endpoint still refuses to execute host changes in Stage D.
    """
    enabled = os.getenv("SECURITY_AUTO_CONTAIN", "").strip() in ("1", "true", "yes")
    if not enabled or not req.confirm:
        log_audit(
            db=db,
            user_id=getattr(current_user, "user_id", None) or 0,
            action="security_contain_blocked",
            resource_type="security_contain",
            details={"action": req.action, "target": req.target, "reason": req.reason, "enabled": enabled},
        )
        raise HTTPException(
            403,
            "Containment actions are disabled by default. "
            "Enable SECURITY_AUTO_CONTAIN and pass confirm=true only after detection rules, "
            "approvals, and rollback are validated. No host changes were performed.",
        )
    # Even when enabled, Stage D does not perform real containment.
    raise HTTPException(
        501,
        f"Containment action '{req.action}' is not implemented yet — stub only (no host change).",
    )


@router.get("/enrichment/templates")
@require_authentication
def list_enrichment_templates(current_user: CurrentUser = Depends(get_current_user)):
    """Approved endpoint snapshot query templates only (no LLM-arbitrary queries)."""
    return {
        "templates": [
            {"id": "process_parent", "description": "Process and parent process"},
            {"id": "exe_path_hash", "description": "Executable path and file hash"},
            {"id": "code_signature", "description": "Code signature status"},
            {"id": "listening_ports", "description": "Listening ports"},
            {"id": "network_connections", "description": "Active network connections"},
            {"id": "logged_in_users", "description": "Logged-in users"},
            {"id": "startup_items", "description": "Startup items"},
        ],
        "note": "Templates are listed for policy planning; execution requires a configured Endpoint Snapshot adapter (Stage D+).",
    }


class MalwareScanRequest(BaseModel):
    path: str = Field(..., min_length=1)
    quarantine: bool = False
    workspace: Optional[str] = None


@router.get("/malware/status")
@require_authentication
def malware_status(current_user: CurrentUser = Depends(get_current_user)):
    """ZECT Security Agent malware engine status (fail closed when degraded)."""
    from app.adapters.detection_malware import malware_engine_status

    return malware_engine_status()


@router.post("/malware/scan")
@require_authentication
def malware_scan(
    req: MalwareScanRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scan an allowlisted path with ZECT Security Agent. Never reports clean without engine."""
    from pathlib import Path as P

    from app.adapters.detection_malware import quarantine_file, scan_file
    from app.infrastructure.allowed_paths import path_under_allowed_roots

    try:
        target = path_under_allowed_roots(req.path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"path_not_allowlisted:{exc}") from exc

    result = scan_file(target)
    if not result.get("ok"):
        raise HTTPException(503 if result.get("error") == "engine_unavailable" else 400, result)

    if result.get("infected"):
        finding = result.get("finding") or {}
        fp = hashlib.sha256(
            f"malware:{target}:{result.get('signature')}".encode()
        ).hexdigest()[:40]
        existing = db.query(SecurityFinding).filter(SecurityFinding.fingerprint == fp).first()
        if not existing:
            row = SecurityFinding(
                fingerprint=fp,
                source="zect_security_agent",
                kind="malware",
                severity="high",
                status="open",
                title=finding.get("title") or "Malware detected",
                description=finding.get("description") or str(target),
                host="",
                user_ref=str(getattr(current_user, "user_id", "") or ""),
                rule_id=str(result.get("signature") or "malware")[:200],
                indicators_json={"file": str(target), "signature": result.get("signature")},
                correlation_id=_correlation_id(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            result["finding_id"] = row.id
        else:
            result["finding_id"] = existing.id

        if req.quarantine:
            ws = None
            if req.workspace:
                try:
                    ws = path_under_allowed_roots(req.workspace)
                except Exception:  # noqa: BLE001
                    ws = None
            q = quarantine_file(target, workspace=ws)
            result["quarantine"] = q
            log_audit(
                db=db,
                user_id=getattr(current_user, "user_id", None) or 0,
                action="security_malware_quarantine",
                resource_type="file",
                details=q,
            )

    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="security_malware_scan",
        resource_type="file",
        details={"path": str(target), "infected": bool(result.get("infected"))},
    )
    return result

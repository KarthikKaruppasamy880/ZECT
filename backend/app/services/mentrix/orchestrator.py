"""MentrixOrchestrator — shared typed/spoken tool path (PA-1).

Feature flag: MENTRIX_PA1_ORCHESTRATOR (default on). Set to 0/false/off for
legacy companion permission+_exec_tool path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy.orm import Session

from app.services.mentrix.command_schema import (
    MUTATING_INTENTS,
    MentrixCommand,
    risk_for_intent,
)
from app.services.mentrix.no_delete_policy import is_delete_intent, refuse_delete
from app.services.mentrix.permission_broker import ALWAYS_CONFIRM_TOOLS
from app.services.mentrix.policy_services import (
    ApprovalService,
    AuditService,
    PermissionService,
)


def pa1_orchestrator_enabled() -> bool:
    raw = (os.getenv("MENTRIX_PA1_ORCHESTRATOR") or "1").strip().lower()
    return raw not in ("0", "false", "off", "no")


@dataclass
class OrchestratorOutcome:
    status: str  # executed | denied | pending_confirm | blocked
    command: MentrixCommand
    permission: dict[str, Any] = field(default_factory=dict)
    pending: dict[str, Any] | None = None
    result: dict[str, Any] = field(default_factory=dict)


ExecToolFn = Callable[..., dict[str, Any]]


class MentrixOrchestrator:
    """Normalize companion tools through schema → policy → exec → verify → audit."""

    def __init__(
        self,
        *,
        permissions: PermissionService | None = None,
        approvals: ApprovalService | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self.permissions = permissions or PermissionService()
        self.approvals = approvals or ApprovalService()
        self.audit = audit or AuditService()

    def execute_tool(
        self,
        db: Session,
        intent: str,
        params: dict[str, Any] | None = None,
        *,
        user_id: int | None = None,
        project_id: int | None = None,
        project_key: str = "",
        created_by: str = "",
        user_confirmed: bool = False,
        correlation_id: str | None = None,
        idempotency_key: str = "",
        exec_tool: ExecToolFn,
    ) -> OrchestratorOutcome:
        cmd = MentrixCommand(
            intent=intent,
            params=dict(params or {}),
            user_id=user_id,
            project_id=project_id,
            project_key=project_key or "",
            created_by=created_by or "",
            correlation_id=correlation_id or str(uuid4()),
            risk=risk_for_intent(intent),
            idempotency_key=idempotency_key or "",
        )

        # Hard no-delete before any permission dance
        if is_delete_intent(intent) or cmd.risk == "never":
            cmd.policy_decision = "deny"
            refused = refuse_delete(intent=intent)
            cmd.result = refused
            self.audit.decision(db, cmd, decision="deny_delete")
            self.audit.tool_result(db, cmd, result="denied")
            return OrchestratorOutcome(
                status="denied",
                command=cmd,
                permission={"result": "denied", "reason": "no_delete_policy"},
                result=refused,
            )

        # Emergency stop blocks mutating intents
        if intent in MUTATING_INTENTS:
            from app.security.emergency_stop import is_emergency_stop_active

            if is_emergency_stop_active(db):
                cmd.policy_decision = "deny"
                blocked = {
                    "ok": False,
                    "error": "emergency_stop_active",
                    "note": "Global emergency stop is active",
                }
                cmd.result = blocked
                self.audit.decision(db, cmd, decision="deny_emergency_stop")
                self.audit.tool_result(db, cmd, result="denied")
                return OrchestratorOutcome(
                    status="blocked",
                    command=cmd,
                    permission={"result": "denied", "reason": "emergency_stop"},
                    result=blocked,
                )

        perm = self.permissions.check(db, cmd, user_confirmed=user_confirmed)
        cmd.capability = str(perm.get("action") or "")
        cmd.approval_id = str(perm["audit_id"]) if perm.get("audit_id") is not None else None

        if perm.get("result") == "denied":
            cmd.policy_decision = "deny"
            denied = {"ok": False, "error": "denied", "permission": perm}
            cmd.result = denied
            self.audit.tool_result(db, cmd, result="denied")
            return OrchestratorOutcome(
                status="denied",
                command=cmd,
                permission=perm,
                result=denied,
            )

        if self.approvals.needs_user_confirm(intent, perm) and not user_confirmed:
            cmd.policy_decision = "needs_approval"
            pending = self.approvals.pending_payload(cmd, perm)
            self.audit.decision(db, cmd, decision="needs_approval")
            return OrchestratorOutcome(
                status="pending_confirm",
                command=cmd,
                permission=perm,
                pending=pending,
                result={"ok": False, "error": "pending_confirm"},
            )

        cmd.policy_decision = "allow"
        result = exec_tool(
            db,
            intent,
            cmd.params,
            project_key=project_key,
            created_by=created_by,
            user_id=user_id,
            project_id=project_id,
            correlation_id=cmd.correlation_id,
        )
        if not isinstance(result, dict):
            result = {"ok": False, "error": "invalid_tool_result"}

        # Structured verification stub (PA-4/5 deepen read-back)
        verification = _verify_result(intent, result)
        cmd.verification = verification
        cmd.result = result
        if verification and not result.get("verification"):
            result = {**result, "verification": verification}

        outcome = "ok" if result.get("ok") else "error"
        self.audit.tool_result(db, cmd, result=outcome)
        self.audit.decision(
            db,
            cmd,
            decision="executed",
            extra={"ok": bool(result.get("ok")), "verification": verification},
        )
        return OrchestratorOutcome(
            status="executed",
            command=cmd,
            permission=perm,
            result=result,
        )


def _verify_result(intent: str, result: dict[str, Any]) -> dict[str, Any]:
    """Best-effort structured verification hints (not a claim of success alone)."""
    v: dict[str, Any] = {"intent": intent}
    if result.get("run_id") is not None:
        v["provider_id"] = f"mentrix_run:{result['run_id']}"
        v["kind"] = "run_id"
    elif result.get("path"):
        v["path"] = str(result["path"])[:500]
        v["kind"] = "filesystem"
        if result.get("bytes") is not None:
            v["bytes"] = result["bytes"]
    elif result.get("browser"):
        br = result["browser"] if isinstance(result["browser"], dict) else {}
        v["kind"] = "browser"
        v["status"] = br.get("status")
        if br.get("url"):
            v["url"] = str(br["url"])[:500]
    elif result.get("pr_url"):
        v["kind"] = "pr_url"
        v["provider_id"] = str(result["pr_url"])[:500]
    elif intent.startswith("computer_") or intent.startswith("desktop_"):
        v["kind"] = "desktop_queued"
        v["note"] = "Electron Computer Mode must confirm active window / read-back"
        v["desktop"] = result.get("desktop") or intent
    else:
        v["kind"] = "ack"
        v["ok"] = bool(result.get("ok"))
    return v

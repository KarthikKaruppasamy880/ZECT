"""Thin PA-1 policy wrappers around existing permission / audit spine."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.domains.audit.audit_trail import log_audit
from app.services.mentrix.command_schema import MentrixCommand
from app.services.mentrix.permission_broker import (
    ALWAYS_CONFIRM_TOOLS,
    check_tool_permission,
    log_mentrix_tool,
)


class PermissionService:
    """Capability checks for companion tools."""

    def check(
        self,
        db: Session,
        cmd: MentrixCommand,
        *,
        user_confirmed: bool = False,
    ) -> dict[str, Any]:
        return check_tool_permission(
            db,
            cmd.intent,
            user_id=cmd.user_id,
            project_id=cmd.project_id,
            user_confirmed=user_confirmed,
        )


class ApprovalService:
    """Approval / confirm gating (immutable preview comes in PA-3)."""

    def needs_user_confirm(self, intent: str, perm: dict[str, Any]) -> bool:
        if perm.get("result") == "denied":
            return False
        if perm.get("needs_confirm"):
            return True
        if perm.get("result") == "pending_approval":
            return True
        return intent in ALWAYS_CONFIRM_TOOLS

    def pending_payload(
        self, cmd: MentrixCommand, perm: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "tool": cmd.intent,
            "args": cmd.params,
            "audit_id": perm.get("audit_id"),
            "correlation_id": cmd.correlation_id,
            "reason": f"Mentrix needs your permission to run `{cmd.intent}`",
            "always_ask": cmd.intent in ALWAYS_CONFIRM_TOOLS,
        }


class AuditService:
    """Structured audit for orchestrated commands."""

    def tool_result(
        self,
        db: Session,
        cmd: MentrixCommand,
        *,
        result: str,
    ) -> None:
        log_mentrix_tool(
            db,
            cmd.intent,
            args=cmd.params,
            result=result,
            user_id=cmd.user_id,
        )

    def decision(
        self,
        db: Session,
        cmd: MentrixCommand,
        *,
        decision: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        details = {
            "correlation_id": cmd.correlation_id,
            "intent": cmd.intent,
            "decision": decision,
            "risk": cmd.risk,
            "capability": cmd.capability,
            **(extra or {}),
        }
        log_audit(
            db,
            action=f"mentrix_orch_{decision}",
            resource_type="mentrix_orchestrator",
            resource_name=cmd.intent,
            details=json.dumps(details)[:4000],
            user_id=cmd.user_id,
        )

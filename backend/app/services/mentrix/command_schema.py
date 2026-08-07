"""Stable Mentrix command schema (PA-1).

Spoken and typed companion tools share this record shape for policy, approval,
audit, and verification — ForgeLoop Delivery is unchanged.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class MentrixCommand:
    """One tool invocation under MentrixOrchestrator."""

    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    actor: str = "companion"
    user_id: int | None = None
    project_id: int | None = None
    project_key: str = ""
    created_by: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    capability: str = ""
    target: str = ""
    risk: str = "low"  # low | medium | high | never
    policy_decision: str = ""  # allow | deny | needs_approval
    approval_id: str | None = None
    idempotency_key: str = ""
    verification: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        """JSON-safe summary (no secrets)."""
        d = asdict(self)
        params = dict(d.get("params") or {})
        for k in list(params):
            lk = str(k).lower()
            if any(s in lk for s in ("password", "token", "secret", "api_key", "apikey")):
                params[k] = "[redacted]"
        d["params"] = params
        return d


# Side-effect tools blocked when emergency stop is active
MUTATING_INTENTS = frozenset(
    {
        "start_delivery",
        "approve_delivery",
        "create_pr",
        "slack_send",
        "email_send",
        "docs_draft",
        "desktop_write_note",
        "computer_click",
        "computer_type",
        "computer_scroll",
        "computer_open_app",
        "desktop_open_presentation",
        "browser_navigate",
        "browser_fill",
        "jira_comment_pr",
        "file_security_ticket",
        "media_generate",
        "media_edit",
        "image_avatar",
    }
)

HIGH_RISK_INTENTS = frozenset(
    {
        "slack_send",
        "email_send",
        "approve_delivery",
        "create_pr",
        "computer_click",
        "computer_type",
        "browser_fill",
        "desktop_delete",
        "delete_file",
    }
)


def risk_for_intent(intent: str) -> str:
    if intent in ("desktop_delete", "delete_file"):
        return "never"
    if intent in HIGH_RISK_INTENTS:
        return "high"
    if intent in MUTATING_INTENTS:
        return "medium"
    return "low"

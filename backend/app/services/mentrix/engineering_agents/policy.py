"""High-risk action policy — L3 Autonomous does not bypass permissions."""

from __future__ import annotations

from typing import Any

# ALLOW | CONFIRM | DENY — L3 never upgrades DENY→ALLOW or CONFIRM→ALLOW silently
HIGH_RISK_POLICY: dict[str, str] = {
    "git_push": "CONFIRM",
    "pr_merge": "CONFIRM",
    "deployment": "CONFIRM",
    "secret_access": "DENY",
    "external_message": "CONFIRM",
    "destructive_filesystem": "DENY",
    "classified_data_exfil": "DENY",
}


def evaluate_high_risk_action(
    action: str,
    *,
    autonomy: str = "L3",
    data_classification: str = "internal",
) -> dict[str, Any]:
    """Return policy decision. Autonomy level cannot bypass DENY/CONFIRM."""
    key = (action or "").strip().lower()
    decision = HIGH_RISK_POLICY.get(key, "CONFIRM")
    classification = (data_classification or "internal").strip().lower()
    if classification in ("confidential", "restricted", "secret") and key in (
        "external_message",
        "git_push",
        "classified_data_exfil",
    ):
        decision = "DENY"
    # L3 still obeys
    allowed = decision == "ALLOW"
    return {
        "action": key,
        "decision": decision,
        "autonomy": autonomy,
        "data_classification": classification,
        "allowed": allowed,
        "needs_confirm": decision == "CONFIRM",
        "denied": decision == "DENY",
        "l3_bypasses_permissions": False,
    }

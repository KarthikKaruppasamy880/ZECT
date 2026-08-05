"""ZECT Detection Provider interface — Phase 9.

Product surfaces never brand third-party SIEM/EDR tools. Adapters may wrap
external systems behind this interface; attribution belongs in THIRD_PARTY_NOTICES.
"""

from __future__ import annotations

from typing import Any, Protocol


class DetectionProvider(Protocol):
    """Collect and normalize security findings."""

    name: str

    def collect(self, db: Any, *, lookback_hours: int = 24) -> dict[str, Any]:
        """Return {findings: [...], scanned: {...}} with normalized findings."""
        ...


def normalize_finding(raw: dict[str, Any], *, source: str = "detection_provider") -> dict[str, Any]:
    """Normalize heterogeneous alert payloads into ZECT finding fields."""
    return {
        "source": source,
        "kind": raw.get("kind") or raw.get("rule") or raw.get("rule_id") or "external_alert",
        "severity": (raw.get("severity") or raw.get("level") or "medium").lower(),
        "title": (raw.get("title") or raw.get("summary") or raw.get("description") or "Security alert")[:250],
        "description": str(raw.get("description") or raw.get("full_log") or raw.get("title") or "")[:8000],
        "host": str(raw.get("host") or raw.get("agent") or raw.get("hostname") or "")[:200],
        "user_ref": str(raw.get("user") or raw.get("user_id") or raw.get("user_ref") or "")[:200],
        "rule_id": str(raw.get("rule_id") or raw.get("rule") or "")[:200],
        "indicators": {
            "process": raw.get("process"),
            "file": raw.get("file"),
            "network": raw.get("network") or raw.get("network_indicators"),
            "hashes": raw.get("hashes") or raw.get("hash"),
        },
        "raw": raw,
    }

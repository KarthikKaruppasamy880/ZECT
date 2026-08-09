"""SecurityScanner interface — product layer over ZECT Security Agent (P3)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SecurityScanner(Protocol):
    """Native scanner contract. Implementations must not invent a parallel Security Agent."""

    name: str

    def scan(self, *, target: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


class MentrixSecurityAgentScanner:
    """Adapter that reports Security Agent surface readiness (no foreign AV branding)."""

    name = "mentrix_security_agent"

    def scan(self, *, target: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "scanner": self.name,
            "target": target or "workspace",
            "findings": [],
            "route": "/security-incidents",
            "note": "Use ZECT Security Agent UI/API for incident workflow; native deep scanner deferred.",
            "context_keys": sorted((context or {}).keys()),
        }


def get_default_security_scanner() -> SecurityScanner:
    return MentrixSecurityAgentScanner()

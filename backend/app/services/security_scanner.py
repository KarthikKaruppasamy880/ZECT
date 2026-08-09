"""SecurityScanner — Mentrix Security Agent adapter with live DB findings (P3)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SecurityScanner(Protocol):
    """Native scanner contract. Implementations must not invent a parallel Security Agent."""

    name: str

    def scan(self, *, target: str = "", context: dict[str, Any] | None = None, db: Any = None) -> dict[str, Any]:
        ...


class MentrixSecurityAgentScanner:
    """Reads SecurityFinding / SecurityIncident — product Security Agent path only."""

    name = "mentrix_security_agent"

    def scan(self, *, target: str = "", context: dict[str, Any] | None = None, db: Any = None) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        incidents = 0
        if db is not None:
            try:
                from app.models import SecurityFinding, SecurityIncident

                incidents = db.query(SecurityIncident).count()
                rows = (
                    db.query(SecurityFinding)
                    .order_by(SecurityFinding.id.desc())
                    .limit(25)
                    .all()
                )
                for f in rows:
                    findings.append(
                        {
                            "id": f.id,
                            "title": getattr(f, "title", "") or "",
                            "severity": getattr(f, "severity", "") or "",
                            "kind": getattr(f, "kind", "") or "security",
                            "status": getattr(f, "status", "") or "",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                return {
                    "ok": False,
                    "scanner": self.name,
                    "target": target or "workspace",
                    "error": str(exc)[:300],
                    "findings": [],
                    "route": "/security-incidents",
                }

        return {
            "ok": True,
            "scanner": self.name,
            "target": target or "workspace",
            "findings": findings,
            "incident_count": incidents,
            "route": "/security-incidents",
            "note": "Findings sourced from ZECT Security Agent store; no foreign AV engine.",
            "context_keys": sorted((context or {}).keys()),
        }


def get_default_security_scanner() -> SecurityScanner:
    return MentrixSecurityAgentScanner()

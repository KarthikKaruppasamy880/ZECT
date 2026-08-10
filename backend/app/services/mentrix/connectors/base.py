"""Connector protocol + health row types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ConnectorCapability:
    name: str
    description: str = ""
    permission_requirement: str = "require_approval"
    scopes: list[str] = field(default_factory=list)
    kind: str = "read"  # read | write
    permission_policy: str = "CONFIRM"  # ALLOW | CONFIRM | DENY


@dataclass
class ConnectorHealth:
    id: str
    name: str
    status: str  # configured | ok | degraded | missing_creds | disabled | error
    transport: str  # native | mcp | desktop | browser
    detail: str = ""
    capabilities: list[ConnectorCapability] = field(default_factory=list)
    permission_requirement: str = "require_approval"
    auth_status: str = ""
    read_tools: list[str] = field(default_factory=list)
    write_tools: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        caps = [
            {
                "name": c.name,
                "description": c.description,
                "permission_requirement": c.permission_requirement,
                "scopes": c.scopes,
                "kind": c.kind,
                "permission_policy": c.permission_policy,
            }
            for c in self.capabilities
        ]
        reads = self.read_tools or [c["name"] for c in caps if c.get("kind") == "read"]
        writes = self.write_tools or [c["name"] for c in caps if c.get("kind") == "write"]
        policies = {str(c.get("permission_policy") or "CONFIRM").upper() for c in caps}
        if "DENY" in policies:
            agg_policy = "DENY"
        elif "CONFIRM" in policies or writes:
            agg_policy = "CONFIRM"
        else:
            agg_policy = "ALLOW"
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "health": self.status,
            "transport": self.transport,
            "detail": self.detail,
            "permission_requirement": self.permission_requirement,
            "permission_policy": agg_policy,
            "auth_status": self.auth_status or self.status,
            "read_tools": reads,
            "write_tools": writes,
            "capabilities": caps,
        }


class MentrixConnector(Protocol):
    id: str
    name: str

    def health(self) -> ConnectorHealth: ...

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]: ...

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


@dataclass
class ConnectorHealth:
    id: str
    name: str
    status: str  # configured | ok | degraded | missing_creds | disabled | error
    transport: str  # native | mcp | desktop | browser
    detail: str = ""
    capabilities: list[ConnectorCapability] = field(default_factory=list)
    permission_requirement: str = "require_approval"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "transport": self.transport,
            "detail": self.detail,
            "permission_requirement": self.permission_requirement,
            "capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "permission_requirement": c.permission_requirement,
                    "scopes": c.scopes,
                }
                for c in self.capabilities
            ],
        }


class MentrixConnector(Protocol):
    id: str
    name: str

    def health(self) -> ConnectorHealth: ...

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]: ...

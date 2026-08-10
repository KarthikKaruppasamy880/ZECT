"""MentrixConnector gateway — native → MCP → desktop/browser. Mentrix only; no second assistant."""

from __future__ import annotations

from app.services.mentrix.connectors.gateway import (
    MentrixConnector,
    connector_health_matrix,
    get_connector,
    list_connectors,
)

__all__ = [
    "MentrixConnector",
    "connector_health_matrix",
    "get_connector",
    "list_connectors",
]

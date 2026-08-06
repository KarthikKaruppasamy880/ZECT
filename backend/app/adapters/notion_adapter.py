"""Notion MCP stub — never claims success without tokens."""

from __future__ import annotations

import os
from typing import Any


def list_tools() -> list[dict[str, str]]:
    return [
        {"name": "status", "description": "Notion configuration status"},
        {"name": "search", "description": "Search Notion (requires tokens)"},
        {"name": "get_page", "description": "Get a Notion page (requires tokens)"},
    ]


def execute(tool_name: str, arguments: dict, *, config: dict | None = None, enabled: bool = True) -> dict[str, Any]:
    config = config or {}
    if not enabled:
        return {"status": "disabled", "server": "notion"}

    token = (
        (config.get("token") or "").strip()
        or (os.getenv("NOTION_API_TOKEN") or os.getenv("NOTION_TOKEN") or "").strip()
    )
    if tool_name == "status":
        if not token:
            return {
                "status": "not_configured",
                "message": "Notion not configured — set NOTION_API_TOKEN when ready",
                "configured": False,
            }
        return {"status": "configured", "configured": True, "message": "Token present (live calls not enabled in stub)"}

    if not token:
        return {
            "status": "not_configured",
            "message": "Notion not configured — set NOTION_API_TOKEN",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }

    # Stub only: refuse fake success even when a token env exists until a Later phase.
    return {
        "status": "not_configured",
        "message": "Notion adapter is a stub until a Later phase — no fake success",
        "dry_run": {"tool": tool_name, "arguments": arguments},
    }

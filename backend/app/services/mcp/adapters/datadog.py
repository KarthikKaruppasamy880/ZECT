from __future__ import annotations

import os
from typing import Any

import httpx


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    api_key = config.get("api_key") or os.getenv("DATADOG_API_KEY", "")
    app_key = config.get("app_key") or os.getenv("DATADOG_APP_KEY", "")
    site = config.get("site") or os.getenv("DATADOG_SITE", "datadoghq.com")
    if not api_key or not app_key:
        return {
            "status": "not_configured",
            "message": "Set DATADOG_API_KEY and DATADOG_APP_KEY",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }
    headers = {
        "DD-API-KEY": api_key,
        "DD-APPLICATION-KEY": app_key,
        "Content-Type": "application/json",
    }
    base = f"https://api.{site}"
    with httpx.Client(timeout=30.0, headers=headers) as client:
        if tool_name == "query_logs":
            query = arguments.get("query", "*")
            r = client.post(
                f"{base}/api/v2/logs/events/search",
                json={"filter": {"query": query}, "page": {"limit": 20}},
            )
            r.raise_for_status()
            return r.json()
        if tool_name == "list_monitors":
            r = client.get(f"{base}/api/v1/monitor")
            r.raise_for_status()
            return {"monitors": r.json()[:50] if isinstance(r.json(), list) else r.json()}
    return {"status": "unknown_tool", "tool": tool_name}

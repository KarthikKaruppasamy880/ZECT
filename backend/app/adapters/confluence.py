from __future__ import annotations

import os
from typing import Any

import httpx


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    base = (config.get("base_url") or os.getenv("MCP_CONFLUENCE_URL") or "").rstrip("/")
    email = config.get("email") or os.getenv("CONFLUENCE_EMAIL", "") or os.getenv("JIRA_EMAIL", "")
    token = config.get("token") or os.getenv("CONFLUENCE_API_TOKEN", "") or os.getenv("JIRA_API_TOKEN", "")
    if not base or not email or not token:
        return {
            "status": "not_configured",
            "message": "Configure MCP_CONFLUENCE_URL + credentials",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }
    auth = (email, token)
    with httpx.Client(timeout=30.0, auth=auth) as client:
        if tool_name == "search":
            q = arguments.get("query", "")
            r = client.get(f"{base}/rest/api/content/search", params={"cql": f'text ~ "{q}"', "limit": 10})
            r.raise_for_status()
            return r.json()
        if tool_name == "get_page":
            page_id = arguments["page_id"]
            r = client.get(f"{base}/rest/api/content/{page_id}", params={"expand": "body.storage"})
            r.raise_for_status()
            return r.json()
        if tool_name == "create_page":
            payload = {
                "type": "page",
                "title": arguments["title"],
                "space": {"key": arguments["space_key"]},
                "body": {
                    "storage": {
                        "value": arguments.get("body", "<p></p>"),
                        "representation": "storage",
                    }
                },
            }
            r = client.post(f"{base}/rest/api/content", json=payload)
            r.raise_for_status()
            return r.json()
    return {"status": "unknown_tool", "tool": tool_name}

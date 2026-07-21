from __future__ import annotations

import os
from typing import Any

import httpx


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    base = (config.get("base_url") or os.getenv("MCP_JIRA_URL") or "").rstrip("/")
    email = config.get("email") or os.getenv("JIRA_EMAIL", "")
    token = config.get("token") or os.getenv("JIRA_API_TOKEN", "")
    if not base or not email or not token:
        return {
            "status": "not_configured",
            "message": "Configure MCP_JIRA_URL + JIRA_EMAIL + JIRA_API_TOKEN (or server config)",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }
    auth = (email, token)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    with httpx.Client(timeout=30.0, auth=auth, headers=headers) as client:
        if tool_name == "search_issues":
            jql = arguments.get("jql", "ORDER BY updated DESC")
            r = client.get(f"{base}/rest/api/3/search", params={"jql": jql, "maxResults": 20})
            r.raise_for_status()
            return r.json()
        if tool_name == "get_issue":
            key = arguments["issue_key"]
            r = client.get(f"{base}/rest/api/3/issue/{key}")
            r.raise_for_status()
            return r.json()
        if tool_name == "create_issue":
            payload = {
                "fields": {
                    "project": {"key": arguments["project"]},
                    "summary": arguments["summary"],
                    "issuetype": {"name": arguments.get("type", "Task")},
                }
            }
            r = client.post(f"{base}/rest/api/3/issue", json=payload)
            r.raise_for_status()
            return r.json()
        if tool_name == "add_comment":
            key = arguments["issue_key"]
            r = client.post(
                f"{base}/rest/api/3/issue/{key}/comment",
                json={"body": arguments.get("body", "")},
            )
            r.raise_for_status()
            return r.json()
    return {"status": "unknown_tool", "tool": tool_name}

from __future__ import annotations

from typing import Any

from app.adapters.jira_env import jira_api_token, jira_base_url, jira_email

import httpx


def _adf_doc(text: str) -> dict[str, Any]:
    """Wrap plain text as Atlassian Document Format for Jira Cloud comments."""
    paragraphs = [p for p in (text or "").split("\n") if p is not None]
    if not paragraphs:
        paragraphs = [""]
    content = []
    for line in paragraphs:
        content.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line}] if line else [],
            }
        )
    return {"type": "doc", "version": 1, "content": content}


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    base = (config.get("base_url") or jira_base_url()).rstrip("/")
    email = config.get("email") or jira_email()
    token = config.get("token") or jira_api_token()
    if not base or not email or not token:
        return {
            "status": "not_configured",
            "message": "Configure MCP_JIRA_URL + JIRA_EMAIL (or JIRA_USERNAME) + JIRA_API_TOKEN (or server config)",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }
    auth = (email, token)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    with httpx.Client(timeout=30.0, auth=auth, headers=headers) as client:
        if tool_name == "search_issues":
            # Atlassian Cloud: GET /rest/api/3/search is gone (HTTP 410). Use POST /search/jql.
            jql = arguments.get("jql", "ORDER BY updated DESC")
            max_results = int(arguments.get("max_results") or arguments.get("maxResults") or 20)
            r = client.post(
                f"{base}/rest/api/3/search/jql",
                json={"jql": jql, "maxResults": max_results},
            )
            r.raise_for_status()
            return r.json()
        if tool_name == "get_issue":
            key = arguments["issue_key"]
            r = client.get(f"{base}/rest/api/3/issue/{key}")
            r.raise_for_status()
            return r.json()
        if tool_name == "create_issue":
            fields: dict[str, Any] = {
                "project": {"key": arguments["project"]},
                "summary": arguments["summary"],
                "issuetype": {"name": arguments.get("type", "Task")},
            }
            if arguments.get("description"):
                # ADF for Cloud; plain string fallback handled by some Server/DC via later retry if needed
                fields["description"] = _adf_doc(str(arguments["description"]))
            payload = {"fields": fields}
            r = client.post(f"{base}/rest/api/3/issue", json=payload)
            if r.status_code >= 400 and arguments.get("description"):
                # Fallback: omit description or use plain string field for older servers
                fields.pop("description", None)
                fields["description"] = str(arguments["description"])[:8000]
                r = client.post(f"{base}/rest/api/3/issue", json={"fields": {
                    "project": {"key": arguments["project"]},
                    "summary": arguments["summary"],
                    "issuetype": {"name": arguments.get("type", "Task")},
                }})
            r.raise_for_status()
            return r.json()
        if tool_name == "add_comment":
            key = arguments["issue_key"]
            body = arguments.get("body", "")
            # Prefer ADF for Cloud; plain string still accepted by some Server/DC.
            payload: dict[str, Any] = {"body": _adf_doc(str(body))}
            r = client.post(f"{base}/rest/api/3/issue/{key}/comment", json=payload)
            if r.status_code >= 400:
                r = client.post(
                    f"{base}/rest/api/3/issue/{key}/comment",
                    json={"body": str(body)},
                )
            r.raise_for_status()
            return r.json()
        if tool_name == "transition_issue":
            key = arguments["issue_key"]
            transition_id = arguments["transition_id"]
            r = client.post(
                f"{base}/rest/api/3/issue/{key}/transitions",
                json={"transition": {"id": str(transition_id)}},
            )
            r.raise_for_status()
            return {"status": "transitioned", "issue_key": key, "transition_id": transition_id}
        if tool_name == "list_projects":
            r = client.get(f"{base}/rest/api/3/project")
            r.raise_for_status()
            data = r.json()
            return {"projects": data[:50] if isinstance(data, list) else data}
    return {"status": "unknown_tool", "tool": tool_name}

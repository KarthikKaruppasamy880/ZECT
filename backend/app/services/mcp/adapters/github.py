"""GitHub MCP adapter — wraps ZECT github_service when token present."""

from __future__ import annotations

import os
from typing import Any


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return obj


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    token = config.get("token") or os.getenv("GITHUB_TOKEN", "")
    if not enabled:
        return {"status": "disabled", "message": "GitHub MCP server disabled"}
    if not token:
        return {
            "status": "not_configured",
            "message": "Set GITHUB_TOKEN or server config.token",
            "echo": arguments,
        }

    from app import github_service

    owner = arguments.get("owner", "")
    repo = arguments.get("repo", "")

    # Catalog aliases
    if tool_name == "list_prs":
        tool_name = "list_pulls"
    if tool_name == "get_pr":
        tool_name = "get_pull"

    if tool_name == "get_repo":
        info = github_service.get_repo_info(owner, repo)
        return {"repo": _dump(info)}
    if tool_name == "list_pulls":
        pulls = github_service.list_pulls(owner, repo, state=arguments.get("state", "open"))
        return {"pulls": [_dump(p) for p in pulls]}
    if tool_name == "get_pull":
        pr = github_service.get_pull(owner, repo, int(arguments["pr_number"]))
        return {"pull": _dump(pr) if not isinstance(pr, dict) else pr}
    if tool_name in ("create_issue", "search_code", "list_commits", "list_issues", "list_repos",
                     "create_pr", "get_file", "get_diff", "list_branches", "create_branch"):
        return {
            "status": "accepted",
            "tool": tool_name,
            "message": f"GitHub tool '{tool_name}' routed; use dedicated GitHub API routes for full payloads.",
            "arguments": arguments,
        }
    return {"status": "unknown_tool", "tool": tool_name, "arguments": arguments}

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
    if tool_name == "list_commits":
        commits = github_service.list_commits(owner, repo, limit=int(arguments.get("limit") or 20))
        return {"commits": [_dump(c) for c in commits]}
    if tool_name == "list_repos":
        repos = github_service.list_org_repos(owner or arguments.get("org", ""), limit=int(arguments.get("limit") or 30))
        return {"repos": [_dump(r) for r in repos]}
    if tool_name == "list_issues":
        return {"issues": github_service.list_issues(owner, repo, state=arguments.get("state", "open"), limit=int(arguments.get("limit") or 20))}
    if tool_name == "create_issue":
        return github_service.create_issue(owner, repo, arguments.get("title", ""), arguments.get("body", ""))
    if tool_name == "create_pr":
        return github_service.create_pull_request(
            owner, repo,
            arguments.get("title", ""), arguments.get("body", ""),
            arguments.get("head", ""), arguments.get("base", "main"),
        )
    if tool_name == "get_file":
        return github_service.get_file(owner, repo, arguments.get("path", ""), arguments.get("ref"))
    if tool_name == "get_diff":
        return github_service.get_diff(owner, repo, arguments.get("base", ""), arguments.get("head", ""))
    if tool_name == "list_branches":
        return {"branches": github_service.list_branches(owner, repo, limit=int(arguments.get("limit") or 50))}
    if tool_name == "create_branch":
        return github_service.create_branch(owner, repo, arguments.get("branch", ""), arguments.get("from_ref"))
    if tool_name == "search_code":
        return {"results": github_service.search_code(owner, repo, arguments.get("query", ""), limit=int(arguments.get("limit") or 20))}
    return {"status": "unknown_tool", "tool": tool_name, "arguments": arguments}

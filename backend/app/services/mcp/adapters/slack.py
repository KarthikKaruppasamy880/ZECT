from __future__ import annotations

import os
from typing import Any

import httpx


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    token = config.get("token") or os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        return {
            "status": "not_configured",
            "message": "Set SLACK_BOT_TOKEN",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        if tool_name == "send_message":
            r = client.post(
                "https://slack.com/api/chat.postMessage",
                json={"channel": arguments.get("channel"), "text": arguments.get("text", "")},
            )
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "slack_error"))
            return data
        if tool_name == "list_channels":
            r = client.get("https://slack.com/api/conversations.list", params={"limit": 100})
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "slack_error"))
            return data
    return {"status": "unknown_tool", "tool": tool_name}

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
        if tool_name == "channel_history":
            channel = arguments.get("channel") or os.getenv("SLACK_DEFAULT_CHANNEL", "engineering")
            channel = str(channel).lstrip("#")
            # Resolve channel name → id if needed
            ch_id = channel
            if not channel.startswith("C") and not channel.startswith("G"):
                listed = client.get("https://slack.com/api/conversations.list", params={"limit": 200})
                ld = listed.json()
                if ld.get("ok"):
                    for c in ld.get("channels") or []:
                        if (c.get("name") or "").lower() == channel.lower():
                            ch_id = c.get("id") or channel
                            break
            r = client.get(
                "https://slack.com/api/conversations.history",
                params={"channel": ch_id, "limit": int(arguments.get("limit") or 10)},
            )
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "slack_error"))
            messages = []
            for m in data.get("messages") or []:
                text = (m.get("text") or "").strip()
                if text:
                    messages.append({"user": m.get("user") or "", "text": text[:280], "ts": m.get("ts") or ""})
            return {"ok": True, "channel": channel, "channel_id": ch_id, "messages": messages}
    return {"status": "unknown_tool", "tool": tool_name}

"""Thin Gmail MCP path — only when GMAIL_* is configured; otherwise use email adapter."""

from __future__ import annotations

import os
from typing import Any


def _gmail_configured() -> bool:
    return bool(
        (os.getenv("GMAIL_CLIENT_ID") or "").strip()
        and (os.getenv("GMAIL_CLIENT_SECRET") or "").strip()
        and (os.getenv("GMAIL_REFRESH_TOKEN") or "").strip()
    )


def list_tools() -> list[dict[str, str]]:
    return [
        {"name": "status", "description": "Gmail OAuth configuration status"},
        {"name": "send_email", "description": "Send via Gmail when configured; else use email/SMTP"},
    ]


def execute(tool_name: str, arguments: dict, *, config: dict | None = None, enabled: bool = True) -> dict[str, Any]:
    config = config or {}
    if not enabled:
        return {"status": "disabled", "server": "gmail"}

    if tool_name == "status":
        ok = _gmail_configured()
        return {
            "status": "ready" if ok else "not_configured",
            "configured": ok,
            "message": (
                "Gmail OAuth env present"
                if ok
                else "Gmail not configured — use MCP email/SMTP (SMTP_HOST) or set GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN"
            ),
            "fallback": "email",
        }

    if not _gmail_configured():
        return {
            "status": "not_configured",
            "message": "Gmail not configured — use the email adapter (SMTP) instead",
            "fallback": "email",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }

    # Configured path still delegates outbound to SMTP email adapter until full Gmail API lands.
    from app.adapters import email_adapter

    mapped = "send_email" if tool_name in ("send_email", "send") else tool_name
    out = email_adapter.execute(mapped, arguments, config=config, enabled=enabled)
    if isinstance(out, dict):
        out = {**out, "via": "gmail_env_then_smtp", "note": "Thin Gmail path — full Gmail API Later"}
    return out

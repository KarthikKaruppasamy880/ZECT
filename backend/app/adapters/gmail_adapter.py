"""Gmail MCP path — OAuth status + IMAP/SMTP fallback; list when refresh token set."""

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
        {"name": "list_messages", "description": "List recent Gmail messages (read-only when OAuth configured)"},
        {"name": "send_email", "description": "Send via Gmail when configured; else use email/SMTP"},
    ]


def _list_via_gmail_api(limit: int = 8) -> dict[str, Any]:
    """Best-effort Gmail API list using refresh token. Falls back with clear error."""
    try:
        import httpx
    except ImportError:
        return {"status": "error", "message": "httpx required"}

    client_id = (os.getenv("GMAIL_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GMAIL_CLIENT_SECRET") or "").strip()
    refresh = (os.getenv("GMAIL_REFRESH_TOKEN") or "").strip()
    try:
        with httpx.Client(timeout=20.0) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh,
                    "grant_type": "refresh_token",
                },
            )
            if token_resp.status_code >= 400:
                return {
                    "status": "error",
                    "message": f"Gmail token refresh failed ({token_resp.status_code})",
                    "fallback": "imap",
                }
            access = token_resp.json().get("access_token")
            if not access:
                return {"status": "error", "message": "no access_token", "fallback": "imap"}
            list_resp = client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {access}"},
                params={"maxResults": max(1, min(limit, 25))},
            )
            if list_resp.status_code >= 400:
                return {
                    "status": "error",
                    "message": f"Gmail list failed ({list_resp.status_code})",
                    "fallback": "imap",
                }
            ids = [m.get("id") for m in (list_resp.json().get("messages") or []) if m.get("id")]
            messages = []
            for mid in ids[:limit]:
                meta = client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                    headers={"Authorization": f"Bearer {access}"},
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                )
                if meta.status_code >= 400:
                    continue
                headers = {
                    h.get("name"): h.get("value")
                    for h in ((meta.json().get("payload") or {}).get("headers") or [])
                }
                messages.append(
                    {
                        "id": mid,
                        "from": headers.get("From") or "",
                        "subject": headers.get("Subject") or "",
                        "date": headers.get("Date") or "",
                    }
                )
            return {
                "status": "ok",
                "configured": True,
                "via": "gmail_api",
                "messages": messages,
                "policy": {"delete": "never"},
            }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)[:300], "fallback": "imap"}


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
                "Gmail OAuth env present — list_messages uses Gmail API; send still may use SMTP bridge"
                if ok
                else "Gmail not configured — use MCP email/SMTP (SMTP_HOST) or set GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN"
            ),
            "fallback": "email",
        }

    if tool_name in ("list_messages", "list", "digest"):
        if not _gmail_configured():
            # Fall back to IMAP digest when Mentrix IMAP is configured
            try:
                from app.services.mentrix.email_inbox import fetch_inbox_digest

                out = fetch_inbox_digest(limit=int(arguments.get("limit") or 8))
                return {**out, "via": "imap_fallback", "fallback": "imap"}
            except Exception as exc:  # noqa: BLE001
                return {
                    "status": "not_configured",
                    "message": f"Gmail OAuth missing and IMAP fallback failed: {exc}",
                    "fallback": "imap",
                }
        return _list_via_gmail_api(limit=int(arguments.get("limit") or 8))

    if not _gmail_configured():
        return {
            "status": "not_configured",
            "message": "Gmail not configured — use the email adapter (SMTP) instead",
            "fallback": "email",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }

    # Configured path still delegates outbound to SMTP email adapter until full Gmail send lands.
    from app.adapters import email_adapter

    mapped = "send_email" if tool_name in ("send_email", "send") else tool_name
    out = email_adapter.execute(mapped, arguments, config=config, enabled=enabled)
    if isinstance(out, dict):
        out = {**out, "via": "gmail_env_then_smtp", "note": "Gmail send uses SMTP bridge; list uses Gmail API"}
    return out

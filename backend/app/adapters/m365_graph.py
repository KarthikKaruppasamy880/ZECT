"""Microsoft 365 / Graph adapter — Outlook mail + calendar when Azure/Graph creds exist.

IMAP/SMTP remain the Mentrix email fallback via email_inbox / email_adapter.
Env (no secrets committed):
  MS_GRAPH_TENANT_ID / AZURE_TENANT_ID
  MS_GRAPH_CLIENT_ID / AZURE_CLIENT_ID
  MS_GRAPH_CLIENT_SECRET
  MS_GRAPH_USER (UPN for app-only /me substitute: /users/{upn}/...)
"""

from __future__ import annotations

import os
from typing import Any

import httpx


def _cfg(config: dict | None = None) -> dict[str, str]:
    config = config or {}
    return {
        "tenant": (
            config.get("tenant_id")
            or os.getenv("MS_GRAPH_TENANT_ID")
            or os.getenv("AZURE_TENANT_ID")
            or ""
        ).strip(),
        "client_id": (
            config.get("client_id")
            or os.getenv("MS_GRAPH_CLIENT_ID")
            or os.getenv("AZURE_CLIENT_ID")
            or ""
        ).strip(),
        "client_secret": (
            config.get("client_secret") or os.getenv("MS_GRAPH_CLIENT_SECRET") or ""
        ).strip(),
        "user": (config.get("user") or os.getenv("MS_GRAPH_USER") or "").strip(),
    }


def configured(config: dict | None = None) -> bool:
    c = _cfg(config)
    return bool(c["tenant"] and c["client_id"] and c["client_secret"])


def list_tools() -> list[dict[str, str]]:
    return [
        {"name": "status", "description": "Graph / M365 configuration status"},
        {"name": "list_messages", "description": "List Outlook inbox messages"},
        {"name": "list_events", "description": "List upcoming calendar events"},
        {"name": "create_draft", "description": "Create Outlook message draft"},
        {"name": "create_event_draft", "description": "Return calendar event draft payload"},
    ]


def _token(c: dict[str, str]) -> str | None:
    if not configured(c):
        return None
    url = f"https://login.microsoftonline.com/{c['tenant']}/oauth2/v2.0/token"
    data = {
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.post(url, data=data)
        if r.status_code >= 400:
            return None
        return (r.json() or {}).get("access_token")


def _user_root(c: dict[str, str]) -> str:
    user = c.get("user") or ""
    if user:
        return f"/users/{user}"
    return "/me"


def execute(tool_name: str, arguments: dict, config: dict | None = None, enabled: bool = True) -> dict[str, Any]:
    config = config or {}
    c = _cfg(config)
    if not enabled:
        return {"status": "disabled", "dry_run": True}
    if tool_name == "status":
        return {
            "configured": configured(c),
            "tenant_set": bool(c["tenant"]),
            "client_id_set": bool(c["client_id"]),
            "secret_set": bool(c["client_secret"]),
            "user": c["user"] or None,
            "fallback": "IMAP/SMTP via Mentrix email providers",
        }
    if not configured(c):
        return {
            "status": "missing_creds",
            "message": "Set MS_GRAPH_TENANT_ID, MS_GRAPH_CLIENT_ID, MS_GRAPH_CLIENT_SECRET (+ MS_GRAPH_USER)",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }

    token = _token(c)
    if not token:
        return {"status": "error", "message": "graph_token_failed"}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    root = _user_root(c)
    base = "https://graph.microsoft.com/v1.0"

    with httpx.Client(timeout=30.0, headers=headers) as client:
        if tool_name == "list_messages":
            limit = int(arguments.get("limit") or 8)
            r = client.get(
                f"{base}{root}/mailFolders/Inbox/messages",
                params={
                    "$top": limit,
                    "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead",
                    "$orderby": "receivedDateTime desc",
                },
            )
            if r.status_code >= 400:
                return {"ok": False, "status": "error", "http": r.status_code, "detail": r.text[:300]}
            raw = r.json().get("value") or []
            messages = []
            for m in raw:
                frm = ((m.get("from") or {}).get("emailAddress") or {})
                messages.append(
                    {
                        "id": m.get("id"),
                        "subject": m.get("subject") or "",
                        "from": frm.get("address") or frm.get("name") or "",
                        "when": m.get("receivedDateTime"),
                        "preview": (m.get("bodyPreview") or "")[:280],
                        "is_read": bool(m.get("isRead")),
                        "source": "m365_graph",
                    }
                )
            return {"ok": True, "via": "m365_graph", "messages": messages}

        if tool_name == "list_events":
            limit = int(arguments.get("limit") or 10)
            r = client.get(
                f"{base}{root}/events",
                params={
                    "$top": limit,
                    "$select": "id,subject,start,end,organizer,bodyPreview,webLink",
                    "$orderby": "start/dateTime",
                },
            )
            if r.status_code >= 400:
                return {"ok": False, "status": "error", "http": r.status_code, "detail": r.text[:300]}
            events = []
            for e in r.json().get("value") or []:
                events.append(
                    {
                        "id": e.get("id"),
                        "title": e.get("subject") or "",
                        "start": (e.get("start") or {}).get("dateTime"),
                        "end": (e.get("end") or {}).get("dateTime"),
                        "preview": (e.get("bodyPreview") or "")[:280],
                        "web_link": e.get("webLink"),
                        "source": "m365_graph",
                    }
                )
            return {"ok": True, "via": "m365_graph", "events": events}

        if tool_name == "create_draft":
            to = arguments.get("to") or ""
            subject = arguments.get("subject") or ""
            body = arguments.get("body") or ""
            payload = {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}] if to else [],
            }
            r = client.post(f"{base}{root}/messages", json=payload)
            if r.status_code >= 400:
                return {"ok": False, "status": "error", "http": r.status_code, "detail": r.text[:300]}
            data = r.json()
            return {"ok": True, "via": "m365_graph", "draft_id": data.get("id"), "subject": subject}

        if tool_name == "create_event_draft":
            return {
                "ok": True,
                "via": "m365_graph",
                "channel": "calendar",
                "title": arguments.get("title") or "",
                "start": arguments.get("start_iso") or "",
                "end": arguments.get("end_iso") or "",
                "attendees": arguments.get("attendees") or [],
                "body": arguments.get("body") or "",
                "note": "Draft only — create in Outlook/Graph with Allow when write scopes are granted",
            }

    return {"status": "unknown_tool", "tool": tool_name}

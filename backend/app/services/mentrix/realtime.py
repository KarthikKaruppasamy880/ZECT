"""Mentrix OpenAI Realtime — session mint + tool bridge (API key stays server-side)."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.services.mentrix.companion import NAV_MAP, _ensure_openai_env, _exec_tool
from app.services.mentrix.permission_broker import ALWAYS_CONFIRM_TOOLS, check_tool_permission

REALTIME_MODEL = os.getenv("MENTRIX_REALTIME_MODEL", "gpt-4o-realtime-preview")


def realtime_enabled() -> bool:
    flag = os.getenv("MENTRIX_REALTIME", "1").strip().lower()
    if flag in ("0", "false", "off", "no"):
        return False
    return bool(_ensure_openai_env())


def mentrix_instructions() -> str:
    nav = ", ".join(f"{k}->{v}" for k, v in NAV_MAP.items())
    return (
        "You are Mentrix, the ZECT company personal operator. "
        "Help with weather, Slack, email, Delivery, Lattice, Sandbox, research, notes, and desktop tools. "
        "ALWAYS use tools for weather (weather_report), Slack digests/sends, and email digests/sends — "
        "never invent inbox contents, Slack messages, or live weather. "
        "When the user mentions mail, inbox, or email, call email_digest (not a generic chat reply). "
        "Prefer spoken_summary from tool results when speaking. "
        "Use tools for real ZECT actions; never invent run IDs. "
        f"Navigate paths: {nav}. "
        "Use lattice_query for code symbols and documentation wikilinks. "
        "For documentation graphs, prefer doc-kind hits and mention backlinks when available. "
        "When a tool needs permission, tell the user to Allow in the Mentrix overlay. "
        "Brand: Mentrix, Lattice, ForgeLoop, ZECT only. No Exa."
    )


def realtime_tool_schemas() -> list[dict[str, Any]]:
    """OpenAI Realtime function tool definitions (subset of companion tools)."""
    return [
        {
            "type": "function",
            "name": "navigate",
            "description": "Open a ZECT UI route",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path like /lattice"},
                    "label": {"type": "string"},
                },
                "required": ["path"],
            },
        },
        {
            "type": "function",
            "name": "delivery_status",
            "description": "Get latest Mentrix Delivery run status",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "start_delivery",
            "description": "Start Mentrix Delivery (needs Allow)",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string"},
                    "mode": {"type": "string"},
                },
                "required": ["goal"],
            },
        },
        {
            "type": "function",
            "name": "research_news",
            "description": "Mentrix web research (not Exa)",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
        {
            "type": "function",
            "name": "weather_report",
            "description": "Live weather for a city or location via Mentrix Open-Meteo",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name e.g. Austin"}},
                "required": ["location"],
            },
        },
        {
            "type": "function",
            "name": "slack_digest",
            "description": "Summarize recent Slack channels/messages (requires SLACK_BOT_TOKEN)",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "slack_send",
            "description": "Send a Slack message (needs user Allow)",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
        {
            "type": "function",
            "name": "email_digest",
            "description": "Recent email subjects (requires MENTRIX_IMAP_*); never invent inbox",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "email_send",
            "description": "Send email via SMTP (needs user Allow)",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["body"],
            },
        },
        {
            "type": "function",
            "name": "content_brief",
            "description": "Draft a Mentrix content brief",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
        {
            "type": "function",
            "name": "report_draft",
            "description": "Draft a Mentrix status report",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
        {
            "type": "function",
            "name": "note_add",
            "description": "Save a Mentrix note",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        {
            "type": "function",
            "name": "note_list",
            "description": "List Mentrix notes",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "lattice_query",
            "description": "Query Lattice knowledge graph",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}, "project_key": {"type": "string"}},
                "required": ["q"],
            },
        },
        {
            "type": "function",
            "name": "diagnose_fix",
            "description": "Diagnose failure and post Mermaid workflow",
            "parameters": {
                "type": "object",
                "properties": {"issue": {"type": "string"}},
                "required": ["issue"],
            },
        },
        {
            "type": "function",
            "name": "media_generate",
            "description": "Generate Mentrix image/thumbnail (needs Allow)",
            "parameters": {
                "type": "object",
                "properties": {"prompt": {"type": "string"}},
                "required": ["prompt"],
            },
        },
        {
            "type": "function",
            "name": "media_list",
            "description": "List Mentrix image board items",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "desktop_screenshot",
            "description": "Screenshot (Computer Mode + Allow)",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "computer_open_app",
            "description": "Open allowlisted app (Computer Mode + Allow)",
            "parameters": {
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
        },
    ]


def mint_realtime_session() -> dict[str, Any]:
    """Mint short-lived OpenAI Realtime client secret. Never returns the long-lived API key."""
    if not realtime_enabled():
        return {
            "ok": False,
            "realtime_enabled": False,
            "fallback": "stt_sse",
            "reason": "realtime_disabled_or_no_key",
        }
    key = _ensure_openai_env()
    body = {
        "model": REALTIME_MODEL,
        "voice": os.getenv("MENTRIX_REALTIME_VOICE", "alloy"),
        "instructions": mentrix_instructions(),
        "tools": realtime_tool_schemas(),
        "input_audio_transcription": {"model": "whisper-1"},
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "OpenAI-Beta": "realtime=v1",
                },
                json=body,
            )
        if resp.status_code >= 400:
            return {
                "ok": False,
                "realtime_enabled": False,
                "fallback": "stt_sse",
                "reason": f"openai_{resp.status_code}",
                "detail": resp.text[:300],
            }
        data = resp.json()
        secret = (data.get("client_secret") or {}).get("value") or ""
        if not secret:
            return {
                "ok": False,
                "realtime_enabled": False,
                "fallback": "stt_sse",
                "reason": "no_client_secret",
            }
        return {
            "ok": True,
            "realtime_enabled": True,
            "model": data.get("model") or REALTIME_MODEL,
            "client_secret": secret,
            "expires_at": (data.get("client_secret") or {}).get("expires_at"),
            "openai_ws_url": f"wss://api.openai.com/v1/realtime?model={data.get('model') or REALTIME_MODEL}",
            "voice": body["voice"],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "realtime_enabled": False,
            "fallback": "stt_sse",
            "reason": type(exc).__name__,
            "detail": str(exc)[:200],
        }


def run_realtime_tool(
    db,
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    user_id: int | None = None,
    project_id: int | None = None,
    project_key: str = "",
    created_by: str = "",
    user_confirmed: bool = False,
) -> dict[str, Any]:
    """Execute a Realtime function call through the Mentrix permission broker."""
    name = (tool_name or "").strip()
    args = args or {}
    perm = check_tool_permission(
        db,
        name,
        user_id=user_id,
        project_id=project_id,
        user_confirmed=user_confirmed,
    )
    if perm["result"] == "denied":
        return {
            "ok": False,
            "denied": True,
            "tool": name,
            "error": "Permission denied",
            "events": [{"event": "tool_end", "data": {"tool": name, "ok": False, "error": "denied"}}],
        }
    if perm["result"] == "pending_approval" or (
        name in ALWAYS_CONFIRM_TOOLS and not user_confirmed
    ):
        return {
            "ok": False,
            "pending": True,
            "tool": name,
            "args": args,
            "pending_confirmations": [
                {
                    "tool": name,
                    "action": perm.get("action"),
                    "args": args,
                    "args_redacted": {k: ("…" if k in ("text", "body", "path") else v) for k, v in args.items()},
                    "reason": "Always-ask Allow required",
                }
            ],
            "events": [
                {"event": "tool_start", "data": {"tool": name, "args": args}},
                {"event": "pending_confirm", "data": {"tool": name}},
            ],
        }

    events: list[dict[str, Any]] = [{"event": "tool_start", "data": {"tool": name, "args": args}}]
    result = _exec_tool(db, name, args, project_key=project_key, created_by=created_by)
    events.append({"event": "tool_end", "data": {"tool": name, "ok": bool(result.get("ok")), "error": result.get("error")}})
    if result.get("board"):
        events.append({"event": "artifact", "data": result["board"]})
    if result.get("board_extra"):
        events.append({"event": "artifact", "data": result["board_extra"]})
    if result.get("board_progress"):
        events.append({"event": "artifact", "data": result["board_progress"]})
    if result.get("navigate"):
        events.append({"event": "navigate", "data": {"path": result["navigate"]}})
    # Prefer short spoken_summary for Realtime vocalization
    spoken = result.get("spoken_summary")
    if spoken:
        out_payload = {"ok": result.get("ok", True), "spoken_summary": spoken, "tool": name}
        if result.get("note"):
            out_payload["note"] = result["note"]
        output = json.dumps(out_payload)[:4000]
    else:
        output = json.dumps(result)[:4000]
    return {
        "ok": bool(result.get("ok", True)),
        "tool": name,
        "result": result,
        "events": events,
        "output": output,
    }

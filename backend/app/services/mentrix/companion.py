"""Mentrix Companion turn — intent + permission-gated tools for company work."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import quote_plus
from urllib.request import urlopen

from sqlalchemy.orm import Session

from app.models import MentrixRun
from app.services.lattice.indexer import query_graph, get_graph
from app.services.mentrix.permission_broker import (
    ALWAYS_CONFIRM_TOOLS,
    check_tool_permission,
    log_mentrix_tool,
)

NAV_MAP = {
    "lattice": "/lattice",
    "blueprint": "/blueprint",
    "delivery": "/mentrix",
    "mentrix delivery": "/mentrix",
    "sandbox": "/sandbox",
    "companion": "/mentrix-home",
    "home": "/mentrix-home",
    "integrations": "/integrations",
    "permissions": "/permissions",
    "dashboard": "/",
    "docs": "/docs",
    "ask": "/ask",
}


def _llm_answer(question: str, context: str = "") -> str:
    """Best-effort Mentrix reply via OpenAI; offline fallback if unavailable."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return (
            "I'm Mentrix. I can navigate ZECT, check Delivery status, research topics, "
            "draft content/reports, and use connectors when permitted. "
            f"You asked: {question[:400]}"
            + (f"\n\nContext:\n{context[:1500]}" if context else "")
        )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Mentrix, the ZECT company personal agent. Help with ads, research, "
                    "content, reporting, internal docs, and Mentrix Delivery. Be concise, practical, "
                    "and never claim you performed a sensitive action without user confirmation."
                ),
            }
        ]
        if context:
            messages.append({"role": "user", "content": f"Tool results:\n{context[:6000]}"})
        messages.append({"role": "user", "content": question})
        resp = client.chat.completions.create(
            model=os.getenv("MENTRIX_COMPANION_MODEL", "gpt-4o-mini"),
            messages=messages,
            max_tokens=1200,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"Mentrix (offline reply): {question[:200]}\n\nNote: LLM unavailable ({exc})."


def _parse_intents(message: str) -> list[dict[str, Any]]:
    """Deterministic intents so Companion works without LLM tool-calling."""
    m = message.lower().strip()
    tools: list[dict[str, Any]] = []

    if re.search(r"\bgo back\b|\bback\b", m) and "feedback" not in m:
        tools.append({"name": "go_back", "args": {}})

    for key, path in NAV_MAP.items():
        if key in m and any(w in m for w in ("open", "go to", "show", "navigate", "take me")):
            tools.append({"name": "navigate", "args": {"path": path, "label": key}})
            break
    if "open lattice" in m or "lattice graph" in m:
        tools.append({"name": "navigate", "args": {"path": "/lattice", "label": "lattice"}})
    if "open delivery" in m or "mentrix delivery" in m:
        tools.append({"name": "navigate", "args": {"path": "/mentrix", "label": "delivery"}})

    if any(w in m for w in ("status", "gates", "what'?s running", "last run", "delivery status")):
        tools.append({"name": "delivery_status", "args": {}})

    if any(w in m for w in ("news", "research", "latest on", "what's happening")):
        topic = re.sub(r".*?(news|research|latest on)\s*", "", m, count=1).strip() or message
        tools.append({"name": "research_news", "args": {"topic": topic[:120]}})

    if any(w in m for w in ("brief", "ad copy", "campaign", "content idea")):
        tools.append({"name": "content_brief", "args": {"topic": message[:200]}})

    if any(w in m for w in ("report", "metrics summary", "weekly update")):
        tools.append({"name": "report_draft", "args": {"topic": message[:200]}})

    if any(w in m for w in ("confluence", "internal doc", "search docs")):
        tools.append({"name": "docs_search", "args": {"query": message[:160]}})

    if "slack" in m and any(w in m for w in ("digest", "summarize", "unread", "channel")):
        tools.append({"name": "slack_digest", "args": {}})
    if "slack" in m and any(w in m for w in ("send", "post", "message")):
        tools.append({"name": "slack_send", "args": {"text": message[:500]}})

    if "gmail" in m or ("email" in m and "digest" in m):
        tools.append({"name": "email_digest", "args": {}})
    if "send email" in m or "email send" in m:
        tools.append({"name": "email_send", "args": {"subject": "Mentrix draft", "body": message[:800]}})

    if any(w in m for w in ("avatar", "generate image", "my photo")):
        tools.append({"name": "image_avatar", "args": {}})

    if "lattice" in m and any(w in m for w in ("query", "search", "symbol", "find")):
        q = message
        tools.append({"name": "lattice_query", "args": {"q": q[:120], "project_key": ""}})

    if any(w in m for w in ("start deliver", "engage delivery", "run upgrade", "start upgrade")):
        tools.append({"name": "start_delivery", "args": {"goal": message[:400], "mode": "deliver"}})

    if "computer mode" in m or "open notepad" in m or "screenshot" in m:
        if "screenshot" in m:
            tools.append({"name": "desktop_screenshot", "args": {}})
        elif "open" in m:
            tools.append({"name": "computer_open_app", "args": {"app": "notepad.exe"}})
        else:
            tools.append({"name": "computer_open_app", "args": {"app": "explorer.exe"}})

    if any(w in m for w in ("diagnose", "fix this", "why is this failing")):
        tools.append({"name": "diagnose_fix", "args": {"issue": message[:400]}})

    # de-dupe by name
    seen = set()
    out = []
    for t in tools:
        if t["name"] not in seen:
            seen.add(t["name"])
            out.append(t)
    return out


def _exec_tool(
    db: Session,
    name: str,
    args: dict,
    project_key: str = "",
) -> dict[str, Any]:
    if name == "navigate":
        return {"ok": True, "navigate": args.get("path") or "/", "label": args.get("label")}
    if name == "go_back":
        return {"ok": True, "navigate": "__back__"}
    if name == "delivery_status":
        runs = db.query(MentrixRun).order_by(MentrixRun.id.desc()).limit(5).all()
        items = [
            {
                "id": r.id,
                "status": r.status,
                "mode": r.mode,
                "goal": (r.goal or "")[:120],
                "gates": json.loads(r.gates_json or "{}"),
                "next_step": r.next_step or "",
            }
            for r in runs
        ]
        return {"ok": True, "runs": items}
    if name == "lattice_query":
        key = args.get("project_key") or project_key
        if not key:
            gkeys = []
            # best effort: any cached graph
            from app.services.lattice.indexer import _GRAPH_CACHE  # type: ignore

            gkeys = list(_GRAPH_CACHE.keys())[:1]
            key = gkeys[0] if gkeys else ""
        if not key:
            return {"ok": False, "error": "No Lattice project_key — ingest a workspace first"}
        hits = query_graph(key, args.get("q") or "", limit=15)
        g = get_graph(key)
        return {
            "ok": True,
            "project_key": key,
            "hits": hits[:15],
            "summary": {
                "files": g.files_indexed if g else 0,
                "symbols": g.symbols if g else 0,
            },
        }
    if name == "research_news":
        topic = args.get("topic") or "technology"
        # Lightweight public RSS/Atom-free stub: DuckDuckGo HTML-less API
        citations = []
        try:
            url = f"https://api.duckduckgo.com/?q={quote_plus(topic)}&format=json&no_html=1"
            with urlopen(url, timeout=6) as resp:  # noqa: S310 — public search API
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            for item in (data.get("RelatedTopics") or [])[:6]:
                if isinstance(item, dict) and item.get("Text"):
                    citations.append({"title": item.get("Text", "")[:160], "url": item.get("FirstURL") or ""})
            abstract = data.get("AbstractText") or ""
        except Exception as exc:  # noqa: BLE001
            abstract = f"Research stub for '{topic}' (live search unavailable: {exc})"
        return {"ok": True, "topic": topic, "summary": abstract or f"Research notes on {topic}", "citations": citations}
    if name == "content_brief":
        topic = args.get("topic") or "campaign"
        md = (
            f"# Mentrix content brief\n\n**Topic:** {topic}\n\n"
            "## Audience\n- Primary segment\n- Secondary segment\n\n"
            "## Key message\nOne clear value proposition.\n\n"
            "## Ad angles\n1. Problem → solution\n2. Social proof\n3. Urgency\n\n"
            "## CTA\nClear next step.\n"
        )
        return {"ok": True, "board": {"type": "markdown", "title": "Content brief", "body": md}}
    if name == "ads_copy":
        topic = args.get("topic") or "offer"
        md = f"# Ad copy variants\n\n1. **Direct:** {topic[:80]} — try it today.\n2. **Story:** Teams waste hours; Mentrix saves them.\n3. **Proof:** Measurable outcomes in one sprint.\n"
        return {"ok": True, "board": {"type": "markdown", "title": "Ad copy", "body": md}}
    if name == "report_draft":
        topic = args.get("topic") or "weekly"
        md = (
            f"# Mentrix report — {topic}\n\n## Highlights\n- Delivery runs reviewed\n- Research completed\n\n"
            "## Risks\n- Blockers needing approval\n\n## Next steps\n- Confirm sends\n- Close open gates\n"
        )
        return {"ok": True, "board": {"type": "markdown", "title": "Report draft", "body": md}}
    if name == "docs_search":
        q = args.get("query") or ""
        try:
            from app.services.mcp.hub import execute_tool

            result = execute_tool(db, server_id="confluence", tool_name="search", arguments={"query": q})
            return {"ok": True, "source": "confluence", "result": result}
        except Exception:
            return {
                "ok": True,
                "source": "local",
                "result": {"note": "Confluence MCP unavailable — use Docs Center", "query": q},
            }
    if name == "docs_draft":
        return {
            "ok": True,
            "needs_publish_confirm": True,
            "board": {
                "type": "markdown",
                "title": "Internal doc draft",
                "body": f"# Draft\n\n{args.get('body') or args.get('query') or 'Outline here.'}\n",
            },
        }
    if name == "slack_digest":
        try:
            from app.services.mcp.hub import execute_tool

            ch = execute_tool(db, server_id="slack", tool_name="list_channels", arguments={})
            return {"ok": True, "digest": ch, "note": "Channel list (read). Sending requires confirm."}
        except Exception as exc:  # noqa: BLE001
            return {"ok": True, "digest": {"channels": []}, "note": f"Slack adapter: {exc}"}
    if name == "slack_send":
        try:
            from app.services.mcp.hub import execute_tool

            sent = execute_tool(
                db,
                server_id="slack",
                tool_name="send_message",
                arguments={"channel": args.get("channel") or "general", "text": args.get("text") or ""},
            )
            return {"ok": True, "sent": sent}
        except Exception as exc:  # noqa: BLE001
            return {"ok": True, "queued": True, "text": args.get("text"), "note": f"Slack send: {exc}"}
    if name == "email_digest":
        try:
            from app.services.mcp.hub import execute_tool

            # Prefer read/list when connector exposes it; else graceful stub
            for tool_name in ("list_messages", "search", "inbox_digest"):
                try:
                    dig = execute_tool(db, server_id="email", tool_name=tool_name, arguments=args or {})
                    return {"ok": True, "digest": dig, "source": f"email:{tool_name}"}
                except Exception:
                    continue
            for tool_name in ("list_messages", "search"):
                try:
                    dig = execute_tool(db, server_id="gmail", tool_name=tool_name, arguments=args or {})
                    return {"ok": True, "digest": dig, "source": f"gmail:{tool_name}"}
                except Exception:
                    continue
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": True,
                "digest": {"items": []},
                "note": f"Email/Gmail read not connected ({exc}). Configure Integrations.",
            }
        return {
            "ok": True,
            "digest": {"items": []},
            "note": "Configure Gmail OAuth read or email MCP in Integrations for inbox digests",
        }
    if name == "email_send":
        try:
            from app.services.mcp.hub import execute_tool

            sent = execute_tool(
                db,
                server_id="email",
                tool_name="send_email",
                arguments={
                    "to": args.get("to") or "",
                    "subject": args.get("subject") or "Mentrix",
                    "body": args.get("body") or "",
                },
            )
            return {"ok": True, "sent": sent}
        except Exception as exc:  # noqa: BLE001
            return {"ok": True, "queued": True, "subject": args.get("subject"), "note": f"Email send: {exc}"}
    if name == "image_avatar":
        return {
            "ok": True,
            "board": {
                "type": "image_placeholder",
                "title": "Avatar generation",
                "body": "Upload photo after confirm — Mentrix will generate a companion avatar (OpenAI images when keyed).",
            },
        }
    if name == "start_delivery":
        return {
            "ok": True,
            "start_delivery": {"goal": args.get("goal"), "mode": args.get("mode") or "deliver"},
            "note": "Open Mentrix Delivery or confirm to start run",
        }
    if name in ("approve_delivery", "create_pr"):
        return {"ok": True, "queued": True, "action": name, "note": "Confirm in Mentrix Delivery UI"}
    if name == "desktop_screenshot":
        return {"ok": True, "desktop": "screenshot", "note": "Electron Computer Mode performs capture after confirm"}
    if name == "desktop_read":
        path = str(args.get("path") or "")
        blocked = (".env", "id_rsa", "credentials", "password", "secrets", ".aws", ".ssh")
        if any(b in path.lower() for b in blocked):
            return {"ok": False, "error": "path_blocked_default_deny", "path": path}
        return {"ok": True, "path": path, "desktop": "desktop_read", "note": "Allowlisted read after confirm"}
    if name == "computer_open_app":
        return {"ok": True, "app": args.get("app") or "notepad.exe", "desktop": "open_app"}
    if name in ("computer_click", "computer_type"):
        return {"ok": True, "desktop": name, "args": args, "note": "Requires Computer Mode ON + confirm"}
    if name == "diagnose_fix":
        issue = args.get("issue") or ""
        runs = db.query(MentrixRun).order_by(MentrixRun.id.desc()).limit(3).all()
        run_bits = ", ".join(f"#{r.id}:{r.status}" for r in runs) or "no recent runs"
        md = (
            f"# Diagnose & fix plan\n\n**Issue:** {issue}\n\n"
            f"**Recent Delivery:** {run_bits}\n\n"
            "1. Gather Lattice + logs (allowed paths only — secrets blocked)\n"
            "2. Propose minimal fix on Mentrix Board\n"
            "3. Confirm → Mentrix Delivery (`/mentrix`) or desktop steps (Computer Mode)\n"
            "4. Verify gates / outcome\n"
        )
        return {
            "ok": True,
            "board": {"type": "markdown", "title": "Diagnose & fix", "body": md},
            "navigate": "/mentrix",
            "start_delivery": {"goal": f"Fix: {issue[:300]}", "mode": "deliver"},
        }
    return {"ok": False, "error": f"Unknown tool {name}"}


def run_companion_turn(
    db: Session,
    message: str,
    *,
    project_key: str = "",
    project_id: int | None = None,
    user_id: int | None = None,
    confirmed_tools: list[str] | None = None,
    history: list[dict] | None = None,
) -> dict[str, Any]:
    confirmed = set(confirmed_tools or [])
    intents = _parse_intents(message)
    tool_results: list[dict] = []
    pending: list[dict] = []
    board_items: list[dict] = []
    navigations: list[str] = []

    for intent in intents:
        name = intent["name"]
        args = intent.get("args") or {}
        perm = check_tool_permission(
            db,
            name,
            user_id=user_id,
            project_id=project_id,
            user_confirmed=name in confirmed,
        )
        if perm["result"] == "denied":
            tool_results.append({"tool": name, "denied": True, "permission": perm})
            log_mentrix_tool(db, name, args=args, result="denied", user_id=user_id)
            continue
        if perm.get("needs_confirm") or (perm["result"] == "pending_approval" and name not in confirmed):
            pending.append(
                {
                    "tool": name,
                    "args": args,
                    "audit_id": perm.get("audit_id"),
                    "reason": f"Mentrix needs your permission to run `{name}`",
                    "always_ask": name in ALWAYS_CONFIRM_TOOLS,
                }
            )
            continue
        result = _exec_tool(db, name, args, project_key=project_key)
        tool_results.append({"tool": name, "result": result, "permission": perm})
        log_mentrix_tool(db, name, args=args, result="ok" if result.get("ok") else "error", user_id=user_id)
        if result.get("board"):
            board_items.append(result["board"])
        nav = result.get("navigate")
        if nav:
            navigations.append(nav)

    context_bits = []
    for tr in tool_results:
        if tr.get("denied"):
            context_bits.append(f"DENIED {tr['tool']}")
        else:
            context_bits.append(json.dumps({tr["tool"]: tr.get("result")}, default=str)[:800])
    if pending:
        context_bits.append("Pending user confirmation: " + ", ".join(p["tool"] for p in pending))

    reply = _llm_answer(message, "\n".join(context_bits))
    if pending and not tool_results:
        reply = (
            "I can help with that, but I need your permission first for: "
            + ", ".join(p["tool"] for p in pending)
            + ". Confirm to continue."
        )
    elif any(tr.get("denied") for tr in tool_results) and not any(not tr.get("denied") for tr in tool_results):
        reply = "Org policy blocked that action. Ask an admin to update Mentrix Permissions if needed."

    return {
        "reply": reply,
        "avatar_state": "needs_permission" if pending else ("speaking" if reply else "idle"),
        "tools": tool_results,
        "pending_confirmations": pending,
        "board": board_items,
        "navigate": navigations[0] if navigations else None,
        "history_tail": (history or [])[-6:] + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}],
    }

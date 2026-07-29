"""Mentrix Companion — streaming agentic turns with permission-gated tools."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Generator, Iterator
from urllib.parse import quote_plus
from urllib.request import urlopen

from sqlalchemy.orm import Session

from app.models import Lesson, MentrixRun, Skill
from app.services.lattice.indexer import get_graph, query_graph
from app.services.mentrix.permission_broker import (
    ALWAYS_CONFIRM_TOOLS,
    check_tool_permission,
    log_mentrix_tool,
)

_LLM_TIMEOUT_S = float(os.getenv("MENTRIX_COMPANION_LLM_TIMEOUT", "6"))
_RESEARCH_TIMEOUT_S = float(os.getenv("MENTRIX_COMPANION_RESEARCH_TIMEOUT", "2.5"))
_MAX_TOOLS = 5

# In-memory resume store for Allow overlay (turn_id → state)
_TURN_STORE: dict[str, dict[str, Any]] = {}

NAV_MAP = {
    "lattice": "/lattice",
    "blueprint": "/blueprint",
    "delivery": "/mentrix",
    "sandbox": "/sandbox",
    "companion": "/mentrix-home",
    "home": "/mentrix-home",
    "control tower": "/mentrix-home",
    "desktop app": "/mentrix-home",
    "mentrix home": "/mentrix-home",
    "integrations": "/integrations",
    "permissions": "/permissions",
    "dashboard": "/",
    "docs": "/docs",
    "ask": "/ask",
    "plan": "/plan",
    "build": "/build",
    "review": "/review",
    "deploy": "/deploy",
    "code review": "/code-review",
    "code-review": "/code-review",
    "git": "/git-ops",
    "ci": "/ci-monitor",
    "skills": "/skills",
    "skills engine": "/skills-engine",
    "dream engine": "/dream-engine",
    "rules": "/rules",
    "secrets": "/secrets",
    "conversations": "/conversations",
    "agent": "/agent-mode",
    "repo": "/repo-workspace",
    "knowledge": "/knowledge-base",
    "playbooks": "/playbooks",
    "audit": "/audit-trail",
}


def os_desktop_phrase(message: str) -> bool:
    m = (message or "").lower()
    if "desktop app" in m or "control tower" in m or "dashboard" in m:
        return False
    return bool(
        re.search(
            r"\b(open|go to|show|enable|take me to)\b.{0,32}\b(desktop|computer mode|os desktop|my desktop)\b",
            m,
        )
        or re.search(r"\b(open desktop|go to desktop|enable computer|computer mode on)\b", m)
    )


def build_agent_context(
    db: Session,
    *,
    skill_id: int | None = None,
    project_id: int | None = None,
    agent_context: str = "",
) -> str:
    """Compose Active Skill + staged Dream lessons for companion / Realtime turns.

    Silent empty string when nothing is configured — never raises to callers.
    """
    bits: list[str] = []
    raw = (agent_context or "").strip()
    if raw:
        bits.append(raw[:4000])
    try:
        if skill_id is not None:
            skill = db.query(Skill).filter(Skill.id == int(skill_id)).first()
            if skill:
                body = (skill.template or skill.description or "").strip()
                bits.append(
                    f"Active skill ({skill.name}): {body[:1200]}"
                    if body
                    else f"Active skill: {skill.name}"
                )
    except Exception:  # noqa: BLE001
        pass
    try:
        if project_id is not None:
            lessons = (
                db.query(Lesson)
                .filter(Lesson.project_id == int(project_id), Lesson.status == "staged")
                .order_by(Lesson.created_at.desc())
                .limit(3)
                .all()
            )
            claims = [str(L.claim or "").strip()[:220] for L in lessons if (L.claim or "").strip()]
            if claims:
                bits.append("Learned patterns (Dream):\n" + "\n".join(f"- {c}" for c in claims))
    except Exception:  # noqa: BLE001
        pass
    return "\n\n".join(bits).strip()[:4000]


def _ensure_openai_env() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parents[3] / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=False)
    except Exception:  # noqa: BLE001
        pass
    return os.getenv("OPENAI_API_KEY", "").strip()


def _gates_mermaid(gates: dict | None, run_id: int | None = None) -> str:
    g = gates or {}
    title = f"Delivery #{run_id}" if run_id else "Mentrix Delivery"
    lines = ["flowchart LR", f"  startNode([{title}])"]
    keys = list(g.keys())[:8] or ["incomplete_ok", "lint_ok", "sandbox_ready", "review_ok", "approve", "create_pr"]
    prev = "startNode"
    for i, k in enumerate(keys):
        nid = f"g{i}"
        val = g.get(k)
        label = f"{k}:{'ok' if val else 'pending'}" if val is not None else k
        lines.append(f"  {nid}[{label}]")
        lines.append(f"  {prev} --> {nid}")
        prev = nid
    return "\n".join(lines)


def _fast_tool_reply(tool_results: list[dict], board_items: list[dict], navigations: list[str]) -> str | None:
    if not tool_results and not board_items and not navigations:
        return None
    parts: list[str] = []
    for tr in tool_results:
        if tr.get("denied"):
            parts.append(f"Blocked: {tr['tool']}")
            continue
        name = tr.get("tool")
        result = tr.get("result") or {}
        if name == "delivery_status":
            runs = result.get("runs") or []
            if not runs:
                parts.append("No Mentrix Delivery runs yet.")
            else:
                r0 = runs[0]
                parts.append(
                    f"Latest Delivery #{r0.get('id')}: {r0.get('status')} ({r0.get('mode')}). "
                    f"Next: {r0.get('next_step') or 'review gates'}."
                )
        elif name == "navigate":
            parts.append(f"Opening {result.get('label') or result.get('navigate')}.")
        elif name == "go_back":
            parts.append("Going back.")
        elif name == "research_news":
            parts.append((result.get("summary") or f"Research on {result.get('topic')}")[:400])
        elif name == "start_delivery":
            parts.append(f"Mentrix Delivery run #{result.get('run_id')} started." if result.get("run_id") else "Delivery queued.")
        elif name in ("content_brief", "ads_copy", "report_draft", "docs_draft", "diagnose_fix"):
            parts.append(f"Artifact ready: {(result.get('board') or {}).get('title') or name}.")
        elif name == "note_add":
            parts.append("Note saved to Mentrix Notes.")
        elif name == "note_list":
            parts.append(f"{len(result.get('notes') or [])} Mentrix notes.")
        elif name == "weather_report":
            parts.append((result.get("spoken_summary") or "Weather ready.")[:400])
        elif name == "slack_digest":
            parts.append((result.get("spoken_summary") or result.get("note") or "Slack digest ready.")[:400])
        elif name == "email_digest":
            parts.append((result.get("spoken_summary") or result.get("note") or "Email digest ready.")[:400])
        elif name == "lattice_query":
            hits = result.get("hits") or []
            parts.append(f"Lattice: {len(hits)} hit(s)." if hits else (result.get("error") or "No hits."))
    if board_items and not parts:
        parts.append(f"Posted {board_items[0].get('title') or 'artifact'}.")
    if navigations and not any(p.startswith("Opening") or p.startswith("Going") for p in parts):
        parts.append(f"Navigating to {navigations[0]}.")
    return " ".join(parts)[:1200] if parts else None


def _llm_plan_tools(message: str) -> list[dict[str, Any]]:
    """Ask LLM for up to N tool calls as JSON; empty on failure."""
    key = _ensure_openai_env()
    if not key:
        return []

    def _call() -> list[dict[str, Any]]:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=_LLM_TIMEOUT_S)
        tool_names = sorted(
            {
                "navigate",
                "go_back",
                "delivery_status",
                "research_news",
                "weather_report",
                "content_brief",
                "report_draft",
                "docs_search",
                "slack_digest",
                "slack_send",
                "email_digest",
                "email_send",
                "note_add",
                "note_list",
                "lattice_query",
                "start_delivery",
                "diagnose_fix",
                "media_generate",
                "media_list",
                "media_edit",
                "jira_get_issue",
                "jira_search_incidents",
                "datadog_query_logs",
                "jira_comment_pr",
            }
        )
        prompt = (
            "You are Mentrix planner. Return ONLY a JSON array of tools to run, max 5. "
            f"Allowed names: {tool_names}. "
            'Each item: {"name":"...","args":{}}. '
            "For navigate use args.path like /lattice. Empty array if just chatting.\n"
            f"User: {message[:800]}"
        )
        resp = client.chat.completions.create(
            model=os.getenv("MENTRIX_COMPANION_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.1,
        )
        text = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            return []
        data = json.loads(m.group(0))
        out = []
        for item in data[:_MAX_TOOLS]:
            if isinstance(item, dict) and item.get("name"):
                out.append({"name": str(item["name"]), "args": item.get("args") or {}})
        return out

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_call).result(timeout=_LLM_TIMEOUT_S + 0.5)
    except Exception:  # noqa: BLE001
        return []


def _llm_answer(question: str, context: str = "") -> str:
    key = _ensure_openai_env()
    if not key:
        return (
            "I'm Mentrix — ready. Ask for Delivery status, research, a brief, notes, "
            "or say Open Lattice."
            + (f"\n\n{context[:900]}" if context else "")
        )

    def _call() -> str:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=_LLM_TIMEOUT_S)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Mentrix, ZECT company agent. Reply in 1-3 short sentences. "
                    "Never claim you sent messages or controlled the desktop without confirmation. "
                    "Never delete files. Prefer writing allowlisted Desktop/Documents notes over Notepad typing. "
                    "For Zoom presentations: open the .pptx path and Zoom; user shares the PowerPoint window."
                ),
            }
        ]
        if context:
            messages.append({"role": "user", "content": f"Tool results:\n{context[:3500]}"})
        messages.append({"role": "user", "content": question})
        resp = client.chat.completions.create(
            model=os.getenv("MENTRIX_COMPANION_MODEL", "gpt-4o-mini"),
            messages=messages,
            max_tokens=280,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_call).result(timeout=_LLM_TIMEOUT_S + 0.5)
    except FuturesTimeout:
        return "Mentrix — quick path (model timed out):\n" + (context[:900] if context else question[:300])
    except Exception as exc:  # noqa: BLE001
        return (
            "I'm Mentrix — ready for status, research, briefs, notes, and Delivery."
            + (f"\n\n{context[:700]}" if context else f"\n\nYou asked: {question[:200]}")
            + f"\n\n({type(exc).__name__})"
        )


def _parse_intents(message: str) -> list[dict[str, Any]]:
    m = message.lower().strip()
    tools: list[dict[str, Any]] = []

    if re.search(r"\bgo back\b", m):
        tools.append({"name": "go_back", "args": {}})

    # OS desktop / Computer Mode — never map to app Dashboard ("/").
    # "desktop app" / "control tower" are Mentrix HUD aliases (handled via NAV_MAP).
    os_desktop = os_desktop_phrase(message)
    if os_desktop:
        if "screenshot" in m:
            tools.append({"name": "desktop_screenshot", "args": {}})
        else:
            tools.append({"name": "computer_open_app", "args": {"app": "explorer.exe"}})

    # Longer NAV keys first so "desktop app" wins over accidental short matches.
    nav_keys = sorted(NAV_MAP.keys(), key=len, reverse=True)
    for key in nav_keys:
        path = NAV_MAP[key]
        if key == "dashboard" and re.search(r"\bdesktop\b", m) and "dashboard" not in m:
            continue
        if os_desktop and path == "/":
            continue
        if key in m and any(w in m for w in ("open", "go to", "show", "navigate", "take me")):
            tools.append({"name": "navigate", "args": {"path": path, "label": key}})
            break
    if "open lattice" in m or "lattice graph" in m:
        tools.append({"name": "navigate", "args": {"path": "/lattice", "label": "lattice"}})
    if re.search(r"\b(open|show|go to)\b.*\b(lattice docs|documentation graph|wiki graph|docs graph)\b", m):
        tools.append({"name": "navigate", "args": {"path": "/lattice?layer=docs", "label": "lattice docs"}})
    if re.search(r"\b(open|go to|show|navigate|take me)\b.*\b(delivery|mentrix delivery)\b", m) or "open delivery" in m:
        tools.append({"name": "navigate", "args": {"path": "/mentrix", "label": "delivery"}})

    if any(w in m for w in ("status", "gates", "what's running", "whats running", "last run", "delivery status")):
        tools.append({"name": "delivery_status", "args": {}})

    if re.search(r"\b(research|news|latest on)\b", m) and "weather" not in m:
        topic = re.sub(r".*?(news|research|latest on)\s*", "", m, count=1).strip() or message
        tools.append({"name": "research_news", "args": {"topic": topic[:120]}})

    if any(w in m for w in ("weather", "forecast", "temperature", "how's the weather", "how is the weather")):
        loc = message
        for prefix in (
            "what's the weather in",
            "whats the weather in",
            "weather in",
            "weather for",
            "forecast for",
            "how's the weather in",
            "how is the weather in",
            "what's the weather",
            "whats the weather",
        ):
            if prefix in m:
                loc = message[m.index(prefix) + len(prefix) :].strip(" ?.")
                break
        tools.append({"name": "weather_report", "args": {"location": (loc or "Austin")[:120]}})

    if any(w in m for w in ("brief", "ad copy", "campaign", "content idea")):
        tools.append({"name": "content_brief", "args": {"topic": message[:200]}})

    if any(w in m for w in ("report", "metrics summary", "weekly update")):
        tools.append({"name": "report_draft", "args": {"topic": message[:200]}})

    if any(w in m for w in ("confluence", "internal doc", "search docs")):
        tools.append({"name": "docs_search", "args": {"query": message[:160]}})

    if re.search(r"\b(open|launch|start)\b.*\b(slack app|slack desktop)\b", m) or re.search(
        r"\blaunch slack\b", m
    ):
        tools.append({"name": "computer_open_app", "args": {"app": "Slack.exe"}})
    elif re.search(r"\b(open|launch|start)\b.*\b(browser|chrome)\b", m) or "open browser" in m:
        tools.append({"name": "computer_open_app", "args": {"app": "chrome.exe"}})
    elif re.search(r"\b(open|launch|start)\b.*\bedge\b", m):
        tools.append({"name": "computer_open_app", "args": {"app": "msedge.exe"}})

    if "slack" in m and any(w in m for w in ("digest", "summarize", "unread", "channel", "what's on", "whats on")):
        tools.append({"name": "slack_digest", "args": {}})
    elif "slack" in m and any(w in m for w in ("send", "post", "message")):
        tools.append({"name": "slack_send", "args": {"text": message[:500]}})
    elif m.strip() in ("slack digest", "slack summary") or "slack digest" in m:
        tools.append({"name": "slack_digest", "args": {}})

    if any(
        p in m
        for p in (
            "email digest",
            "check email",
            "check my email",
            "check mail",
            "read email",
            "my inbox",
            "inbox",
            "gmail",
        )
    ) or re.search(r"\b(e-?mail|inbox|gmail)\b", m) or ("email" in m and "digest" in m):
        tools.append({"name": "email_digest", "args": {}})
    if "send email" in m or "email send" in m:
        tools.append({"name": "email_send", "args": {"subject": "Mentrix draft", "body": message[:800]}})

    # Jira incident / issue tools
    issue_key_m = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", message)
    if issue_key_m and any(
        w in m for w in ("jira", "ticket", "incident", "issue", "load", "fetch", "get")
    ):
        tools.append({"name": "jira_get_issue", "args": {"issue_key": issue_key_m.group(1)}})
    if any(w in m for w in ("search incidents", "list incidents", "open incidents", "jira incidents")):
        tools.append({"name": "jira_search_incidents", "args": {}})
    if "datadog" in m or ("logs" in m and any(w in m for w in ("query", "search", "incident", "error"))):
        q = re.sub(r".*?(datadog|logs|errors?)\s*", "", m, count=1).strip() or "status:error"
        tools.append({"name": "datadog_query_logs", "args": {"query": q[:200]}})
    if "comment" in m and ("pr" in m or "pull request" in m) and issue_key_m:
        pr_m = re.search(r"https?://[^\s]+", message)
        tools.append(
            {
                "name": "jira_comment_pr",
                "args": {
                    "issue_key": issue_key_m.group(1),
                    "pr_url": pr_m.group(0) if pr_m else "",
                },
            }
        )
    if any(w in m for w in ("avatar", "generate image", "my photo", "thumbnail", "image board")):
        if "list" in m or "show board" in m:
            tools.append({"name": "media_list", "args": {}})
        else:
            tools.append({"name": "media_generate", "args": {"prompt": message[:800]}})

    if re.search(r"\b(edit image|edit thumbnail|edit media)\b", m):
        num_m = re.search(r"#?\b(\d{1,4})\b", m)
        tools.append(
            {
                "name": "media_edit",
                "args": {
                    "number": int(num_m.group(1)) if num_m else 1,
                    "prompt": message[:800],
                },
            }
        )

    if re.search(r"\b(note|notes)\b", m) and any(w in m for w in ("list", "show", "my")):
        tools.append({"name": "note_list", "args": {}})
    if re.search(r"\b(add note|save note|remember|note that)\b", m):
        tools.append({"name": "note_add", "args": {"text": message[:800]}})

    # Prefer writing an allowlisted Desktop/Documents file over Notepad for docs/notes.
    if re.search(
        r"\b(write|create|save)\b.{0,40}\b(note|notes|doc|docs|document|markdown|txt)\b",
        m,
    ) or re.search(r"\b(on (my )?desktop|to (my )?desktop|in documents)\b", m) and re.search(
        r"\b(write|create|save|note)\b", m
    ):
        folder = "Documents" if "document" in m else "Desktop"
        tools.append(
            {
                "name": "desktop_write_note",
                "args": {
                    "content": message[:4000],
                    "folder": folder,
                    "filename": "mentrix-note.md",
                },
            }
        )

    if "lattice" in m and any(w in m for w in ("query", "search", "symbol", "find", "wiki", "doc", "markdown")):
        tools.append({"name": "lattice_query", "args": {"q": message[:120], "project_key": ""}})

    if any(w in m for w in ("start deliver", "engage delivery", "run upgrade", "start upgrade", "start mentrix")):
        tools.append({"name": "start_delivery", "args": {"goal": message[:400], "mode": "deliver"}})

    if re.search(
        r"\b(open (my )?(deck|pptx|powerpoint|presentation)|present on zoom|narrate my slides|open zoom)\b",
        m,
    ):
        path_m = re.search(
            r"([A-Za-z]:\\[^\s\"']+\.(?:pptx|ppt|pdf)|/(?:Users|home)/[^\s\"']+\.(?:pptx|ppt|pdf))",
            message,
            re.I,
        )
        if path_m:
            tools.append({"name": "desktop_open_presentation", "args": {"path": path_m.group(1)}})
        if "zoom" in m or "present on zoom" in m:
            tools.append({"name": "computer_open_app", "args": {"app": "Zoom.exe"}})
        if any(w in m for w in ("powerpoint", "pptx", "deck", "presentation")) and not path_m:
            tools.append({"name": "computer_open_app", "args": {"app": "POWERPNT.EXE"}})

    if "computer mode" in m or "open notepad" in m or "screenshot" in m or "ui inspect" in m:
        if "screenshot" in m:
            tools.append({"name": "desktop_screenshot", "args": {}})
        elif "inspect" in m:
            tools.append({"name": "computer_ui_inspect", "args": {}})
        elif "scroll" in m:
            tools.append({"name": "computer_scroll", "args": {"direction": "down"}})
        elif "click" in m:
            tools.append({"name": "computer_click", "args": {"x": 100, "y": 100}})
        elif "type" in m:
            tools.append({"name": "computer_type", "args": {"text": message[:200]}})
        elif "open notepad" in m:
            tools.append({"name": "computer_open_app", "args": {"app": "notepad.exe"}})
        elif "open explorer" in m or "file explorer" in m:
            tools.append({"name": "computer_open_app", "args": {"app": "explorer.exe"}})
        elif "computer mode" in m:
            tools.append({"name": "computer_open_app", "args": {"app": "explorer.exe"}})

    if any(w in m for w in ("open sandbox", "go to sandbox", "show sandbox")):
        tools.append({"name": "navigate", "args": {"path": "/sandbox", "label": "sandbox"}})
    if any(w in m for w in ("open ask", "go to ask")):
        tools.append({"name": "navigate", "args": {"path": "/ask", "label": "ask"}})
    if any(w in m for w in ("open plan", "go to plan")):
        tools.append({"name": "navigate", "args": {"path": "/plan", "label": "plan"}})
    if any(w in m for w in ("open docs", "go to docs")):
        tools.append({"name": "navigate", "args": {"path": "/docs", "label": "docs"}})
    if any(w in m for w in ("open integrations", "go to integrations")):
        tools.append({"name": "navigate", "args": {"path": "/integrations", "label": "integrations"}})

    if any(w in m for w in ("diagnose", "fix this", "why is this failing")):
        tools.append({"name": "diagnose_fix", "args": {"issue": message[:400]}})

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for t in tools:
        if t["name"] not in seen:
            seen.add(t["name"])
            out.append(t)
    return out[:_MAX_TOOLS]


def _exec_tool(db: Session, name: str, args: dict, project_key: str = "", created_by: str = "") -> dict[str, Any]:
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
        board = None
        if items:
            board = {
                "type": "mermaid",
                "title": f"Gates — run #{items[0]['id']}",
                "body": _gates_mermaid(items[0].get("gates") or {}, items[0]["id"]),
            }
        return {"ok": True, "runs": items, "board": board}
    if name == "lattice_query":
        key = args.get("project_key") or project_key
        if not key:
            from app.services.lattice.indexer import _GRAPH_CACHE  # type: ignore

            gkeys = list(_GRAPH_CACHE.keys())[:1]
            key = gkeys[0] if gkeys else ""
        if not key:
            return {"ok": False, "error": "No Lattice project_key — ingest a workspace first"}
        q = args.get("q") or ""
        doc_mode = any(w in q.lower() for w in ("wiki", "doc", "markdown", "note"))
        kinds = ["doc", "folder", "vault"] if doc_mode else None
        hits = query_graph(key, q, limit=15, kinds=kinds)
        if not hits and doc_mode:
            hits = query_graph(key, q, limit=15)
        g = get_graph(key)
        from app.services.lattice.markdown_graph import doc_backlinks as lattice_doc_backlinks

        bl_rows: list[list[str]] = []
        if hits and hits[0].get("kind") in ("doc", "folder", "vault"):
            bl = lattice_doc_backlinks(key, hits[0].get("path") or hits[0].get("name") or q, limit=8)
            for item in bl.get("backlinks") or []:
                src = item.get("source") or {}
                bl_rows.append([src.get("name") or "", src.get("kind") or "", src.get("path") or ""])
        summary = {
            "files": g.files_indexed if g else 0,
            "symbols": g.symbols if g else 0,
            "docs": getattr(g, "doc_files_indexed", 0) if g else 0,
            "wikilinks": getattr(g, "wikilinks_resolved", 0) if g else 0,
        }
        boards: list[dict] = [
            {
                "type": "table",
                "title": "Lattice hits",
                "data": {
                    "columns": ["name", "kind", "path"],
                    "rows": [
                        [h.get("name") or "", h.get("kind") or "", h.get("path") or ""]
                        for h in (hits[:12] if isinstance(hits, list) else [])
                    ],
                },
            }
        ]
        if bl_rows:
            boards.append(
                {
                    "type": "table",
                    "title": "Doc backlinks",
                    "data": {"columns": ["name", "kind", "path"], "rows": bl_rows},
                }
            )
        spoken = f"Found {len(hits)} Lattice matches"
        if summary.get("docs"):
            spoken += f", including {summary['docs']} documentation nodes."
        return {
            "ok": True,
            "project_key": key,
            "hits": hits[:15],
            "summary": summary,
            "board": boards[0],
            "board_extra": boards[1] if len(boards) > 1 else None,
            "spoken_summary": spoken,
        }
    if name == "research_news":
        topic = args.get("topic") or "technology"
        citations: list[dict[str, str]] = []
        abstract = ""

        def _fetch() -> tuple[str, list[dict[str, str]]]:
            url = f"https://api.duckduckgo.com/?q={quote_plus(topic)}&format=json&no_html=1"
            with urlopen(url, timeout=_RESEARCH_TIMEOUT_S) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            cites: list[dict[str, str]] = []
            for item in (data.get("RelatedTopics") or [])[:6]:
                if isinstance(item, dict) and item.get("Text"):
                    cites.append({"title": item.get("Text", "")[:160], "url": item.get("FirstURL") or ""})
            return (data.get("AbstractText") or ""), cites

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                abstract, citations = pool.submit(_fetch).result(timeout=_RESEARCH_TIMEOUT_S + 0.4)
        except Exception as exc:  # noqa: BLE001
            abstract = f"Quick Mentrix research on '{topic}' (live lookup skipped: {type(exc).__name__})."
        return {
            "ok": True,
            "topic": topic,
            "summary": abstract or f"Research notes on {topic}",
            "citations": citations,
            "board": {
                "type": "markdown",
                "title": f"Research — {topic[:60]}",
                "body": (abstract or f"Research notes on {topic}")
                + (
                    "\n\n## Sources\n" + "\n".join(f"- {c.get('title')}" for c in citations[:6])
                    if citations
                    else ""
                ),
            },
        }
    if name == "content_brief":
        topic = args.get("topic") or "campaign"
        md = (
            f"# Mentrix content brief\n\n**Topic:** {topic}\n\n"
            "## Audience\n- Primary\n- Secondary\n\n## Key message\nValue proposition.\n\n"
            "## Ad angles\n1. Problem → solution\n2. Social proof\n3. Urgency\n"
        )
        return {"ok": True, "board": {"type": "markdown", "title": "Content brief", "body": md}}
    if name == "ads_copy":
        topic = args.get("topic") or "offer"
        md = f"# Ad copy\n\n1. **Direct:** {topic[:80]}\n2. **Story:** Mentrix saves hours.\n3. **Proof:** Outcomes in one sprint.\n"
        return {"ok": True, "board": {"type": "markdown", "title": "Ad copy", "body": md}}
    if name == "report_draft":
        topic = args.get("topic") or "weekly"
        md = f"# Mentrix report — {topic}\n\n## Highlights\n- Delivery reviewed\n\n## Risks\n- Open gates\n\n## Next\n- Confirm sends\n"
        return {"ok": True, "board": {"type": "markdown", "title": "Report draft", "body": md}}
    if name == "docs_search":
        q = args.get("query") or ""
        try:
            from app.services.mcp.hub import execute_tool

            result = execute_tool(db, server_id="confluence", tool_name="search", arguments={"query": q})
            return {"ok": True, "source": "confluence", "result": result}
        except Exception:
            return {"ok": True, "source": "local", "result": {"note": "Confluence unavailable", "query": q}}
    if name == "docs_draft":
        return {
            "ok": True,
            "board": {
                "type": "markdown",
                "title": "Internal doc draft",
                "body": f"# Draft\n\n{args.get('body') or args.get('query') or 'Outline.'}\n",
            },
        }
    if name == "jira_get_issue":
        try:
            from app.services.mcp.hub import execute_tool

            key = (args.get("issue_key") or "").strip().upper()
            if not key:
                return {"ok": False, "error": "issue_key required"}
            out = execute_tool(
                db,
                server_id="jira",
                tool_name="get_issue",
                arguments={"issue_key": key},
                user_email=created_by,
            )
            result = out.get("result") or out
            if out.get("status") in ("not_configured", "disabled") or result.get("status") in (
                "not_configured",
                "disabled",
            ):
                return {
                    "ok": False,
                    "error": result.get("message") or "Jira not configured — set MCP_JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN",
                    "result": result,
                }
            fields = result.get("fields") or {}
            summary = fields.get("summary") or ""
            status = (fields.get("status") or {}).get("name") or ""
            itype = (fields.get("issuetype") or {}).get("name") or ""
            desc = fields.get("description")
            desc_text = ""
            if isinstance(desc, str):
                desc_text = desc[:2000]
            elif isinstance(desc, dict):
                # flatten ADF lightly
                def _walk(n: Any) -> str:
                    if isinstance(n, dict):
                        if n.get("type") == "text":
                            return str(n.get("text") or "")
                        return "".join(_walk(c) for c in (n.get("content") or []))
                    if isinstance(n, list):
                        return "".join(_walk(c) for c in n)
                    return ""

                desc_text = _walk(desc)[:2000]
            spoken = f"Jira {key}: {summary}. Status {status or 'unknown'}."
            md = (
                f"# {key} — {summary}\n\n"
                f"**Type:** {itype}  \n**Status:** {status}\n\n"
                f"## Description\n\n{desc_text or '_No description_'}\n"
            )
            return {
                "ok": True,
                "issue_key": key,
                "summary": summary,
                "status": status,
                "issuetype": itype,
                "description": desc_text,
                "result": result,
                "spoken_summary": spoken,
                "board": {"type": "markdown", "title": f"Jira {key}", "body": md},
                "delivery_goal": f"Fix incident {key}: {summary}\n\n{desc_text[:1500]}",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
    if name == "jira_search_incidents":
        try:
            from app.services.mcp.hub import execute_tool

            jql = (
                args.get("jql")
                or os.getenv("JIRA_INCIDENT_JQL")
                or 'issuetype = Incident ORDER BY updated DESC'
            )
            out = execute_tool(
                db,
                server_id="jira",
                tool_name="search_issues",
                arguments={"jql": jql, "max_results": int(args.get("max_results") or 20)},
                user_email=created_by,
            )
            result = out.get("result") or out
            if result.get("status") in ("not_configured", "disabled"):
                return {
                    "ok": False,
                    "error": result.get("message") or "Jira not configured",
                    "result": result,
                }
            issues = result.get("issues") or result.get("values") or []
            rows = []
            for iss in issues[:20]:
                f = iss.get("fields") or {}
                rows.append(
                    [
                        iss.get("key") or "",
                        f.get("summary") or "",
                        (f.get("status") or {}).get("name") or "",
                    ]
                )
            return {
                "ok": True,
                "jql": jql,
                "count": len(rows),
                "spoken_summary": f"Found {len(rows)} Jira incident(s).",
                "board": {
                    "type": "table",
                    "title": "Jira incidents",
                    "data": {"columns": ["key", "summary", "status"], "rows": rows},
                },
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
    if name == "datadog_query_logs":
        try:
            from app.services.mcp.hub import execute_tool

            query = args.get("query") or "status:error"
            out = execute_tool(
                db,
                server_id="datadog",
                tool_name="query_logs",
                arguments={"query": query},
                user_email=created_by,
            )
            result = out.get("result") or out
            if result.get("status") in ("not_configured", "disabled"):
                return {
                    "ok": False,
                    "error": result.get("message") or "Datadog not configured",
                    "result": result,
                }
            data = result.get("data") or []
            rows = []
            for ev in data[:15]:
                attrs = (ev.get("attributes") or {}) if isinstance(ev, dict) else {}
                rows.append(
                    [
                        str(attrs.get("timestamp") or attrs.get("service") or "")[:40],
                        str(attrs.get("message") or attrs.get("status") or ev)[:120],
                    ]
                )
            return {
                "ok": True,
                "query": query,
                "spoken_summary": f"Datadog returned {len(rows)} log event(s) for '{query[:60]}'.",
                "board": {
                    "type": "table",
                    "title": f"Datadog — {query[:40]}",
                    "data": {"columns": ["meta", "message"], "rows": rows},
                },
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
    if name == "jira_comment_pr":
        try:
            from app.services.mcp.hub import execute_tool

            key = (args.get("issue_key") or "").strip().upper()
            pr_url = (args.get("pr_url") or "").strip()
            if not key or not pr_url:
                return {"ok": False, "error": "issue_key and pr_url required"}
            body = args.get("body") or f"Mentrix Delivery PR: {pr_url}"
            out = execute_tool(
                db,
                server_id="jira",
                tool_name="add_comment",
                arguments={"issue_key": key, "body": body},
                user_email=created_by,
            )
            result = out.get("result") or out
            if result.get("status") in ("not_configured", "disabled") or out.get("status") == "error":
                return {
                    "ok": False,
                    "error": result.get("message") or result.get("error") or "Jira comment failed",
                    "result": result,
                }
            return {
                "ok": True,
                "issue_key": key,
                "pr_url": pr_url,
                "spoken_summary": f"Commented PR link on {key}.",
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
    if name == "weather_report":
        from app.services.mentrix.weather import weather_report as _weather

        wr = _weather(str(args.get("location") or args.get("place") or "Austin"))
        if not wr.get("ok") and wr.get("fallback_research"):
            # Caller / agent may follow with research_news; still return honest failure
            return wr
        return wr
    if name == "slack_digest":
        try:
            from app.services.mcp.hub import execute_tool

            hist = execute_tool(
                db,
                server_id="slack",
                tool_name="channel_history",
                arguments={
                    "channel": args.get("channel") or os.getenv("SLACK_DEFAULT_CHANNEL", "engineering"),
                    "limit": 10,
                },
            )
            if hist.get("status") == "not_configured" or hist.get("dry_run"):
                return {
                    "ok": True,
                    "digest": {"messages": []},
                    "spoken_summary": "Slack is not configured. Set SLACK_BOT_TOKEN in backend/.env.",
                    "note": "Set SLACK_BOT_TOKEN in backend/.env",
                }
            messages = hist.get("messages") or []
            channel = hist.get("channel") or "default"
            if not messages:
                spoken = f"No recent Slack messages in #{channel}."
            else:
                bits = [m.get("text") or "" for m in messages[:5] if m.get("text")]
                spoken = f"Recent Slack in #{channel}: " + "; ".join(bits)[:500]
            rows = [[m.get("user") or "", m.get("text") or ""] for m in messages[:10]]
            return {
                "ok": True,
                "digest": hist,
                "spoken_summary": spoken,
                "note": f"{len(messages)} message(s) in #{channel}",
                "board": {
                    "type": "table",
                    "title": f"Slack — #{channel}",
                    "data": {"columns": ["user", "text"], "rows": rows},
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": True,
                "digest": {"messages": []},
                "spoken_summary": f"Slack digest unavailable: {type(exc).__name__}. Set SLACK_BOT_TOKEN if needed.",
                "note": str(exc)[:200],
            }
    if name == "slack_send":
        try:
            from app.services.mcp.hub import execute_tool

            channel = args.get("channel") or os.getenv("SLACK_DEFAULT_CHANNEL", "general")
            text = args.get("text") or ""
            sent = execute_tool(
                db,
                server_id="slack",
                tool_name="send_message",
                arguments={"channel": str(channel).lstrip("#"), "text": text},
            )
            return {
                "ok": True,
                "sent": sent,
                "spoken_summary": f"Slack message sent to {channel}." if not sent.get("dry_run") else "Slack send queued (token missing).",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": True,
                "queued": True,
                "note": f"Slack send: {exc}",
                "spoken_summary": f"Could not send Slack message: {type(exc).__name__}.",
            }
    if name == "email_digest":
        from app.services.mentrix.email_inbox import fetch_inbox_digest

        return fetch_inbox_digest(limit=8)
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
            return {
                "ok": True,
                "sent": sent,
                "spoken_summary": "Email sent." if not sent.get("dry_run") else "Email not sent — configure SMTP_HOST.",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": True,
                "queued": True,
                "note": f"Email send: {exc}",
                "spoken_summary": f"Email send failed: {type(exc).__name__}.",
            }
    if name == "image_avatar":
        from app.services.mentrix.media_board import generate_media

        entry = generate_media(args.get("prompt") or "Mentrix companion avatar", created_by=created_by)
        return {
            "ok": True,
            "media": entry,
            "board": {
                "type": "image",
                "title": f"Mentrix image #{entry['number']:03d}",
                "body": entry.get("prompt") or "",
                "data": entry,
            },
        }
    if name == "media_generate":
        from app.services.mentrix.media_board import generate_media

        entry = generate_media(args.get("prompt") or "Mentrix image", created_by=created_by)
        return {
            "ok": True,
            "media": entry,
            "board": {
                "type": "image",
                "title": f"Mentrix image #{entry['number']:03d}",
                "body": entry.get("prompt") or "",
                "data": entry,
            },
        }
    if name == "media_edit":
        from app.services.mentrix.media_board import edit_media

        num = int(args.get("number") or 1)
        entry = edit_media(num, args.get("prompt") or "edit", created_by=created_by)
        return {
            "ok": True,
            "media": entry,
            "board": {
                "type": "image",
                "title": f"Mentrix edit #{entry['number']:03d}",
                "body": entry.get("prompt") or "",
                "data": entry,
            },
        }
    if name == "media_list":
        from app.services.mentrix.media_board import list_media

        items = list_media()
        return {
            "ok": True,
            "media": items,
            "board": {
                "type": "record",
                "title": "Mentrix Image board",
                "body": f"{len(items)} images",
                "data": {
                    "records": [
                        {
                            "id": f"#{it.get('number'):03d}",
                            "text": it.get("prompt") or "",
                            "tags": ["media", f"n{it.get('number')}"],
                            "createdAt": it.get("createdAt"),
                        }
                        for it in items
                    ]
                },
            },
        }
    if name == "note_list":
        from app.services.mentrix.notes import list_notes

        notes = list_notes()
        return {
            "ok": True,
            "notes": notes,
            "board": {
                "type": "record",
                "title": "Mentrix Notes",
                "data": {"records": notes},
            },
        }
    if name == "note_add":
        from app.services.mentrix.notes import add_note

        note = add_note(str(args.get("text") or ""), tags=args.get("tags") or ["mentrix"])
        return {
            "ok": True,
            "note": note,
            "board": {"type": "note", "title": "Note saved", "body": note.get("text") or "", "data": note},
        }
    if name == "start_delivery":
        from app.services.forge_loop.orchestrator import MODE_PIPELINE, run_mentrix

        goal = (args.get("goal") or "Mentrix Delivery").strip()
        mode = args.get("mode") or "upgrade"
        if mode not in MODE_PIPELINE:
            mode = "upgrade" if "upgrade" in MODE_PIPELINE else "chat"
        run = run_mentrix(
            db,
            goal=goal,
            mode=mode,
            project_key=project_key or args.get("project_key") or "",
            created_by=created_by or "mentrix-companion",
            workspace=args.get("workspace") or "",
        )
        gates = json.loads(run.gates_json or "{}")
        return {
            "ok": True,
            "run_id": run.id,
            "status": run.status,
            "navigate": "/mentrix",
            "board": {
                "type": "mermaid",
                "title": f"Delivery workflow #{run.id}",
                "body": _gates_mermaid(gates, run.id),
            },
            "board_progress": {
                "type": "progress",
                "title": f"Run #{run.id}",
                "data": {"status": run.status, "next_step": run.next_step or "", "percent": 35},
            },
        }
    if name in ("approve_delivery", "create_pr"):
        return {"ok": True, "queued": True, "action": name, "note": "Confirm in Mentrix Delivery UI"}
    if name == "desktop_screenshot":
        return {"ok": True, "desktop": "screenshot", "note": "Electron Computer Mode after confirm"}
    if name == "desktop_read":
        path = str(args.get("path") or "")
        blocked = (".env", "id_rsa", "credentials", "password", "secrets", ".aws", ".ssh")
        if any(b in path.lower() for b in blocked):
            return {"ok": False, "error": "path_blocked_default_deny", "path": path}
        return {"ok": True, "path": path, "desktop": "desktop_read"}
    if name in ("desktop_delete", "delete_file"):
        return {
            "ok": False,
            "error": "delete_never_allowed",
            "note": "Mentrix never deletes files. Create/read only.",
        }
    if name == "desktop_write_note":
        content = str(args.get("content") or "")
        if not content.strip():
            return {"ok": False, "error": "empty_content"}
        folder_name = str(args.get("folder") or "Desktop").strip() or "Desktop"
        if folder_name.lower() not in ("desktop", "documents"):
            folder_name = "Desktop"
        home = Path.home()
        base = home / ("Desktop" if folder_name.lower() == "desktop" else "Documents")
        raw_name = str(args.get("filename") or "mentrix-note.md").strip() or "mentrix-note.md"
        safe = Path(raw_name).name
        if not safe.lower().endswith((".md", ".txt")):
            safe = f"{safe}.md"
        target = (base / safe).resolve()
        try:
            target.relative_to(base.resolve())
        except ValueError:
            return {"ok": False, "error": "path_outside_allowlist"}
        try:
            base.mkdir(parents=True, exist_ok=True)
            target.write_text(content[:50_000], encoding="utf-8")
            return {
                "ok": True,
                "desktop": "desktop_write_note",
                "path": str(target),
                "bytes": len(content.encode("utf-8")),
                "note": "Wrote allowlisted note file (prefer over Notepad)",
                "electron_action": "write_note",
                "electron_args": {"path": str(target), "content": content[:50_000]},
            }
        except OSError as exc:
            return {
                "ok": True,
                "desktop": "desktop_write_note",
                "queued": True,
                "path": str(target),
                "error_local": str(exc)[:200],
                "note": "Confirm Allow — Electron will write under Desktop/Documents",
                "electron_action": "write_note",
                "electron_args": {
                    "folder": folder_name,
                    "filename": safe,
                    "content": content[:50_000],
                },
            }
    if name == "computer_open_app":
        return {"ok": True, "app": args.get("app") or "notepad.exe", "desktop": "open_app"}
    if name == "desktop_open_presentation":
        path = str(args.get("path") or "").strip()
        if not path:
            return {"ok": False, "error": "missing_path"}
        return {
            "ok": True,
            "path": path,
            "desktop": "open_presentation",
            "note": "Open presentation; user shares PowerPoint in Zoom",
        }
    if name in ("computer_click", "computer_type", "computer_scroll", "computer_ui_inspect"):
        return {"ok": True, "desktop": name, "args": args}
    if name == "diagnose_fix":
        issue = args.get("issue") or ""
        runs = db.query(MentrixRun).order_by(MentrixRun.id.desc()).limit(3).all()
        run_bits = ", ".join(f"#{r.id}:{r.status}" for r in runs) or "none"
        md = (
            f"# Diagnose & fix\n\n**Issue:** {issue}\n\n**Recent Delivery:** {run_bits}\n\n"
            "1. Gather Lattice + logs\n2. Propose fix\n3. Confirm → Delivery\n4. Verify gates\n"
        )
        mermaid = (
            "flowchart TD\n"
            "  gather[Gather context] --> plan[Board plan]\n"
            "  plan --> confirm[User Allow]\n"
            "  confirm --> deliver[Mentrix Delivery]\n"
            "  deliver --> verify[Verify gates]\n"
        )
        return {
            "ok": True,
            "board": {"type": "markdown", "title": "Diagnose & fix", "body": md},
            "board_extra": {"type": "mermaid", "title": "Fix workflow", "body": mermaid},
        }
    return {"ok": False, "error": f"Unknown tool {name}"}


def _merge_intents(message: str) -> list[dict[str, Any]]:
    det = _parse_intents(message)
    if det:
        return det
    planned = _llm_plan_tools(message)
    return planned[:_MAX_TOOLS]


def iter_companion_events(
    db: Session,
    message: str,
    *,
    project_key: str = "",
    project_id: int | None = None,
    user_id: int | None = None,
    created_by: str = "",
    confirmed_tools: list[str] | None = None,
    history: list[dict] | None = None,
    turn_id: str | None = None,
    resume_pending: list[dict] | None = None,
    agent_context: str = "",
    skill_id: int | None = None,
) -> Generator[dict[str, Any], None, dict[str, Any]]:
    """Yield SSE-shaped events; return final turn summary."""
    t0 = time.time()
    tid = turn_id or str(uuid.uuid4())
    confirmed = set(confirmed_tools or [])
    yield {"event": "thinking", "turn_id": tid, "data": {"message": "Mentrix thinking…"}}

    intents = resume_pending or _merge_intents(message)
    packed_ctx = build_agent_context(
        db,
        skill_id=skill_id,
        project_id=project_id,
        agent_context=agent_context,
    )
    tool_results: list[dict] = []
    pending: list[dict] = []
    board_items: list[dict] = []
    navigations: list[str] = []
    run_id: int | None = None

    for intent in intents[:_MAX_TOOLS]:
        name = intent["name"]
        args = intent.get("args") or {}
        yield {"event": "tool_start", "turn_id": tid, "data": {"tool": name, "args": {k: v for k, v in args.items() if "password" not in k.lower() and "token" not in k.lower()}}}

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
            yield {"event": "tool_end", "turn_id": tid, "data": {"tool": name, "ok": False, "error": "denied"}}
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
            yield {
                "event": "pending_confirm",
                "turn_id": tid,
                "data": {"tool": name, "args": args, "reason": f"Allow Mentrix to run {name}?"},
            }
            yield {"event": "tool_end", "turn_id": tid, "data": {"tool": name, "ok": False, "error": "pending_confirm"}}
            continue

        result = _exec_tool(db, name, args, project_key=project_key, created_by=created_by)
        tool_results.append({"tool": name, "result": result, "permission": perm})
        log_mentrix_tool(db, name, args=args, result="ok" if result.get("ok") else "error", user_id=user_id)
        if result.get("board"):
            board_items.append(result["board"])
            yield {"event": "artifact", "turn_id": tid, "data": result["board"]}
        if result.get("board_extra"):
            board_items.append(result["board_extra"])
            yield {"event": "artifact", "turn_id": tid, "data": result["board_extra"]}
        if result.get("board_progress"):
            board_items.append(result["board_progress"])
            yield {"event": "artifact", "turn_id": tid, "data": result["board_progress"]}
        nav = result.get("navigate")
        if nav:
            navigations.append(nav)
            yield {"event": "navigate", "turn_id": tid, "data": {"path": nav}}
        if result.get("run_id"):
            run_id = int(result["run_id"])
        yield {
            "event": "tool_end",
            "turn_id": tid,
            "data": {"tool": name, "ok": bool(result.get("ok")), "error": result.get("error")},
        }

    context_bits = []
    if packed_ctx:
        context_bits.append(packed_ctx)
    for tr in tool_results:
        if tr.get("denied"):
            context_bits.append(f"DENIED {tr['tool']}")
        else:
            context_bits.append(json.dumps({tr["tool"]: tr.get("result")}, default=str)[:800])
    if pending:
        context_bits.append("Pending: " + ", ".join(p["tool"] for p in pending))

    if pending and not tool_results:
        reply = (
            "I can help, but I need your permission for: "
            + ", ".join(p["tool"] for p in pending)
            + ". Allow to continue."
        )
    elif any(tr.get("denied") for tr in tool_results) and not any(not tr.get("denied") for tr in tool_results):
        reply = "Org policy blocked that action."
    else:
        # Spoken clarification when OS-desktop intent opened Explorer (not Dashboard).
        if any(
            tr.get("tool") == "computer_open_app" and not tr.get("denied")
            for tr in tool_results
        ) and os_desktop_phrase(message):
            reply = (
                "Computer Mode desktop action is ready — confirm Allow if prompted. "
                "That is your OS desktop, not the ZECT Dashboard."
            )
        else:
            fast = _fast_tool_reply(tool_results, board_items, navigations)
            reply = fast or _llm_answer(message, "\n".join(context_bits))

    # token chunks for realtime feel
    chunk = max(24, len(reply) // 4 or 24)
    for i in range(0, len(reply), chunk):
        yield {"event": "token", "turn_id": tid, "data": {"text": reply[i : i + chunk]}}

    summary = {
        "reply": reply,
        "avatar_state": "needs_permission" if pending else ("speaking" if reply else "idle"),
        "tools": tool_results,
        "pending_confirmations": pending,
        "board": board_items,
        "navigate": navigations[0] if navigations else None,
        "latency_mode": "fast_tools" if tool_results and not pending else ("pending" if pending else "llm"),
        "turn_id": tid,
        "run_id": run_id,
        "latency_ms": int((time.time() - t0) * 1000),
        "history_tail": (history or [])[-6:]
        + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}],
    }

    if pending:
        _TURN_STORE[tid] = {
            "message": message,
            "project_key": project_key,
            "project_id": project_id,
            "user_id": user_id,
            "created_by": created_by,
            "pending": pending,
            "history": history or [],
        }

    yield {
        "event": "done",
        "turn_id": tid,
        "data": {
            "reply": reply,
            "run_id": run_id,
            "latency_ms": summary["latency_ms"],
            "pending_confirmations": pending,
            "navigate": summary["navigate"],
            "board": board_items,
            "avatar_state": summary["avatar_state"],
            "latency_mode": summary["latency_mode"],
        },
    }
    return summary


def run_companion_turn_v2(
    db: Session,
    message: str,
    *,
    project_key: str = "",
    project_id: int | None = None,
    user_id: int | None = None,
    created_by: str = "",
    confirmed_tools: list[str] | None = None,
    history: list[dict] | None = None,
    agent_context: str = "",
    skill_id: int | None = None,
) -> dict[str, Any]:
    """Non-streaming turn that executes once and returns full payload."""
    events: list[dict] = []
    gen = iter_companion_events(
        db,
        message,
        project_key=project_key,
        project_id=project_id,
        user_id=user_id,
        created_by=created_by,
        confirmed_tools=confirmed_tools,
        history=history,
        agent_context=agent_context,
        skill_id=skill_id,
    )
    final: dict[str, Any] | None = None
    try:
        while True:
            events.append(next(gen))
    except StopIteration as stop:
        final = stop.value if isinstance(stop.value, dict) else None
    if final:
        return final
    done = next((e for e in reversed(events) if e.get("event") == "done"), None)
    if not done:
        return {"reply": "Mentrix ready.", "tools": [], "pending_confirmations": [], "board": []}
    d = done.get("data") or {}
    tools = []
    for e in events:
        if e.get("event") == "tool_end":
            td = e.get("data") or {}
            tools.append(
                {
                    "tool": td.get("tool"),
                    "denied": td.get("error") == "denied",
                    "result": {"ok": td.get("ok"), "error": td.get("error")},
                }
            )
    return {
        "reply": d.get("reply"),
        "avatar_state": d.get("avatar_state"),
        "tools": tools,
        "pending_confirmations": d.get("pending_confirmations") or [],
        "board": d.get("board") or [],
        "navigate": d.get("navigate"),
        "latency_mode": d.get("latency_mode"),
        "turn_id": done.get("turn_id"),
        "run_id": d.get("run_id"),
        "latency_ms": d.get("latency_ms"),
        "history_tail": (history or [])[-6:]
        + [{"role": "user", "content": message}, {"role": "assistant", "content": d.get("reply") or ""}],
    }


# Public alias used by router
def run_companion_turn(
    db: Session,
    message: str,
    *,
    project_key: str = "",
    project_id: int | None = None,
    user_id: int | None = None,
    created_by: str = "",
    confirmed_tools: list[str] | None = None,
    history: list[dict] | None = None,
    agent_context: str = "",
    skill_id: int | None = None,
) -> dict[str, Any]:
    return run_companion_turn_v2(
        db,
        message,
        project_key=project_key,
        project_id=project_id,
        user_id=user_id,
        created_by=created_by,
        confirmed_tools=confirmed_tools,
        history=history,
        agent_context=agent_context,
        skill_id=skill_id,
    )


def resume_companion_turn(
    db: Session,
    turn_id: str,
    confirmed_tools: list[str],
    *,
    created_by: str = "",
) -> Iterator[dict[str, Any]]:
    state = _TURN_STORE.pop(turn_id, None)
    if not state:
        yield {"event": "error", "turn_id": turn_id, "data": {"error": "turn_expired"}}
        return
    pending_intents = [{"name": p["tool"], "args": p.get("args") or {}} for p in state.get("pending") or []]
    yield from iter_companion_events(
        db,
        state["message"],
        project_key=state.get("project_key") or "",
        project_id=state.get("project_id"),
        user_id=state.get("user_id"),
        created_by=created_by or "",
        confirmed_tools=confirmed_tools,
        history=state.get("history"),
        turn_id=turn_id,
        resume_pending=pending_intents,
    )


def sse_pack(event: dict[str, Any]) -> str:
    name = event.get("event") or "message"
    payload = json.dumps(event, default=str)
    return f"event: {name}\ndata: {payload}\n\n"

"""MentrixConnector gateway — routes personal-ops actions native → MCP → desktop/browser."""

from __future__ import annotations

import os
from typing import Any

from app.services.mentrix.connectors.base import ConnectorCapability, ConnectorHealth, MentrixConnector


class _BaseConnector:
    id: str = "base"
    name: str = "Base"
    permission_requirement: str = "require_approval"

    def health(self) -> ConnectorHealth:
        raise NotImplementedError

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError


class M365Connector(_BaseConnector):
    id = "m365"
    name = "Microsoft 365 / Graph"
    permission_requirement = "email:read"

    def health(self) -> ConnectorHealth:
        from app.adapters import m365_graph

        st = m365_graph.execute("status", {})
        configured = bool(st.get("configured"))
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured" if configured else "missing_creds",
            transport="native",
            detail="Graph mail/calendar" if configured else "IMAP/SMTP fallback active",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("list_messages", "Outlook inbox", "email:read", ["Mail.Read"], kind="read", permission_policy="ALLOW"),
                ConnectorCapability("list_events", "Calendar events", "email:read", ["Calendars.Read"], kind="read", permission_policy="ALLOW"),
                ConnectorCapability("create_draft", "Outlook draft", "email:draft", ["Mail.ReadWrite"], kind="write", permission_policy="CONFIRM"),
            ],
            auth_status="configured" if configured else "missing_creds",
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        from app.adapters import m365_graph

        return m365_graph.execute(action, arguments or {})


class EmailImapSmtpConnector(_BaseConnector):
    id = "email_imap_smtp"
    name = "Email IMAP/SMTP"
    permission_requirement = "email:read"

    def health(self) -> ConnectorHealth:
        imap = bool((os.getenv("IMAP_HOST") or os.getenv("EMAIL_IMAP_HOST") or "").strip())
        smtp = bool((os.getenv("SMTP_HOST") or "").strip())
        if imap or smtp:
            status = "configured"
        else:
            status = "missing_creds"
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status=status,
            transport="native",
            detail=f"imap={imap} smtp={smtp}",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("digest", "IMAP inbox digest", "email:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("send", "SMTP send", "email:send", kind="write", permission_policy="CONFIRM"),
            ],
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if action in ("digest", "list_messages"):
            from app.services.mentrix.providers import get_email_provider

            return get_email_provider().digest(limit=int(args.get("limit") or 8))
        if action in ("send", "send_email"):
            from app.adapters import email_adapter

            return email_adapter.execute("send_email", args, enabled=True)
        return {"status": "unknown_action", "action": action}


class SlackConnector(_BaseConnector):
    id = "slack"
    name = "Slack"
    permission_requirement = "slack:read"

    def health(self) -> ConnectorHealth:
        tok = bool((os.getenv("SLACK_BOT_TOKEN") or "").strip())
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured" if tok else "missing_creds",
            transport="mcp",
            detail="SLACK_BOT_TOKEN" if tok else "set SLACK_BOT_TOKEN",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("digest", "Channel history / mentions", "slack:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("send_message", "Post message", "slack:send", kind="write", permission_policy="CONFIRM"),
                ConnectorCapability("mentions", "Mention scan", "slack:read", kind="read", permission_policy="ALLOW"),
            ],
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        from app.infrastructure.database import SessionLocal
        from app.services.mcp.hub import execute_tool

        args = arguments or {}
        db = SessionLocal()
        try:
            if action in ("digest", "channel_history", "mentions"):
                channel = args.get("channel") or os.getenv("SLACK_DEFAULT_CHANNEL", "general")
                hist = execute_tool(
                    db,
                    server_id="slack",
                    tool_name="channel_history",
                    arguments={"channel": str(channel).lstrip("#"), "limit": int(args.get("limit") or 20)},
                )
                messages = (hist.get("result") or hist).get("messages") if isinstance(hist, dict) else []
                if not isinstance(messages, list):
                    # hub may nest differently
                    inner = hist.get("result") if isinstance(hist, dict) else hist
                    if isinstance(inner, dict):
                        messages = inner.get("messages") or []
                    else:
                        messages = []
                if action == "mentions":
                    needle = (args.get("user") or os.getenv("SLACK_MENTION_USER") or "").strip().lower()
                    if needle:
                        messages = [
                            m
                            for m in messages
                            if needle in str(m.get("text") or "").lower() or "<@" in str(m.get("text") or "")
                        ]
                return {"ok": True, "via": "slack_mcp", "channel": channel, "messages": messages}
            if action == "send_message":
                return execute_tool(
                    db,
                    server_id="slack",
                    tool_name="send_message",
                    arguments=args,
                )
            return {"status": "unknown_action", "action": action}
        finally:
            db.close()


class JiraConnector(_BaseConnector):
    id = "jira"
    name = "Jira"
    permission_requirement = "jira:read"

    def health(self) -> ConnectorHealth:
        ok = bool((os.getenv("JIRA_BASE_URL") or os.getenv("MCP_JIRA_URL") or "").strip()) and bool(
            (os.getenv("JIRA_API_TOKEN") or "").strip()
        )
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured" if ok else "missing_creds",
            transport="mcp",
            detail="JIRA_* configured" if ok else "set JIRA_BASE_URL + JIRA_EMAIL + JIRA_API_TOKEN",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("assigned", "Issues assigned to me", "jira:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("get_issue", "Get issue", "jira:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("search", "JQL search", "jira:read", kind="read", permission_policy="ALLOW"),
            ],
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        from app.infrastructure.database import SessionLocal
        from app.services.mcp.hub import execute_tool

        args = dict(arguments or {})
        db = SessionLocal()
        try:
            if action in ("assigned", "my_issues"):
                user = args.get("assignee") or os.getenv("JIRA_ASSIGNEE") or "currentUser()"
                jql = args.get("jql") or f"assignee = {user} AND resolution = EMPTY ORDER BY updated DESC"
                return execute_tool(
                    db,
                    server_id="jira",
                    tool_name="search_issues",
                    arguments={"jql": jql, "max_results": int(args.get("limit") or 15)},
                )
            if action == "get_issue":
                return execute_tool(db, server_id="jira", tool_name="get_issue", arguments=args)
            if action == "search":
                return execute_tool(db, server_id="jira", tool_name="search_issues", arguments=args)
            return {"status": "unknown_action", "action": action}
        finally:
            db.close()


class GitHubConnector(_BaseConnector):
    id = "github"
    name = "GitHub"
    permission_requirement = "repository:read"

    def health(self) -> ConnectorHealth:
        tok = bool((os.getenv("GITHUB_TOKEN") or "").strip())
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured" if tok else "missing_creds",
            transport="mcp",
            detail="GITHUB_TOKEN" if tok else "set GITHUB_TOKEN",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("list_prs", "Open PRs", "repository:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("ci_status", "PR / CI summary", "repository:read", kind="read", permission_policy="ALLOW"),
            ],
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        from app.infrastructure.database import SessionLocal
        from app.services.mcp.hub import execute_tool

        args = dict(arguments or {})
        owner = args.get("owner") or os.getenv("GITHUB_OWNER") or ""
        repo = args.get("repo") or os.getenv("GITHUB_REPO") or ""
        db = SessionLocal()
        try:
            if action in ("list_prs", "prs"):
                return execute_tool(
                    db,
                    server_id="github",
                    tool_name="list_pulls",
                    arguments={"owner": owner, "repo": repo, "state": args.get("state", "open")},
                )
            if action in ("ci_status", "pr_ci"):
                pulls = execute_tool(
                    db,
                    server_id="github",
                    tool_name="list_pulls",
                    arguments={"owner": owner, "repo": repo, "state": "open"},
                )
                return {"ok": True, "via": "github_mcp", "owner": owner, "repo": repo, "pulls": pulls}
            return {"status": "unknown_action", "action": action}
        finally:
            db.close()


class ZoomConnector(_BaseConnector):
    id = "zoom"
    name = "Zoom"
    permission_requirement = "desktop:control"

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured",
            transport="desktop",
            detail="Open/join only — no Zoom Meeting API schedule",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("open", "Open Zoom.exe", "desktop:control", kind="write", permission_policy="CONFIRM"),
                ConnectorCapability("join_url", "Open zoom.us join URL", "desktop:control", kind="write", permission_policy="CONFIRM"),
                ConnectorCapability("schedule", "Zoom Meeting API schedule", "desktop:control", kind="write", permission_policy="DENY"),
            ],
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        act = str(action or "").strip().lower()
        if act in ("schedule", "create_meeting", "auto_share", "share"):
            return {
                "ok": False,
                "status": "denied",
                "error": "zoom_schedule_and_auto_share_denied",
                "note": "Open/join only — Zoom Meeting API schedule and auto screen-share are out of scope",
            }
        if act not in ("open", "join_url", "join"):
            return {
                "ok": False,
                "status": "denied",
                "error": "zoom_action_not_allowed",
                "action": act,
            }
        return {
            "ok": True,
            "via": "desktop",
            "action": act,
            "desktop": "computer_open_app" if act == "open" else "open_zoom",
            "args": arguments or {},
            "note": "Routed to Computer Mode — schedule refused by design",
        }


class FilesystemConnector(_BaseConnector):
    id = "filesystem"
    name = "Filesystem (allowlisted)"
    permission_requirement = "filesystem:move"

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured",
            transport="desktop",
            detail="Desktop/Documents/Downloads — never delete",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("mkdir", "Create folder", "filesystem:move", kind="write", permission_policy="CONFIRM"),
                ConnectorCapability("list_dir", "List directory", "filesystem:scan", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("move_path", "Move/rename", "filesystem:move", kind="write", permission_policy="CONFIRM"),
                ConnectorCapability("organize", "File organize plan/execute", "filesystem:move", kind="write", permission_policy="CONFIRM"),
                ConnectorCapability("delete", "Delete files", "filesystem:move", kind="write", permission_policy="DENY"),
            ],
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        act = str(action or "").strip().lower()
        if act in ("delete", "unlink", "rmdir", "remove", "rm", "rmtree", "delete_file"):
            return {
                "ok": False,
                "status": "denied",
                "error": "delete_never_allowed",
                "note": "Mentrix never deletes files",
            }
        if act not in ("mkdir", "list_dir", "move_path", "organize", "file_organize"):
            return {
                "ok": False,
                "status": "denied",
                "error": "filesystem_action_not_allowed",
                "action": act,
            }
        return {
            "ok": True,
            "via": "desktop",
            "action": act,
            "desktop": act if act in ("mkdir", "list_dir", "move_path") else "file_organize",
            "args": arguments or {},
        }


class BrowserFallbackConnector(_BaseConnector):
    id = "browser"
    name = "Browser fallback"
    permission_requirement = "desktop:control"

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured",
            transport="browser",
            detail="Playwright / browser_navigate allowlisted",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("navigate", "Open allowlisted URL", "desktop:control", kind="write", permission_policy="CONFIRM"),
                ConnectorCapability("snapshot", "DOM snapshot", "desktop:view", kind="read", permission_policy="ALLOW"),
            ],
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "via": "browser",
            "action": action,
            "desktop": f"browser_{action}" if not str(action).startswith("browser_") else action,
            "args": arguments or {},
        }


class WebIntelligenceConnector(_BaseConnector):
    id = "web"
    name = "Web Intelligence"
    permission_requirement = "web:read"

    def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            id=self.id,
            name=self.name,
            status="configured",
            transport="native",
            detail="URL/RSS/GitHub fetch with SSRF boundary + UNTRUSTED_EXTERNAL_CONTEXT",
            permission_requirement=self.permission_requirement,
            capabilities=[
                ConnectorCapability("fetch_url", "Fetch approved URL", "web:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("fetch_rss", "Ingest RSS/Atom", "web:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability("fetch_github", "GitHub content via trusted path", "repository:read", kind="read", permission_policy="ALLOW"),
                ConnectorCapability(
                    "browser_snapshot",
                    "Allowlisted browser snapshot (confirm required)",
                    "desktop:view",
                    kind="read",
                    permission_policy="CONFIRM",
                ),
            ],
            auth_status="configured",
        )

    def invoke(self, action: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        from app.services.web_intelligence.service import fetch_external

        args = arguments or {}
        url = str(args.get("url") or "")
        raw_adapter = str(args.get("adapter") or action.replace("fetch_", "") or "url")
        adapter = raw_adapter.strip().lower()
        if adapter in ("browser_snapshot", "snapshot"):
            adapter = "browser"
        confirmed = bool(args.get("confirmed_browser") or args.get("confirmed"))
        try:
            fr = fetch_external(url, adapter=adapter if adapter != "url" else None, confirmed_browser=confirmed)
            return {
                "ok": True,
                "via": "web_intelligence",
                "url": fr.url,
                "title": fr.title,
                "adapter": fr.adapter,
                "markdown_preview": (fr.markdown or "")[:2000],
                "tag": "UNTRUSTED_EXTERNAL_CONTEXT",
            }
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e), "tag": "UNTRUSTED_EXTERNAL_CONTEXT"}


_REGISTRY: dict[str, MentrixConnector] = {
    "m365": M365Connector(),
    "email_imap_smtp": EmailImapSmtpConnector(),
    "slack": SlackConnector(),
    "jira": JiraConnector(),
    "github": GitHubConnector(),
    "zoom": ZoomConnector(),
    "filesystem": FilesystemConnector(),
    "browser": BrowserFallbackConnector(),
    "web": WebIntelligenceConnector(),
}


def list_connectors() -> list[MentrixConnector]:
    return list(_REGISTRY.values())


def get_connector(connector_id: str) -> MentrixConnector | None:
    return _REGISTRY.get((connector_id or "").strip().lower())


def connector_health_matrix() -> dict[str, Any]:
    rows = [c.health().as_dict() for c in list_connectors()]
    # Prefer M365 when configured; IMAP always listed as fallback
    m365 = next((r for r in rows if r["id"] == "m365"), None)
    email = next((r for r in rows if r["id"] == "email_imap_smtp"), None)
    mail_primary = "m365" if m365 and m365.get("status") == "configured" else "email_imap_smtp"
    return {
        "connectors": rows,
        "mail_primary": mail_primary,
        "mail_fallback": "email_imap_smtp",
        "permission_note": "All writes gate via Mentrix Permission Broker + CapabilityGrant",
    }


def route_personal_action(
    source: str,
    action: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve connector by source preference: native Graph → IMAP → MCP → desktop/browser."""
    src = (source or "").strip().lower()
    mapping = {
        "email": ["m365", "email_imap_smtp"],
        "m365": ["m365", "email_imap_smtp"],
        "outlook": ["m365", "email_imap_smtp"],
        "calendar": ["m365", "email_imap_smtp"],
        "slack": ["slack"],
        "jira": ["jira"],
        "github": ["github"],
        "zoom": ["zoom"],
        "filesystem": ["filesystem"],
        "desktop": ["filesystem"],
        "browser": ["browser"],
    }
    order = mapping.get(src, [src] if src in _REGISTRY else [])
    last: dict[str, Any] = {"ok": False, "error": "no_connector", "source": src}
    for cid in order:
        conn = get_connector(cid)
        if not conn:
            continue
        h = conn.health()
        if h.status == "missing_creds" and cid == "m365":
            continue  # fall through to IMAP
        try:
            out = conn.invoke(action, arguments)
            out = dict(out) if isinstance(out, dict) else {"result": out}
            out.setdefault("connector", cid)
            out.setdefault("transport", h.transport)
            if out.get("status") in ("missing_creds", "not_configured") and cid == "m365":
                last = out
                continue
            return out
        except Exception as exc:  # noqa: BLE001
            last = {"ok": False, "error": str(exc)[:300], "connector": cid}
    return last

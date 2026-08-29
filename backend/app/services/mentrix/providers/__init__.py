"""PA-2 provider interfaces — Email / Slack / Calendar (ZECT-owned names only)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlparse


@dataclass
class ProviderItem:
    id: str
    title: str
    body: str = ""
    source: str = ""
    when: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class DraftCitation:
    kind: str  # email | slack | calendar | lattice | note
    ref: str
    excerpt: str = ""


def _csv_allowlist(env_name: str, default: str = "") -> list[str]:
    raw = (os.getenv(env_name) or default).strip()
    if not raw:
        return []
    if raw == "*":
        return ["*"]
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def allowlist_permits(value: str, allow: list[str]) -> bool:
    v = (value or "").strip().lower()
    if not allow:
        return True  # empty = no extra restriction beyond capability grants
    if "*" in allow:
        return True
    return any(v == a or v.endswith("@" + a) or v.endswith("." + a) or a in v for a in allow)


class EmailProvider(Protocol):
    def digest(self, *, limit: int = 8) -> dict[str, Any]: ...

    def draft_reply(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        citations: list[DraftCitation] | None = None,
        dictation: str = "",
    ) -> dict[str, Any]: ...


class SlackProvider(Protocol):
    def digest(self, *, limit: int = 20) -> dict[str, Any]: ...

    def draft_message(
        self,
        *,
        channel: str,
        text: str,
        citations: list[DraftCitation] | None = None,
    ) -> dict[str, Any]: ...


class CalendarProvider(Protocol):
    def upcoming(self, *, limit: int = 10) -> list[ProviderItem]: ...

    def draft_event(
        self,
        *,
        title: str,
        start_iso: str,
        end_iso: str = "",
        attendees: list[str] | None = None,
        body: str = "",
    ) -> dict[str, Any]: ...


class MentrixEmailProvider:
    """Graph-first when configured; IMAP digest fallback (no second email system)."""

    def digest(self, *, limit: int = 8) -> dict[str, Any]:
        from app.adapters import m365_graph

        if m365_graph.configured():
            out = m365_graph.execute("list_messages", {"limit": limit})
            if out.get("ok"):
                out["via"] = "m365_graph"
                return out
            # fall through to IMAP on Graph errors

        from app.services.mentrix.email_inbox import fetch_inbox_digest

        out = fetch_inbox_digest(limit=limit)
        allow = _csv_allowlist("MENTRIX_EMAIL_ALLOWLIST")
        if allow and "*" not in allow and out.get("ok"):
            items = out.get("messages") or out.get("items") or []
            filtered = []
            for it in items:
                addr = str(it.get("from") or it.get("address") or "")
                domain = addr.split("@")[-1].lower() if "@" in addr else addr.lower()
                if allowlist_permits(domain, allow) or allowlist_permits(addr, allow):
                    filtered.append(it)
            if "messages" in out:
                out["messages"] = filtered
            if "items" in out:
                out["items"] = filtered
            out["allowlist_applied"] = True
        out.setdefault("via", "imap")
        return out

    def draft_reply(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        citations: list[DraftCitation] | None = None,
        dictation: str = "",
    ) -> dict[str, Any]:
        allow = _csv_allowlist("MENTRIX_EMAIL_ALLOWLIST")
        domain = to.split("@")[-1].lower() if "@" in to else ""
        if to and allow and not allowlist_permits(domain or to, allow):
            return {"ok": False, "error": "email_destination_not_allowlisted", "to": to}
        return {
            "ok": True,
            "channel": "email",
            "to": to,
            "subject": subject,
            "body": body,
            "dictation": dictation,
            "citations": [
                {"kind": c.kind, "ref": c.ref, "excerpt": c.excerpt[:500]} for c in (citations or [])
            ],
        }


class MentrixSlackProvider:
    def digest(self, *, limit: int = 20) -> dict[str, Any]:
        try:
            from app.services.mcp.hub import execute_tool
            from app.infrastructure.database import SessionLocal

            db = SessionLocal()
            try:
                channel = os.getenv("SLACK_DEFAULT_CHANNEL", "general")
                allow = _csv_allowlist("MENTRIX_SLACK_CHANNEL_ALLOWLIST")
                if allow and "*" not in allow and not allowlist_permits(channel, allow):
                    return {"ok": False, "error": "slack_channel_not_allowlisted", "channel": channel}
                hist = execute_tool(
                    db,
                    server_id="slack",
                    tool_name="channel_history",
                    arguments={"channel": channel.lstrip("#"), "limit": limit},
                )
                return {"ok": True, "channel": channel, "history": hist, "via": "SlackProvider"}
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:300], "via": "SlackProvider"}

    def draft_message(
        self,
        *,
        channel: str,
        text: str,
        citations: list[DraftCitation] | None = None,
    ) -> dict[str, Any]:
        allow = _csv_allowlist("MENTRIX_SLACK_CHANNEL_ALLOWLIST")
        ch = str(channel or "").lstrip("#")
        if allow and not allowlist_permits(ch, allow):
            return {"ok": False, "error": "slack_channel_not_allowlisted", "channel": ch}
        return {
            "ok": True,
            "channel": ch,
            "text": text,
            "citations": [
                {"kind": c.kind, "ref": c.ref, "excerpt": c.excerpt[:500]} for c in (citations or [])
            ],
        }


class MentrixCalendarProvider:
    """Graph calendar when configured; else ICS / demo — never deletes events."""

    def upcoming(self, *, limit: int = 10) -> list[ProviderItem]:
        from app.adapters import m365_graph

        if m365_graph.configured():
            out = m365_graph.execute("list_events", {"limit": limit})
            if out.get("ok"):
                items: list[ProviderItem] = []
                for e in out.get("events") or []:
                    items.append(
                        ProviderItem(
                            id=str(e.get("id") or "")[:200],
                            title=str(e.get("title") or "Event")[:300],
                            body=str(e.get("preview") or "")[:1000],
                            source="m365_graph",
                            when=e.get("start"),
                            meta={"web_link": e.get("web_link"), "end": e.get("end")},
                        )
                    )
                return items

        ics_url = (os.getenv("MENTRIX_CALENDAR_ICS_URL") or "").strip()
        if ics_url:
            return self._from_ics(ics_url, limit=limit)
        # Fallback: static demo events from env MENTRIX_CALENDAR_DEMO=1
        if (os.getenv("MENTRIX_CALENDAR_DEMO") or "").strip().lower() in ("1", "true", "yes"):
            now = datetime.now(timezone.utc).isoformat()
            return [
                ProviderItem(
                    id="demo-1",
                    title="Mentrix standup",
                    body="Demo calendar event (set MENTRIX_CALENDAR_ICS_URL or MS_GRAPH_* for real data)",
                    source="calendar_demo",
                    when=now,
                    meta={"attendees": []},
                )
            ]
        return []

    def draft_event(
        self,
        *,
        title: str,
        start_iso: str,
        end_iso: str = "",
        attendees: list[str] | None = None,
        body: str = "",
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "channel": "calendar",
            "title": title,
            "start": start_iso,
            "end": end_iso,
            "attendees": attendees or [],
            "body": body,
            "needs_write_approval": True,
            "note": "Calendar write requires explicit approval (PA-3). Never auto-create.",
        }

    def _from_ics(self, url: str, *, limit: int) -> list[ProviderItem]:
        try:
            import httpx

            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return []
            resp = httpx.get(url, timeout=15.0)
            if resp.status_code >= 400:
                return []
            text = resp.text or ""
            items: list[ProviderItem] = []
            blocks = text.split("BEGIN:VEVENT")
            for block in blocks[1 : limit + 1]:
                def _field(name: str) -> str:
                    for line in block.splitlines():
                        if line.startswith(name + ":") or line.startswith(name + ";"):
                            return line.split(":", 1)[-1].strip()
                    return ""

                uid = _field("UID") or f"ics-{len(items)}"
                summary = _field("SUMMARY") or "Event"
                dtstart = _field("DTSTART")
                desc = _field("DESCRIPTION")
                items.append(
                    ProviderItem(
                        id=uid[:200],
                        title=summary[:300],
                        body=desc[:1000],
                        source="ics",
                        when=dtstart or None,
                        meta={"url_host": parsed.hostname or ""},
                    )
                )
            return items
        except Exception:  # noqa: BLE001
            return []


def get_email_provider() -> MentrixEmailProvider:
    return MentrixEmailProvider()


def get_slack_provider() -> MentrixSlackProvider:
    return MentrixSlackProvider()


def get_calendar_provider() -> MentrixCalendarProvider:
    return MentrixCalendarProvider()

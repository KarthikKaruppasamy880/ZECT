"""PersonalAction API + DailyBrief aggregation — Mentrix personal ops only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication, log_audit
from app.infrastructure.database import get_db
from app.models import PersonalAction, WorkItem

router = APIRouter(prefix="/api/personal-actions", tags=["personal-actions"])

SUGGESTED_VERBS = ("Analyze", "Fix", "Draft", "Reply", "Prepare", "Organize", "Continue")


def _parse_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def serialize_action(row: PersonalAction) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "source": row.source,
        "type": row.type,
        "title": row.title,
        "due": row.due.isoformat() if row.due else None,
        "priority": row.priority or "normal",
        "status": row.status or "open",
        "target": row.target or "",
        "provenance": _parse_json(row.provenance_json, {}),
        "suggested_actions": _parse_json(row.suggested_actions_json, []),
        "permission_requirement": row.permission_requirement or "require_approval",
        "external_id": row.external_id or "",
        "project_id": row.project_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class PersonalActionCreate(BaseModel):
    source: str
    type: str = "task"
    title: str
    due: Optional[datetime] = None
    priority: str = "normal"
    status: str = "open"
    target: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    suggested_actions: list[str] = Field(default_factory=list)
    permission_requirement: str = "require_approval"
    external_id: str = ""
    project_id: Optional[int] = None


class PersonalActionPatch(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    title: Optional[str] = None
    due: Optional[datetime] = None
    suggested_actions: Optional[list[str]] = None
    target: Optional[str] = None


@router.get("")
@require_authentication
def list_personal_actions(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(PersonalAction)
    uid = getattr(current_user, "user_id", None)
    if uid:
        q = q.filter((PersonalAction.user_id == uid) | (PersonalAction.user_id.is_(None)))
    if status:
        q = q.filter(PersonalAction.status == status)
    if source:
        q = q.filter(PersonalAction.source == source)
    rows = q.order_by(PersonalAction.updated_at.desc()).limit(limit).all()
    return {"actions": [serialize_action(r) for r in rows]}


@router.post("")
@require_authentication
def create_personal_action(
    data: PersonalActionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verbs = [v for v in (data.suggested_actions or []) if v in SUGGESTED_VERBS]
    if not verbs:
        verbs = ["Continue"]
    row = PersonalAction(
        user_id=getattr(current_user, "user_id", None),
        source=(data.source or "other").strip().lower(),
        type=(data.type or "task").strip().lower(),
        title=(data.title or "").strip()[:500] or "Untitled",
        due=data.due,
        priority=(data.priority or "normal").strip().lower(),
        status=(data.status or "open").strip().lower(),
        target=(data.target or "")[:2000],
        provenance_json=json.dumps(data.provenance or {}),
        suggested_actions_json=json.dumps(verbs),
        permission_requirement=data.permission_requirement or "require_approval",
        external_id=(data.external_id or "")[:200],
        project_id=data.project_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="create_personal_action",
        resource_id=row.id,
        resource_type="personal_action",
        details={"source": row.source, "title": row.title},
    )
    return serialize_action(row)


@router.patch("/{action_id}")
@require_authentication
def patch_personal_action(
    action_id: int,
    data: PersonalActionPatch,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(PersonalAction).filter(PersonalAction.id == action_id).first()
    if not row:
        raise HTTPException(404, "PersonalAction not found")
    if data.status is not None:
        row.status = data.status.strip().lower()
    if data.priority is not None:
        row.priority = data.priority.strip().lower()
    if data.title is not None:
        row.title = data.title.strip()[:500]
    if data.due is not None:
        row.due = data.due
    if data.target is not None:
        row.target = data.target[:2000]
    if data.suggested_actions is not None:
        verbs = [v for v in data.suggested_actions if v in SUGGESTED_VERBS]
        row.suggested_actions_json = json.dumps(verbs or ["Continue"])
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return serialize_action(row)


@router.get("/connectors/health")
@require_authentication
def connectors_health(current_user: CurrentUser = Depends(get_current_user)):
    from app.services.mentrix.connectors import connector_health_matrix

    return connector_health_matrix()


@router.post("/daily-brief")
@require_authentication
def build_daily_brief(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate information + PersonalActions from connectors + WorkItems."""
    brief = assemble_daily_brief(db, user_id=getattr(current_user, "user_id", None))
    return brief


def _upsert_action(
    db: Session,
    *,
    user_id: int | None,
    source: str,
    type_: str,
    title: str,
    target: str = "",
    external_id: str = "",
    suggested: list[str] | None = None,
    permission: str = "require_approval",
    provenance: dict | None = None,
    priority: str = "normal",
) -> PersonalAction:
    existing = None
    if external_id:
        existing = (
            db.query(PersonalAction)
            .filter(
                PersonalAction.external_id == external_id,
                PersonalAction.source == source,
            )
            .first()
        )
    verbs = [v for v in (suggested or []) if v in SUGGESTED_VERBS] or ["Continue"]
    if existing:
        existing.title = title[:500]
        existing.target = target[:2000]
        existing.suggested_actions_json = json.dumps(verbs)
        existing.provenance_json = json.dumps(provenance or {})
        existing.updated_at = datetime.now(timezone.utc)
        if existing.status == "done":
            pass
        db.commit()
        db.refresh(existing)
        return existing
    row = PersonalAction(
        user_id=user_id,
        source=source,
        type=type_,
        title=title[:500],
        target=target[:2000],
        external_id=external_id[:200],
        suggested_actions_json=json.dumps(verbs),
        permission_requirement=permission,
        provenance_json=json.dumps(provenance or {}),
        priority=priority,
        status="open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def assemble_daily_brief(db: Session, *, user_id: int | None = None) -> dict[str, Any]:
    from app.services.mentrix.connectors.gateway import route_personal_action, connector_health_matrix

    info: dict[str, Any] = {"email": [], "calendar": [], "slack": [], "jira": [], "github": [], "work_items": []}
    created: list[dict[str, Any]] = []

    # Email — Graph first, IMAP fallback
    try:
        mail = route_personal_action("email", "list_messages", {"limit": 8})
        if not mail.get("messages") and mail.get("ok") is not False:
            # IMAP digest shape
            dig = route_personal_action("email", "digest", {"limit": 8})
            msgs = dig.get("messages") or dig.get("items") or []
            mail = {"messages": msgs, "via": dig.get("via") or dig.get("connector")}
        for m in (mail.get("messages") or [])[:8]:
            title = m.get("subject") or m.get("title") or "Email"
            eid = str(m.get("id") or "")[:180]
            info["email"].append(m)
            row = _upsert_action(
                db,
                user_id=user_id,
                source="email",
                type_="message",
                title=f"Reply: {title}"[:500],
                target=str(m.get("from") or ""),
                external_id=f"email:{eid}" if eid else "",
                suggested=["Analyze", "Draft", "Reply"],
                permission="email:draft",
                provenance={"connector": mail.get("connector") or mail.get("via"), "raw_id": eid},
            )
            created.append(serialize_action(row))
    except Exception as exc:  # noqa: BLE001
        info["email"] = [{"error": str(exc)[:200]}]

    try:
        cal = route_personal_action("calendar", "list_events", {"limit": 8})
        events = cal.get("events") or []
        if not events:
            from app.services.mentrix.providers import get_calendar_provider

            items = get_calendar_provider().upcoming(limit=8)
            events = [
                {"id": i.id, "title": i.title, "start": i.when, "preview": i.body, "source": i.source}
                for i in items
            ]
        for e in events[:8]:
            title = e.get("title") or e.get("subject") or "Event"
            eid = str(e.get("id") or "")[:180]
            info["calendar"].append(e)
            row = _upsert_action(
                db,
                user_id=user_id,
                source="calendar",
                type_="event",
                title=f"Prepare: {title}"[:500],
                target=str(e.get("web_link") or e.get("start") or ""),
                external_id=f"cal:{eid}" if eid else "",
                suggested=["Prepare", "Continue"],
                permission="email:read",
                provenance={"start": e.get("start"), "raw_id": eid},
            )
            created.append(serialize_action(row))
    except Exception as exc:  # noqa: BLE001
        info["calendar"] = [{"error": str(exc)[:200]}]

    try:
        slack = route_personal_action("slack", "mentions", {"limit": 15})
        for m in (slack.get("messages") or [])[:10]:
            text = (m.get("text") or "")[:120]
            eid = str(m.get("ts") or "")[:180]
            info["slack"].append(m)
            row = _upsert_action(
                db,
                user_id=user_id,
                source="slack",
                type_="mention",
                title=f"Slack: {text}"[:500],
                target=str(slack.get("channel") or ""),
                external_id=f"slack:{eid}" if eid else "",
                suggested=["Analyze", "Draft", "Reply"],
                permission="slack:read",
                provenance={"ts": eid, "channel": slack.get("channel")},
            )
            created.append(serialize_action(row))
    except Exception as exc:  # noqa: BLE001
        info["slack"] = [{"error": str(exc)[:200]}]

    try:
        jira = route_personal_action("jira", "assigned", {"limit": 10})
        issues = []
        result = jira.get("result") if isinstance(jira.get("result"), dict) else jira
        if isinstance(result, dict):
            issues = result.get("issues") or []
        for issue in issues[:10]:
            key = issue.get("key") or ""
            fields = issue.get("fields") or {}
            summary = fields.get("summary") or key or "Jira issue"
            info["jira"].append({"key": key, "summary": summary})
            row = _upsert_action(
                db,
                user_id=user_id,
                source="jira",
                type_="issue",
                title=f"{key}: {summary}"[:500],
                target=key,
                external_id=f"jira:{key}" if key else "",
                suggested=["Analyze", "Fix", "Continue"],
                permission="jira:read",
                provenance={"key": key},
                priority="high",
            )
            created.append(serialize_action(row))
    except Exception as exc:  # noqa: BLE001
        info["jira"] = [{"error": str(exc)[:200]}]

    try:
        gh = route_personal_action("github", "list_prs", {})
        pulls = []
        result = gh.get("result") if isinstance(gh.get("result"), dict) else gh
        if isinstance(result, dict):
            pulls = result.get("pulls") or result.get("result", {}).get("pulls") if isinstance(result.get("result"), dict) else result.get("pulls") or []
        if not isinstance(pulls, list):
            pulls = []
        for pr in pulls[:10]:
            if isinstance(pr, dict):
                title = pr.get("title") or f"PR #{pr.get('number')}"
                num = str(pr.get("number") or pr.get("id") or "")
            else:
                title = str(pr)[:200]
                num = ""
            info["github"].append(pr if isinstance(pr, dict) else {"title": title})
            row = _upsert_action(
                db,
                user_id=user_id,
                source="github",
                type_="pr",
                title=f"Review PR: {title}"[:500],
                target=num,
                external_id=f"gh-pr:{num}" if num else "",
                suggested=["Analyze", "Fix", "Continue"],
                permission="repository:read",
                provenance={"pr": num},
            )
            created.append(serialize_action(row))
    except Exception as exc:  # noqa: BLE001
        info["github"] = [{"error": str(exc)[:200]}]

    try:
        wis = (
            db.query(WorkItem)
            .filter(WorkItem.status.notin_(["DONE", "CANCELLED"]))
            .order_by(WorkItem.updated_at.desc())
            .limit(10)
            .all()
        )
        for wi in wis:
            info["work_items"].append({"id": wi.id, "title": wi.title, "status": wi.status, "source": wi.source})
            row = _upsert_action(
                db,
                user_id=user_id,
                source="work_item",
                type_="task",
                title=f"Continue: {wi.title}"[:500],
                target=str(wi.id),
                external_id=f"wi:{wi.id}",
                suggested=["Continue", "Analyze", "Fix"],
                permission="repository:edit_workspace",
                provenance={"work_item_id": wi.id, "status": wi.status},
            )
            created.append(serialize_action(row))
    except Exception as exc:  # noqa: BLE001
        info["work_items"] = [{"error": str(exc)[:200]}]

    open_actions = (
        db.query(PersonalAction)
        .filter(PersonalAction.status.in_(["open", "in_progress"]))
        .order_by(PersonalAction.updated_at.desc())
        .limit(40)
        .all()
    )

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "information": info,
        "actions": [serialize_action(a) for a in open_actions],
        "upserted": len(created),
        "connectors": connector_health_matrix(),
        "suggested_verbs": list(SUGGESTED_VERBS),
    }

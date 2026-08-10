"""Personal Ops — connectors, PersonalAction, session grants, M365 fallback."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_connector_health_matrix_shape():
    from app.services.mentrix.connectors import connector_health_matrix

    matrix = connector_health_matrix()
    assert "connectors" in matrix
    ids = {c["id"] for c in matrix["connectors"]}
    assert "m365" in ids
    assert "email_imap_smtp" in ids
    assert "slack" in ids
    assert matrix.get("mail_fallback") == "email_imap_smtp"
    for row in matrix["connectors"]:
        assert "status" in row
        assert "capabilities" in row
        assert "permission_requirement" in row


def test_m365_status_missing_creds():
    from app.adapters import m365_graph

    out = m365_graph.execute("status", {})
    assert "configured" in out
    assert out.get("fallback")


def test_personal_action_crud_and_brief(client, auth_headers):
    r = client.post(
        "/api/personal-actions",
        headers=auth_headers,
        json={
            "source": "email",
            "type": "message",
            "title": "Reply: Test",
            "suggested_actions": ["Analyze", "Draft", "Reply"],
            "permission_requirement": "email:draft",
            "external_id": "test-email-1",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "email"
    assert "Reply" in body["suggested_actions"]
    assert body["id"]

    listed = client.get("/api/personal-actions?status=open", headers=auth_headers)
    assert listed.status_code == 200
    assert any(a["id"] == body["id"] for a in listed.json().get("actions") or [])

    brief = client.post("/api/personal-actions/daily-brief", headers=auth_headers)
    assert brief.status_code == 200, brief.text
    data = brief.json()
    assert data.get("ok") is True
    assert "information" in data
    assert "actions" in data
    assert "connectors" in data


def test_session_grant_mints_desktop_control(client, auth_headers, db: Session):
    r = client.post(
        "/api/permissions/grants/session",
        headers=auth_headers,
        json={"capability": "desktop:control", "duration_minutes": 15, "reason": "test"},
    )
    assert r.status_code == 200, r.text
    grant = r.json()
    assert grant["capability"] == "desktop:control"
    assert grant.get("active") is True

    from app.services.mentrix.permission_broker import check_tool_permission

    uid = grant.get("subject_id")
    try:
        uid_int = int(uid) if uid else None
    except ValueError:
        uid_int = None
    res = check_tool_permission(
        db,
        "desktop_write_note",
        user_id=uid_int,
        user_confirmed=False,
    )
    assert res["result"] == "granted"
    assert res.get("needs_confirm") is False


def test_permission_broker_always_confirm_without_grant(db: Session):
    from app.services.mentrix.permission_broker import check_tool_permission

    res = check_tool_permission(
        db,
        "desktop_write_note",
        user_id=None,
        user_confirmed=False,
    )
    assert res.get("needs_confirm") is True or res["result"] == "pending_approval"


def test_tts_word_boundary_chunk_helper():
    text = "Hello beautiful world and more words here to wrap safely"
    max_len = 20
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        window = remaining[:max_len]
        sp = window.rfind(" ")
        cut = sp if sp > max_len // 3 else max_len
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")


def test_schedule_daily_brief_dispatch(db: Session):
    from app.domains.personal_agent.schedule_executor import _dispatch
    from app.models import Schedule

    sched = Schedule(
        name="brief-test",
        task_type="daily_brief",
        schedule_type="once",
        is_active=True,
        task_config={},
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    summary = _dispatch(db, sched)
    assert "DailyBrief" in summary or "actions=" in summary

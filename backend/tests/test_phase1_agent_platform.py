"""Phase 1 — MockCodingRuntime + Mentrix event sequence / retry / stream helpers."""

from __future__ import annotations

import json

from app.adapters.coding_runtime import MockCodingRuntime, get_coding_runtime


def test_mock_coding_runtime_lifecycle():
    rt = get_coding_runtime()
    assert isinstance(rt, MockCodingRuntime)
    run_id = rt.start_run("build hello", workspace="/tmp/ws")
    data = rt.get_run(run_id)
    assert data["status"] == "completed"
    assert data["events"][0]["sequence_id"] == 1
    more = rt.stream_events(run_id, after=1)
    assert all(e.sequence_id > 1 for e in more)
    arts = rt.get_artifacts(run_id)
    assert arts and arts[0].path == "mock_output.txt"
    rt.cancel_run(run_id)
    assert rt.get_run(run_id)["status"] == "cancelled"
    rt.dispose_workspace(run_id)


def test_mentrix_events_have_sequence_id(client, auth_headers, monkeypatch):
    monkeypatch.setenv("LATTICE_ENABLED", "false")
    start = client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={"goal": "seq fixture", "mode": "chat", "project_key": "seq"},
    )
    assert start.status_code == 200, start.text
    body = start.json()
    assert "event_cursor" in body
    assert isinstance(body.get("artifacts"), list)
    assert isinstance(body.get("terminal"), list)
    assert isinstance(body.get("test_results"), dict)


def test_mentrix_retry_and_audit(client, auth_headers, monkeypatch):
    monkeypatch.setenv("LATTICE_ENABLED", "false")
    start = client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={
            "goal": "Retry fixture",
            "mode": "upgrade",
            "project_key": "retry-fixture",
            "workspace": ".",
        },
    )
    assert start.status_code == 200, start.text
    run_id = start.json()["id"]
    # Force terminal retryable status
    from app.infrastructure.database import SessionLocal
    from app.models import MentrixRun

    db = SessionLocal()
    try:
        row = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
        row.status = "failed"
        db.commit()
    finally:
        db.close()

    retried = client.post(f"/api/mentrix/runs/{run_id}/retry", headers=auth_headers)
    assert retried.status_code == 200, retried.text
    new_body = retried.json()
    assert new_body["id"] != run_id
    assert new_body["status"] == "running"
    assert any(e.get("event") == "retry" for e in new_body.get("events") or [])

    audits = client.get("/api/audit?action=mentrix_run_retry&limit=5", headers=auth_headers)
    assert audits.status_code == 200
    assert any(a.get("action") == "mentrix_run_retry" for a in audits.json())


def test_mentrix_event_stream_reconnect(client, auth_headers, monkeypatch):
    monkeypatch.setenv("LATTICE_ENABLED", "false")
    start = client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={"goal": "stream fixture", "mode": "chat"},
    )
    assert start.status_code == 200
    run_id = start.json()["id"]
    # Seed two sequenced events
    from app.infrastructure.database import SessionLocal
    from app.models import MentrixRun

    db = SessionLocal()
    try:
        row = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
        row.status = "completed"
        row.events_json = json.dumps(
            [
                {"sequence_id": 1, "event": "a", "message": "one"},
                {"sequence_id": 2, "event": "b", "message": "two"},
            ]
        )
        db.commit()
    finally:
        db.close()

    with client.stream(
        "GET",
        f"/api/mentrix/runs/{run_id}/events/stream?after=1",
        headers=auth_headers,
    ) as resp:
        assert resp.status_code == 200
        text = "".join(resp.iter_text())
    assert "mentrix_event" in text
    assert '"sequence_id": 2' in text or '"sequence_id":2' in text
    assert "event: done" in text or "event: status" in text

"""Phase 10 Stage B — typed memory, skill gates, watches, due schedules."""

from datetime import datetime, timezone, timedelta

from app.security.redact import contains_raw_secret
from app.domains.personal_agent.schedule_executor import list_due_schedules
from types import SimpleNamespace


def test_contains_raw_secret_detects_token():
    assert contains_raw_secret("api_key=sk-abcdefghijklmnopqrstuvwxyz12")
    assert not contains_raw_secret("plain memory note")


def test_memory_types_and_typed_crud_blocks_secrets(authed_client):
    types = authed_client.get("/api/memory/types")
    assert types.status_code == 200
    assert "project_knowledge" in types.json()["types"]

    bad = authed_client.post(
        "/api/memory/typed",
        json={
            "memory_type": "project_knowledge",
            "title": "bad",
            "content": "token sk-abcdefghijklmnopqrstuvwxyz12",
            "source": "test",
        },
    )
    assert bad.status_code == 400

    ok = authed_client.post(
        "/api/memory/typed",
        json={
            "memory_type": "project_knowledge",
            "title": "arch note",
            "content": "Prefer adapters over vendor UI",
            "source": "test",
            "attribution": "phase10",
            "retention_days": 30,
        },
    )
    assert ok.status_code == 200
    rid = ok.json()["id"]
    exported = authed_client.get("/api/memory/typed/export")
    assert exported.status_code == 200
    assert exported.json()["count"] >= 1
    deleted = authed_client.delete(f"/api/memory/typed/{rid}")
    assert deleted.status_code == 200


def test_skill_execute_requires_approval(authed_client):
    skills = authed_client.get("/api/skills-engine/skills")
    assert skills.status_code == 200
    items = skills.json()
    assert items
    sid = items[0]["id"]
    denied = authed_client.post(
        f"/api/skills-engine/execute/{sid}",
        json={"skill_id": sid, "approved": False, "success": True},
    )
    assert denied.status_code == 403
    allowed = authed_client.post(
        f"/api/skills-engine/execute/{sid}",
        json={"skill_id": sid, "approved": True, "success": True, "duration_seconds": 0.1},
    )
    assert allowed.status_code == 200
    assert allowed.json()["output_data"]["_gate"]["script_executed"] is False


def test_automation_watch_keyword_evaluate(authed_client):
    created = authed_client.post(
        "/api/automation-watches",
        json={
            "name": "error-watch",
            "condition_type": "keyword",
            "condition_config": {"keywords": ["P0"]},
            "action_type": "mentrix",
            "max_attempts": 2,
        },
    )
    assert created.status_code == 200
    wid = created.json()["id"]
    miss = authed_client.post(f"/api/automation-watches/{wid}/evaluate", json={"text": "all good"})
    assert miss.json()["matched"] is False
    hit = authed_client.post(f"/api/automation-watches/{wid}/evaluate", json={"text": "P0 outage"})
    assert hit.json()["matched"] is True


def test_list_due_schedules_helper_filters():
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    future = datetime.now(timezone.utc) + timedelta(hours=1)

    class FakeQuery:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *_a, **_k):
            return self

        def all(self):
            return self._rows

    class FakeDB:
        def __init__(self, rows):
            self._rows = rows

        def query(self, *_a):
            return FakeQuery(self._rows)

    due_row = SimpleNamespace(
        id=1,
        is_active=True,
        max_attempts=3,
        retry_count=0,
        next_run_at=past,
        schedule_type="cron",
        interval_minutes=None,
        scheduled_time=None,
        last_run_at=None,
    )
    skip_row = SimpleNamespace(
        id=2,
        is_active=True,
        max_attempts=3,
        retry_count=0,
        next_run_at=future,
        schedule_type="cron",
        interval_minutes=None,
        scheduled_time=None,
        last_run_at=None,
    )
    due = list_due_schedules(FakeDB([due_row, skip_row]))
    assert [s.id for s in due] == [1]


def test_schedules_due_run_endpoint(authed_client):
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    created = authed_client.post(
        "/api/schedules",
        json={
            "name": "due-test",
            "schedule_type": "interval",
            "interval_minutes": 1,
            "task_type": "custom",
            "task_config": {"goal": "ping"},
            "max_attempts": 2,
        },
    )
    assert created.status_code == 200
    sid = created.json()["id"]
    authed_client.put(f"/api/schedules/{sid}", json={"next_run_at": past, "is_active": True})
    due = authed_client.post("/api/schedules/due/run")
    assert due.status_code == 200, due.text
    assert "ran" in due.json()

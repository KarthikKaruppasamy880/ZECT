"""Phases 6–11 Stage A smoke tests."""

from app.services.mentrix.outbound_drafts import serialize_draft
from app.domains.personal_agent.schedule_executor import _idempotency_key
from app.models import Schedule
from types import SimpleNamespace


def test_idempotency_key_stable_within_minute():
    sched = SimpleNamespace(id=7, task_type="review")
    a = _idempotency_key(sched, "manual")
    b = _idempotency_key(sched, "manual")
    assert a == b
    assert len(a) == 32


def test_serialize_draft_shape():
    d = SimpleNamespace(
        id=1,
        channel="email",
        status="draft",
        payload_json={"to": "a@b.c"},
        provider_message_id="",
        created_at=None,
        sent_at=None,
    )
    out = serialize_draft(d)
    assert out["id"] == 1
    assert out["channel"] == "email"
    assert out["payload"]["to"] == "a@b.c"

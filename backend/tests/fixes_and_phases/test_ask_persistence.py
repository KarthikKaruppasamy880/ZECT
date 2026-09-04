"""Ask persistence (V2 closure §5).

Previously every Ask call created a brand new WorkItem (developer_service.py's
_ensure_work_item() only reuses one if work_item_id is passed and truthy) and
only wrote a truncated 500-char audit event with no way to replay a prior
answer. These tests prove: (1) reusing the same work_item_id keeps multiple
Ask turns on one WorkItem, and (2) ask_history() replays them in order with
the full, untruncated question/answer -- what AskPane fetches on mount to
restore the conversation across navigation/refresh/backend restart."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.orm import Session

from app.domains.work_items.events import append_event
from app.infrastructure.database import SessionLocal
from app.models import Project, Repo, WorkItemEvent
from app.services.work_items.developer_service import MentrixDeveloperService


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_project_with_repo(db: Session) -> tuple[Project, Repo]:
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"ask-persist-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main")
    db.add(r)
    db.commit()
    db.refresh(p)
    db.refresh(r)
    return p, r


def test_second_ask_reuses_the_same_work_item_when_id_is_passed(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r = _seed_project_with_repo(db)
    svc = MentrixDeveloperService(db)

    first = svc.ask(question="What does this repo do?", project_id=p.id, repository_id=r.id)
    wi_id = first["work_item_id"]

    second = svc.ask(question="Where is the entrypoint?", work_item_id=wi_id, project_id=p.id, repository_id=r.id)

    assert second["work_item_id"] == wi_id, "passing the prior work_item_id must not spawn a new WorkItem"


def test_ask_history_replays_full_turns_in_order(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r = _seed_project_with_repo(db)
    svc = MentrixDeveloperService(db)

    long_question = "Why " + ("x" * 600) + "?"  # longer than the truncated "ask" audit event's 500 chars
    first = svc.ask(question=long_question, project_id=p.id, repository_id=r.id)
    wi_id = first["work_item_id"]
    svc.ask(question="follow-up question", work_item_id=wi_id, project_id=p.id, repository_id=r.id)

    turns = svc.ask_history(wi_id)
    assert len(turns) == 2, "both turns must be recorded against the same work item, in order"
    assert turns[0]["question"] == long_question, "the full question must survive, not the 500-char audit truncation"
    assert turns[0]["answer"], "each turn must carry its own answer"
    assert turns[1]["question"] == "follow-up question"

    other_wi = svc.ask(question="unrelated", project_id=p.id, repository_id=r.id)["work_item_id"]
    assert other_wi != wi_id
    assert svc.ask_history(other_wi) != turns, "a different work item must not see another's history"


def test_ask_history_empty_for_unused_work_item(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    p, _r = _seed_project_with_repo(db)
    svc = MentrixDeveloperService(db)
    assert svc.ask_history(999_999_999) == []


_CONTEXT_USED_KEYS = {"knowledge", "lattice_hits", "lattice_indexed", "lattice_state", "blueprint", "skill"}


def test_ask_turn_persists_context_used_summary_matching_the_response(db: Session, tmp_path, monkeypatch):
    """The gap this closes: ask()'s HTTP response already carries
    project_intelligence, but nothing durable summarized it, so the
    Context Used strip went blank on reload. The persisted ask_turn event
    must carry the SAME compact summary contextFromDeveloperPi() derives
    from a live response, not a second, independently-computed shape."""
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r = _seed_project_with_repo(db)
    svc = MentrixDeveloperService(db)

    res = svc.ask(question="What does this repo do?", project_id=p.id, repository_id=r.id)
    wi_id = res["work_item_id"]

    row = (
        db.query(WorkItemEvent)
        .filter(WorkItemEvent.work_item_id == wi_id, WorkItemEvent.event_type == "ask_turn")
        .order_by(WorkItemEvent.id.desc())
        .first()
    )
    assert row is not None
    payload = json.loads(row.payload_json)
    context_used = payload.get("context_used")
    assert isinstance(context_used, dict)
    assert set(context_used) == _CONTEXT_USED_KEYS

    from app.services.coding_engine.skill_router import ROLE_ASK, select_skill_with_db
    from app.services.work_items.developer_service import _context_used_summary

    # CP-09B: ask() selects a skill deterministically (no LLM call), so the
    # same selection is reproducible here for comparison rather than
    # threading the live SkillSelection object out of ask()'s response.
    skill = select_skill_with_db(db, ROLE_ASK, project_id=p.id)
    assert context_used == _context_used_summary(res.get("project_intelligence"), skill=skill), (
        "the persisted summary must match what this same call actually computed"
    )


def test_ask_history_returns_context_used_on_replay(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r = _seed_project_with_repo(db)
    svc = MentrixDeveloperService(db)

    res = svc.ask(question="What does this repo do?", project_id=p.id, repository_id=r.id)
    wi_id = res["work_item_id"]

    turns = svc.ask_history(wi_id)
    assert len(turns) == 1
    assert "context_used" in turns[0]
    assert set(turns[0]["context_used"]) == _CONTEXT_USED_KEYS


def test_ask_history_tolerates_old_style_event_without_context_used(db: Session, tmp_path, monkeypatch):
    """Additive change: rows persisted before context_used existed have no
    such key. ask_history() must not crash and must simply omit the field
    for that turn rather than backfilling a fake summary."""
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    p, r = _seed_project_with_repo(db)
    svc = MentrixDeveloperService(db)
    from app.domains.work_items import service as wi_svc

    wi = wi_svc.create_work_item(
        db,
        title="legacy ask",
        description="legacy",
        project_id=p.id,
        repository_id=r.id,
    )
    append_event(
        db,
        work_item_id=wi.id,
        event_type="ask_turn",
        payload={
            "question": "old question",
            "answer": "old answer",
            "model": "gpt-x",
            "offline": False,
            "image_count": 0,
        },
        commit=True,
    )

    turns = svc.ask_history(wi.id)
    assert len(turns) == 1
    assert turns[0]["question"] == "old question"
    assert "context_used" not in turns[0], "an old-style row must not fabricate a context_used summary"

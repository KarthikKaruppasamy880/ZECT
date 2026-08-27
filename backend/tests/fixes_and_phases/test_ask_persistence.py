"""Ask persistence (V2 closure §5).

Previously every Ask call created a brand new WorkItem (developer_service.py's
_ensure_work_item() only reuses one if work_item_id is passed and truthy) and
only wrote a truncated 500-char audit event with no way to replay a prior
answer. These tests prove: (1) reusing the same work_item_id keeps multiple
Ask turns on one WorkItem, and (2) ask_history() replays them in order with
the full, untruncated question/answer -- what AskPane fetches on mount to
restore the conversation across navigation/refresh/backend restart."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
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

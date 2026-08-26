"""Learning Studio content must always be traceable to a real source_ref —
a Lattice node or a Knowledge Base entry. Nothing renders without one."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.domains.personal_agent.learning_studio import generate_quiz, get_catalog, get_lesson
from app.infrastructure.auth.deps import CurrentUser
from app.infrastructure.database import Base
from app.models import KnowledgeEntry

USER = CurrentUser(user_id=1, username="a", email="a@b.c", auth_mode="local", token="t", role="admin")
READY = {"state": "READY", "indexed": True, "project_key": "demo"}

LATTICE_NODE = {
    "id": "mod:app/foo.py",
    "kind": "module",
    "name": "foo",
    "path": "app/foo.py",
    "title": "",
    "slug": "",
    "group": "",
}


def _db_with_knowledge_entry() -> tuple:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    entry = KnowledgeEntry(title="Deploy runbook", content="Run scripts/deploy.sh from main.", is_active=True)
    db.add(entry)
    db.commit()
    return db, entry


class TestGrounding:
    @patch("app.domains.personal_agent.learning_studio.query_graph", return_value=[LATTICE_NODE])
    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=READY)
    def test_catalog_topics_all_carry_source_refs(self, _status, _query):
        db, entry = _db_with_knowledge_entry()
        result = get_catalog(project_key="demo", db=db, current_user=USER)
        assert len(result["topics"]) == 2  # one lattice node + one knowledge entry
        for topic in result["topics"]:
            assert topic["source_refs"], f"topic {topic['topic_id']} has no source_ref"

    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=READY)
    def test_knowledge_lesson_cites_the_real_entry(self, _status):
        db, entry = _db_with_knowledge_entry()
        lesson = get_lesson(f"knowledge:{entry.id}", project_key="demo", db=db, current_user=USER)
        assert lesson["body"] == entry.content
        assert lesson["source_refs"][0]["id"] == str(entry.id)

    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=READY)
    def test_unknown_knowledge_topic_404s_not_fabricated(self, _status):
        db, _entry = _db_with_knowledge_entry()
        with pytest.raises(HTTPException) as exc:
            get_lesson("knowledge:99999", project_key="demo", db=db, current_user=USER)
        assert exc.value.status_code == 404

    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=READY)
    def test_quiz_questions_all_cite_the_lesson_source_ref(self, _status):
        db, entry = _db_with_knowledge_entry()
        result = generate_quiz(f"knowledge:{entry.id}", project_key="demo", db=db, current_user=USER)
        assert result["questions"]
        for q in result["questions"]:
            assert q["source_ref"]["id"] == str(entry.id)

    @patch("app.domains.personal_agent.learning_studio.explain", return_value={"summary": "", "neighbors": {}})
    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=READY)
    def test_quiz_rejects_empty_lesson_content(self, _status, _explain):
        db = sessionmaker(bind=create_engine("sqlite:///:memory:"))()
        Base.metadata.create_all(bind=db.get_bind())
        with pytest.raises(HTTPException) as exc:
            generate_quiz("lattice:mod:app/foo.py", project_key="demo", db=db, current_user=USER)
        assert exc.value.status_code == 422

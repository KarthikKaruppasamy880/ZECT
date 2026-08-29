"""Learning Studio must never invent a syllabus when the Lattice index isn't
READY — catalog degrades to empty + status; lesson/quiz hard-block with 409.
Mirrors the plan's bullet: 'show re-index — do not invent a syllabus.'"""

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

USER = CurrentUser(user_id=1, username="a", email="a@b.c", auth_mode="local", token="t", role="admin")


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


NOT_READY = {"state": "NOT_INDEXED", "indexed": False, "project_key": "demo"}
READY = {"state": "READY", "indexed": True, "project_key": "demo"}


class TestStatusGate:
    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=NOT_READY)
    def test_catalog_returns_empty_topics_when_not_ready(self, _mock):
        result = get_catalog(project_key="demo", db=_db(), current_user=USER)
        assert result["status"] == NOT_READY
        assert result["topics"] == []

    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=NOT_READY)
    def test_lesson_blocks_with_409_when_not_ready(self, _mock):
        with pytest.raises(HTTPException) as exc:
            get_lesson("lattice:x", project_key="demo", db=_db(), current_user=USER)
        assert exc.value.status_code == 409
        assert exc.value.detail["reason"] == "not_ready"

    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=NOT_READY)
    def test_quiz_blocks_with_409_when_not_ready(self, _mock):
        with pytest.raises(HTTPException) as exc:
            generate_quiz("lattice:x", project_key="demo", db=_db(), current_user=USER)
        assert exc.value.status_code == 409

    @patch("app.domains.personal_agent.learning_studio.query_graph", return_value=[])
    @patch("app.domains.personal_agent.learning_studio.get_lattice_status", return_value=READY)
    def test_catalog_proceeds_when_ready(self, _status, _query):
        result = get_catalog(project_key="demo", db=_db(), current_user=USER)
        assert result["status"] == READY
        assert result["topics"] == []  # no lattice nodes, no knowledge entries seeded

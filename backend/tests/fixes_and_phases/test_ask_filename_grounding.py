"""ASK must ground itself in a file the user names, not just grep for
vocabulary overlap.

_workspace_file_items() previously only matched query tokens against LINE
CONTENT. Asking "what does calc.py do?" against a file whose code never
literally contains the word "calc" (a trivially small, realistic case) found
nothing -- ASK had zero file content to reason from and could only ask
generic clarifying questions, indistinguishable from being fully offline.
This is the gap behind the "why doesn't ASK work like Cursor" report: Cursor
doesn't require semantic-index hits before it can read a file you named.

Fix: detect filename-shaped tokens in the query (e.g. "calc.py") and, when
one matches a real file under an authorized repo root, include that file's
full content directly -- ahead of and independent from the line-grep
fallback, which still covers everything else (symbol/keyword mentions with
no literal filename)."""

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


def _seed_repo(db: Session, local_path: str) -> Repo:
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"ask-grounding-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main", local_path=local_path)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


class TestFilenameGrounding:
    def test_includes_full_content_of_a_named_file_with_no_vocabulary_overlap(self, db, tmp_path):
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        repo = _seed_repo(db, str(tmp_path))
        svc = MentrixDeveloperService(db)

        items = svc._workspace_file_items(repository_ids=[repo.id], query="What does calc.py do?")

        assert any(i.source_id == "calc.py" and "def add" in i.content for i in items)

    def test_still_falls_back_to_line_grep_when_no_filename_is_named(self, db, tmp_path):
        (tmp_path / "service.py").write_text("class BudgetValidator:\n    pass\n", encoding="utf-8")
        repo = _seed_repo(db, str(tmp_path))
        svc = MentrixDeveloperService(db)

        items = svc._workspace_file_items(repository_ids=[repo.id], query="Where is BudgetValidator defined?")

        assert any("BudgetValidator" in i.content for i in items)

    def test_returns_nothing_for_a_filename_that_does_not_exist(self, db, tmp_path):
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        repo = _seed_repo(db, str(tmp_path))
        svc = MentrixDeveloperService(db)

        items = svc._workspace_file_items(repository_ids=[repo.id], query="What does missing.py do?")

        assert items == []

    def test_filename_match_takes_priority_and_does_not_crowd_out_line_hits(self, db, tmp_path):
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        (tmp_path / "other.py").write_text("# calc.py is used by the budget module\n", encoding="utf-8")
        repo = _seed_repo(db, str(tmp_path))
        svc = MentrixDeveloperService(db)

        items = svc._workspace_file_items(repository_ids=[repo.id], query="What does calc.py do?")

        full = [i for i in items if i.source_id == "calc.py"]
        assert len(full) == 1
        assert "def add" in full[0].content

    def test_large_file_is_truncated_not_dropped(self, db, tmp_path):
        big = "x = 1\n" * 5000
        (tmp_path / "big.py").write_text(big, encoding="utf-8")
        repo = _seed_repo(db, str(tmp_path))
        svc = MentrixDeveloperService(db)

        items = svc._workspace_file_items(repository_ids=[repo.id], query="What does big.py do?")

        match = next(i for i in items if i.source_id == "big.py")
        assert len(match.content) <= 8100

    def test_no_repository_ids_returns_nothing(self, db, tmp_path):
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        svc = MentrixDeveloperService(db)

        assert svc._workspace_file_items(repository_ids=[], query="What does calc.py do?") == []

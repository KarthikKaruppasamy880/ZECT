"""CP-02 -- ASK must be evidence-grounded and must not invent files, classes,
APIs, DB objects or symbols (finding A1).

The CMS benchmark proved ASK will confidently name specific, plausible
classes/APIs (CampaignWizard, ApprovalService, POST /campaigns/initiate) that
do not exist in the target repository when the real retrieved context is
weak. The system prompt alone (llm_phase.run_ask) cannot be trusted to stop
this -- the same lesson Roo Code's mode-tool enforcement teaches: a
model-obedience-only guard is not a real guard. This is the second,
deterministic layer: MentrixDeveloperService._check_answer_grounding() scans
the model's own answer for class/file/route-shaped names and checks each one
against what was actually retrieved, independent of whether the model
followed instructions.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

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
    p = Project(name=f"cp02-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main", local_path=local_path)
    db.add(r)
    db.commit()
    db.refresh(p)
    db.refresh(r)
    return p, r


class TestCheckAnswerGrounding:
    def test_real_filename_present_in_context_is_verified(self, db: Session):
        svc = MentrixDeveloperService(db)
        pack = SimpleNamespace(items=[SimpleNamespace(content="calc.py:\ndef add(a, b):\n    return a - b\n")])
        result = svc._check_answer_grounding("The bug is in calc.py's add() function.", pack)
        assert "calc.py" in result["verified"]
        assert result["unverified"] == []

    def test_fake_class_name_not_in_context_is_unverified(self, db: Session):
        svc = MentrixDeveloperService(db)
        pack = SimpleNamespace(items=[SimpleNamespace(content="com/planetsoft/drs/complaint/action/InboxAction.java")])
        result = svc._check_answer_grounding(
            "This is handled by CampaignWizard and the ApprovalService class.", pack
        )
        assert "CampaignWizard" in result["unverified"]
        assert "ApprovalService" in result["unverified"]
        assert result["verified"] == []

    def test_fake_api_route_not_in_context_is_unverified(self, db: Session):
        svc = MentrixDeveloperService(db)
        pack = SimpleNamespace(items=[])
        result = svc._check_answer_grounding("Submit via POST /campaigns/initiate.", pack)
        assert "POST /campaigns/initiate" in result["unverified"]

    def test_real_api_route_present_in_context_is_verified(self, db: Session):
        svc = MentrixDeveloperService(db)
        pack = SimpleNamespace(items=[SimpleNamespace(content="router.add_route('POST /campaigns/initiate', ...)")])
        result = svc._check_answer_grounding("Submit via POST /campaigns/initiate.", pack)
        assert "POST /campaigns/initiate" in result["verified"]
        assert result["unverified"] == []

    def test_answer_with_no_named_entities_is_clean(self, db: Session):
        svc = MentrixDeveloperService(db)
        pack = SimpleNamespace(items=[])
        result = svc._check_answer_grounding("I could not determine an answer from the available context.", pack)
        assert result == {"verified": [], "unverified": [], "checked": True}

    def test_empty_context_makes_every_named_entity_unverified(self, db: Session):
        svc = MentrixDeveloperService(db)
        pack = SimpleNamespace(items=[])
        result = svc._check_answer_grounding("See BudgetValidator for the rule.", pack)
        assert result["unverified"] == ["BudgetValidator"]

    def test_plain_capitalized_prose_is_not_flagged_as_a_class(self, db: Session):
        """Single-hump capitalization (a sentence-initial word, an acronym
        like API/JSON) must not false-positive as a class name -- only
        genuine multi-hump CamelCase should."""
        svc = MentrixDeveloperService(db)
        pack = SimpleNamespace(items=[])
        result = svc._check_answer_grounding("React uses a JSON API for this.", pack)
        assert result["unverified"] == []
        assert result["verified"] == []

    def test_no_pack_object_does_not_crash(self, db: Session):
        svc = MentrixDeveloperService(db)
        result = svc._check_answer_grounding("See CampaignWizard.", None)
        assert result["unverified"] == ["CampaignWizard"]


class TestAskPrependsUnverifiedWarning:
    def test_hallucinated_class_name_gets_a_warning_banner(self, db: Session, monkeypatch, tmp_path):
        """The exact CMS-benchmark shape: the model names a specific,
        plausible-sounding class that does not exist anywhere in the
        (tiny, real) target repo. ASK must flag it, not repeat it silently."""
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "unrelated.py").write_text("x = 1\n", encoding="utf-8")

        def fake_run_ask(question, **kwargs):
            return {"answer": "This is implemented by CampaignWizard.java.", "model": "test", "offline": False}

        monkeypatch.setattr("app.services.phases.llm_phase.run_ask", fake_run_ask)
        svc = MentrixDeveloperService(db)
        result = svc.ask(question="How is campaign creation implemented?", project_id=p.id, repository_id=repo.id)

        assert "Unverified references" in result["answer"]
        assert "CampaignWizard.java" in result["answer"]
        assert "CampaignWizard.java" in result["grounding"]["unverified"]

    def test_grounded_answer_naming_a_real_file_gets_no_warning(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

        def fake_run_ask(question, **kwargs):
            return {"answer": "The bug is in calc.py.", "model": "test", "offline": False}

        monkeypatch.setattr("app.services.phases.llm_phase.run_ask", fake_run_ask)
        svc = MentrixDeveloperService(db)
        result = svc.ask(question="What does calc.py do?", project_id=p.id, repository_id=repo.id)

        assert "Unverified references" not in result["answer"]
        assert result["grounding"]["unverified"] == []

    def test_ask_history_replays_the_warning_banner_baked_into_the_answer(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))

        def fake_run_ask(question, **kwargs):
            return {"answer": "See ApprovalService for the rule.", "model": "test", "offline": False}

        monkeypatch.setattr("app.services.phases.llm_phase.run_ask", fake_run_ask)
        svc = MentrixDeveloperService(db)
        result = svc.ask(question="How are approvals routed?", project_id=p.id, repository_id=repo.id)

        history = svc.ask_history(result["work_item_id"])
        assert "Unverified references" in history[-1]["answer"]
        assert "ApprovalService" in history[-1]["grounding"]["unverified"]

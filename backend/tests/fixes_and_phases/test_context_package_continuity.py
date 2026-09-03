"""CP-04 -- the canonical ASK -> PLAN structured context package.

Regression coverage for finding F1 (three independent, hand-duplicated
context builders) and the CMS-benchmark hallucination chain: ASK's answer
named CampaignManagement.java / POST /campaigns/initiate with no real
evidence, and nothing stopped PLAN from later treating those same invented
names as if they were real, existing files to modify -- because PLAN never
received ASK's grounding as anything other than prose (including CP-02's
own warning banner) baked into the `goal` string. This suite proves the
structured Evidence Ledger now travels WorkItem -> WorkItem, not
turn -> turn-as-a-string, and that PLAN actually reads it.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.work_items import context_package as cp_module
from app.services.work_items.developer_service import MentrixDeveloperService


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_repo(db: Session, local_path: str) -> tuple[Project, Repo]:
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"cp04-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r = Repo(project_id=p.id, owner="acme", repo_name="cms-sbigeneral", default_branch="main", local_path=local_path)
    db.add(r)
    db.commit()
    db.refresh(p)
    db.refresh(r)
    return p, r


def _mock_ask(monkeypatch, answer: str) -> None:
    monkeypatch.setattr("app.services.phases.llm_phase.run_ask", lambda *a, **kw: {"answer": answer, "model": "test", "offline": False})


def _mock_plan(monkeypatch, narrative: str, *, proposed_file_impacts: list | None = None) -> None:
    monkeypatch.setattr(
        "app.services.phases.llm_phase.run_grounded_plan",
        lambda *a, **kw: {
            "narrative": narrative,
            "proposed_file_impacts": proposed_file_impacts or [],
            "model": "test",
            "offline": False,
        },
    )


class TestContextPackagePersistence:
    def test_ask_persists_a_round_trippable_context_package(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        _mock_ask(monkeypatch, "The bug is in calc.py.")
        svc = MentrixDeveloperService(db)

        result = svc.ask(question="What does calc.py do?", project_id=p.id, repository_id=repo.id)
        wi_id = result["work_item_id"]

        from app.domains.work_items import service as wi_svc

        wi = wi_svc.get_work_item(db, wi_id)
        pkg = cp_module.ContextPackage.from_dict(__import__("json").loads(wi.context_snapshot_json))
        assert pkg.primary_repo_id == repo.id
        assert pkg.requirement == "What does calc.py do?"
        assert any(e.entity == "calc.py" and e.status == cp_module.STATUS_VERIFIED for e in pkg.evidence_ledger)

    def test_context_package_never_stores_the_full_original_answer_unbounded(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        huge_answer = "See calc.py. " + ("padding text " * 2000)  # far larger than the summary cap
        _mock_ask(monkeypatch, huge_answer)
        svc = MentrixDeveloperService(db)

        result = svc.ask(question="Explain", project_id=p.id, repository_id=repo.id)
        pkg_dict = result["context_package"]
        assert len(pkg_dict["ask_findings_summary"]) < len(huge_answer)
        assert len(pkg_dict["ask_findings_summary"]) <= cp_module._ASK_FINDINGS_SUMMARY_CHARS + 200  # + warning banner


class TestAskToPlanDeterministicContinuity:
    def test_plan_inherits_same_repo_requirement_and_evidence_ask_produced(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        _mock_ask(monkeypatch, "The bug is in calc.py.")
        svc = MentrixDeveloperService(db)

        ask_result = svc.ask(question="What does calc.py do?", project_id=p.id, repository_id=repo.id)
        wi_id = ask_result["work_item_id"]
        ask_pkg = ask_result["context_package"]

        _mock_plan(monkeypatch, "## Architecture\nFix calc.py's add() function.")
        plan_result = svc.plan(goal="Fix the bug", work_item_id=wi_id)
        plan_pkg = plan_result["context_package"]

        assert plan_pkg is not None
        assert plan_pkg["primary_repo_id"] == ask_pkg["primary_repo_id"] == repo.id
        assert plan_pkg["requirement"] == ask_pkg["requirement"]
        assert plan_pkg["evidence_ledger"] == ask_pkg["evidence_ledger"]
        assert plan_pkg["scope_decisions"] == ask_pkg["scope_decisions"]

    def test_plan_run_twice_produces_the_same_inherited_evidence(self, db: Session, monkeypatch, tmp_path):
        """Re-running Create Plan (e.g. Revise) on the same WorkItem must
        keep resolving to the identical inherited evidence, not drift."""
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        _mock_ask(monkeypatch, "The bug is in calc.py.")
        svc = MentrixDeveloperService(db)
        wi_id = svc.ask(question="What does calc.py do?", project_id=p.id, repository_id=repo.id)["work_item_id"]

        _mock_plan(monkeypatch, "## Architecture\nFirst draft.")
        first = svc.plan(goal="Fix the bug", work_item_id=wi_id)["context_package"]
        _mock_plan(monkeypatch, "## Architecture\nRevised draft.")
        second = svc.plan(goal="Fix the bug, revised", work_item_id=wi_id)["context_package"]

        assert first["evidence_ledger"] == second["evidence_ledger"]
        assert first["primary_repo_id"] == second["primary_repo_id"]
        assert first["attachments"] == second["attachments"]

    def test_attachments_persisted_by_ask_are_visible_to_plan(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        _mock_ask(monkeypatch, "Reviewing the attached requirement.")
        svc = MentrixDeveloperService(db)
        wi_id = svc.ask(question="Analyze the attached BRD", project_id=p.id, repository_id=repo.id)["work_item_id"]

        from app.services.document_intelligence.service import ingest_document, link_artifact_to_work_item

        art = ingest_document(db, user_id=1, filename="brd.md", data=b"# BRD\n\nCampaign requirement.", scope="USER_PRIVATE")
        link_artifact_to_work_item(db, artifact_id=art["id"], user_id=1, work_item_id=wi_id)

        # A second Ask turn is what actually re-snapshots attachments today
        # (the package is written at the end of ask(), not on link alone).
        _mock_ask(monkeypatch, "Reviewing the attached requirement, again.")
        result = svc.ask(question="Analyze the attached BRD", work_item_id=wi_id, project_id=p.id, repository_id=repo.id)

        _mock_plan(monkeypatch, "## Architecture\nDraft.")
        plan_pkg = svc.plan(goal="Build it", work_item_id=wi_id)["context_package"]
        assert any(a["id"] == art["id"] for a in plan_pkg["attachments"])
        assert any(a["id"] == art["id"] for a in result["context_package"]["attachments"])


class TestCmsHallucinationRegression:
    """The exact CMS-benchmark shape: ASK, with real grounding, cannot find
    Campaign Management code in the repo and correctly marks the model's
    invented names NOT_FOUND. PLAN must not silently treat them as existing
    modify-targets afterward."""

    def test_not_found_entities_flagged_when_plan_treats_them_as_existing(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "InboxAction.java").write_text("class InboxAction {}\n", encoding="utf-8")
        _mock_ask(
            monkeypatch,
            "This is implemented by CampaignManagement.java, submitted via POST /campaigns/initiate.",
        )
        svc = MentrixDeveloperService(db)
        ask_result = svc.ask(
            question="Analyze the attached Campaign Management requirement against this repository.",
            project_id=p.id,
            repository_id=repo.id,
        )
        ledger = ask_result["context_package"]["evidence_ledger"]
        not_found = {e["entity"] for e in ledger if e["status"] == cp_module.STATUS_NOT_FOUND}
        assert "CampaignManagement.java" in not_found
        assert "POST /campaigns/initiate" in not_found

        # The model's own prose narrative treats the NOT_FOUND entities as
        # if they already exist -- no structured CREATE_NEW proposal at
        # all. This is the free-text safety net (_check_plan_against_not_found)
        # over and above the structured file-impact validation.
        _mock_plan(
            monkeypatch,
            "## Current implementation\n1. Modify CampaignManagement.java to add the new field.\n"
            "2. Submit via POST /campaigns/initiate as before.",
        )
        plan_result = svc.plan(goal="Implement campaign creation", work_item_id=ask_result["work_item_id"])

        assert "Plan references entities ASK could not verify" in plan_result["plan"]
        assert "CampaignManagement.java" in plan_result["plan"]
        assert "POST /campaigns/initiate" in plan_result["plan"]

    def test_not_found_entity_explicitly_marked_create_new_is_not_flagged(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        _mock_ask(monkeypatch, "No existing CampaignManagement.java was found in this repository.")
        svc = MentrixDeveloperService(db)
        ask_result = svc.ask(question="Analyze the requirement", project_id=p.id, repository_id=repo.id)

        # The structured path: the model proposes CampaignManagement.java as
        # an explicit, justified CREATE_NEW file-impact -- this is what
        # legitimately promotes a NOT_FOUND entity into the plan.
        _mock_plan(
            monkeypatch,
            "## Architecture\nA new campaign creation module will be added.",
            proposed_file_impacts=[
                {
                    "path": "CampaignManagement.java",
                    "action": "CREATE_NEW",
                    "language": "java",
                    "rationale": "Does not exist yet -- new file implementing campaign CRUD.",
                    "dependencies": [],
                    "verification": "Add unit tests for campaign creation.",
                }
            ],
        )
        plan_result = svc.plan(goal="Implement campaign creation", work_item_id=ask_result["work_item_id"])

        assert "Plan references entities ASK could not verify" not in plan_result["plan"]
        assert "CampaignManagement.java" in plan_result["plan"]
        assert any(i["path"] == "CampaignManagement.java" and i["action"] == "CREATE_NEW" for i in plan_result["file_impacts"])

    def test_plan_with_no_prior_ask_has_no_context_package_and_is_not_checked(self, db: Session, monkeypatch, tmp_path):
        """A WorkItem that never went through ASK has nothing to check
        against -- plan() must not crash and must simply skip the guard."""
        p, repo = _seed_repo(db, str(tmp_path))
        _mock_plan(monkeypatch, "## Architecture\nModify CampaignManagement.java.")
        svc = MentrixDeveloperService(db)
        plan_result = svc.plan(goal="Implement campaign creation", project_id=p.id, repository_id=repo.id)
        assert plan_result["context_package"] is None
        assert "Plan references entities ASK could not verify" not in plan_result["plan"]


class TestEvidenceLedgerMerge:
    def test_verified_status_is_sticky_across_merges(self):
        existing = [
            cp_module.EvidenceLedgerEntry(entity="calc.py", entity_type="file", status=cp_module.STATUS_VERIFIED, evidence_refs=["calc.py"])
        ]
        new = [cp_module.EvidenceLedgerEntry(entity="calc.py", entity_type="file", status=cp_module.STATUS_NOT_FOUND)]
        merged = cp_module.merge_evidence_ledgers(existing, new)
        assert len(merged) == 1
        assert merged[0].status == cp_module.STATUS_VERIFIED

    def test_not_found_can_be_upgraded_to_verified(self):
        existing = [cp_module.EvidenceLedgerEntry(entity="new.py", entity_type="file", status=cp_module.STATUS_NOT_FOUND)]
        new = [
            cp_module.EvidenceLedgerEntry(entity="new.py", entity_type="file", status=cp_module.STATUS_VERIFIED, evidence_refs=["new.py"])
        ]
        merged = cp_module.merge_evidence_ledgers(existing, new)
        assert merged[0].status == cp_module.STATUS_VERIFIED

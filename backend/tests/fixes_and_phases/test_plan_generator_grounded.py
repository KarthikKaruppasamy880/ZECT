"""CP-05 -- grounded PLAN.md generator + typed file-impact schema.

Finding B1's root cause was a literal broken prompt instruction ("port
module N") and no concrete file-impact list at all. This suite proves the
replacement: file impacts are deterministically seeded from CP-04's
Evidence Ledger, validated against the real filesystem and detected repo
architecture, and rendered into every mandated PLAN.md section -- and that
the CMS benchmark's exact failure (a Python path proposed for an all-Java
repo, an existing-file claim for a NOT_FOUND entity) is now rejected before
it ever reaches a written plan.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.work_items import context_package as cp_module
from app.services.work_items import plan_generator as pg
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
    p = Project(name=f"cp05-{tag}", description="test", status="active")
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


def _mock_grounded_plan(monkeypatch, narrative: str, proposed_file_impacts: list | None = None) -> None:
    monkeypatch.setattr(
        "app.services.phases.llm_phase.run_grounded_plan",
        lambda *a, **kw: {
            "narrative": narrative,
            "proposed_file_impacts": proposed_file_impacts or [],
            "model": "test",
            "offline": False,
        },
    )


class TestDetectRepoArchitecture:
    def test_maven_marker_wins_over_extension_counting(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "Main.py").write_text("x = 1\n", encoding="utf-8")  # would mislead pure extension counting
        arch = pg.detect_repo_architecture(tmp_path)
        assert arch.primary_language == "java"
        assert arch.build_system == "maven"

    def test_falls_back_to_extension_counting_without_a_build_marker(self, tmp_path):
        for i in range(5):
            (tmp_path / f"Service{i}.java").write_text("class X {}\n", encoding="utf-8")
        (tmp_path / "notes.md").write_text("# notes\n", encoding="utf-8")
        arch = pg.detect_repo_architecture(tmp_path)
        assert arch.primary_language == "java"

    def test_empty_or_missing_repo_is_honestly_unknown(self, tmp_path):
        arch = pg.detect_repo_architecture(tmp_path / "does-not-exist")
        assert arch.primary_language == "unknown"


class TestPlaceholderDetection:
    @pytest.mark.parametrize(
        "text",
        [
            "## Phase 2: Port Module N",
            "See example/file.py for reference.",
            "Status: TBD",
            "Target: <module_name>",
            "Use {{placeholder}} here",
        ],
    )
    def test_known_placeholder_patterns_are_caught(self, text):
        assert pg.find_placeholder_violations(text)

    def test_a_real_specific_plan_has_no_placeholder_violations(self):
        text = "## Architecture\nCampaignService.java will own the new REST endpoint POST /api/campaigns."
        assert pg.find_placeholder_violations(text) == []


class TestSeedFileImpactsFromLedger:
    def test_only_verified_file_entities_are_seeded(self):
        pkg = cp_module.ContextPackage(
            work_item_id=1, primary_repo_id=1, repo_sha="abc", requirement="r", ask_findings_summary="",
            evidence_ledger=[
                cp_module.EvidenceLedgerEntry(entity="calc.py", entity_type="file", status=cp_module.STATUS_VERIFIED, evidence_refs=["calc.py"]),
                cp_module.EvidenceLedgerEntry(entity="CampaignManagement.java", entity_type="file", status=cp_module.STATUS_NOT_FOUND),
                cp_module.EvidenceLedgerEntry(entity="ApprovalService", entity_type="class", status=cp_module.STATUS_VERIFIED, evidence_refs=["x.java:1"]),
            ],
        )
        seeded = pg.seed_file_impacts_from_ledger(pkg)
        assert [i.path for i in seeded] == ["calc.py"]
        assert seeded[0].action == pg.ACTION_MODIFY_EXISTING


class TestValidateFileImpacts:
    def _pkg(self, not_found: list[str] | None = None) -> cp_module.ContextPackage:
        ledger = [cp_module.EvidenceLedgerEntry(entity=e, entity_type="file", status=cp_module.STATUS_NOT_FOUND) for e in (not_found or [])]
        return cp_module.ContextPackage(
            work_item_id=1, primary_repo_id=1, repo_sha="abc", requirement="r", ask_findings_summary="", evidence_ledger=ledger
        )

    def test_modify_existing_requires_real_file_on_disk(self, tmp_path):
        (tmp_path / "real.java").write_text("class Real {}\n", encoding="utf-8")
        impacts = [
            pg.FileImpact(path="real.java", action=pg.ACTION_MODIFY_EXISTING, language="java"),
            pg.FileImpact(path="ghost.java", action=pg.ACTION_MODIFY_EXISTING, language="java"),
        ]
        accepted, rejected = pg.validate_file_impacts(
            impacts, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven")
        )
        assert [i.path for i in accepted] == ["real.java"]
        assert any("ghost.java" in r for r in rejected)

    def test_not_found_entity_cannot_be_modify_existing_even_if_a_file_exists_at_that_path(self, tmp_path):
        (tmp_path / "CampaignManagement.java").write_text("class CampaignManagement {}\n", encoding="utf-8")
        impacts = [pg.FileImpact(path="CampaignManagement.java", action=pg.ACTION_MODIFY_EXISTING, language="java")]
        accepted, rejected = pg.validate_file_impacts(
            impacts,
            context_package=self._pkg(not_found=["CampaignManagement.java"]),
            repo_root=tmp_path,
            architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert accepted == []
        assert any("NOT_FOUND" in r for r in rejected)

    def test_create_new_requires_a_rationale(self, tmp_path):
        impacts = [pg.FileImpact(path="New.java", action=pg.ACTION_CREATE_NEW, language="java", rationale="")]
        accepted, rejected = pg.validate_file_impacts(
            impacts, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven")
        )
        assert accepted == []
        assert any("rationale" in r for r in rejected)

    def test_create_new_for_an_already_existing_path_is_rejected(self, tmp_path):
        (tmp_path / "Existing.java").write_text("class Existing {}\n", encoding="utf-8")
        impacts = [pg.FileImpact(path="Existing.java", action=pg.ACTION_CREATE_NEW, language="java", rationale="new module")]
        accepted, rejected = pg.validate_file_impacts(
            impacts, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven")
        )
        assert accepted == []
        assert any("already exists" in r for r in rejected)

    def test_cms_regression_arbitrary_python_target_in_java_repo_is_rejected(self, tmp_path):
        """The exact CMS-benchmark failure: `rel/campaign_management.py`
        proposed against an all-Java repository."""
        impacts = [
            pg.FileImpact(
                path="rel/campaign_management.py", action=pg.ACTION_CREATE_NEW, language="python",
                rationale="Implements campaign management.",
            )
        ]
        accepted, rejected = pg.validate_file_impacts(
            impacts, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven")
        )
        assert accepted == []
        assert any("language mismatch" in r for r in rejected)

    def test_create_new_matching_detected_language_is_accepted(self, tmp_path):
        impacts = [
            pg.FileImpact(
                path="CampaignService.java", action=pg.ACTION_CREATE_NEW, language="java",
                rationale="New service implementing campaign CRUD.",
            )
        ]
        accepted, rejected = pg.validate_file_impacts(
            impacts, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven")
        )
        assert [i.path for i in accepted] == ["CampaignService.java"]
        assert rejected == []

    def test_placeholder_path_is_rejected_outright(self, tmp_path):
        impacts = [pg.FileImpact(path="example/file.py", action=pg.ACTION_CREATE_NEW, language="python", rationale="placeholder")]
        accepted, rejected = pg.validate_file_impacts(
            impacts, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("unknown", "unknown")
        )
        assert accepted == []
        assert any("placeholder" in r for r in rejected)

    def test_duplicate_paths_keep_only_the_first(self, tmp_path):
        (tmp_path / "real.java").write_text("class Real {}\n", encoding="utf-8")
        impacts = [
            pg.FileImpact(path="real.java", action=pg.ACTION_MODIFY_EXISTING, language="java"),
            pg.FileImpact(path="real.java", action=pg.ACTION_MODIFY_EXISTING, language="java"),
        ]
        accepted, rejected = pg.validate_file_impacts(
            impacts, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven")
        )
        assert len(accepted) == 1
        assert any("duplicate" in r for r in rejected)


class TestRenderGroundedPlanMarkdown:
    def test_all_mandated_sections_are_present_in_order(self):
        text = pg.render_grounded_plan_markdown(
            goal="Implement campaign creation",
            context_package=None,
            architecture=pg.RepoArchitecture("java", "maven"),
            accepted_impacts=[],
            rejected_reasons=[],
            narrative_sections={},
        )
        positions = [text.find(f"## {s}") for s in pg._SECTION_ORDER]
        assert all(p != -1 for p in positions), positions
        assert positions == sorted(positions)

    def test_file_impact_sections_always_reflect_accepted_impacts_not_narrative(self):
        impacts = [pg.FileImpact(path="Real.java", action=pg.ACTION_MODIFY_EXISTING, language="java", rationale="fix bug")]
        text = pg.render_grounded_plan_markdown(
            goal="g",
            context_package=None,
            architecture=pg.RepoArchitecture("java", "maven"),
            accepted_impacts=impacts,
            rejected_reasons=[],
            # The narrative tries to claim something different for this
            # section -- must be ignored; the table always wins.
            narrative_sections={"Existing files to modify": "Nothing to modify."},
        )
        assert "Real.java" in text
        assert "Nothing to modify." not in text


class TestCmsGroundedPlanIntegration:
    """The full ASK -> PLAN path, proving the CMS Campaign Management
    requirement now produces a repository-grounded, typed file-impact plan
    instead of the previous generic/file-less "Port Module N" plan."""

    def test_campaign_requirement_produces_grounded_java_file_impacts(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "InboxAction.java").write_text("class InboxAction {}\n", encoding="utf-8")
        _mock_ask(
            monkeypatch,
            "No existing Campaign Management code was found; this repository implements party/enrollment workflow only.",
        )
        svc = MentrixDeveloperService(db)
        ask_result = svc.ask(
            question="Analyze the attached Campaign Management requirement against this repository.",
            project_id=p.id,
            repository_id=repo.id,
        )

        _mock_grounded_plan(
            monkeypatch,
            "## Architecture\nA new CampaignService will own creation and DOFA approval routing.\n"
            "## Risks\nNo existing campaign code to build on; greenfield implementation.",
            proposed_file_impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java",
                    "action": "CREATE_NEW",
                    "language": "java",
                    "rationale": "Does not exist yet -- new service implementing campaign creation and DOFA routing.",
                    "dependencies": [],
                    "verification": "Add CampaignServiceTest with creation and approval-routing cases.",
                },
                # A wrong-language distractor the model might still propose --
                # must be rejected, not silently accepted, proving the CMS
                # regression (rel/campaign_management.py) cannot recur.
                {
                    "path": "rel/campaign_management.py",
                    "action": "CREATE_NEW",
                    "language": "python",
                    "rationale": "Implements campaign management.",
                    "dependencies": [],
                    "verification": "",
                },
            ],
        )
        plan_result = svc.plan(goal="Implement campaign creation", work_item_id=ask_result["work_item_id"])
        plan_text = plan_result["plan"]

        assert plan_result["architecture"]["primary_language"] == "java"
        assert not pg.find_placeholder_violations(plan_text)
        assert "com/zinnia/cms/campaign/CampaignService.java" in plan_text
        assert any(i["path"] == "com/zinnia/cms/campaign/CampaignService.java" for i in plan_result["file_impacts"])
        # Rejected, wrong-language proposal must never appear as an accepted
        # file-impact target -- it's fine (transparent, even) that it's
        # visible in the "rejected" banner explaining why it was excluded.
        assert not any(i["path"] == "rel/campaign_management.py" for i in plan_result["file_impacts"])
        assert any("language mismatch" in r for r in plan_result["rejected_file_impacts"])
        for section in pg._SECTION_ORDER:
            assert f"## {section}" in plan_text
        # The exact old defect this replaces -- must never reappear.
        assert "port module" not in plan_text.lower()

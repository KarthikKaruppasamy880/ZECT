"""CP-06 -- plan validation as a deterministic hard pre-approval gate.

Not another warning system: CP-04/CP-05 already prepend visible banners for
known defects, but a banner is still just text a user could approve past.
approve_plan() must re-run this gate fresh every time and hard-refuse
(HTTP 409, structured findings, no mutation of approved_plan_hash) unless
the result is VALID. This suite proves both the standalone validator
(plan_validator.py) against hand-constructed machine contracts -- so each
CMS-named failure mode is caught independently of whether CP-05's own
generation-time filter happened to also catch it -- and the real
approve_plan()/validate_plan() wiring end to end.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.work_items import context_package as cp_module
from app.services.work_items import plan_generator as pg
from app.services.work_items import plan_validator as pv
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
    p = Project(name=f"cp06-{tag}", description="test", status="active")
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
        lambda *a, **kw: {"narrative": narrative, "proposed_file_impacts": proposed_file_impacts or [], "model": "test", "offline": False},
    )


_GOOD_NARRATIVE = "\n\n".join(f"## {s}\nSee above." for s in pg._SECTION_ORDER if s not in ("Existing files to modify", "New files"))


class TestValidatorDirectCmsRegressions:
    """Each of the exact CMS-named failure modes, hand-constructed so the
    approval-time gate is proven independently of generation-time
    filtering (defense in depth: CP-05 should already reject most of
    these, but a hand-edited .plan.md or corrupted sidecar must still be
    caught here)."""

    def _pkg(self, evidence_ledger=None) -> cp_module.ContextPackage:
        return cp_module.ContextPackage(
            work_item_id=1, primary_repo_id=1, repo_sha="abc123", requirement="r", ask_findings_summary="",
            evidence_ledger=evidence_ledger or [],
        )

    def _base_plan_text(self, extra: str = "") -> str:
        text = f"# Plan\n\n{_GOOD_NARRATIVE}\n\n## Existing files to modify\n{extra}\n\n## New files\n{extra}\n"
        return text

    def test_placeholder_port_module_n(self, tmp_path):
        text = self._base_plan_text() + "\n## Phase 2: Port Module N\n"
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar={"work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h", "file_impacts": []},
            context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any(f.rule == "unresolved_placeholder" for f in result.findings)

    def test_nonexistent_modify_target(self, tmp_path):
        sidecar = {
            "work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h",
            "file_impacts": [{"path": "Ghost.java", "action": "MODIFY_EXISTING", "language": "java", "requirement_ids": ["R1"]}],
        }
        text = self._base_plan_text("Ghost.java")
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=sidecar, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any(f.rule == "file_impact_revalidation_failed" for f in result.findings)

    def test_java_repo_python_create_new(self, tmp_path):
        sidecar = {
            "work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h",
            "file_impacts": [
                {
                    "path": "rel/campaign_management.py", "action": "CREATE_NEW", "language": "python",
                    "rationale": "Implements campaign management.", "requirement_ids": ["R1"],
                }
            ],
        }
        text = self._base_plan_text("rel/campaign_management.py")
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=sidecar, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any("language mismatch" in f.detail for f in result.findings)

    def test_not_found_entity_as_modify(self, tmp_path):
        (tmp_path / "CampaignManagement.java").write_text("class CampaignManagement {}\n", encoding="utf-8")
        ledger = [cp_module.EvidenceLedgerEntry(entity="CampaignManagement.java", entity_type="file", status=cp_module.STATUS_NOT_FOUND)]
        sidecar = {
            "work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h",
            "file_impacts": [{"path": "CampaignManagement.java", "action": "MODIFY_EXISTING", "language": "java", "requirement_ids": ["R1"]}],
        }
        text = self._base_plan_text("CampaignManagement.java")
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=sidecar, context_package=self._pkg(ledger), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any("NOT_FOUND" in f.detail for f in result.findings)

    def test_repo_root_escape(self, tmp_path):
        sidecar = {
            "work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h",
            "file_impacts": [
                {"path": "../../etc/passwd", "action": "CREATE_NEW", "language": "unknown", "rationale": "x", "requirement_ids": ["R1"]}
            ],
        }
        text = self._base_plan_text("../../etc/passwd")
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=sidecar, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("unknown", "unknown"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any("escapes" in f.detail for f in result.findings)

    def test_stale_plan_hash(self, tmp_path):
        text = self._base_plan_text()
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="old-hash", plan_text=text, current_plan_hash="new-hash",
            sidecar={"work_item_id": 1, "primary_repo_id": 1, "plan_hash": "old-hash", "file_impacts": []},
            context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_STALE

    def test_conflicting_duplicate_file_impacts(self, tmp_path):
        (tmp_path / "Real.java").write_text("class Real {}\n", encoding="utf-8")
        sidecar = {
            "work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h",
            "file_impacts": [
                {"path": "Real.java", "action": "MODIFY_EXISTING", "language": "java", "requirement_ids": ["R1"]},
                {"path": "Real.java", "action": "DELETE_EXISTING", "language": "java", "requirement_ids": ["R1"]},
            ],
        }
        text = self._base_plan_text("Real.java")
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=sidecar, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any("duplicate" in f.detail for f in result.findings)


class TestValidatorGeneralRules:
    def _pkg(self) -> cp_module.ContextPackage:
        return cp_module.ContextPackage(work_item_id=1, primary_repo_id=1, repo_sha="abc123", requirement="r", ask_findings_summary="")

    def test_missing_required_sections_is_invalid(self, tmp_path):
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text="# Plan\n\n## Goal\nDo it.\n", current_plan_hash="h",
            sidecar=None, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any(f.rule == "missing_sections" for f in result.findings)

    def test_missing_base_sha_is_invalid(self, tmp_path):
        text = "# Plan\n\n" + _GOOD_NARRATIVE + "\n\n## Existing files to modify\n_None._\n\n## New files\n_None._\n"
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar={"work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h", "file_impacts": []},
            context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any(f.rule == "missing_base_sha" for f in result.findings)

    def test_untied_file_impact_with_no_requirement_or_evidence_refs(self, tmp_path):
        (tmp_path / "Real.java").write_text("class Real {}\n", encoding="utf-8")
        sidecar = {
            "work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h",
            "file_impacts": [{"path": "Real.java", "action": "MODIFY_EXISTING", "language": "java"}],
        }
        text = "# Plan\n\n" + _GOOD_NARRATIVE + "\n\n## Existing files to modify\nReal.java\n\n## New files\n_None._\n"
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=sidecar, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any(f.rule == "untied_file_impact" for f in result.findings)

    def test_missing_machine_contract_is_invalid(self, tmp_path):
        text = "# Plan\n\n" + _GOOD_NARRATIVE + "\n\n## Existing files to modify\n_None._\n\n## New files\n_None._\n"
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=None, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID
        assert any(f.rule == "missing_machine_contract" for f in result.findings)

    def test_fully_clean_plan_is_valid(self, tmp_path):
        (tmp_path / "Real.java").write_text("class Real {}\n", encoding="utf-8")
        sidecar = {
            "work_item_id": 1, "primary_repo_id": 1, "plan_hash": "h",
            "file_impacts": [
                {"path": "Real.java", "action": "MODIFY_EXISTING", "language": "java", "requirement_ids": ["R1"], "evidence_refs": ["Real.java"]}
            ],
        }
        text = "# Plan\n\n" + _GOOD_NARRATIVE + "\n\n## Existing files to modify\nReal.java\n\n## New files\n_None._\n"
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="h", plan_text=text, current_plan_hash="h",
            sidecar=sidecar, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_VALID
        assert result.findings == []

    def test_empty_plan_is_invalid(self, tmp_path):
        result = pv.validate_plan_for_approval(
            work_item_id=1, primary_repo_id=1, base_commit_sha="abc123",
            recorded_plan_hash="", plan_text="   ", current_plan_hash="",
            sidecar=None, context_package=self._pkg(), repo_root=tmp_path, architecture=pg.RepoArchitecture("java", "maven"),
        )
        assert result.status == pv.STATUS_INVALID


class TestMissionApprovePlanHardGate:
    """The Developer Workspace's real "Approve & Build" button calls
    POST /api/coding-agent/missions/{id}/approve-plan
    (lifecycle.approve_plan), never developer_service.py's WorkItem-level
    approve_plan -- that method is a separate, lower-level primitive also
    used directly by app.services.mentrix.engineering_agents and must keep
    working unconditionally for that unrelated caller (verified by the
    broader regression sweep). This class proves the gate that actually
    guards the UI action: lifecycle.py only enforces it when the Mission's
    work_item_id points at a WorkItem that went through the grounded
    ASK/PLAN pipeline (has a FILE_IMPACTS.json machine contract) -- a
    Mission created without one, or the many existing missions built
    without ever calling developer plan(), are correctly left alone."""

    def _create_and_approve(self, work_item_id: int, plan_text: str, repo_local_path: str):
        from app.services.coding_engine import lifecycle

        mission = lifecycle.start_mission(
            goal="Implement campaign creation",
            roots=[{"id": 1, "label": "cms", "path": repo_local_path}],
            plan=plan_text,
            work_item_id=work_item_id,
        )
        return lifecycle.approve_plan(mission["id"])

    def test_approve_plan_blocks_and_never_flips_plan_approved_when_invalid(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        # Mentioning the literal name is what makes ASK's evidence ledger
        # actually register it as a NOT_FOUND candidate entity in the first
        # place -- a generic "no such code exists" sentence with no literal
        # name has nothing for the ledger (or PLAN's leak-check) to key on.
        _mock_ask(monkeypatch, "No existing CampaignManagement.java was found in this repository.")
        svc = MentrixDeveloperService(db)
        ask_result = svc.ask(
            question="Analyze the Campaign Management requirement",
            project_id=p.id, repository_id=repo.id, base_commit_sha="abc123def456",
        )
        # The model's prose leaks that same NOT_FOUND entity as if it
        # already exists, with no structured file-impact proposal at all.
        _mock_grounded_plan(monkeypatch, "## Current implementation\nCampaignManagement.java already handles this.")
        plan_result = svc.plan(goal="Implement campaign creation", work_item_id=ask_result["work_item_id"])
        assert plan_result["validation"]["status"] != pv.STATUS_VALID, plan_result["validation"]

        with pytest.raises(ValueError, match="plan_validation_failed"):
            self._create_and_approve(ask_result["work_item_id"], plan_result["plan"], str(tmp_path))

    def test_approve_plan_succeeds_for_a_clean_grounded_plan(self, db: Session, monkeypatch, tmp_path):
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "InboxAction.java").write_text("class InboxAction {}\n", encoding="utf-8")
        _mock_ask(monkeypatch, "InboxAction.java handles inbox routing; no Campaign Management code exists.")
        svc = MentrixDeveloperService(db)
        ask_result = svc.ask(
            question="Analyze InboxAction.java and propose campaign creation",
            project_id=p.id, repository_id=repo.id, base_commit_sha="abc123def456",
        )
        _mock_grounded_plan(
            monkeypatch,
            _GOOD_NARRATIVE,
            proposed_file_impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java",
                    "action": "CREATE_NEW",
                    "language": "java",
                    "rationale": "New service implementing campaign creation.",
                    "requirement_ids": ["R1"],
                    "dependencies": [],
                    "verification": "Add CampaignServiceTest.",
                }
            ],
        )
        plan_result = svc.plan(goal="Implement campaign creation", work_item_id=ask_result["work_item_id"])
        assert plan_result["validation"]["status"] == pv.STATUS_VALID, plan_result["validation"]

        approved = self._create_and_approve(ask_result["work_item_id"], plan_result["plan"], str(tmp_path))
        assert approved["plan_approved"] is True
        assert approved["plan_validation"]["status"] == pv.STATUS_VALID

    def test_editing_the_repo_local_plan_directly_makes_it_stale(self, db: Session, monkeypatch, tmp_path):
        """The exact Monaco-edit scenario: the mission's own plan text (what
        the Approve & Build call actually sends) differs from what was
        last generated/validated -- lifecycle.py's existing plan_hash_drift
        re-hash used to silently accept this; CP-06 must block it instead."""
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        _mock_ask(monkeypatch, "No existing Campaign Management code was found.")
        svc = MentrixDeveloperService(db)
        ask_result = svc.ask(
            question="Analyze the requirement", project_id=p.id, repository_id=repo.id, base_commit_sha="abc123def456",
        )
        _mock_grounded_plan(
            monkeypatch,
            _GOOD_NARRATIVE,
            proposed_file_impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java",
                    "action": "CREATE_NEW",
                    "language": "java",
                    "rationale": "New service implementing campaign creation.",
                    "requirement_ids": ["R1"],
                }
            ],
        )
        plan_result = svc.plan(goal="Implement campaign creation", work_item_id=ask_result["work_item_id"])
        assert plan_result["validation"]["status"] == pv.STATUS_VALID, plan_result["validation"]

        hand_edited = plan_result["plan"] + "\n\n## Hand-edited note\nSomething changed by hand.\n"
        with pytest.raises(ValueError, match="plan_validation_failed:STALE"):
            self._create_and_approve(ask_result["work_item_id"], hand_edited, str(tmp_path))

    def test_missions_without_a_grounded_workitem_are_unaffected(self, tmp_path):
        """A Mission created directly (no work_item_id, or one that never
        called developer plan()) has no machine contract to validate
        against -- the gate must not apply, preserving every pre-CP-06
        Mission-creation test's behavior."""
        from app.services.coding_engine import lifecycle

        mission = lifecycle.start_mission(
            goal="Ad hoc smoke test", roots=[{"id": 1, "label": "x", "path": str(tmp_path)}], plan="# Anything goes\n"
        )
        approved = lifecycle.approve_plan(mission["id"])
        assert approved["plan_approved"] is True
        assert approved["plan_validation"] is None

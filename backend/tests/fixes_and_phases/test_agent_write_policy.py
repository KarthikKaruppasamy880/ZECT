"""CP-07 -- AGENT context + write enforcement, the hard execution-security
boundary between an approved PLAN and any actual filesystem mutation.

CP-06 made "Approve & Build" a hard gate on the PLAN *document*, checked
once before a Mission ever enters the editing phase. This suite proves the
companion gate CP-07 adds on every individual *write*: even a Mission that
passed CP-06's gate can drift (the plan edited afterward) or an LLM tool
call can simply propose a path never listed in the approved plan -- and
until this change, the only thing standing between that proposal and bytes
on disk was the git-worktree jail (any path inside the worktree was
writable). Structured the same way as test_plan_validation_gate.py: direct
unit tests against the pure authorize_write() function for every CMS-named
rule (fast, independent of the DB/LLM pipeline), then end-to-end tests
through the real lifecycle._apply_patches()/_authorize_agent_write() wiring
with a real ASK->PLAN->FILE_IMPACTS.json pipeline underneath, so the
wiring itself -- not just the rule logic -- is proven correct.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.coding_engine import agent_write_policy as awp
from app.services.coding_engine import lifecycle
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
    p = Project(name=f"cp07-{tag}", description="test", status="active")
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


class TestAuthorizeWriteDirect:
    """Hand-constructed AgentWritePolicy objects, one per CMS-named rule --
    proven independently of build_agent_write_policy()/the DB pipeline so
    the actual authorization logic is covered in isolation."""

    def _policy(self, **overrides) -> awp.AgentWritePolicy:
        base = dict(work_item_id=1, authorized=True, primary_repo_id=7, plan_hash="h", file_impacts=[], not_found_entities=set())
        base.update(overrides)
        return awp.AgentWritePolicy(**base)

    def test_blocked_policy_refuses_every_write(self):
        policy = awp.AgentWritePolicy(work_item_id=1, authorized=False, block_reason="plan_stale", block_detail="edited after approval")
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="Real.java", workspace="/tmp/x")
        assert decision.allowed is False
        assert decision.reason == "plan_stale"

    def test_wrong_repository_blocked_unless_primary_write(self, tmp_path):
        policy = self._policy(file_impacts=[pg.FileImpact(path="Real.java", action=pg.ACTION_MODIFY_EXISTING, language="java")])
        (tmp_path / "Real.java").write_text("class Real {}\n", encoding="utf-8")
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=999, path="Real.java", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "wrong_repository"

    def test_path_escapes_authorized_root_blocked(self, tmp_path):
        policy = self._policy(file_impacts=[pg.FileImpact(path="../../etc/passwd", action=pg.ACTION_CREATE_NEW, language="unknown")])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="../../etc/passwd", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "path_escapes_authorized_root"

    def test_not_found_entity_blocked_even_if_listed(self, tmp_path):
        (tmp_path / "CampaignManagement.java").write_text("class CampaignManagement {}\n", encoding="utf-8")
        policy = self._policy(
            file_impacts=[pg.FileImpact(path="CampaignManagement.java", action=pg.ACTION_MODIFY_EXISTING, language="java")],
            not_found_entities={"CampaignManagement.java"},
        )
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="CampaignManagement.java", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "not_found_entity"

    def test_unplanned_hallucinated_path_blocked(self, tmp_path):
        policy = self._policy(file_impacts=[pg.FileImpact(path="Real.java", action=pg.ACTION_MODIFY_EXISTING, language="java")])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="rel/campaign_management.py", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "unplanned_path"

    def test_modify_existing_requires_file_to_exist(self, tmp_path):
        policy = self._policy(file_impacts=[pg.FileImpact(path="Ghost.java", action=pg.ACTION_MODIFY_EXISTING, language="java")])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="Ghost.java", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "modify_target_missing"

    def test_modify_existing_allowed_when_file_exists(self, tmp_path):
        (tmp_path / "Real.java").write_text("class Real {}\n", encoding="utf-8")
        policy = self._policy(file_impacts=[pg.FileImpact(path="Real.java", action=pg.ACTION_MODIFY_EXISTING, language="java")])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="Real.java", workspace=tmp_path)
        assert decision.allowed is True
        assert decision.matched_action == pg.ACTION_MODIFY_EXISTING

    def test_create_new_allowed(self, tmp_path):
        policy = self._policy(file_impacts=[pg.FileImpact(path="New.java", action=pg.ACTION_CREATE_NEW, language="java")])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="New.java", workspace=tmp_path)
        assert decision.allowed is True
        assert decision.matched_action == pg.ACTION_CREATE_NEW

    def test_reference_only_never_writable(self, tmp_path):
        (tmp_path / "Ref.java").write_text("class Ref {}\n", encoding="utf-8")
        policy = self._policy(file_impacts=[pg.FileImpact(path="Ref.java", action=pg.ACTION_REFERENCE_ONLY, language="java")])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="Ref.java", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "not_writable_action"

    def test_delete_existing_not_deletable_via_write_file(self, tmp_path):
        (tmp_path / "Dead.java").write_text("class Dead {}\n", encoding="utf-8")
        policy = self._policy(file_impacts=[pg.FileImpact(path="Dead.java", action=pg.ACTION_DELETE_EXISTING, language="java")])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="Dead.java", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "delete_target_not_deletable_here"

    def test_delete_existing_allowed_via_delete_tool(self, tmp_path):
        (tmp_path / "Dead.java").write_text("class Dead {}\n", encoding="utf-8")
        policy = self._policy(file_impacts=[pg.FileImpact(path="Dead.java", action=pg.ACTION_DELETE_EXISTING, language="java")])
        decision = awp.authorize_write(policy, tool_name="delete_file", repo_id=7, path="Dead.java", workspace=tmp_path)
        assert decision.allowed is True

    def test_create_new_not_deletable(self, tmp_path):
        policy = self._policy(file_impacts=[pg.FileImpact(path="New.java", action=pg.ACTION_CREATE_NEW, language="java")])
        decision = awp.authorize_write(policy, tool_name="delete_file", repo_id=7, path="New.java", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "delete_not_authorized"


class TestApplyPatchesIntegration:
    """End-to-end through lifecycle._apply_patches() against a real
    ASK -> PLAN -> FILE_IMPACTS.json pipeline -- proves the wiring itself,
    not just authorize_write()'s pure logic."""

    def _ground(self, db, monkeypatch, tmp_path, *, ask_answer: str, narrative: str, impacts: list, question: str = "Analyze the Campaign Management requirement") -> tuple[dict, dict]:
        p, repo = _seed_repo(db, str(tmp_path))
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        _mock_ask(monkeypatch, ask_answer)
        svc = MentrixDeveloperService(db)
        ask_result = svc.ask(
            question=question,
            project_id=p.id, repository_id=repo.id, base_commit_sha="abc123def456",
        )
        _mock_grounded_plan(monkeypatch, narrative, proposed_file_impacts=impacts)
        plan_result = svc.plan(goal="Implement campaign creation", work_item_id=ask_result["work_item_id"])
        assert plan_result["validation"]["status"] == pv.STATUS_VALID, plan_result["validation"]
        mission = lifecycle.start_mission(
            goal="Implement campaign creation",
            roots=[{"id": repo.id, "label": "cms", "path": str(tmp_path)}],
            plan=plan_result["plan"],
            work_item_id=ask_result["work_item_id"],
            primary_repository_id=repo.id,
        )
        return mission, mission["repos"][0]

    def test_valid_planned_existing_java_file_write_allowed(self, db, monkeypatch, tmp_path):
        (tmp_path / "InboxAction.java").write_text("class InboxAction {}\n", encoding="utf-8")
        mission, repo = self._ground(
            db, monkeypatch, tmp_path,
            question="Analyze InboxAction.java and propose a campaign hook",
            ask_answer="InboxAction.java handles inbox routing; no Campaign Management code exists.",
            narrative=_GOOD_NARRATIVE,
            impacts=[
                {
                    "path": "InboxAction.java", "action": "MODIFY_EXISTING", "language": "java",
                    "rationale": "Add campaign hook.", "requirement_ids": ["R1"],
                }
            ],
        )
        result = lifecycle._apply_patches(mission, repo, tmp_path, [{"path": "InboxAction.java", "content": "class InboxAction { /* campaign hook */ }\n"}])
        assert result["ok"] is True
        assert "InboxAction.java" in "".join(result["files"])
        assert "campaign hook" in (tmp_path / "InboxAction.java").read_text(encoding="utf-8")

    def test_explicitly_approved_create_new_allowed(self, db, monkeypatch, tmp_path):
        mission, repo = self._ground(
            db, monkeypatch, tmp_path,
            ask_answer="No existing Campaign Management code was found.",
            narrative=_GOOD_NARRATIVE,
            impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java", "action": "CREATE_NEW", "language": "java",
                    "rationale": "New service implementing campaign creation.", "requirement_ids": ["R1"],
                }
            ],
        )
        result = lifecycle._apply_patches(
            mission, repo, tmp_path,
            [{"path": "com/zinnia/cms/campaign/CampaignService.java", "content": "class CampaignService {}\n"}],
        )
        assert result["ok"] is True
        assert (tmp_path / "com/zinnia/cms/campaign/CampaignService.java").is_file()

    def test_hallucinated_not_found_file_blocked_before_patch(self, db, monkeypatch, tmp_path):
        mission, repo = self._ground(
            db, monkeypatch, tmp_path,
            ask_answer="No existing CampaignManagement.java was found in this repository.",
            narrative=_GOOD_NARRATIVE,
            impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java", "action": "CREATE_NEW", "language": "java",
                    "rationale": "New service.", "requirement_ids": ["R1"],
                }
            ],
        )
        result = lifecycle._apply_patches(mission, repo, tmp_path, [{"path": "CampaignManagement.java", "content": "class CampaignManagement { /* hijacked */ }\n"}])
        assert result["ok"] is False
        assert "write_blocked" in result["error"]
        assert not (tmp_path / "CampaignManagement.java").exists()

    def test_java_repo_python_target_blocked(self, db, monkeypatch, tmp_path):
        mission, repo = self._ground(
            db, monkeypatch, tmp_path,
            ask_answer="No existing Campaign Management code was found.",
            narrative=_GOOD_NARRATIVE,
            impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java", "action": "CREATE_NEW", "language": "java",
                    "rationale": "New service.", "requirement_ids": ["R1"],
                }
            ],
        )
        result = lifecycle._apply_patches(mission, repo, tmp_path, [{"path": "rel/campaign_management.py", "content": "def create_campaign(): ...\n"}])
        assert result["ok"] is False
        assert "write_blocked" in result["error"]
        assert not (tmp_path / "rel/campaign_management.py").exists()

    def test_plan_edited_after_approval_blocks_as_stale(self, db, monkeypatch, tmp_path):
        mission, repo = self._ground(
            db, monkeypatch, tmp_path,
            ask_answer="No existing Campaign Management code was found.",
            narrative=_GOOD_NARRATIVE,
            impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java", "action": "CREATE_NEW", "language": "java",
                    "rationale": "New service.", "requirement_ids": ["R1"],
                }
            ],
        )
        # Simulate a Monaco edit landing in the repo-local plan copy after
        # PLAN generated FILE_IMPACTS.json -- the exact drift scenario a
        # human editing .plan.md directly produces.
        from app.infrastructure.allowed_paths import path_under_allowed_roots
        from app.services.coding_engine.plan_store import save_plan

        allowed_root = str(path_under_allowed_roots(str(tmp_path)))
        save_plan(work_item_or_run=str(mission["work_item_id"]), title="coding", markdown=mission["plan"] + "\n\nHand-edited.\n", workspace=allowed_root)

        result = lifecycle._apply_patches(
            mission, repo, tmp_path,
            [{"path": "com/zinnia/cms/campaign/CampaignService.java", "content": "class CampaignService {}\n"}],
        )
        assert result["ok"] is False
        assert "plan_stale" in result["error"]

    def test_another_attached_repo_blocked_unless_primary_write(self, db, monkeypatch, tmp_path):
        mission, primary_repo = self._ground(
            db, monkeypatch, tmp_path,
            ask_answer="No existing Campaign Management code was found.",
            narrative=_GOOD_NARRATIVE,
            impacts=[
                {
                    "path": "com/zinnia/cms/campaign/CampaignService.java", "action": "CREATE_NEW", "language": "java",
                    "rationale": "New service.", "requirement_ids": ["R1"],
                }
            ],
        )
        sibling_repo = {"repository_id": primary_repo["repository_id"] + 999, "label": "sibling", "files": [], "commands": [], "committed_shas": []}
        result = lifecycle._apply_patches(mission, sibling_repo, tmp_path, [{"path": "com/zinnia/cms/campaign/CampaignService.java", "content": "class CampaignService {}\n"}])
        assert result["ok"] is False
        assert "wrong_repository" in result["error"]

    def test_missions_without_work_item_id_unaffected(self, tmp_path):
        mission = lifecycle.start_mission(
            goal="Ad hoc smoke test", roots=[{"id": 1, "label": "x", "path": str(tmp_path)}], plan="# Anything goes\n"
        )
        result = lifecycle._apply_patches(mission, mission["repos"][0], tmp_path, [{"path": "anything.txt", "content": "hello\n"}])
        assert result["ok"] is True
        assert (tmp_path / "anything.txt").read_text(encoding="utf-8") == "hello\n"


class TestNativeLoopWiring:
    """coding_engine_mentrix._authorize_agent_write() is the equivalent
    checkpoint for the native tool-calling loop -- proven directly against
    a hand-built `run` dict, without needing a real LLM loop."""

    def test_non_mutating_tool_is_never_gated(self, tmp_path):
        from app.adapters.coding_engine_mentrix import _authorize_agent_write

        run = {"work_item_id": 1, "repo_id": "7"}
        assert _authorize_agent_write(run, tmp_path, "read_file", {"path": "Real.java"}) is None

    def test_run_without_work_item_id_is_never_gated(self, tmp_path):
        from app.adapters.coding_engine_mentrix import _authorize_agent_write

        run = {"work_item_id": None, "repo_id": "7"}
        assert _authorize_agent_write(run, tmp_path, "write_file", {"path": "Real.java", "content": "x"}) is None

    def test_write_file_with_no_machine_contract_is_blocked(self, db, tmp_path):
        from app.adapters.coding_engine_mentrix import _authorize_agent_write
        from app.models import WorkItem

        p, repo = _seed_repo(db, str(tmp_path))
        wi = WorkItem(project_id=p.id, title="t", status="planned", repository_id=repo.id)
        db.add(wi)
        db.commit()
        db.refresh(wi)

        run = {"work_item_id": wi.id, "repo_id": str(repo.id)}
        decision = _authorize_agent_write(run, tmp_path, "write_file", {"path": "Real.java", "content": "class Real {}"})
        assert decision is not None
        assert decision.allowed is False
        assert decision.reason == "missing_machine_contract"

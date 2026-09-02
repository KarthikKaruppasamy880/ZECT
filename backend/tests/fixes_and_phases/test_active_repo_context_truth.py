"""CP-01 -- one authoritative active-repository/context truth for ASK/PLAN/AGENT.

Regression coverage for finding A2 (ZECT_CURSOR_CLASS_REFERENCE_RECONCILIATION.md):
Context Used used to always report the project's first-added repo instead of
the repo the WorkItem is actually bound to, because (1)
resolve_authorized_repository_ids() only floated a primary id to the front of
the list when it was *absent*, never when it was merely not first, and (2)
merge_context_packs() always took packs[0] regardless of which repo the
caller considered primary. A WorkItem's own repository_id, once set, is now
the sticky, authoritative truth: later calls cannot silently rebind it to
whatever repo happens to be first in a request's repository_ids list.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.coding_engine.lifecycle import start_mission
from app.services.work_items.context_engine import ContextPack
from app.services.work_items.developer_service import MentrixDeveloperService
from app.services.work_items.multi_repo_context import (
    merge_context_packs,
    resolve_authorized_repository_ids,
)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_two_repos(db: Session) -> tuple[Project, Repo, Repo]:
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"cp01-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r1 = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main")
    r2 = Repo(project_id=p.id, owner="acme", repo_name="beta", default_branch="main")
    db.add_all([r1, r2])
    db.commit()
    db.refresh(p)
    db.refresh(r1)
    db.refresh(r2)
    return p, r1, r2


def _env_offline(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


class TestResolveAuthorizedRepositoryIds:
    def test_floats_primary_to_front_even_when_already_present(self, db: Session):
        p, r1, r2 = _seed_two_repos(db)
        # repository_ids arrives in fetch order [r1, r2]; the caller's real
        # primary is r2 -- it must end up first, not stay at index 1.
        out = resolve_authorized_repository_ids(
            db, project_id=p.id, repository_ids=[r1.id, r2.id], repository_id=r2.id
        )
        assert out[0] == r2.id
        assert set(out) == {r1.id, r2.id}

    def test_still_inserts_primary_when_absent(self, db: Session):
        p, r1, r2 = _seed_two_repos(db)
        out = resolve_authorized_repository_ids(
            db, project_id=p.id, repository_ids=[r1.id], repository_id=r2.id
        )
        assert out[0] == r2.id


class TestMergeContextPacksPrimarySelection:
    def test_selects_pack_matching_primary_id_not_list_position(self):
        pack_a = ContextPack(repository_id=16)
        pack_b = ContextPack(repository_id=17)
        # packs[0] is repo 16 -- the old bug would report 16 regardless.
        merged = merge_context_packs([pack_a, pack_b], primary_repository_id=17)
        assert merged.repository_id == 17

    def test_falls_back_to_packs_zero_when_no_primary_given(self):
        pack_a = ContextPack(repository_id=16)
        pack_b = ContextPack(repository_id=17)
        merged = merge_context_packs([pack_a, pack_b])
        assert merged.repository_id == 16

    def test_falls_back_to_packs_zero_when_primary_not_found(self):
        pack_a = ContextPack(repository_id=16)
        merged = merge_context_packs([pack_a], primary_repository_id=999)
        assert merged.repository_id == 16


class TestAskPlanRespectStickyWorkItemBinding:
    def test_ask_reports_workitem_bound_repo_not_first_requested_id(self, db: Session, monkeypatch, tmp_path):
        """The exact CMS-benchmark scenario: a WorkItem already bound to the
        second-added repo must keep reporting that repo in Context Used even
        when a later call's repository_ids lists the first-added repo first."""
        _env_offline(monkeypatch, tmp_path)
        p, r1, r2 = _seed_two_repos(db)
        svc = MentrixDeveloperService(db)

        first = svc.ask(question="first question", project_id=p.id, repository_id=r2.id, repository_ids=[r2.id])
        wi_id = first["work_item_id"]
        assert first["context_pack"]["repository_id"] == r2.id

        second = svc.ask(
            question="second question",
            work_item_id=wi_id,
            project_id=p.id,
            repository_id=r1.id,
            repository_ids=[r1.id, r2.id],
        )
        assert second["context_pack"]["repository_id"] == r2.id

    def test_plan_reports_workitem_bound_repo_not_first_requested_id(self, db: Session, monkeypatch, tmp_path):
        _env_offline(monkeypatch, tmp_path)
        p, r1, r2 = _seed_two_repos(db)
        svc = MentrixDeveloperService(db)

        first = svc.ask(question="seed", project_id=p.id, repository_id=r2.id, repository_ids=[r2.id])
        wi_id = first["work_item_id"]

        planned = svc.plan(
            goal="do the thing",
            work_item_id=wi_id,
            project_id=p.id,
            repository_id=r1.id,
            repository_ids=[r1.id, r2.id],
        )
        assert planned["context_pack"]["repository_id"] == r2.id

    def test_new_workitem_binds_to_requested_primary(self, db: Session, monkeypatch, tmp_path):
        """A brand-new WorkItem (no prior binding) takes whatever primary the
        first call names -- this is what a corrected frontend active-repo
        selection now seeds it with."""
        _env_offline(monkeypatch, tmp_path)
        p, r1, r2 = _seed_two_repos(db)
        svc = MentrixDeveloperService(db)

        result = svc.ask(question="hello", project_id=p.id, repository_id=r2.id, repository_ids=[r1.id, r2.id])
        assert result["context_pack"]["repository_id"] == r2.id


class TestMissionPrimaryRepository:
    def test_start_mission_records_explicit_primary(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
        root1 = tmp_path / "repo1"
        root2 = tmp_path / "repo2"
        root1.mkdir()
        root2.mkdir()
        mission = start_mission(
            goal="build something",
            roots=[
                {"id": 16, "label": "alpha", "path": str(root1)},
                {"id": 17, "label": "beta", "path": str(root2)},
            ],
            primary_repository_id=17,
        )
        assert mission["primary_repository_id"] == 17

    def test_start_mission_falls_back_to_first_root_without_explicit_primary(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
        root1 = tmp_path / "repo1"
        root1.mkdir()
        mission = start_mission(
            goal="build something",
            roots=[{"id": 16, "label": "alpha", "path": str(root1)}],
        )
        assert mission["primary_repository_id"] == 16

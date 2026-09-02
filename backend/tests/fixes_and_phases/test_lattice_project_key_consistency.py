"""One Lattice key for one repository, whoever is asking.

The Lattice indexes per repository root under derive_project_key(owner, repo)
-- the same key the frontend computes. But a Mission only ever knew its
repository_id and passed no project_key at all, so ProjectIntelligenceService
returned NOT_APPLICABLE and the Mission reported lattice_indexed=false against
a graph that was genuinely READY; and the Ask/Plan path derived its key from
the Project *display name*, looking up a graph that was never written. Same
repository, three different answers. That is finding F6 / section 1 item 12 of
ZECT_CMS_REAL_PROJECT_CODING_AGENT_GOLDEN_BENCHMARK_V1.md.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.lattice.indexer import derive_project_key, project_key_for_repository


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed(db: Session, owner: str = "acme", repo_name: str = "alpha") -> tuple[Project, Repo]:
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"Lattice Key Test {tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r = Repo(project_id=p.id, owner=owner, repo_name=repo_name, default_branch="main")
    db.add(r)
    db.commit()
    db.refresh(p)
    db.refresh(r)
    return p, r


class TestProjectKeyForRepository:
    def test_derives_the_same_key_the_lattice_indexed_under(self, db: Session):
        _, r = _seed(db, owner="Zinnia", repo_name="Campaign_Mgmt")
        assert project_key_for_repository(db, r.id) == derive_project_key("Zinnia", "Campaign_Mgmt")

    def test_accepts_a_string_repository_id(self, db: Session):
        _, r = _seed(db)
        assert project_key_for_repository(db, str(r.id)) == "acme-alpha"

    def test_two_repos_in_one_project_get_distinct_keys(self, db: Session):
        _, a = _seed(db, repo_name="alpha")
        _, b = _seed(db, repo_name="beta")
        assert project_key_for_repository(db, a.id) != project_key_for_repository(db, b.id)

    @pytest.mark.parametrize("bad", [None, "", "not-a-number", 0])
    def test_returns_empty_rather_than_raising_on_unusable_input(self, db: Session, bad):
        assert project_key_for_repository(db, bad) == ""

    def test_returns_empty_for_an_unknown_repository(self, db: Session):
        assert project_key_for_repository(db, 987654321) == ""

    def test_returns_empty_without_a_session(self):
        """Context assembly must never be blocked on this lookup."""
        assert project_key_for_repository(None, 1) == ""


class TestMissionContextPack:
    def test_derives_the_project_key_from_the_repository_alone(self, db: Session, monkeypatch):
        """A Mission passes repository_id and no project_key. Before the fix
        the snapshot was asked for project_key="" and answered
        NOT_APPLICABLE."""
        from app.services.coding_engine import agent_context

        _, r = _seed(db, owner="acme", repo_name="alpha")
        seen: dict[str, object] = {}

        class _Snap:
            knowledge: list = []
            memory: list = []
            lattice = {"status": "READY", "hits": [{"path": "a.py"}, {"path": "b.py"}]}
            blueprint = {"snippet": ""}

        class _PI:
            def snapshot(self, **kwargs):
                seen.update(kwargs)
                return _Snap()

        monkeypatch.setattr(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService",
            _PI,
        )

        meta = agent_context.compose_rich_agent_context_pack(
            goal="add a campaign parameter",
            repository_id=r.id,
            db=db,
        )

        assert seen.get("project_key") == "acme-alpha"
        assert meta["project_key"] == "acme-alpha"
        assert meta["lattice_indexed"] is True
        assert meta["lattice_state"] == "READY"
        assert meta["lattice_hits"] == 2

    def test_an_explicit_project_key_is_not_overridden(self, db: Session, monkeypatch):
        from app.services.coding_engine import agent_context

        _, r = _seed(db)
        seen: dict[str, object] = {}

        class _Snap:
            knowledge: list = []
            memory: list = []
            lattice = {"status": "READY", "hits": []}
            blueprint = {"snippet": ""}

        class _PI:
            def snapshot(self, **kwargs):
                seen.update(kwargs)
                return _Snap()

        monkeypatch.setattr(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService",
            _PI,
        )
        agent_context.compose_rich_agent_context_pack(
            goal="g", project_key="caller-supplied", repository_id=r.id, db=db
        )
        assert seen.get("project_key") == "caller-supplied"

    def test_reports_the_real_state_not_just_the_indexed_boolean(self, db: Session, monkeypatch):
        """INDEXING and STALE must not be rendered as NOT_INDEXED."""
        from app.services.coding_engine import agent_context

        _, r = _seed(db)

        class _Snap:
            knowledge: list = []
            memory: list = []
            lattice = {"status": "STALE", "hits": []}
            blueprint = {"snippet": ""}

        class _PI:
            def snapshot(self, **kwargs):
                return _Snap()

        monkeypatch.setattr(
            "app.services.work_items.project_intelligence.ProjectIntelligenceService",
            _PI,
        )
        meta = agent_context.compose_rich_agent_context_pack(goal="g", repository_id=r.id, db=db)
        assert meta["lattice_state"] == "STALE"
        assert meta["lattice_indexed"] is False

    def test_defaults_to_not_applicable_when_project_intelligence_is_unavailable(self):
        from app.services.coding_engine import agent_context

        meta = agent_context.compose_rich_agent_context_pack(goal="g")
        assert meta["lattice_state"] == "NOT_APPLICABLE"
        assert meta["lattice_indexed"] is False


class TestDeveloperServicePack:
    def test_prefers_the_repository_derived_key_over_the_project_name(self, db: Session, monkeypatch):
        """`Project.name` is a human label ("Lattice Key Test ab12cd34"), not
        the key any graph was written under."""
        from app.services.work_items.developer_service import MentrixDeveloperService

        p, r = _seed(db, owner="acme", repo_name="alpha")
        seen: dict[str, object] = {}
        svc = MentrixDeveloperService(db)

        class _Snap:
            knowledge: list = []
            memory: list = []
            lattice = {"status": "READY", "hits": []}
            blueprint = {"snippet": ""}
            related_work: list = []
            skill_selection: list = []
            playbook_selection: list = []
            freshness: dict = {}

            def to_dict(self):
                return {"lattice": self.lattice, "blueprint": self.blueprint}

        def _snapshot(**kwargs):
            seen.update(kwargs)
            return _Snap()

        monkeypatch.setattr(svc.pi, "snapshot", _snapshot)

        class _WI:
            id = 1
            project_id = p.id
            repository_id = r.id
            repository_ref = "main"
            base_commit_sha = ""
            created_by = ""

        svc._build_pack(_WI(), "goal")
        assert seen.get("project_key") == "acme-alpha"
        assert p.name not in str(seen.get("project_key"))

"""Phase C — Context Store persistence.

context_management.py used to hold context in a bare module-level dict,
global across every user and wiped on restart. This verifies the DB-backed
replacement (ContextStoreEntry) actually persists, upserts, and — the part
the old dict never did at all — isolates context per user_id.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register ContextStoreEntry
from app.core.auth.deps import CurrentUser
from app.database import Base
from app.routers.context_management import (
    LoadContextRequest,
    SaveContextRequest,
    clear_context,
    get_context_recommendations,
    list_pages_with_context,
    load_context,
    save_context,
)

USER_A = CurrentUser(user_id=1, username="a", email="a@zinnia.com", auth_mode="local", token="t1")
USER_B = CurrentUser(user_id=2, username="b", email="b@zinnia.com", auth_mode="local", token="t2")


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestSaveAndLoad:
    def test_save_then_load_roundtrips(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="tech_stack", value="fastapi+react"), db=db, user=USER_A)

        result = load_context(LoadContextRequest(page="build"), db=db, user=USER_A)

        assert len(result.entries) == 1
        assert result.entries[0].key == "tech_stack"
        assert result.entries[0].value == "fastapi+react"

    def test_save_upserts_existing_key(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="tech_stack", value="v1"), db=db, user=USER_A)
        save_context(SaveContextRequest(page="build", key="tech_stack", value="v2"), db=db, user=USER_A)

        result = load_context(LoadContextRequest(page="build"), db=db, user=USER_A)

        assert len(result.entries) == 1
        assert result.entries[0].value == "v2"

    def test_load_filters_by_requested_keys(self):
        db = _session()
        save_context(SaveContextRequest(page="plan", key="a", value="1"), db=db, user=USER_A)
        save_context(SaveContextRequest(page="plan", key="b", value="2"), db=db, user=USER_A)

        result = load_context(LoadContextRequest(page="plan", keys=["a"]), db=db, user=USER_A)

        assert len(result.entries) == 1
        assert result.entries[0].key == "a"

    def test_persists_across_separate_calls_unlike_old_in_memory_dict(self):
        db = _session()
        save_context(SaveContextRequest(page="ask", key="k", value="v" * 40), db=db, user=USER_A)
        result = load_context(LoadContextRequest(page="ask"), db=db, user=USER_A)
        assert result.total_tokens_estimated == 10  # 40 chars // 4


class TestUserIsolation:
    def test_users_do_not_see_each_others_context(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="secret", value="user-a-data"), db=db, user=USER_A)
        save_context(SaveContextRequest(page="build", key="secret", value="user-b-data"), db=db, user=USER_B)

        result_a = load_context(LoadContextRequest(page="build"), db=db, user=USER_A)
        result_b = load_context(LoadContextRequest(page="build"), db=db, user=USER_B)

        assert result_a.entries[0].value == "user-a-data"
        assert result_b.entries[0].value == "user-b-data"

    def test_anonymous_callers_share_the_none_bucket(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="k", value="anon"), db=db, user=None)

        result = load_context(LoadContextRequest(page="build"), db=db, user=None)
        result_a = load_context(LoadContextRequest(page="build"), db=db, user=USER_A)

        assert result.entries[0].value == "anon"
        assert result_a.entries == []


class TestClearAndList:
    def test_clear_removes_only_that_page(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="k", value="v"), db=db, user=USER_A)
        save_context(SaveContextRequest(page="plan", key="k", value="v"), db=db, user=USER_A)

        clear_context("build", db=db, user=USER_A)

        assert load_context(LoadContextRequest(page="build"), db=db, user=USER_A).entries == []
        assert len(load_context(LoadContextRequest(page="plan"), db=db, user=USER_A).entries) == 1

    def test_clear_does_not_affect_other_users(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="k", value="v"), db=db, user=USER_A)
        save_context(SaveContextRequest(page="build", key="k", value="v"), db=db, user=USER_B)

        clear_context("build", db=db, user=USER_A)

        assert load_context(LoadContextRequest(page="build"), db=db, user=USER_B).entries != []

    def test_list_pages_scoped_to_user(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="k1", value="v"), db=db, user=USER_A)
        save_context(SaveContextRequest(page="plan", key="k2", value="v"), db=db, user=USER_A)
        save_context(SaveContextRequest(page="build", key="k3", value="v"), db=db, user=USER_B)

        pages_a = {p["page"] for p in list_pages_with_context(db=db, user=USER_A)}

        assert pages_a == {"build", "plan"}


class TestRecommendations:
    def test_currently_loaded_reflects_persisted_keys(self):
        db = _session()
        save_context(SaveContextRequest(page="build", key="tech_stack", value="v"), db=db, user=USER_A)

        rec = get_context_recommendations("build", db=db, user=USER_A)

        assert "tech_stack" in rec["currently_loaded"]
        assert "coding_standards" in rec["recommended_keys"]

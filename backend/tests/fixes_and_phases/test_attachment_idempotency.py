"""CP-03 -- attachment persistence must be truly idempotent at the
service/data boundary (finding K1): same authorized scope + project/work
item + owner + content SHA resolves/reuses the existing content version
instead of attempting a second INSERT and hitting
uq_doc_content_version_identity. Concurrent duplicate uploads must be safe
too, and no raw SQL/constraint name/filesystem path may ever reach the
ASK/PLAN/AGENT UI.

Root cause (already fixed for PROJECT_SHARED before this PR): the reuse
lookup (find_reusable_content_version) was gated to `scope == PROJECT_SHARED`
only. USER_PRIVATE -- the scope essentially every ASK-composer upload
actually uses -- always fell through to an unconditional INSERT, colliding
on a second identical upload. Fixed by widening the reuse branch to apply to
every scope (owner_user_id already isolates USER_PRIVATE per-user, so this
cannot leak one user's content into another's), plus a bounded retry in
ingest_document() for the residual true-concurrency race the DB's own
unique index is the only thing that can catch with certainty.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.scopes import PROJECT_SHARED, USER_PRIVATE
from app.infrastructure.database import Base
from app.models import DocumentArtifact, DocumentContentVersion, User
from app.services.document_intelligence.service import (
    ingest_document,
    link_artifact_to_work_item,
    list_work_item_attachments,
    sha256_bytes,
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_DOCUMENT_ROOT", str(tmp_path / "docs"))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    u1 = User(email="u1@test.local", name="User One")
    session.add(u1)
    session.commit()
    yield session, u1, engine
    session.close()


class TestSameContentAttachedTwice:
    def test_same_md_attached_twice_reuses_content_version_no_crash(self, db):
        session, u1, _engine = db
        payload = b"# Campaign Management Requirement\n\nSame document."
        first = ingest_document(session, user_id=u1.id, filename="req.md", data=payload, scope=USER_PRIVATE)
        second = ingest_document(session, user_id=u1.id, filename="req.md", data=payload, scope=USER_PRIVATE)

        assert second["reused_shared_version"] is True
        assert first["content_version_id"] == second["content_version_id"]
        assert first["id"] != second["id"]  # each upload still gets its own artifact row
        versions = session.query(DocumentContentVersion).filter_by(content_sha256=first["content_sha256"]).all()
        assert len(versions) == 1

    def test_same_content_under_a_different_filename_still_dedupes(self, db):
        session, u1, _engine = db
        payload = b"identical bytes, different name"
        a1 = ingest_document(session, user_id=u1.id, filename="requirement-v1.md", data=payload, scope=USER_PRIVATE)
        a2 = ingest_document(session, user_id=u1.id, filename="requirement-renamed.md", data=payload, scope=USER_PRIVATE)

        assert a1["content_version_id"] == a2["content_version_id"]
        assert a2["reused_shared_version"] is True
        assert a1["filename"] == "requirement-v1.md"
        assert a2["filename"] == "requirement-renamed.md"
        versions = session.query(DocumentContentVersion).filter_by(content_sha256=a1["content_sha256"]).all()
        assert len(versions) == 1

    def test_reuse_also_applies_to_project_shared_scope(self, db):
        """The PROJECT_SHARED path already worked before this PR -- must
        stay working after widening the condition to include USER_PRIVATE."""
        session, u1, _engine = db
        payload = b"shared spec bytes"
        a1 = ingest_document(session, user_id=u1.id, filename="spec.md", data=payload, project_id=1, scope=PROJECT_SHARED)
        a2 = ingest_document(session, user_id=u1.id, filename="spec2.md", data=payload, project_id=1, scope=PROJECT_SHARED)
        assert a1["content_version_id"] == a2["content_version_id"]
        assert a2["reused_shared_version"] is True


class TestLegitimateNewVersion:
    def test_genuinely_different_content_gets_its_own_version(self, db):
        session, u1, _engine = db
        v1 = ingest_document(session, user_id=u1.id, filename="doc.md", data=b"version one text", scope=USER_PRIVATE)
        v2 = ingest_document(
            session,
            user_id=u1.id,
            filename="doc.md",
            data=b"version two text, materially different",
            scope=USER_PRIVATE,
            replace_artifact_id=v1["id"],
        )
        assert v1["content_version_id"] != v2["content_version_id"]
        assert v2["reused_shared_version"] is False
        # the old artifact is superseded, not silently duplicated
        old = session.query(DocumentArtifact).filter_by(id=v1["id"]).first()
        assert old.status == "SUPERSEDED"
        assert old.superseded_by_id == v2["id"]


class TestConcurrentDuplicateUpload:
    def test_ordinary_sequential_duplicate_needs_no_retry_at_all(self, db):
        """The common case (not a true race): a second upload arrives after
        the first already committed. The pre-check alone finds it -- no
        flush, no retry, just reuse. Establishes the baseline the two race
        tests below are contrasted against."""
        session, u1, _engine = db
        payload = b"racing upload bytes"
        winner = ingest_document(session, user_id=u1.id, filename="other-name.md", data=payload, scope=USER_PRIVATE)
        result = ingest_document(session, user_id=u1.id, filename="racer.md", data=payload, scope=USER_PRIVATE)
        assert result["content_version_id"] == winner["content_version_id"]
        assert result["reused_shared_version"] is True

    def test_flush_conflict_after_a_missed_precheck_retries_instead_of_crashing(self, db, monkeypatch):
        """Force find_reusable_content_version() to (falsely) report no
        existing row on the first call -- exactly what a true simultaneous
        race looks like from inside a single transaction -- so
        ingest_document() proceeds to a fresh INSERT, and force that flush
        to raise the real IntegrityError. It must roll back and retry
        rather than let the exception escape."""
        import app.services.document_intelligence.service as svc

        session, u1, _engine = db
        payload = b"true race bytes"
        winner = ingest_document(session, user_id=u1.id, filename="winner.md", data=payload, scope=USER_PRIVATE)

        real_lookup = svc.find_reusable_content_version
        state = {"calls": 0}

        def lookup_misses_once(db_, **kw):
            state["calls"] += 1
            if state["calls"] == 1:
                return None
            return real_lookup(db_, **kw)

        monkeypatch.setattr(svc, "find_reusable_content_version", lookup_misses_once)

        # Only the flush that actually has a pending new
        # DocumentContentVersion is the one this test cares about -- the
        # earlier `db.add(art); db.flush()` in ingest_document() must pass
        # through untouched, or this would fail the wrong insert entirely.
        real_flush = session.flush
        flush_state = {"failed_once": False}

        def flush_fails_once_for_content_version(*a, **kw):
            if not flush_state["failed_once"] and any(isinstance(o, DocumentContentVersion) for o in session.new):
                flush_state["failed_once"] = True
                raise IntegrityError("UNIQUE constraint failed: document_content_versions...", None, None)
            return real_flush(*a, **kw)

        monkeypatch.setattr(session, "flush", flush_fails_once_for_content_version)

        result = ingest_document(session, user_id=u1.id, filename="loser.md", data=payload, scope=USER_PRIVATE)
        assert result["content_version_id"] == winner["content_version_id"]
        assert result["reused_shared_version"] is True
        versions = session.query(DocumentContentVersion).filter_by(content_sha256=winner["content_sha256"]).all()
        assert len(versions) == 1

    def test_retries_are_bounded_and_reraise_the_real_exception_if_exhausted(self, db, monkeypatch):
        """A pathological, permanently-broken flush (not an ordinary
        transient race) must eventually surface as a real error rather than
        recursing forever."""
        import app.services.document_intelligence.service as svc

        session, u1, _engine = db
        payload = b"never resolves bytes"
        monkeypatch.setattr(svc, "find_reusable_content_version", lambda *a, **kw: None)

        def always_fails(*a, **kw):
            raise IntegrityError("UNIQUE constraint failed: document_content_versions...", None, None)

        monkeypatch.setattr(session, "flush", always_fails)

        with pytest.raises(IntegrityError):
            ingest_document(session, user_id=u1.id, filename="x.md", data=payload, scope=USER_PRIVATE)


class TestPersistenceAcrossSessions:
    def test_reuse_survives_a_fresh_session_against_the_same_engine(self, db):
        """A proxy for 'survives refresh/restart': a brand-new Session bound
        to the same (committed) engine state must still find and reuse the
        version, not just the original in-memory Session object."""
        session, u1, engine = db
        payload = b"persisted across a restart"
        first = ingest_document(session, user_id=u1.id, filename="a.md", data=payload, scope=USER_PRIVATE)
        u1_id = u1.id  # read before commit/close expires the detached instance
        session.commit()
        session.close()

        Session2 = sessionmaker(bind=engine)
        fresh = Session2()
        try:
            second = ingest_document(fresh, user_id=u1_id, filename="b.md", data=payload, scope=USER_PRIVATE)
            assert second["content_version_id"] == first["content_version_id"]
            assert second["reused_shared_version"] is True
        finally:
            fresh.close()


class TestAskPlanAgentAttachmentContinuity:
    def test_same_filename_reattached_by_plan_supersedes_cleanly_not_a_duplicate(self, db):
        """ASK attaches a requirement before a WorkItem id is known; PLAN
        re-attaches the identical file (same name, same bytes) once a
        WorkItem exists. This must not appear as two attachments cluttering
        the WorkItem, and must not re-parse/re-chunk the content -- the
        existing filename-supersede rule already retires the older row;
        CP-03 only has to guarantee the *content version* underneath is
        reused rather than re-inserted."""
        session, u1, _engine = db
        payload = b"# Campaign Management Module BRD\n\nSame requirement both times."

        ask_upload = ingest_document(session, user_id=u1.id, filename="brd.md", data=payload, scope=USER_PRIVATE)
        link_artifact_to_work_item(session, artifact_id=ask_upload["id"], user_id=u1.id, work_item_id=42)

        plan_reupload = ingest_document(session, user_id=u1.id, filename="brd.md", data=payload, scope=USER_PRIVATE)
        link_artifact_to_work_item(session, artifact_id=plan_reupload["id"], user_id=u1.id, work_item_id=42)

        assert plan_reupload["content_version_id"] == ask_upload["content_version_id"]
        versions = session.query(DocumentContentVersion).filter_by(content_sha256=ask_upload["content_sha256"]).all()
        assert len(versions) == 1  # no duplicate parse/chunk work happened

        attachments = list_work_item_attachments(session, work_item_id=42)
        assert [a["id"] for a in attachments] == [plan_reupload["id"]]  # exactly one current, clean view

    def test_same_content_attached_under_a_different_name_stays_multi_visible(self, db):
        """AGENT (or a later ASK turn) attaches the same requirement bytes
        under a different filename -- e.g. a renamed export. Because the
        filenames differ, the older artifact is not superseded; both remain
        visible for the WorkItem, and both still share one content version
        underneath (no duplicate parse)."""
        session, u1, _engine = db
        payload = b"# Campaign Management Module BRD\n\nSame requirement, exported twice."

        ask_upload = ingest_document(session, user_id=u1.id, filename="brd.md", data=payload, scope=USER_PRIVATE)
        link_artifact_to_work_item(session, artifact_id=ask_upload["id"], user_id=u1.id, work_item_id=99)

        agent_upload = ingest_document(session, user_id=u1.id, filename="brd-export.md", data=payload, scope=USER_PRIVATE)
        link_artifact_to_work_item(session, artifact_id=agent_upload["id"], user_id=u1.id, work_item_id=99)

        assert agent_upload["content_version_id"] == ask_upload["content_version_id"]
        attachments = list_work_item_attachments(session, work_item_id=99)
        ids = {a["id"] for a in attachments}
        assert {ask_upload["id"], agent_upload["id"]} == ids
        versions = {a["content_version_id"] for a in attachments}
        assert versions == {ask_upload["content_version_id"]}

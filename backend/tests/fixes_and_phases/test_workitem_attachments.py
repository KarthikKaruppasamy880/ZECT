"""An attachment made in ASK belongs to the WorkItem, not to one composer.

Before this, every pane's `useComposerAttachments()` instance was fully
isolated and self-resetting -- an ASK attachment survived only inside the
one `ask_turn.question` text it was flattened into. Navigating to PLAN or
AGENT showed no trace that anything had been attached at all, and there was
no way to reuse it without re-uploading. `DocumentArtifact` now carries a
`work_item_id` link and a `kind` ("document" | "image"), and images -- never
durably stored before -- persist through the same table via a
parse-free ingest path. See section 1 item 2 of
ZECT_CMS_REAL_PROJECT_CODING_AGENT_GOLDEN_BENCHMARK_V1.md /
ZECT_DEVELOPER_V4_1_LIVE_AGENT_ACTIVITY_SKILLS_CONTEXT_ADDENDUM.md.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database import Base
from app.models import DocumentArtifact, User, WorkItem
from app.services.document_intelligence.service import (
    ingest_document,
    ingest_image,
    link_artifact_to_work_item,
    list_work_item_attachments,
    read_image_data_url,
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_DOCUMENT_ROOT", str(tmp_path / "docs"))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    u1 = User(email="u1@test.local", name="User One")
    u2 = User(email="u2@test.local", name="User Two")
    session.add_all([u1, u2])
    session.commit()
    wi = WorkItem(title="Campaign approval routing", source="user")
    session.add(wi)
    session.commit()
    yield session, u1, u2, wi
    session.close()


class TestImageIngest:
    def test_stores_raw_bytes_and_reads_them_back(self, db):
        session, u1, _u2, wi = db
        out = ingest_image(
            session,
            user_id=u1.id,
            filename="screenshot.png",
            data=b"\x89PNG\r\n\x1a\nfakebytes",
            mime_type="image/png",
            work_item_id=wi.id,
        )
        assert out["kind"] == "image"
        assert out["work_item_id"] == wi.id

        raw = read_image_data_url(session, artifact_id=out["id"], user_id=u1.id)
        assert raw["data_url"].startswith("data:image/png;base64,")
        assert raw["mime_type"] == "image/png"

    def test_rejects_an_unsupported_extension(self, db):
        session, u1, _u2, _wi = db
        with pytest.raises(ValueError, match="unsupported_image_format"):
            ingest_image(session, user_id=u1.id, filename="malware.exe", data=b"x", mime_type="")

    def test_another_user_cannot_read_the_image(self, db):
        session, u1, u2, _wi = db
        out = ingest_image(session, user_id=u1.id, filename="s.png", data=b"abc", mime_type="image/png")
        with pytest.raises(ValueError, match="image_not_found"):
            read_image_data_url(session, artifact_id=out["id"], user_id=u2.id)

    def test_a_document_artifact_is_not_readable_as_an_image(self, db, tmp_path):
        session, u1, _u2, _wi = db
        doc = ingest_document(session, user_id=u1.id, filename="notes.md", data=b"# hi")
        with pytest.raises(ValueError, match="image_not_found"):
            read_image_data_url(session, artifact_id=doc["id"], user_id=u1.id)


class TestLinkToWorkItem:
    def test_links_a_document_uploaded_before_the_work_item_existed(self, db):
        session, u1, _u2, wi = db
        doc = ingest_document(session, user_id=u1.id, filename="brd.md", data=b"# Requirement")
        assert doc["work_item_id"] is None

        linked = link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=wi.id)
        assert linked["work_item_id"] == wi.id

    def test_relinking_to_the_same_work_item_is_a_noop(self, db):
        session, u1, _u2, wi = db
        doc = ingest_document(session, user_id=u1.id, filename="brd.md", data=b"# Requirement")
        link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=wi.id)
        again = link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=wi.id)
        assert again["work_item_id"] == wi.id

    def test_cannot_relink_to_a_different_work_item(self, db):
        session, u1, _u2, wi = db
        other = WorkItem(title="Other", source="user")
        session.add(other)
        session.commit()
        doc = ingest_document(session, user_id=u1.id, filename="brd.md", data=b"# Requirement")
        link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=wi.id)
        with pytest.raises(ValueError, match="already_linked_to_another_work_item"):
            link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=other.id)

    def test_cannot_link_another_users_document(self, db):
        session, u1, u2, wi = db
        doc = ingest_document(session, user_id=u1.id, filename="brd.md", data=b"# Requirement")
        with pytest.raises(ValueError, match="document_not_found"):
            link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u2.id, work_item_id=wi.id)


class TestListWorkItemAttachments:
    def test_lists_documents_and_images_together_in_upload_order(self, db):
        session, u1, _u2, wi = db
        doc = ingest_document(session, user_id=u1.id, filename="brd.md", data=b"# Requirement")
        link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=wi.id)
        img = ingest_image(
            session, user_id=u1.id, filename="s.png", data=b"abc", mime_type="image/png", work_item_id=wi.id
        )

        attachments = list_work_item_attachments(session, work_item_id=wi.id)
        assert [a["id"] for a in attachments] == [doc["id"], img["id"]]
        assert [a["kind"] for a in attachments] == ["document", "image"]

    def test_a_second_work_item_sees_none_of_the_firsts_attachments(self, db):
        session, u1, _u2, wi = db
        other = WorkItem(title="Unrelated", source="user")
        session.add(other)
        session.commit()
        doc = ingest_document(session, user_id=u1.id, filename="brd.md", data=b"# Requirement")
        link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=wi.id)

        assert list_work_item_attachments(session, work_item_id=other.id) == []

    def test_empty_before_anything_is_attached(self, db):
        session, _u1, _u2, wi = db
        assert list_work_item_attachments(session, work_item_id=wi.id) == []

    def test_a_superseded_document_drops_out_of_the_list(self, db):
        session, u1, _u2, wi = db
        doc = ingest_document(session, user_id=u1.id, filename="brd.md", data=b"# v1")
        link_artifact_to_work_item(session, artifact_id=doc["id"], user_id=u1.id, work_item_id=wi.id)
        replacement = ingest_document(
            session, user_id=u1.id, filename="brd.md", data=b"# v2", replace_artifact_id=doc["id"]
        )
        link_artifact_to_work_item(session, artifact_id=replacement["id"], user_id=u1.id, work_item_id=wi.id)

        attachments = list_work_item_attachments(session, work_item_id=wi.id)
        assert [a["id"] for a in attachments] == [replacement["id"]]

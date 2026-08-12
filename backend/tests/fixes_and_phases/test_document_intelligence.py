"""Document Intelligence — SHA-256 versioning, scope isolation, freshness gates."""

from __future__ import annotations

import io
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database import Base
from app.models import DocumentArtifact, DocumentChunk, DocumentContentVersion, User
from app.services.document_intelligence.service import (
    ingest_document,
    parse_document,
    retrieve_document_context,
    sha256_bytes,
)
from app.services.work_items.context_engine import MentrixContextEngine, ProvenanceItem
from app.core.scopes import PROJECT_SHARED, USER_PRIVATE


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
    yield session, u1, u2
    session.close()


def _minimal_docx(text: str = "Hello DOCX") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        zf.writestr(
            "word/document.xml",
            f'<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>",
        )
    return buf.getvalue()


def test_parse_txt_and_docx():
    pr = parse_document("notes.md", b"# Title\n\nBody alpha", "text/markdown")
    assert "Title" in pr.markdown
    pr2 = parse_document("a.docx", _minimal_docx("DocxBody"), "")
    assert "DocxBody" in pr2.markdown
    assert "table_formula_completeness" in pr2.partial


def test_project_shared_reuses_content_version(db):
    session, u1, u2 = db
    payload = b"# Spec\n\nShared design doc about auth."
    a1 = ingest_document(
        session,
        user_id=u1.id,
        filename="spec.md",
        data=payload,
        project_id=1,
        scope=PROJECT_SHARED,
    )
    a2 = ingest_document(
        session,
        user_id=u2.id,
        filename="spec-copy.md",
        data=payload,
        project_id=1,
        scope=PROJECT_SHARED,
    )
    assert a1["content_sha256"] == a2["content_sha256"] == sha256_bytes(payload)
    assert a1["content_version_id"] == a2["content_version_id"]
    assert a2["reused_shared_version"] is True
    versions = session.query(DocumentContentVersion).filter_by(content_sha256=a1["content_sha256"]).all()
    assert len(versions) == 1


def test_user_private_isolated_even_same_hash(db):
    session, u1, u2 = db
    payload = b"private note same bytes"
    a1 = ingest_document(session, user_id=u1.id, filename="p.md", data=payload, scope=USER_PRIVATE)
    a2 = ingest_document(session, user_id=u2.id, filename="p.md", data=payload, scope=USER_PRIVATE)
    assert a1["content_sha256"] == a2["content_sha256"]
    assert a1["content_version_id"] != a2["content_version_id"]
    assert a2["reused_shared_version"] is False
    # u1 cannot retrieve u2 private via retrieve with u1
    items, _ = retrieve_document_context(session, user_id=u1.id, query="private", artifact_ids=[a2["id"]])
    assert items == []


def test_stale_chunks_excluded_from_context_pack(db):
    session, u1, _u2 = db
    v1 = ingest_document(session, user_id=u1.id, filename="x.md", data=b"version one alpha", scope=USER_PRIVATE)
    v2 = ingest_document(
        session,
        user_id=u1.id,
        filename="x.md",
        data=b"version two beta unique",
        scope=USER_PRIVATE,
        replace_artifact_id=v1["id"],
    )
    old = session.query(DocumentArtifact).filter_by(id=v1["id"]).first()
    assert old.is_current is False
    stale = session.query(DocumentChunk).filter_by(document_artifact_id=v1["id"]).all()
    assert stale and all(c.freshness == "stale" for c in stale)

    items, meta = retrieve_document_context(session, user_id=u1.id, query="beta", artifact_ids=[v1["id"], v2["id"]])
    assert all(i.freshness == "current" for i in items)
    assert all(m["document_artifact_id"] == v2["id"] for m in meta["chunks"])
    assert all(m["content_sha256"] == v2["content_sha256"] for m in meta["chunks"])

    pack = MentrixContextEngine(token_budget=4000).build(
        goal="q",
        extra_items=items
        + [
            ProvenanceItem(
                source_type="document",
                source_id="stale-fake",
                content="should not appear",
                freshness="stale",
                commit_sha="deadbeef",
            )
        ],
    )
    assert all(i.freshness != "stale" for i in pack.items)
    assert not any("should not appear" in i.content for i in pack.items)
    assert any(i.source_type == "document" for i in pack.items)


def test_chunk_provenance_fields(db):
    session, u1, _ = db
    out = ingest_document(
        session,
        user_id=u1.id,
        filename="slides.md",
        data=b"## Page 1\n\nIntro\n\n## Page 2\n\nDetails about lattice",
        scope=USER_PRIVATE,
    )
    chunks = session.query(DocumentChunk).filter_by(document_artifact_id=out["id"]).all()
    assert chunks
    for c in chunks:
        assert c.content_sha256 == out["content_sha256"]
        assert c.content_version_id == out["content_version_id"]
        assert c.freshness == "current"
        assert c.document_artifact_id == out["id"]


def test_pdf_partial_capability_honest():
    pr = parse_document("scan.pdf", b"%PDF-1.4 fake", "application/pdf")
    assert "ocr_scanned_pdf" in pr.partial or pr.parser_name in ("pdf_stub", "pypdf_text", "PyPDF2_text")


def test_documents_api_upload_list_retrieve(authed_client, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_DOCUMENT_ROOT", str(tmp_path / "docs-api"))
    files = {"file": ("note.md", b"# API Doc\n\nlattice context", "text/markdown")}
    data = {"scope": "USER_PRIVATE", "sensitivity": "INTERNAL"}
    r = authed_client.post("/api/documents/upload", files=files, data=data)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    art_id = body["artifact"]["id"]
    assert body["artifact"]["content_sha256"]

    listed = authed_client.get("/api/documents")
    assert listed.status_code == 200
    assert any(d["id"] == art_id for d in listed.json()["documents"])

    md = authed_client.get(f"/api/documents/{art_id}/markdown")
    assert md.status_code == 200
    assert md.json()["freshness"] == "current"
    assert "API Doc" in md.json()["markdown"]

    ret = authed_client.post(
        "/api/documents/retrieve",
        json={"query": "lattice", "artifact_ids": [art_id], "build_context_pack": True},
    )
    assert ret.status_code == 200, ret.text
    payload = ret.json()
    assert payload["ok"] is True
    assert payload["items"]
    assert all(i.get("freshness") == "current" for i in payload["items"])
    pack_items = (payload.get("context_pack") or {}).get("items") or []
    assert not any(i.get("freshness") == "stale" for i in pack_items)

    # Cleanup so shared test DB does not pollute companion empty-context tests.
    authed_client.delete(f"/api/documents/{art_id}")


def test_project_shared_requires_project_id_for_retrieve(db):
    session, u1, u2 = db
    payload = b"# Shared\n\nsecret project material"
    a1 = ingest_document(
        session,
        user_id=u1.id,
        filename="shared.md",
        data=payload,
        project_id=42,
        scope=PROJECT_SHARED,
    )
    # Unscoped retrieve must not leak PROJECT_SHARED
    items_none, _ = retrieve_document_context(session, user_id=u2.id, query="secret", project_id=None)
    assert all(
        not (getattr(i, "commit_sha", None) == a1["content_sha256"]) for i in items_none
    ) or items_none == []
    items_wrong, _ = retrieve_document_context(session, user_id=u2.id, query="secret", project_id=99)
    assert items_wrong == []
    items_ok, meta = retrieve_document_context(session, user_id=u2.id, query="secret", project_id=42)
    assert items_ok
    assert all(m["document_artifact_id"] == a1["id"] for m in meta["chunks"])

"""Document Intelligence — parsers, versioning, Knowledge/ContextEngine bridge.

No second RAG/vector/memory system. OCR/XLSX/image-layout remain honestly PARTIAL.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session

from app.core.scopes import PROJECT_SHARED, USER_PRIVATE
from app.models import DocumentArtifact, DocumentChunk, DocumentContentVersion, KnowledgeEntry
from app.services.mentrix.untrusted_content import sanitize_for_prompt, tag_untrusted
from app.services.work_items.context_engine import ProvenanceItem

PARSER_VERSION = "di-1.0.0"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# Plain-text-shaped formats decode straight to UTF-8 text like .txt/.md
# already did -- the Developer composer's @file-attachment picker needs to
# accept source/config/log files, not just prose documents.
_PLAIN_TEXT_EXT = {
    ".txt", ".md", ".markdown", ".json", ".yaml", ".yml", ".log", ".xml",
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".sql", ".sh", ".ps1",
}
ALLOWED_EXT = _PLAIN_TEXT_EXT | {".docx", ".pdf", ".pptx"}
PARTIAL_CAPS = ("ocr_scanned_pdf", "xlsx", "image_layout", "table_formula_completeness")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def documents_root() -> Path:
    base = Path(os.getenv("ZECT_DOCUMENT_ROOT") or (_repo_root() / ".zect" / "documents"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


@dataclass
class ParseResult:
    markdown: str
    structured: dict[str, Any]
    pages: int = 0
    partial: list[str] = field(default_factory=list)
    parser_name: str = "text"


def parse_document(filename: str, data: bytes, mime_type: str = "") -> ParseResult:
    ext = Path(filename).suffix.lower()
    if ext in _PLAIN_TEXT_EXT:
        text = data.decode("utf-8", errors="replace")
        return ParseResult(
            markdown=text,
            structured={"type": "text", "chars": len(text)},
            pages=1,
            parser_name="text_utf8",
        )
    if ext == ".docx":
        return _parse_docx(data)
    if ext == ".pptx":
        return _parse_pptx(data)
    if ext == ".pdf":
        return _parse_pdf(data)
    raise ValueError(f"unsupported_format:{ext or mime_type}")


def _parse_docx(data: bytes) -> ParseResult:
    parts: list[str] = []
    import io

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Basic zip-bomb guard: reject oversized uncompressed members.
        total_uncompressed = 0
        for info in zf.infolist():
            total_uncompressed += max(0, int(info.file_size or 0))
            if info.file_size > MAX_UPLOAD_BYTES or total_uncompressed > MAX_UPLOAD_BYTES * 4:
                raise ValueError("docx_too_large_or_suspicious")
        try:
            xml = zf.read("word/document.xml")
        except KeyError as e:
            raise ValueError("invalid_docx") from e
        if len(xml) > MAX_UPLOAD_BYTES:
            raise ValueError("docx_document_xml_too_large")
        root = ET.fromstring(xml)
        for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
            t = (node.text or "").strip()
            if t:
                parts.append(t)
    text = "\n\n".join(parts)
    return ParseResult(
        markdown=text,
        structured={"type": "docx", "paragraphs": len(parts)},
        pages=max(1, len(parts) // 40),
        parser_name="docx_ooxml",
        partial=["table_formula_completeness"],
    )


def _parse_pptx(data: bytes) -> ParseResult:
    from app.services.pptx_parse import parse_pptx_bytes

    slides = parse_pptx_bytes(data)
    md_parts = []
    for s in slides:
        idx = s.get("index", 0)
        body = (s.get("text") or "").strip()
        notes = (s.get("notes") or "").strip()
        block = f"## Slide {idx}\n\n{body}"
        if notes:
            block += f"\n\n*Notes:* {notes}"
        md_parts.append(block)
    return ParseResult(
        markdown="\n\n".join(md_parts),
        structured={"type": "pptx", "slides": slides},
        pages=len(slides),
        parser_name="pptx_ooxml",
    )


def _parse_pdf(data: bytes) -> ParseResult:
    text = ""
    parser = "pdf_unavailable"
    partial = list(PARTIAL_CAPS)
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(__import__("io").BytesIO(data))
        pages_txt = []
        for i, page in enumerate(reader.pages):
            try:
                pages_txt.append(page.extract_text() or "")
            except Exception:
                pages_txt.append("")
        text = "\n\n".join(f"## Page {i + 1}\n\n{t}" for i, t in enumerate(pages_txt) if t.strip())
        parser = "pypdf_text"
        partial = ["ocr_scanned_pdf", "image_layout", "table_formula_completeness"]
        if not text.strip():
            partial = list(PARTIAL_CAPS)
            text = "(No extractable text — scanned PDF OCR not available in this build.)"
        return ParseResult(
            markdown=text,
            structured={"type": "pdf", "pages": len(pages_txt), "text_extractable": bool(text.strip())},
            pages=len(pages_txt),
            parser_name=parser,
            partial=partial,
        )
    except ImportError:
        pass
    try:
        from PyPDF2 import PdfReader as LegacyReader  # type: ignore

        reader = LegacyReader(__import__("io").BytesIO(data))
        pages_txt = [(p.extract_text() or "") for p in reader.pages]
        text = "\n\n".join(f"## Page {i + 1}\n\n{t}" for i, t in enumerate(pages_txt) if t.strip())
        return ParseResult(
            markdown=text or "(No extractable text — OCR not available.)",
            structured={"type": "pdf", "pages": len(pages_txt)},
            pages=len(pages_txt),
            parser_name="PyPDF2_text",
            partial=list(PARTIAL_CAPS),
        )
    except ImportError:
        return ParseResult(
            markdown="(PDF text extraction library not installed — OCR/scanned PDF PARTIAL.)",
            structured={"type": "pdf", "error": "pdf_library_missing"},
            pages=0,
            parser_name="pdf_stub",
            partial=list(PARTIAL_CAPS),
        )


def chunk_markdown(markdown: str, *, max_chars: int = 1200) -> list[dict[str, Any]]:
    """Heading-aware chunking — no vector index."""
    blocks = re.split(r"(?=^#{1,3}\s)", markdown, flags=re.M) if markdown.strip() else [markdown]
    chunks: list[dict[str, Any]] = []
    offset = 0
    heading = ""
    page = None
    slide = None
    for block in blocks:
        if not block.strip():
            offset += len(block)
            continue
        hm = re.match(r"^(#{1,3})\s+(.+)$", block.strip().splitlines()[0] if block.strip() else "")
        if hm:
            heading = hm.group(2).strip()
            if heading.lower().startswith("page "):
                try:
                    page = int(heading.split()[1])
                except Exception:
                    page = page
            if heading.lower().startswith("slide "):
                try:
                    slide = int(heading.split()[1])
                except Exception:
                    slide = slide
        # split large blocks
        start = 0
        while start < len(block):
            piece = block[start : start + max_chars]
            if not piece.strip():
                start += max_chars
                continue
            chunks.append(
                {
                    "text": piece.strip(),
                    "heading_path": heading,
                    "source_offset": offset + start,
                    "page": page,
                    "slide": slide,
                    "token_count": _est_tokens(piece),
                    "chunk_hash": sha256_bytes(piece.encode("utf-8")),
                }
            )
            start += max_chars
        offset += len(block)
    if not chunks and markdown.strip():
        chunks.append(
            {
                "text": markdown[:max_chars],
                "heading_path": "",
                "source_offset": 0,
                "page": None,
                "slide": None,
                "token_count": _est_tokens(markdown),
                "chunk_hash": sha256_bytes(markdown.encode("utf-8")),
            }
        )
    return chunks


def _version_owner_key(scope: str, user_id: int) -> int:
    """USER_PRIVATE versions are owner-keyed; PROJECT_SHARED uses owner_user_id=0 sentinel."""
    if scope == PROJECT_SHARED:
        return 0
    return int(user_id)


def find_reusable_content_version(
    db: Session,
    *,
    scope: str,
    project_id: int | None,
    user_id: int,
    content_sha256: str,
) -> DocumentContentVersion | None:
    owner = _version_owner_key(scope, user_id)
    q = db.query(DocumentContentVersion).filter(
        DocumentContentVersion.content_sha256 == content_sha256,
        DocumentContentVersion.scope == scope,
        DocumentContentVersion.owner_user_id == owner,
        DocumentContentVersion.project_id == project_id,
    )
    return q.first()


def ingest_document(
    db: Session,
    *,
    user_id: int,
    filename: str,
    data: bytes,
    project_id: int | None = None,
    scope: str = USER_PRIVATE,
    mime_type: str = "",
    sensitivity: str = "INTERNAL",
    replace_artifact_id: int | None = None,
    work_item_id: int | None = None,
) -> dict[str, Any]:
    if user_id is None:
        raise ValueError("user_required")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("file_too_large")
    scope = (scope or USER_PRIVATE).upper()
    if scope not in (USER_PRIVATE, PROJECT_SHARED):
        scope = USER_PRIVATE
    if scope == PROJECT_SHARED and project_id is None:
        raise ValueError("project_required_for_project_shared")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"unsupported_format:{ext}")

    content_sha = sha256_bytes(data)
    reused = False
    cv = find_reusable_content_version(
        db, scope=scope, project_id=project_id, user_id=user_id, content_sha256=content_sha
    )

    art = DocumentArtifact(
        user_id=user_id,
        project_id=project_id,
        scope=scope,
        filename=filename[:500],
        mime_type=mime_type or ext,
        content_sha256=content_sha,
        sensitivity=sensitivity,
        status="PARSING",
        is_current=True,
        bytes_size=len(data),
        kind="document",
        work_item_id=work_item_id,
    )
    db.add(art)
    db.flush()

    # Collect priors to supersede only after successful READY (never on parse ERROR).
    to_supersede: list[DocumentArtifact] = []
    if replace_artifact_id:
        old = (
            db.query(DocumentArtifact)
            .filter(
                DocumentArtifact.id == replace_artifact_id,
                DocumentArtifact.user_id == user_id,
                DocumentArtifact.scope == scope,
            )
            .first()
        )
        if old and old.id != art.id:
            to_supersede.append(old)

    prior_same = (
        db.query(DocumentArtifact)
        .filter(
            DocumentArtifact.user_id == user_id,
            DocumentArtifact.project_id == project_id,
            DocumentArtifact.scope == scope,
            DocumentArtifact.filename == filename[:500],
            DocumentArtifact.is_current == True,  # noqa: E712
            DocumentArtifact.id != art.id,
        )
        .all()
    )
    for old in prior_same:
        if old.id not in {a.id for a in to_supersede}:
            to_supersede.append(old)

    def _apply_supersede() -> None:
        for old in to_supersede:
            old.is_current = False
            old.status = "SUPERSEDED"
            old.superseded_by_id = art.id
            db.query(DocumentChunk).filter(DocumentChunk.document_artifact_id == old.id).update(
                {"freshness": "stale"}
            )

    root = documents_root() / f"u{user_id}" / f"a{art.id}"
    root.mkdir(parents=True, exist_ok=True)

    if cv and scope == PROJECT_SHARED:
        reused = True
        art.content_version_id = cv.id
        art.status = "READY"
        # Clone current chunks referencing shared version onto this artifact (fresh)
        shared_chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.content_version_id == cv.id,
                DocumentChunk.freshness == "current",
            )
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(500)
            .all()
        )
        # Dedupe by chunk_index (one set of content-version chunks)
        seen_idx: set[int] = set()
        unique_chunks = []
        for ch in shared_chunks:
            if ch.chunk_index in seen_idx:
                continue
            seen_idx.add(ch.chunk_index)
            unique_chunks.append(ch)
        # If prior artifact chunks were all marked stale, rebuild from stored markdown
        # (never silently attach empty/stale provenance).
        if not unique_chunks and cv.markdown_path and Path(cv.markdown_path).is_file():
            md = Path(cv.markdown_path).read_text(encoding="utf-8", errors="replace")
            for i, ch in enumerate(chunk_markdown(md)):
                unique_chunks.append(
                    type(
                        "Tmp",
                        (),
                        {
                            "page": ch.get("page"),
                            "slide": ch.get("slide"),
                            "sheet": "",
                            "heading_path": ch.get("heading_path") or "",
                            "source_offset": ch.get("source_offset") or 0,
                            "token_count": ch.get("token_count") or 0,
                            "chunk_hash": ch.get("chunk_hash") or "",
                            "text": ch.get("text") or "",
                        },
                    )()
                )
        if not unique_chunks:
            # Cannot safely reuse — re-parse below (new content version identity still same sha;
            # unique constraint may hit; delete orphan art path by reusing found cv after reparse attempt).
            # Prefer re-chunk from markdown if possible already handled; otherwise leave reuse and parse.
            reused = False
            # Keep cv for identity; fall through only if we clear content_version and reparse bytes.
            # Write original bytes then rebuild chunks under existing cv.
            orig = root / "original.bin"
            orig.write_bytes(data)
            if cv.markdown_path and Path(cv.markdown_path).is_file():
                md = Path(cv.markdown_path).read_text(encoding="utf-8", errors="replace")
            else:
                parsed = parse_document(filename, data, mime_type)
                md = parsed.markdown
                md_path = root / "document.md"
                md_path.write_text(md, encoding="utf-8")
                cv.markdown_path = str(md_path)
            source_map = []
            for i, ch in enumerate(chunk_markdown(md)):
                nc = DocumentChunk(
                    document_artifact_id=art.id,
                    content_version_id=cv.id,
                    content_sha256=content_sha,
                    chunk_index=i,
                    page=ch.get("page"),
                    slide=ch.get("slide"),
                    sheet="",
                    heading_path=ch.get("heading_path") or "",
                    source_offset=int(ch.get("source_offset") or 0),
                    token_count=int(ch.get("token_count") or 0),
                    chunk_hash=ch.get("chunk_hash") or "",
                    text=ch.get("text") or "",
                    sensitivity=sensitivity,
                    freshness="current",
                )
                db.add(nc)
                source_map.append(
                    {
                        "chunk_index": i,
                        "document_artifact_id": art.id,
                        "content_version_id": cv.id,
                        "content_sha256": content_sha,
                        "page": ch.get("page"),
                        "slide": ch.get("slide"),
                        "heading_path": ch.get("heading_path"),
                        "source_offset": ch.get("source_offset"),
                        "chunk_hash": ch.get("chunk_hash"),
                        "freshness": "current",
                    }
                )
            art.source_map_json = json.dumps(source_map)
            art.status = "READY"
            _apply_supersede()
            _index_knowledge(db, art, cv)
            db.commit()
            db.refresh(art)
            return serialize_artifact(art, reused=True, content_version=cv)
        source_map = []
        for i, ch in enumerate(unique_chunks):
            nc = DocumentChunk(
                document_artifact_id=art.id,
                content_version_id=cv.id,
                content_sha256=content_sha,
                chunk_index=i,
                page=ch.page,
                slide=ch.slide,
                sheet=getattr(ch, "sheet", "") or "",
                heading_path=ch.heading_path or "",
                source_offset=ch.source_offset or 0,
                token_count=ch.token_count or 0,
                chunk_hash=ch.chunk_hash or "",
                text=ch.text or "",
                sensitivity=sensitivity,
                freshness="current",
            )
            db.add(nc)
            source_map.append(
                {
                    "chunk_index": i,
                    "document_artifact_id": art.id,
                    "content_version_id": cv.id,
                    "content_sha256": content_sha,
                    "page": ch.page,
                    "slide": ch.slide,
                    "heading_path": ch.heading_path,
                    "source_offset": ch.source_offset,
                    "chunk_hash": ch.chunk_hash,
                    "freshness": "current",
                }
            )
        art.source_map_json = json.dumps(source_map)
        art.status = "READY"
        _apply_supersede()
        _index_knowledge(db, art, cv)
        db.commit()
        db.refresh(art)
        return serialize_artifact(art, reused=reused, content_version=cv)

    # Parse fresh (USER_PRIVATE always; PROJECT_SHARED cache miss)
    try:
        parsed = parse_document(filename, data, mime_type)
    except Exception as e:
        art.status = "ERROR"
        art.is_current = False
        art.error_message = str(e)[:500]
        db.commit()
        db.refresh(art)
        return serialize_artifact(art, reused=False)

    orig = root / "original.bin"
    orig.write_bytes(data)
    md_path = root / "document.md"
    md_path.write_text(parsed.markdown, encoding="utf-8")
    js_path = root / "document.json"
    js_path.write_text(json.dumps(parsed.structured, indent=2, default=str), encoding="utf-8")

    cv = DocumentContentVersion(
        content_sha256=content_sha,
        scope=scope,
        project_id=project_id,
        owner_user_id=_version_owner_key(scope, user_id),
        parser_name=parsed.parser_name,
        parser_version=PARSER_VERSION,
        mime_type=mime_type or ext,
        page_count=parsed.pages,
        markdown_path=str(md_path),
        json_path=str(js_path),
        original_path=str(orig),
        partial_capabilities=list(dict.fromkeys(list(parsed.partial) + (["xlsx"] if "xlsx" in PARTIAL_CAPS else []))),
    )
    db.add(cv)
    db.flush()
    art.content_version_id = cv.id

    chunks = chunk_markdown(parsed.markdown)
    source_map = []
    for i, ch in enumerate(chunks):
        row = DocumentChunk(
            document_artifact_id=art.id,
            content_version_id=cv.id,
            content_sha256=content_sha,
            chunk_index=i,
            page=ch.get("page"),
            slide=ch.get("slide"),
            heading_path=ch.get("heading_path") or "",
            source_offset=int(ch.get("source_offset") or 0),
            token_count=int(ch.get("token_count") or 0),
            chunk_hash=ch.get("chunk_hash") or "",
            text=ch.get("text") or "",
            sensitivity=sensitivity,
            freshness="current",
        )
        db.add(row)
        source_map.append(
            {
                "chunk_index": i,
                "document_artifact_id": art.id,
                "content_version_id": cv.id,
                "content_sha256": content_sha,
                "page": ch.get("page"),
                "slide": ch.get("slide"),
                "heading_path": ch.get("heading_path"),
                "source_offset": ch.get("source_offset"),
                "chunk_hash": ch.get("chunk_hash"),
                "freshness": "current",
            }
        )
    art.source_map_json = json.dumps(source_map)
    art.status = "READY"
    _apply_supersede()
    _index_knowledge(db, art, cv)
    db.commit()
    db.refresh(art)
    return serialize_artifact(art, reused=False, content_version=cv)


def _index_knowledge(db: Session, art: DocumentArtifact, cv: DocumentContentVersion) -> None:
    md = ""
    if cv.markdown_path and Path(cv.markdown_path).is_file():
        md = Path(cv.markdown_path).read_text(encoding="utf-8", errors="replace")[:8000]
    entry = KnowledgeEntry(
        user_id=art.user_id if art.scope == USER_PRIVATE else None,
        project_id=art.project_id,
        title=f"Document: {art.filename}",
        content=sanitize_for_prompt(md[:4000], source="document", max_chars=4000),
        category="document",
        tags=["document", art.content_sha256[:12], f"artifact:{art.id}", f"version:{cv.id}"],
        source="document_intelligence",
        is_active=True,
    )
    db.add(entry)
    db.flush()
    art.knowledge_entry_id = entry.id


def serialize_artifact(
    art: DocumentArtifact,
    *,
    reused: bool = False,
    content_version: DocumentContentVersion | None = None,
) -> dict[str, Any]:
    cv = content_version
    partial = list(cv.partial_capabilities or []) if cv else list(PARTIAL_CAPS)
    return {
        "id": art.id,
        "user_id": art.user_id,
        "project_id": art.project_id,
        "scope": art.scope,
        "filename": art.filename,
        "mime_type": art.mime_type,
        "content_sha256": art.content_sha256,
        "content_version_id": art.content_version_id,
        "sensitivity": art.sensitivity,
        "status": art.status,
        "is_current": bool(art.is_current),
        "superseded_by_id": art.superseded_by_id,
        "knowledge_entry_id": art.knowledge_entry_id,
        "bytes_size": art.bytes_size,
        "error_message": art.error_message or "",
        "kind": art.kind or "document",
        "work_item_id": art.work_item_id,
        "reused_shared_version": reused,
        "parser_name": cv.parser_name if cv else "",
        "parser_version": cv.parser_version if cv else "",
        "page_count": cv.page_count if cv else 0,
        "partial_capabilities": partial,
        "created_at": art.created_at.isoformat() if art.created_at else None,
        "updated_at": art.updated_at.isoformat() if art.updated_at else None,
    }


def get_accessible_artifact(
    db: Session,
    artifact_id: int,
    user_id: int,
    *,
    project_id: int | None = None,
) -> DocumentArtifact | None:
    """USER_PRIVATE = owner only. PROJECT_SHARED = uploader or matching project_id bound."""
    art = db.query(DocumentArtifact).filter(DocumentArtifact.id == artifact_id).first()
    if not art:
        return None
    if art.scope == USER_PRIVATE:
        return art if art.user_id == user_id else None
    if art.scope == PROJECT_SHARED:
        if art.user_id == user_id:
            return art
        if project_id is not None and art.project_id is not None and int(art.project_id) == int(project_id):
            return art
        return None
    return None


_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_IMAGE_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def ingest_image(
    db: Session,
    *,
    user_id: int,
    filename: str,
    data: bytes,
    mime_type: str = "",
    project_id: int | None = None,
    work_item_id: int | None = None,
) -> dict[str, Any]:
    """A pasted/attached screenshot, stored durably (raw bytes, no parsing --
    there is nothing to chunk) so PLAN/AGENT can reuse it without asking the
    user to re-attach. Deliberately bypasses ingest_document's
    parse/version/dedup machinery, which exists for extracting markdown from
    prose documents, not for vision content."""
    if user_id is None:
        raise ValueError("user_required")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("file_too_large")
    ext = Path(filename).suffix.lower() or _IMAGE_MIME_TO_EXT.get(mime_type, "")
    if ext not in _IMAGE_EXT:
        raise ValueError(f"unsupported_image_format:{ext or mime_type}")

    art = DocumentArtifact(
        user_id=user_id,
        project_id=project_id,
        scope=USER_PRIVATE,
        filename=filename[:500],
        mime_type=mime_type or f"image/{ext.lstrip('.')}",
        content_sha256=sha256_bytes(data),
        sensitivity="INTERNAL",
        status="READY",
        is_current=True,
        bytes_size=len(data),
        kind="image",
        work_item_id=work_item_id,
    )
    db.add(art)
    db.flush()

    root = documents_root() / f"u{user_id}" / f"a{art.id}"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"original{ext}").write_bytes(data)

    db.commit()
    db.refresh(art)
    return serialize_artifact(art)


def read_image_data_url(db: Session, *, artifact_id: int, user_id: int) -> dict[str, Any]:
    art = get_accessible_artifact(db, artifact_id, user_id)
    if not art or (art.kind or "document") != "image":
        raise ValueError("image_not_found")
    root = documents_root() / f"u{art.user_id}" / f"a{art.id}"
    matches = sorted(root.glob("original.*")) if root.is_dir() else []
    if not matches:
        raise ValueError("image_not_found")
    data = matches[0].read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    mime = art.mime_type or "image/png"
    return {
        "artifact_id": art.id,
        "filename": art.filename,
        "mime_type": mime,
        "data_url": f"data:{mime};base64,{b64}",
    }


def link_artifact_to_work_item(db: Session, *, artifact_id: int, user_id: int, work_item_id: int) -> dict[str, Any]:
    """An ASK attachment uploaded before the WorkItem existed (the very first
    turn) is linked retroactively once developerAsk() resolves and a real
    work_item_id is known -- see MentrixCodingAgentPanel's useComposerAttachments
    usage. A no-op if it's already linked to this same work item."""
    art = get_accessible_artifact(db, artifact_id, user_id)
    if not art:
        raise ValueError("document_not_found")
    if art.work_item_id and art.work_item_id != work_item_id:
        raise ValueError("already_linked_to_another_work_item")
    art.work_item_id = work_item_id
    db.commit()
    db.refresh(art)
    return serialize_artifact(art)


def list_work_item_attachments(db: Session, *, work_item_id: int) -> list[dict[str, Any]]:
    """Everything attached across ASK/PLAN/AGENT for this WorkItem -- the one
    list every pane reads, so an attachment made in ASK is visible in PLAN
    and AGENT without re-upload."""
    rows = (
        db.query(DocumentArtifact)
        .filter(DocumentArtifact.work_item_id == work_item_id, DocumentArtifact.is_current == True)  # noqa: E712
        .order_by(DocumentArtifact.created_at.asc())
        .all()
    )
    return [serialize_artifact(a) for a in rows]


def retrieve_document_context(
    db: Session,
    *,
    user_id: int,
    query: str = "",
    project_id: int | None = None,
    artifact_ids: list[int] | None = None,
    max_tokens: int = 1200,
) -> tuple[list[ProvenanceItem], dict[str, Any]]:
    """Only current + freshness=current chunks whose sha matches artifact content_sha256.

    PROJECT_SHARED chunks require an explicit matching project_id (no unscoped cross-project leak).
    """
    from sqlalchemy import and_, or_

    scope_filter = and_(DocumentArtifact.scope == USER_PRIVATE, DocumentArtifact.user_id == user_id)
    if project_id is not None:
        scope_filter = or_(
            scope_filter,
            and_(
                DocumentArtifact.scope == PROJECT_SHARED,
                DocumentArtifact.project_id == project_id,
            ),
        )

    q = (
        db.query(DocumentChunk, DocumentArtifact)
        .join(DocumentArtifact, DocumentChunk.document_artifact_id == DocumentArtifact.id)
        .filter(
            DocumentArtifact.is_current == True,  # noqa: E712
            DocumentArtifact.status == "READY",
            DocumentChunk.freshness == "current",
            DocumentChunk.content_sha256 == DocumentArtifact.content_sha256,
            scope_filter,
        )
    )
    if artifact_ids:
        q = q.filter(DocumentArtifact.id.in_(artifact_ids))

    rows = q.order_by(DocumentChunk.chunk_index.asc()).limit(200).all()
    qn = (query or "").strip().lower()
    if qn:
        ranked = []
        for ch, art in rows:
            score = 0
            text = (ch.text or "").lower()
            if qn in text:
                score += 2
            if qn in (art.filename or "").lower():
                score += 1
            if score:
                ranked.append((score, ch, art))
        ranked.sort(key=lambda x: -x[0])
        rows = [(c, a) for _, c, a in ranked]

    items: list[ProvenanceItem] = []
    used = 0
    meta_chunks = []
    for ch, art in rows:
        if art.scope == USER_PRIVATE and art.user_id != user_id:
            continue
        if art.scope == PROJECT_SHARED:
            if project_id is None or art.project_id != project_id:
                continue
        if not art.is_current or ch.freshness != "current":
            continue
        if ch.content_sha256 != art.content_sha256:
            continue  # refuse stale/replaced version
        body = sanitize_for_prompt(ch.text or "", source="document", max_chars=1500)
        tc = ch.token_count or _est_tokens(body)
        if used + tc > max_tokens:
            break
        loc = []
        if ch.page is not None:
            loc.append(f"page={ch.page}")
        if ch.slide is not None:
            loc.append(f"slide={ch.slide}")
        if ch.heading_path:
            loc.append(f"heading={ch.heading_path}")
        loc.append(f"offset={ch.source_offset}")
        items.append(
            ProvenanceItem(
                source_type="document",
                source_id=f"doc:{art.id}:v{art.content_version_id}:c{ch.id}",
                content=body,
                repository=str(art.project_id or ""),
                commit_sha=art.content_sha256,
                retrieval_score=1.0,
                freshness="current",
                verification_state="untrusted_document",
                token_count=tc,
                selection_reason=(
                    f"UNTRUSTED_DOCUMENT_CONTEXT artifact={art.id} version={art.content_version_id} "
                    f"sha={art.content_sha256[:12]} {' '.join(loc)}"
                ),
            )
        )
        used += tc
        meta_chunks.append(
            {
                "chunk_id": ch.id,
                "document_artifact_id": art.id,
                "content_version_id": art.content_version_id,
                "content_sha256": art.content_sha256,
                "freshness": "current",
                "page": ch.page,
                "slide": ch.slide,
                "heading_path": ch.heading_path,
                "source_offset": ch.source_offset,
            }
        )
    return items, {
        "chunk_count": len(meta_chunks),
        "tokens_used": used,
        "max_tokens": max_tokens,
        "chunks": meta_chunks,
        "untrusted": tag_untrusted({"chunks": len(meta_chunks)}, source="document"),
    }

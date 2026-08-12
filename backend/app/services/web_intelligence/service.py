"""Web Intelligence — fetch/normalize external content into Mentrix ContextPack.

No second RAG. All content tagged UNTRUSTED_EXTERNAL_CONTEXT.
SSRF/network-boundary enforced on generic URL/browser retrieval.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.request import Request

from sqlalchemy.orm import Session

from app.core.scopes import PROJECT_SHARED, USER_PRIVATE
from app.models import (
    ExternalContentArtifact,
    ExternalContentChunk,
    ExternalContentVersion,
    KnowledgeEntry,
)
from app.services.mentrix.untrusted_content import sanitize_for_prompt, tag_untrusted
from app.services.web_intelligence.ssrf import (
    FETCH_TIMEOUT_SEC,
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    SsrfBlocked,
    content_type_allowed,
    validate_redirect_target,
    validate_url_for_fetch,
)
from app.services.work_items.context_engine import ProvenanceItem

PARSER_VERSION = "wi-1.0.0"
PARTIAL_CAPS = ("general_web_search", "youtube_transcripts", "reddit_discussions")
UNTRUSTED_TAG = "UNTRUSTED_EXTERNAL_CONTEXT"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def web_root() -> Path:
    base = Path(os.getenv("ZECT_WEB_ROOT") or (_repo_root() / ".zect" / "web"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _version_owner_key(scope: str, user_id: int) -> int:
    if scope == PROJECT_SHARED:
        return 0
    return int(user_id)


def html_to_markdown(html: str, *, base_url: str = "") -> str:
    """Minimal HTML→text/markdown — untrusted data only."""
    text = html or ""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"(?i)</div>", "\n", text)
    text = re.sub(r"(?i)</h([1-6])>", "\n\n", text)
    text = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", text)
    text = re.sub(r"(?i)<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r"[\2](\1)", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    title_note = f"Source: {base_url}\n\n" if base_url else ""
    return (title_note + text.strip())[:200_000]


def chunk_markdown(markdown: str, *, max_chars: int = 1200) -> list[dict[str, Any]]:
    blocks = re.split(r"(?=^#{1,3}\s)", markdown, flags=re.M) if markdown.strip() else [markdown]
    chunks: list[dict[str, Any]] = []
    offset = 0
    heading = ""
    for block in blocks:
        if not block.strip():
            offset += len(block)
            continue
        hm = re.match(r"^(#{1,3})\s+(.+)$", block.strip().splitlines()[0] if block.strip() else "")
        if hm:
            heading = hm.group(2).strip()
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
                "token_count": _est_tokens(markdown),
                "chunk_hash": sha256_bytes(markdown.encode("utf-8")),
            }
        )
    return chunks


@dataclass
class FetchResult:
    url: str
    markdown: str
    title: str = ""
    author: str = ""
    mime_type: str = ""
    adapter: str = "url"
    connector_id: str = "web"
    partial: list[str] = field(default_factory=list)
    raw_meta: dict[str, Any] = field(default_factory=dict)


def _http_get(url: str, *, trusted_connector: str | None = None) -> tuple[str, bytes, str]:
    """GET with SSRF checks, redirect revalidation, size/timeout/content-type limits."""
    import urllib.error
    import urllib.request

    class _NoAutoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
            return None  # force manual handling

    current = validate_url_for_fetch(url, trusted_connector=trusted_connector)
    opener = urllib.request.build_opener(_NoAutoRedirect)
    redirects = 0
    while True:
        req = Request(
            current,
            headers={"User-Agent": "ZECT-WebIntelligence/1.0 (+untrusted-external-context)"},
            method="GET",
        )
        try:
            resp = opener.open(req, timeout=FETCH_TIMEOUT_SEC)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location") or ""
                redirects += 1
                if redirects > MAX_REDIRECTS:
                    raise SsrfBlocked("too_many_redirects") from e
                current = validate_redirect_target(current, loc)
                continue
            raise
        with resp:
            ct = resp.headers.get("Content-Type") or ""
            if not content_type_allowed(ct):
                raise ValueError(f"content_type_not_allowed:{ct}")
            chunks = []
            total = 0
            while True:
                block = resp.read(64 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response_too_large")
                chunks.append(block)
            return current, b"".join(chunks), ct


def fetch_url(url: str) -> FetchResult:
    final, body, ct = _http_get(url)
    text = body.decode("utf-8", errors="replace")
    if "html" in (ct or "").lower() or "<html" in text[:500].lower():
        md = html_to_markdown(text, base_url=final)
    else:
        md = f"Source: {final}\n\n{text}"
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", text)
    title = (title_m.group(1).strip() if title_m else urlparse(final).path.rsplit("/", 1)[-1])[:200]
    return FetchResult(
        url=final,
        markdown=md,
        title=title or final,
        mime_type=ct,
        adapter="url",
        connector_id="web",
        partial=list(PARTIAL_CAPS),
    )


def fetch_rss(url: str) -> FetchResult:
    final, body, ct = _http_get(url)
    text = body.decode("utf-8", errors="replace")
    parts = [f"# RSS/Atom feed\n\nSource: {final}\n"]
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return FetchResult(
            url=final,
            markdown=html_to_markdown(text, base_url=final),
            title="RSS (unparsed)",
            mime_type=ct,
            adapter="rss",
            partial=list(PARTIAL_CAPS) + ["rss_parse_fallback"],
        )
    # RSS 2.0 items or Atom entries
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    channel_title = (
        (root.findtext("channel/title") or root.findtext("{http://www.w3.org/2005/Atom}title") or "Feed")
        .strip()
    )
    for it in items[:40]:
        title = (
            it.findtext("title")
            or it.findtext("{http://www.w3.org/2005/Atom}title")
            or "entry"
        ).strip()
        link = (
            it.findtext("link")
            or (it.find("{http://www.w3.org/2005/Atom}link").get("href") if it.find("{http://www.w3.org/2005/Atom}link") is not None else "")
            or ""
        ).strip()
        desc = (
            it.findtext("description")
            or it.findtext("{http://www.w3.org/2005/Atom}summary")
            or it.findtext("{http://www.w3.org/2005/Atom}content")
            or ""
        ).strip()
        desc = re.sub(r"<[^>]+>", " ", desc)[:800]
        parts.append(f"## {title}\n\n{link}\n\n{desc}\n")
    return FetchResult(
        url=final,
        markdown="\n".join(parts),
        title=channel_title[:200],
        mime_type=ct,
        adapter="rss",
        connector_id="web",
        partial=list(PARTIAL_CAPS),
    )


def fetch_github(url: str) -> FetchResult:
    """Public GitHub content via raw/API-friendly URLs — still SSRF-gated; trusted_connector=github."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    if host not in ("github.com", "raw.githubusercontent.com", "api.github.com"):
        raise ValueError("github_host_required")
    # Normalize blob → raw
    path = parsed.path or ""
    fetch_url_s = url
    if host == "github.com" and "/blob/" in path:
        parts = path.strip("/").split("/")
        # owner/repo/blob/ref/path...
        if len(parts) >= 5 and parts[2] == "blob":
            owner, repo, _, ref = parts[0], parts[1], parts[2], parts[3]
            rest = "/".join(parts[4:])
            fetch_url_s = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{rest}"
    final, body, ct = _http_get(fetch_url_s, trusted_connector="github")
    text = body.decode("utf-8", errors="replace")
    md = f"# GitHub content\n\nSource: {url}\nFetched: {final}\n\n```\n{text[:50000]}\n```"
    return FetchResult(
        url=final,
        markdown=md,
        title=path.rsplit("/", 1)[-1] or "github",
        mime_type=ct or "text/plain",
        adapter="github",
        connector_id="github",
        partial=list(PARTIAL_CAPS),
        raw_meta={"original_url": url},
    )


def fetch_browser_snapshot(url: str, *, confirmed: bool) -> FetchResult:
    """Allowlisted browser snapshot — requires explicit confirmation."""
    if not confirmed:
        raise ValueError("browser_snapshot_requires_confirmation")
    from app.services.browser.allowlist import host_allowed

    ok, reason = host_allowed(url)
    if not ok:
        raise ValueError(f"browser_host_not_allowed:{reason}")
    # Still apply SSRF (deny private even if allowlist has localhost from defaults —
    # web intelligence tightens: strip localhost from browser path for WI)
    safe = validate_url_for_fetch(url)
    host = (urlparse(safe).hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost"):
        raise SsrfBlocked("browser_localhost_denied_for_web_intelligence")
    # Prefer lightweight HTTP fetch when possible; browser runtime is optional
    try:
        return FetchResult(
            **{**fetch_url(safe).__dict__, "adapter": "browser", "connector_id": "browser"},
        )
    except Exception:
        pass
    try:
        from app.services.browser.runtime import BrowserRuntime

        rt = BrowserRuntime()
        snap = rt.snapshot(safe) if hasattr(rt, "snapshot") else None
        if isinstance(snap, dict):
            body = str(snap.get("text") or snap.get("html") or snap.get("content") or "")
        else:
            body = str(snap or "")
        md = html_to_markdown(body, base_url=safe) if "<" in body[:200] else f"Source: {safe}\n\n{body}"
        return FetchResult(
            url=safe,
            markdown=md or f"(empty browser snapshot for {safe})",
            title=safe,
            adapter="browser",
            connector_id="browser",
            partial=list(PARTIAL_CAPS) + (["browser_runtime_partial"] if not body else []),
        )
    except Exception as e:
        raise ValueError(f"browser_snapshot_failed:{e}") from e


def detect_adapter(url: str, adapter: str | None = None) -> str:
    a = (adapter or "").strip().lower()
    if a in ("url", "rss", "github", "browser"):
        return a
    u = (url or "").lower()
    if "github.com" in u or "raw.githubusercontent.com" in u or "api.github.com" in u:
        return "github"
    if any(x in u for x in ("/feed", ".rss", "/atom", "format=rss", "rss.xml", "atom.xml")):
        return "rss"
    return "url"


def fetch_external(url: str, *, adapter: str | None = None, confirmed_browser: bool = False) -> FetchResult:
    kind = detect_adapter(url, adapter)
    if kind == "github":
        return fetch_github(url)
    if kind == "rss":
        return fetch_rss(url)
    if kind == "browser":
        return fetch_browser_snapshot(url, confirmed=confirmed_browser)
    return fetch_url(url)


def find_reusable_version(
    db: Session,
    *,
    scope: str,
    project_id: int | None,
    user_id: int,
    content_sha256: str,
) -> ExternalContentVersion | None:
    return (
        db.query(ExternalContentVersion)
        .filter(
            ExternalContentVersion.content_sha256 == content_sha256,
            ExternalContentVersion.scope == scope,
            ExternalContentVersion.owner_user_id == _version_owner_key(scope, user_id),
            ExternalContentVersion.project_id == project_id,
        )
        .first()
    )


def ingest_external(
    db: Session,
    *,
    user_id: int,
    url: str,
    project_id: int | None = None,
    scope: str = USER_PRIVATE,
    sensitivity: str = "INTERNAL",
    adapter: str | None = None,
    confirmed_browser: bool = False,
    replace_artifact_id: int | None = None,
) -> dict[str, Any]:
    if user_id is None:
        raise ValueError("user_required")
    scope = (scope or USER_PRIVATE).upper()
    if scope not in (USER_PRIVATE, PROJECT_SHARED):
        scope = USER_PRIVATE
    if scope == PROJECT_SHARED and project_id is None:
        raise ValueError("project_required_for_project_shared")

    art = ExternalContentArtifact(
        user_id=user_id,
        project_id=project_id,
        scope=scope,
        source_url=url[:2000],
        content_sha256="",
        sensitivity=sensitivity,
        status="FETCHING",
        is_current=True,
        confirmed_browser=bool(confirmed_browser),
        adapter=detect_adapter(url, adapter),
    )
    db.add(art)
    db.flush()

    to_supersede: list[ExternalContentArtifact] = []
    if replace_artifact_id:
        old = (
            db.query(ExternalContentArtifact)
            .filter(
                ExternalContentArtifact.id == replace_artifact_id,
                ExternalContentArtifact.user_id == user_id,
                ExternalContentArtifact.scope == scope,
            )
            .first()
        )
        if old and old.id != art.id:
            to_supersede.append(old)
    prior = (
        db.query(ExternalContentArtifact)
        .filter(
            ExternalContentArtifact.user_id == user_id,
            ExternalContentArtifact.project_id == project_id,
            ExternalContentArtifact.scope == scope,
            ExternalContentArtifact.source_url == url[:2000],
            ExternalContentArtifact.is_current == True,  # noqa: E712
            ExternalContentArtifact.id != art.id,
        )
        .all()
    )
    for old in prior:
        if old.id not in {a.id for a in to_supersede}:
            to_supersede.append(old)

    def _apply_supersede() -> None:
        for old in to_supersede:
            old.is_current = False
            old.status = "SUPERSEDED"
            old.superseded_by_id = art.id
            db.query(ExternalContentChunk).filter(
                ExternalContentChunk.external_artifact_id == old.id
            ).update({"freshness": "stale"})

    try:
        fetched = fetch_external(url, adapter=adapter, confirmed_browser=confirmed_browser)
    except (SsrfBlocked, ValueError) as e:
        art.status = "ERROR"
        art.is_current = False
        art.error_message = str(e)[:500]
        db.commit()
        db.refresh(art)
        return serialize_artifact(art)

    content_sha = sha256_bytes(fetched.markdown.encode("utf-8"))
    art.content_sha256 = content_sha
    art.title = fetched.title[:500]
    art.adapter = fetched.adapter
    art.connector_id = fetched.connector_id
    art.source_url = fetched.url[:2000]

    cv = find_reusable_version(
        db, scope=scope, project_id=project_id, user_id=user_id, content_sha256=content_sha
    )
    root = web_root() / f"u{user_id}" / f"a{art.id}"
    root.mkdir(parents=True, exist_ok=True)

    if cv and scope == PROJECT_SHARED:
        art.content_version_id = cv.id
        art.status = "READY"
        _clone_or_rebuild_chunks(db, art, cv, content_sha, sensitivity)
        _apply_supersede()
        _index_knowledge(db, art, cv)
        db.commit()
        db.refresh(art)
        return serialize_artifact(art, reused=True, content_version=cv)

    md_path = root / "content.md"
    md_path.write_text(fetched.markdown, encoding="utf-8")
    js_path = root / "content.json"
    js_path.write_text(
        json.dumps(
            {"url": fetched.url, "adapter": fetched.adapter, "meta": fetched.raw_meta},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    cv = ExternalContentVersion(
        content_sha256=content_sha,
        scope=scope,
        project_id=project_id,
        owner_user_id=_version_owner_key(scope, user_id),
        source_url=fetched.url[:2000],
        connector_id=fetched.connector_id,
        adapter=fetched.adapter,
        mime_type=fetched.mime_type[:200],
        title=fetched.title[:500],
        author=fetched.author[:200],
        markdown_path=str(md_path),
        json_path=str(js_path),
        partial_capabilities=list(dict.fromkeys(list(fetched.partial) + list(PARTIAL_CAPS))),
        fetched_at=datetime.now(timezone.utc),
    )
    db.add(cv)
    db.flush()
    art.content_version_id = cv.id
    _write_chunks(db, art, cv, fetched.markdown, content_sha, sensitivity)
    art.status = "READY"
    _apply_supersede()
    _index_knowledge(db, art, cv)
    db.commit()
    db.refresh(art)
    return serialize_artifact(art, reused=False, content_version=cv)


def _write_chunks(
    db: Session,
    art: ExternalContentArtifact,
    cv: ExternalContentVersion,
    markdown: str,
    content_sha: str,
    sensitivity: str,
) -> None:
    source_map = []
    for i, ch in enumerate(chunk_markdown(markdown)):
        row = ExternalContentChunk(
            external_artifact_id=art.id,
            content_version_id=cv.id,
            content_sha256=content_sha,
            chunk_index=i,
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
                "external_artifact_id": art.id,
                "content_version_id": cv.id,
                "content_sha256": content_sha,
                "source_url": art.source_url,
                "heading_path": ch.get("heading_path"),
                "source_offset": ch.get("source_offset"),
                "chunk_hash": ch.get("chunk_hash"),
                "freshness": "current",
            }
        )
    art.source_map_json = json.dumps(source_map)


def _clone_or_rebuild_chunks(
    db: Session,
    art: ExternalContentArtifact,
    cv: ExternalContentVersion,
    content_sha: str,
    sensitivity: str,
) -> None:
    shared = (
        db.query(ExternalContentChunk)
        .filter(
            ExternalContentChunk.content_version_id == cv.id,
            ExternalContentChunk.freshness == "current",
        )
        .order_by(ExternalContentChunk.chunk_index.asc())
        .limit(500)
        .all()
    )
    seen: set[int] = set()
    unique = []
    for ch in shared:
        if ch.chunk_index in seen:
            continue
        seen.add(ch.chunk_index)
        unique.append(ch)
    if not unique and cv.markdown_path and Path(cv.markdown_path).is_file():
        md = Path(cv.markdown_path).read_text(encoding="utf-8", errors="replace")
        _write_chunks(db, art, cv, md, content_sha, sensitivity)
        return
    source_map = []
    for i, ch in enumerate(unique):
        nc = ExternalContentChunk(
            external_artifact_id=art.id,
            content_version_id=cv.id,
            content_sha256=content_sha,
            chunk_index=i,
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
                "external_artifact_id": art.id,
                "content_version_id": cv.id,
                "content_sha256": content_sha,
                "source_url": art.source_url,
                "heading_path": ch.heading_path,
                "source_offset": ch.source_offset,
                "freshness": "current",
            }
        )
    art.source_map_json = json.dumps(source_map)


def _index_knowledge(db: Session, art: ExternalContentArtifact, cv: ExternalContentVersion) -> None:
    md = ""
    if cv.markdown_path and Path(cv.markdown_path).is_file():
        md = Path(cv.markdown_path).read_text(encoding="utf-8", errors="replace")[:8000]
    entry = KnowledgeEntry(
        user_id=art.user_id if art.scope == USER_PRIVATE else None,
        project_id=art.project_id,
        title=f"Web: {art.title or art.source_url}",
        content=sanitize_for_prompt(md[:4000], source="web", max_chars=4000),
        category="web",
        tags=["web", art.content_sha256[:12], f"artifact:{art.id}", f"version:{cv.id}", UNTRUSTED_TAG],
        source="web_intelligence",
        is_active=True,
    )
    db.add(entry)
    db.flush()
    art.knowledge_entry_id = entry.id


def serialize_artifact(
    art: ExternalContentArtifact,
    *,
    reused: bool = False,
    content_version: ExternalContentVersion | None = None,
) -> dict[str, Any]:
    cv = content_version
    partial = list(cv.partial_capabilities or []) if cv else list(PARTIAL_CAPS)
    return {
        "id": art.id,
        "user_id": art.user_id,
        "project_id": art.project_id,
        "scope": art.scope,
        "source_url": art.source_url,
        "title": art.title,
        "connector_id": art.connector_id,
        "adapter": art.adapter,
        "content_sha256": art.content_sha256,
        "content_version_id": art.content_version_id,
        "sensitivity": art.sensitivity,
        "status": art.status,
        "is_current": bool(art.is_current),
        "superseded_by_id": art.superseded_by_id,
        "knowledge_entry_id": art.knowledge_entry_id,
        "error_message": art.error_message or "",
        "reused_shared_version": reused,
        "partial_capabilities": partial,
        "tag": UNTRUSTED_TAG,
        "fetched_at": cv.fetched_at.isoformat() if cv and cv.fetched_at else None,
        "created_at": art.created_at.isoformat() if art.created_at else None,
    }


def get_accessible_artifact(
    db: Session,
    artifact_id: int,
    user_id: int,
    *,
    project_id: int | None = None,
) -> ExternalContentArtifact | None:
    art = db.query(ExternalContentArtifact).filter(ExternalContentArtifact.id == artifact_id).first()
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


def retrieve_web_context(
    db: Session,
    *,
    user_id: int,
    query: str = "",
    project_id: int | None = None,
    artifact_ids: list[int] | None = None,
    max_tokens: int = 1200,
) -> tuple[list[ProvenanceItem], dict[str, Any]]:
    from sqlalchemy import and_, or_

    scope_filter = and_(
        ExternalContentArtifact.scope == USER_PRIVATE,
        ExternalContentArtifact.user_id == user_id,
    )
    if project_id is not None:
        scope_filter = or_(
            scope_filter,
            and_(
                ExternalContentArtifact.scope == PROJECT_SHARED,
                ExternalContentArtifact.project_id == project_id,
            ),
        )

    q = (
        db.query(ExternalContentChunk, ExternalContentArtifact)
        .join(
            ExternalContentArtifact,
            ExternalContentChunk.external_artifact_id == ExternalContentArtifact.id,
        )
        .filter(
            ExternalContentArtifact.is_current == True,  # noqa: E712
            ExternalContentArtifact.status == "READY",
            ExternalContentChunk.freshness == "current",
            ExternalContentChunk.content_sha256 == ExternalContentArtifact.content_sha256,
            scope_filter,
        )
    )
    if artifact_ids:
        q = q.filter(ExternalContentArtifact.id.in_(artifact_ids))

    rows = q.order_by(ExternalContentChunk.chunk_index.asc()).limit(200).all()
    qn = (query or "").strip().lower()
    if qn:
        ranked = []
        for ch, art in rows:
            score = 0
            text = (ch.text or "").lower()
            if qn in text:
                score += 2
            if qn in (art.source_url or "").lower() or qn in (art.title or "").lower():
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
        if art.scope == PROJECT_SHARED and (project_id is None or art.project_id != project_id):
            continue
        if not art.is_current or ch.freshness != "current":
            continue
        if ch.content_sha256 != art.content_sha256:
            continue
        body = sanitize_for_prompt(ch.text or "", source="web", max_chars=1500)
        tc = ch.token_count or _est_tokens(body)
        if used + tc > max_tokens:
            break
        items.append(
            ProvenanceItem(
                source_type="web",
                source_id=f"web:{art.id}:v{art.content_version_id}:c{ch.id}",
                content=body,
                repository=str(art.project_id or ""),
                commit_sha=art.content_sha256,
                retrieval_score=1.0,
                freshness="current",
                verification_state="untrusted_external",
                token_count=tc,
                selection_reason=(
                    f"{UNTRUSTED_TAG} artifact={art.id} version={art.content_version_id} "
                    f"sha={art.content_sha256[:12]} url={art.source_url} "
                    f"connector={art.connector_id} adapter={art.adapter} "
                    f"heading={ch.heading_path} offset={ch.source_offset}"
                ),
            )
        )
        used += tc
        meta_chunks.append(
            {
                "chunk_id": ch.id,
                "external_artifact_id": art.id,
                "content_version_id": art.content_version_id,
                "content_sha256": art.content_sha256,
                "source_url": art.source_url,
                "freshness": "current",
                "tag": UNTRUSTED_TAG,
            }
        )
    return items, {
        "chunk_count": len(meta_chunks),
        "tokens_used": used,
        "max_tokens": max_tokens,
        "chunks": meta_chunks,
        "untrusted": tag_untrusted({"chunks": len(meta_chunks)}, source="web"),
        "tag": UNTRUSTED_TAG,
    }

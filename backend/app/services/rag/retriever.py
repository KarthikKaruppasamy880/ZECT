"""RAG retriever — bag-of-tokens vectors in embedding_chunks (JSON TEXT).

pgvector / Chroma / FAISS are not used. Same application DB as Projects/WorkItems
(desktop_sqlite or server_postgres). Retrieval is in-process cosine similarity.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import EmbeddingChunk
from app.services.lattice.indexer import LANG_EXTS, SKIP_DIRS, get_graph

_TOKEN_SPLIT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def _tokenize(text: str, dim: int = 64) -> list[float]:
    """Deterministic bag-of-tokens embedding (no API required for local/dev)."""
    vec = [0.0] * dim
    for tok in _TOKEN_SPLIT.findall(text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _chunk_file(path: str, content: str, max_chars: int = 1200) -> list[tuple[str, int]]:
    chunks: list[tuple[str, int]] = []
    lines = content.splitlines()
    buf: list[str] = []
    start = 1
    size = 0
    for i, line in enumerate(lines, 1):
        if not buf:
            start = i
        buf.append(line)
        size += len(line) + 1
        if size >= max_chars:
            chunks.append(("\n".join(buf), start))
            buf, size = [], 0
    if buf:
        chunks.append(("\n".join(buf), start))
    return chunks


def index_directory(
    db: Session,
    root: str,
    *,
    project_id: int | None = None,
    repo_id: int | None = None,
    project_key: str = "",
    max_files: int = 500,
    cancel_check=None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")

    if cancel_check is not None and cancel_check():
        from app.services.lattice.indexer import LatticeCancelled

        raise LatticeCancelled("lattice_cancelled")

    # Clear prior chunks for this project_key scope
    q = db.query(EmbeddingChunk)
    if project_id is not None:
        q = q.filter(EmbeddingChunk.project_id == project_id)
    if repo_id is not None:
        q = q.filter(EmbeddingChunk.repo_id == repo_id)
    if project_key:
        q = q.filter(EmbeddingChunk.project_key == project_key)
    q.delete(synchronize_session=False)

    files = 0
    chunks_n = 0
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in LANG_EXTS and ext not in {".md", ".txt", ".rst"}:
                continue
            fpath = Path(dirpath) / fname
            rel = str(fpath.relative_to(root_path)).replace("\\", "/")
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if cancel_check is not None and cancel_check():
                from app.services.lattice.indexer import LatticeCancelled

                db.rollback()
                raise LatticeCancelled("lattice_cancelled")
            files += 1
            for text, line_start in _chunk_file(rel, content):
                emb = _tokenize(text)
                row = EmbeddingChunk(
                    project_id=project_id,
                    repo_id=repo_id,
                    project_key=project_key or str(root_path),
                    path=rel,
                    source_type="code" if ext in LANG_EXTS else "doc",
                    language=LANG_EXTS.get(ext, ""),
                    line_start=line_start,
                    content=text[:8000],
                    embedding_json=json.dumps(emb),
                )
                db.add(row)
                chunks_n += 1
            if files >= max_files:
                break
        if files >= max_files:
            break
    db.commit()
    return {"files": files, "chunks": chunks_n, "project_key": project_key or str(root_path)}


def hybrid_retrieve(
    db: Session,
    query: str,
    *,
    project_key: str = "",
    project_id: int | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    k = top_k or int(os.getenv("RAG_TOP_K", "12"))
    q_emb = _tokenize(query)
    q = db.query(EmbeddingChunk)
    if project_id is not None:
        q = q.filter(EmbeddingChunk.project_id == project_id)
    if project_key:
        q = q.filter(EmbeddingChunk.project_key == project_key)
    rows = q.limit(5000).all()
    scored: list[tuple[float, EmbeddingChunk]] = []
    for row in rows:
        try:
            emb = json.loads(row.embedding_json or "[]")
        except json.JSONDecodeError:
            continue
        if not emb:
            continue
        scored.append((_cosine(q_emb, emb), row))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Lattice boost: graph node paths + wikilink neighbors
    boost_paths: set[str] = set()
    g = get_graph(project_key) if project_key else None
    if g:
        ql = query.lower()
        seed_ids: set[str] = set()
        for n in g.nodes:
            hay = " ".join(x for x in (n.name, n.path, getattr(n, "title", ""), getattr(n, "slug", "")) if x).lower()
            if ql in hay:
                boost_paths.add(n.path)
                seed_ids.add(n.id)
        if seed_ids:
            for e in g.edges:
                if e.kind in ("wikilink", "md_link", "references", "in_folder"):
                    if e.source in seed_ids:
                        tgt = next((n for n in g.nodes if n.id == e.target), None)
                        if tgt:
                            boost_paths.add(tgt.path)
                    if e.target in seed_ids:
                        src = next((n for n in g.nodes if n.id == e.source), None)
                        if src:
                            boost_paths.add(src.path)

    results = []
    for score, row in scored[: k * 2]:
        bonus = 0.15 if row.path in boost_paths else 0.0
        results.append({
            "score": round(score + bonus, 4),
            "path": row.path,
            "line_start": row.line_start,
            "source_type": row.source_type,
            "language": row.language,
            "content": row.content[:1500],
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]

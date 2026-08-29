"""Semantic indexer — builds the CodeEmbedding table Build's retriever reads from.

Mirrors auto_indexer.index_repo's structure (same repo/clone_status validation,
same SKIP_DIRS walk) but embeds real content chunks instead of extracting symbol
names, so it costs real embedding-API money per run — MAX_FILES/MAX_CHUNKS below
are deliberately more conservative than the free regex symbol indexer's caps.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import CodeEmbedding, Repo
from app.services.auto_indexer import EXT_TO_LANG, SKIP_DIRS
from app.services.build_intel.chunker import chunk_file
from app.services.build_intel.embeddings import EMBEDDING_MODEL, embed_texts

MAX_FILES = 500
MAX_FILE_SIZE = 500_000  # 500 KB — large generated/vendored files aren't worth embedding
MAX_CHUNKS = 2000  # hard cap on embedding-API spend per index run


def index_repo_semantic(db: Session, repo_id: int, user_id: int | None = None) -> dict:
    """(Re)build the semantic index for a cloned repo. Replaces existing chunks."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found"}
    if repo.clone_status != "cloned" or not repo.local_path:
        return {"error": "Repo is not cloned"}
    if not os.path.isdir(repo.local_path):
        return {"error": "Clone directory missing"}

    root = Path(repo.local_path)

    db.query(CodeEmbedding).filter(CodeEmbedding.repo_id == repo_id).delete()
    db.flush()

    files_scanned = 0
    chunks_truncated = False
    errors: list[str] = []
    pending: list[dict] = []  # accumulate chunk metadata before the batched embed call

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if files_scanned >= MAX_FILES or len(pending) >= MAX_CHUNKS:
                break

            fpath = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            lang = EXT_TO_LANG.get(ext)
            if not lang:
                continue

            try:
                size = os.path.getsize(fpath)
                if size > MAX_FILE_SIZE:
                    continue

                with open(fpath, "r", errors="replace") as f:
                    content = f.read()

                rel_path = str(Path(fpath).relative_to(root))
                files_scanned += 1

                for idx, chunk in enumerate(chunk_file(content, lang)):
                    if len(pending) >= MAX_CHUNKS:
                        chunks_truncated = True
                        break
                    pending.append({
                        "repo_id": repo_id,
                        "file_path": rel_path,
                        "chunk_index": idx,
                        "language": lang,
                        "line_start": chunk["line_start"],
                        "line_end": chunk["line_end"],
                        "symbol_name": chunk.get("symbol_name"),
                        "content": chunk["content"],
                    })
            except (OSError, PermissionError) as e:
                errors.append(f"{fname}: {e}")
                continue

        if files_scanned >= MAX_FILES or len(pending) >= MAX_CHUNKS:
            if files_scanned >= MAX_FILES:
                chunks_truncated = True
            break

    if not pending:
        return {
            "status": "indexed",
            "files_scanned": files_scanned,
            "chunks_added": 0,
            "truncated": chunks_truncated,
            "errors": errors[:10],
        }

    try:
        vectors = embed_texts([p["content"] for p in pending], user_id=user_id)
    except RuntimeError as e:
        return {"error": str(e)}

    now = datetime.now(timezone.utc)
    for meta, vector in zip(pending, vectors):
        db.add(CodeEmbedding(
            repo_id=meta["repo_id"],
            file_path=meta["file_path"],
            chunk_index=meta["chunk_index"],
            language=meta["language"],
            line_start=meta["line_start"],
            line_end=meta["line_end"],
            symbol_name=meta["symbol_name"],
            content=meta["content"],
            embedding=json.dumps(vector),
            embedding_model=EMBEDDING_MODEL,
            created_at=now,
        ))

    db.commit()

    return {
        "status": "indexed",
        "files_scanned": files_scanned,
        "chunks_added": len(pending),
        "truncated": chunks_truncated,
        "errors": errors[:10],
    }

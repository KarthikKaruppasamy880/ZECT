"""Semantic search over a repo's CodeEmbedding rows.

Pure-Python cosine similarity — no numpy dependency. Fine at single-repo scale
(hundreds to low thousands of chunks); see embeddings.py for why a vector DB
wasn't introduced for Phase 1.
"""

from __future__ import annotations

import json
import math

from sqlalchemy.orm import Session

from app.models import CodeEmbedding
from app.services.build_intel.embeddings import embed_query


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def has_index(db: Session, repo_id: int) -> bool:
    return db.query(CodeEmbedding).filter(CodeEmbedding.repo_id == repo_id).first() is not None


def search(db: Session, repo_id: int, query: str, top_k: int = 6, user_id: int | None = None) -> list[dict]:
    """Return the top_k most semantically relevant chunks for `query` in this repo.

    Returns [] if no index exists yet for this repo — callers should fall back
    to whatever context strategy they used before this existed.
    """
    rows = db.query(CodeEmbedding).filter(CodeEmbedding.repo_id == repo_id).all()
    if not rows:
        return []

    query_vec = embed_query(query, user_id=user_id)
    if not query_vec:
        return []

    scored = []
    for row in rows:
        try:
            vec = json.loads(row.embedding)
        except (ValueError, TypeError):
            continue
        score = _cosine_similarity(query_vec, vec)
        scored.append((score, row))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = scored[:top_k]

    return [
        {
            "file_path": row.file_path,
            "content": row.content,
            "line_start": row.line_start,
            "line_end": row.line_end,
            "symbol_name": row.symbol_name,
            "similarity": round(score, 4),
        }
        for score, row in top
    ]

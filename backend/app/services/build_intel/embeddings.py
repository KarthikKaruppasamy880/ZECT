"""Embedding generation for Build's retrieval index — OpenAI only, no new dependency.

Deliberately avoids adding a vector-DB dependency (chromadb/pgvector/sqlite-vec):
at single-repo scale (hundreds to low thousands of chunks) plain cosine similarity
in Python over rows already in SQLite is fast enough, and it keeps Phase 1 at zero
new pip dependencies. Revisit if a repo's chunk count grows large enough that this
becomes the bottleneck.
"""

from __future__ import annotations

import os

from openai import OpenAI

from app.token_tracker import log_tokens

EMBEDDING_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 100  # OpenAI embeddings endpoint accepts a list of inputs per call


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OpenAI API key not configured. Go to Settings and add your OPENAI_API_KEY.")
    return OpenAI(api_key=key)


def embed_texts(texts: list[str], user_id: int | None = None) -> list[list[float]]:
    """Embed a batch of texts, preserving input order. Logs token usage per batch
    so per-user budget enforcement (Fix #4) actually sees this cost — embedding
    calls are real, billed OpenAI usage, not free local computation."""
    if not texts:
        return []
    client = _get_client()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i:i + _BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend(item.embedding for item in resp.data)
        tokens = resp.usage.total_tokens if resp.usage else 0
        log_tokens(
            action="build_intel_embed",
            feature="build_intel",
            model=EMBEDDING_MODEL,
            prompt_tokens=tokens,
            completion_tokens=0,
            total_tokens=tokens,
            user_id=user_id,
        )
    return vectors


def embed_query(text: str, user_id: int | None = None) -> list[float]:
    """Embed a single query string."""
    vectors = embed_texts([text], user_id=user_id)
    return vectors[0] if vectors else []

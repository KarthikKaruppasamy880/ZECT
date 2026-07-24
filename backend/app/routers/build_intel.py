"""Build Intelligence — semantic index status/search for retrieval-augmented Build.

Reindexing is also triggered automatically from POST /api/repos/{id}/index
(repo_clone.py) alongside the existing symbol indexer — these endpoints exist
for manual reindex, status checks, and debugging retrieval quality directly.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.core.budget import enforce_token_budget
from app.database import get_db
from app.models import CodeEmbedding
from app.services.build_intel.indexer import index_repo_semantic
from app.services.build_intel.retriever import search as semantic_search

router = APIRouter(prefix="/api/build-intel", tags=["build-intel"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 6


@router.post("/{repo_id}/reindex")
def reindex(
    repo_id: int,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Rebuild the semantic index for a cloned repo."""
    result = index_repo_semantic(db, repo_id, user_id=current_user.user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{repo_id}/status")
def status(
    repo_id: int,
    _user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chunk count + last-indexed time for this repo's semantic index."""
    row = (
        db.query(func.count(CodeEmbedding.id), func.max(CodeEmbedding.created_at))
        .filter(CodeEmbedding.repo_id == repo_id)
        .first()
    )
    chunk_count, last_indexed = row if row else (0, None)
    return {
        "repo_id": repo_id,
        "indexed": bool(chunk_count),
        "chunk_count": chunk_count or 0,
        "last_indexed_at": last_indexed.isoformat() if last_indexed else None,
    }


@router.post("/{repo_id}/search")
def search(
    repo_id: int,
    req: SearchRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Debug endpoint: run the same retrieval Build uses, directly."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")
    return {"results": semantic_search(db, repo_id, req.query, top_k=req.top_k, user_id=current_user.user_id)}

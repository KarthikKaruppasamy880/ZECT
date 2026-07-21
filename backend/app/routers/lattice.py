"""Lattice graph API for Mentrix Understand."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.database import get_db
from app.services.lattice.indexer import get_graph, ingest_path, query_graph
from app.services.rag.retriever import hybrid_retrieve, index_directory

router = APIRouter(prefix="/api/lattice", tags=["lattice"])


class IngestPathRequest(BaseModel):
    path: str
    project_key: str = ""
    project_id: int | None = None
    repo_id: int | None = None
    index_rag: bool = True
    max_files: int = 2000


class QueryRequest(BaseModel):
    project_key: str
    q: str
    limit: int = 50


@router.post("/ingest")
def ingest(
    req: IngestPathRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    if os.getenv("LATTICE_ENABLED", "true").lower() in ("0", "false"):
        raise HTTPException(status_code=503, detail="Lattice is disabled")
    try:
        graph = ingest_path(req.path, project_key=req.project_key or req.path, max_files=req.max_files)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rag_stats = {}
    if req.index_rag and os.getenv("RAG_ENABLED", "true").lower() not in ("0", "false"):
        rag_stats = index_directory(
            db,
            req.path,
            project_id=req.project_id,
            repo_id=req.repo_id,
            project_key=graph.project_key,
            max_files=min(req.max_files, 500),
        )
    return {"graph": graph.to_dict(), "rag": rag_stats}


@router.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    project_key: str = "",
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip archive")
    with tempfile.TemporaryDirectory(prefix="lattice_") as tmp:
        zpath = Path(tmp) / "upload.zip"
        zpath.write_bytes(await file.read())
        extract_dir = Path(tmp) / "src"
        extract_dir.mkdir()
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(extract_dir)
        key = project_key or file.filename
        graph = ingest_path(str(extract_dir), project_key=key)
        rag_stats = index_directory(db, str(extract_dir), project_key=key)
    return {"graph": graph.to_dict(), "rag": rag_stats}


@router.get("/graph")
def graph(project_key: str, _user: CurrentUser = Depends(get_current_user)):
    g = get_graph(project_key)
    if not g:
        raise HTTPException(status_code=404, detail="Graph not found — run /api/lattice/ingest first")
    return g.to_dict()


@router.post("/query")
def query(req: QueryRequest, _user: CurrentUser = Depends(get_current_user)):
    return {"hits": query_graph(req.project_key, req.q, req.limit)}


@router.post("/rag/search")
def rag_search(
    req: QueryRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    hits = hybrid_retrieve(db, req.q, project_key=req.project_key, top_k=req.limit)
    return {"hits": hits}

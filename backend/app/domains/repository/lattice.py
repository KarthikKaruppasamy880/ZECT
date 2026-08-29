"""Lattice graph API for Mentrix Understand."""

from __future__ import annotations

import os
import tempfile
import time
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.budget import enforce_token_budget
from app.infrastructure.database import get_db
from app.services.lattice.indexer import (
    attach_cross_repo_edge,
    communities as lattice_communities,
    explain as lattice_explain,
    find_path,
    get_graph,
    get_lattice_status,
    god_nodes as lattice_god_nodes,
    ingest_path,
    LatticeCancelled,
    neighbors as lattice_neighbors,
    query_graph,
)
from app.services.lattice.markdown_graph import doc_backlinks, filter_graph_layer
from app.services.lattice.structural_blueprint import (
    build_deep_prompt,
    build_structural_blueprint,
    get_structural_blueprint,
    persist_structural_blueprint,
)
from app.services.rag.retriever import hybrid_retrieve, index_directory

router = APIRouter(prefix="/api/lattice", tags=["lattice"])


class IngestPathRequest(BaseModel):
    path: str
    project_key: str = ""
    project_id: int | None = None
    repo_id: int | None = None
    index_rag: bool = True
    index_docs: bool = True
    max_files: int = 2000
    build_blueprint: bool = True
    run_id: str = ""
    force: bool = False


class QueryRequest(BaseModel):
    project_key: str
    q: str
    limit: int = 50
    kinds: list[str] | None = None
    include_backlinks: bool = False


class PathRequest(BaseModel):
    project_key: str
    source: str
    target: str
    max_depth: int = 8


class NeighborsRequest(BaseModel):
    project_key: str
    node: str
    depth: int = 1
    limit: int = 50


class ExplainRequest(BaseModel):
    project_key: str
    source: str = ""
    target: str = ""
    node: str = ""


class BlueprintBuildRequest(BaseModel):
    path: str
    project_key: str = ""
    max_files: int = 2000
    refresh_graph: bool = True


class BlueprintPromptRequest(BaseModel):
    project_key: str
    path: str = ""
    rebuild: bool = False


class HldRequest(BaseModel):
    project_key: str
    goal: str = "Produce a high-level design document for this codebase"


class CrossRepoEdgeRequest(BaseModel):
    project_key: str
    source_repo: str
    source_sha: str
    target_repo: str
    target_sha: str
    edge_type: str
    evidence: str
    confidence: float = 0.7


@router.post("/ingest")
def ingest(
    req: IngestPathRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    if os.getenv("LATTICE_ENABLED", "true").lower() in ("0", "false"):
        raise HTTPException(status_code=503, detail="Lattice is disabled")
    key = req.project_key or req.path
    from app.infrastructure.observability import (
        begin_operation,
        cancel_check_for,
        emit_event,
        new_id,
    )

    run_id = (req.run_id or "").strip() or new_id()
    t0 = time.perf_counter()
    begin_operation(
        run_id,
        kind="lattice_ingest",
        extra={"project_key": key[:120]},
        user_id=_user.user_id,
    )
    check = cancel_check_for(run_id)
    try:
        graph = ingest_path(
            req.path,
            project_key=key,
            max_files=req.max_files,
            index_docs=req.index_docs,
            cancel_check=check,
            force=req.force,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LatticeCancelled as exc:
        emit_event(
            operation="lattice_ingest",
            stage="cancelled",
            run_id=run_id,
            failure_class="cancelled",
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        raise HTTPException(status_code=409, detail={"error": "cancelled", "run_id": run_id}) from exc
    rag_stats = {}
    if req.index_rag and os.getenv("RAG_ENABLED", "true").lower() not in ("0", "false"):
        try:
            rag_stats = index_directory(
                db,
                req.path,
                project_id=req.project_id,
                repo_id=req.repo_id,
                project_key=graph.project_key,
                max_files=min(req.max_files, 500),
                cancel_check=check,
            )
        except LatticeCancelled as exc:
            emit_event(
                operation="lattice_ingest",
                stage="rag_cancelled",
                run_id=run_id,
                failure_class="cancelled",
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
            raise HTTPException(status_code=409, detail={"error": "cancelled", "run_id": run_id}) from exc
    blueprint_summary = None
    if req.build_blueprint:
        try:
            bp = build_structural_blueprint(
                req.path,
                graph.project_key,
                max_files=req.max_files,
                refresh_graph=False,
            )
            persist_structural_blueprint(db, bp)
            blueprint_summary = {
                "project_key": bp["project_key"],
                "stats": bp.get("stats"),
                "tech_stack": bp.get("tech_stack"),
                "api_endpoints": len(bp.get("api_endpoints") or []),
                "god_nodes": len(bp.get("god_nodes") or []),
            }
        except Exception as exc:  # noqa: BLE001 — ingest must still succeed
            blueprint_summary = {"error": str(exc)}
    emit_event(
        operation="lattice_ingest",
        stage="complete",
        run_id=run_id,
        duration_ms=int((time.perf_counter() - t0) * 1000),
        extra={"files_indexed": graph.files_indexed},
    )
    return {
        "graph": graph.to_dict(),
        "rag": rag_stats,
        "blueprint": blueprint_summary,
        "god_nodes": lattice_god_nodes(graph.project_key, limit=10),
        "run_id": run_id,
    }


class CancelIngestRequest(BaseModel):
    run_id: str


@router.post("/ingest/cancel")
def ingest_cancel(req: CancelIngestRequest, _user: CurrentUser = Depends(get_current_user)):
    from app.infrastructure.observability import cancel_operation

    if not (req.run_id or "").strip():
        raise HTTPException(status_code=400, detail="run_id required")
    if not cancel_operation(req.run_id, user_id=_user.user_id):
        raise HTTPException(status_code=403, detail="not_operation_owner")
    return {"ok": True, "run_id": req.run_id, "cancelled": True}


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
        bp = build_structural_blueprint(str(extract_dir), key, refresh_graph=False)
        persist_structural_blueprint(db, bp)
    return {"graph": graph.to_dict(), "rag": rag_stats, "blueprint": bp.get("stats")}


@router.get("/graph")
def graph(
    project_key: str,
    layer: str = "combined",
    _user: CurrentUser = Depends(get_current_user),
):
    g = get_graph(project_key)
    if not g:
        raise HTTPException(status_code=404, detail="Graph not found — run /api/lattice/ingest first")
    data = filter_graph_layer(g.to_dict(), layer=layer)
    data["god_nodes"] = lattice_god_nodes(project_key, limit=15)
    data["communities"] = lattice_communities(project_key, limit=10)
    return data


@router.get("/graph/backlinks")
def graph_backlinks(
    project_key: str,
    doc: str,
    limit: int = 50,
    _user: CurrentUser = Depends(get_current_user),
):
    return doc_backlinks(project_key, doc, limit=limit)


@router.post("/query")
def query(req: QueryRequest, _user: CurrentUser = Depends(get_current_user)):
    hits = query_graph(req.project_key, req.q, req.limit, kinds=req.kinds)
    out: dict = {"hits": hits}
    if req.include_backlinks and hits:
        first = hits[0]
        ref = first.get("path") or first.get("name") or req.q
        out["backlinks"] = doc_backlinks(req.project_key, str(ref), limit=20)
    return out


@router.post("/rag/search")
def rag_search(
    req: QueryRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    hits = hybrid_retrieve(db, req.q, project_key=req.project_key, top_k=req.limit)
    return {"hits": hits}


@router.post("/path")
def path(req: PathRequest, _user: CurrentUser = Depends(get_current_user)):
    return find_path(req.project_key, req.source, req.target, max_depth=req.max_depth)


@router.post("/neighbors")
def neighbors_api(req: NeighborsRequest, _user: CurrentUser = Depends(get_current_user)):
    return lattice_neighbors(req.project_key, req.node, depth=req.depth, limit=req.limit)


@router.post("/explain")
def explain_api(req: ExplainRequest, _user: CurrentUser = Depends(get_current_user)):
    return lattice_explain(
        req.project_key,
        source_ref=req.source,
        target_ref=req.target,
        node_ref=req.node,
    )


@router.get("/god-nodes")
def god_nodes_api(project_key: str, limit: int = 20, _user: CurrentUser = Depends(get_current_user)):
    return {"nodes": lattice_god_nodes(project_key, limit=limit)}


@router.get("/communities")
def communities_api(project_key: str, limit: int = 12, _user: CurrentUser = Depends(get_current_user)):
    return {"communities": lattice_communities(project_key, limit=limit)}


@router.post("/blueprint/build")
def blueprint_build(
    req: BlueprintBuildRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    try:
        bp = build_structural_blueprint(
            req.path,
            req.project_key or req.path,
            max_files=req.max_files,
            refresh_graph=req.refresh_graph,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    persist_structural_blueprint(db, bp)
    return bp


@router.get("/blueprint")
def blueprint_get(project_key: str, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    bp = get_structural_blueprint(db, project_key)
    if not bp:
        raise HTTPException(status_code=404, detail="Structural blueprint not found — ingest or build first")
    return bp


@router.get("/snapshot")
def lattice_snapshot_api(
    project_key: str,
    repository_id: int | None = None,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.lattice.graphify_snapshot import graphify_snapshot

    return graphify_snapshot(project_key, db=db, repository_id=repository_id)


@router.post("/cross-repo-edge")
def lattice_cross_repo_edge(
    req: CrossRepoEdgeRequest,
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.lattice.cross_repo import CrossRepoEdgeError, make_cross_repo_edge

    try:
        edge = make_cross_repo_edge(
            source_repo=req.source_repo,
            source_sha=req.source_sha,
            target_repo=req.target_repo,
            target_sha=req.target_sha,
            edge_type=req.edge_type,
            evidence=req.evidence,
            confidence=req.confidence,
        )
        graph = attach_cross_repo_edge(req.project_key, edge)
    except CrossRepoEdgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "edge": edge, "cross_repo_edges": graph.cross_repo_edges}


@router.get("/status")
def lattice_status_api(
    project_key: str,
    repository_id: int | None = None,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """Canonical Lattice state plus backward-compatible indexed/has_blueprint fields."""
    detail = get_lattice_status(project_key, db=db, repository_id=repository_id)
    graph = get_graph(project_key)
    bp = get_structural_blueprint(db, project_key)
    stats: dict = {}
    if graph:
        stats = {
            "files_indexed": graph.files_indexed,
            "symbols": graph.symbols,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "languages": graph.languages,
        }
    updated_at = None
    if bp and bp.get("updated_at"):
        updated_at = bp["updated_at"]
    elif bp and bp.get("created_at"):
        updated_at = bp["created_at"]
    return {
        "indexed": bool(detail.get("indexed")),
        "state": detail.get("state") or ("READY" if graph else "NOT_INDEXED"),
        "reason": detail.get("reason"),
        "action": detail.get("action"),
        "action_label": detail.get("action_label"),
        "project_key": project_key,
        "has_blueprint": bp is not None,
        "graph_stats": stats if stats else None,
        "blueprint_updated_at": updated_at,
        "errors": detail.get("errors") or [],
        "indexed_at": detail.get("indexed_at"),
        "repository_id": detail.get("repository_id"),
        "indexed_commit_sha": detail.get("indexed_commit_sha") or (bp or {}).get("indexed_commit_sha") or "",
        "live_commit_sha": detail.get("live_commit_sha") or "",
    }


@router.post("/blueprint/prompt")
def blueprint_prompt(
    req: BlueprintPromptRequest,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    bp = get_structural_blueprint(db, req.project_key)
    if req.rebuild or not bp:
        if not req.path:
            raise HTTPException(
                status_code=400,
                detail="Blueprint missing — provide path to rebuild or run ingest first",
            )
        bp = build_structural_blueprint(req.path, req.project_key, refresh_graph=True)
        persist_structural_blueprint(db, bp)
    prompt = build_deep_prompt(bp)
    return {
        "prompt": prompt,
        "token_estimate": max(1, len(prompt) // 4),
        "project_key": req.project_key,
        "stats": bp.get("stats"),
    }


@router.post("/hld")
def hld_generate_api(
    req: HldRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(enforce_token_budget),
):
    """Generate a real High-Level Design document (component breakdown, data
    flow, Mermaid diagram, risks) from Lattice's structural blueprint — unlike
    /blueprint/prompt, this actually calls an LLM to synthesize the data rather
    than just templating it into a prompt for the user to paste elsewhere."""
    from app.services.phases.hld_phase import run_hld_generate

    try:
        result = run_hld_generate(db, req.project_key, goal=req.goal, user_id=current_user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result

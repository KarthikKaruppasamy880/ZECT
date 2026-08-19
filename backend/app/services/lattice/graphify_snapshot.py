"""GraphifySnapshot adapter — Lattice is the store. No second graph database."""

from __future__ import annotations

from typing import Any

from app.services.lattice.indexer import LATTICE_STATES, get_graph, get_lattice_status


def graphify_snapshot(
    project_key: str,
    *,
    db: Any = None,
    repository_id: int | None = None,
) -> dict[str, Any]:
    """One adapter: GraphifySnapshot(repo, SHA) from Lattice graph + status."""
    status = get_lattice_status(project_key, db=db, repository_id=repository_id)
    graph = get_graph(project_key)
    return {
        "kind": "GraphifySnapshot",
        "adapter": "lattice",
        "project_key": project_key,
        "state": status.get("state"),
        "states": list(LATTICE_STATES),
        "indexed_commit_sha": status.get("indexed_commit_sha") or (graph.commit_sha if graph else ""),
        "live_commit_sha": status.get("live_commit_sha") or "",
        "commit_sha": (graph.commit_sha if graph else "") or status.get("indexed_commit_sha") or "",
        "incremental": bool(graph.incremental) if graph else False,
        "files_indexed": status.get("files_indexed") or (graph.files_indexed if graph else 0),
        "symbols": status.get("symbols") or (graph.symbols if graph else 0),
        "errors": list(status.get("errors") or [])[:8],
        "cross_repo_edges": list(graph.cross_repo_edges) if graph else [],
        "lattice_status": status,
        "ux_label": "Lattice",
    }

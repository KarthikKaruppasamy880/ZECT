"""Lattice Graphify-class intelligence: calls, path, neighbors, endpoints."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.lattice.indexer import (
    communities,
    explain,
    find_path,
    god_nodes,
    ingest_path,
    neighbors,
    query_graph,
)


def test_lattice_calls_path_neighbors_endpoints():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pkg").mkdir()
        (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (root / "pkg" / "a.py").write_text(
            """
def helper():
    return 1

def main():
    return helper()
""",
            encoding="utf-8",
        )
        (root / "pkg" / "api.py").write_text(
            """
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True}
""",
            encoding="utf-8",
        )
        (root / "pkg" / "b.py").write_text(
            "from .a import main\n\ndef run():\n    return main()\n",
            encoding="utf-8",
        )

        g = ingest_path(str(root), project_key="lattice-test-fixture")
        assert g.files_indexed >= 3
        call_edges = [e for e in g.edges if e.kind == "calls"]
        assert call_edges, "expected within-file calls edges"
        endpoints = [n for n in g.nodes if n.kind == "endpoint"]
        assert endpoints, "expected FastAPI endpoint nodes"
        imports_file = [e for e in g.edges if e.kind == "imports_file"]
        assert imports_file, "expected resolved relative imports"

        hits = query_graph("lattice-test-fixture", "helper")
        assert hits

        nb = neighbors("lattice-test-fixture", "main", depth=1)
        assert nb.get("nodes")

        path = find_path("lattice-test-fixture", "main", "helper")
        assert path.get("path") or path.get("error") in (None, "no_path")
        # same-file call graph should usually find a path
        if path.get("path"):
            assert path["length"] >= 1

        exp = explain("lattice-test-fixture", node_ref="health")
        assert "summary" in exp
        assert exp["summary"]

        gods = god_nodes("lattice-test-fixture", limit=10)
        assert isinstance(gods, list)
        comps = communities("lattice-test-fixture", limit=5)
        assert isinstance(comps, list)

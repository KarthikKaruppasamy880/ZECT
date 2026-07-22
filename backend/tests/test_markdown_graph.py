"""Tests for Lattice markdown / wikilink documentation graph."""

from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "doc_vault"


def test_ingest_markdown_wikilinks():
    from app.services.lattice.indexer import ingest_path

    root = FIXTURE
    if not root.is_dir():
        pytest.skip("fixture missing")
    g = ingest_path(str(root), project_key="doc_vault_test", max_files=50, index_docs=True)
    assert g.doc_files_indexed >= 3
    kinds = {n.kind for n in g.nodes}
    assert "doc" in kinds
    assert "vault" in kinds
    edge_kinds = {e.kind for e in g.edges}
    assert "wikilink" in edge_kinds or "md_link" in edge_kinds
    assert g.wikilinks_resolved >= 1


def test_doc_backlinks():
    from app.services.lattice.indexer import ingest_path
    from app.services.lattice.markdown_graph import doc_backlinks

    root = FIXTURE
    if not root.is_dir():
        pytest.skip("fixture missing")
    key = "doc_vault_bl"
    ingest_path(str(root), project_key=key, max_files=50, index_docs=True)
    bl = doc_backlinks(key, "concepts.md", limit=10)
    assert bl.get("backlinks") is not None
    assert bl.get("count", 0) >= 0


def test_filter_graph_layer():
    from app.services.lattice.markdown_graph import filter_graph_layer

    data = {
        "nodes": [{"id": "1", "kind": "doc"}, {"id": "2", "kind": "file"}],
        "edges": [{"source": "1", "target": "2"}],
    }
    docs = filter_graph_layer(data, "docs")
    assert len(docs["nodes"]) == 1
    assert docs["layer"] == "docs"

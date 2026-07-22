"""Markdown / wikilink documentation graph (brain-map patterns) for Lattice."""

from __future__ import annotations

import os
import re
from dataclasses import asdict
from pathlib import Path

from app.services.lattice.indexer import SKIP_DIRS, GraphEdge, GraphNode, LatticeGraph, _add_node

DOC_EXTS = {".md", ".mdx"}
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MDLINK = re.compile(r"\]\(([^)#\s]+\.(?:md|mdx))\)", re.I)
CODE_LINK = re.compile(r"\]\(([^)#\s]+\.(?:py|ts|tsx|js|jsx|go|java))\)", re.I)

DOC_KINDS = {"doc", "folder", "vault", "wikilink_stub"}
DOC_EDGE_KINDS = {"wikilink", "md_link", "in_folder", "references"}


def _label_of(rel: str) -> str:
    stem = Path(rel).stem
    if stem.upper() in ("SKILL", "README", "INDEX"):
        parent = Path(rel).parent.name
        return parent or stem
    return stem


def _doc_node_id(path: str, kind: str, name: str) -> str:
    import hashlib

    return hashlib.sha1(f"doc:{path}:{kind}:{name}".encode()).hexdigest()[:16]


def ingest_markdown_graph(
    root_path: Path,
    graph: LatticeGraph,
    seen: set[str],
    max_files: int = 2000,
) -> dict[str, int]:
    """Walk markdown files and add doc nodes/edges to an existing Lattice graph."""
    stats = {
        "doc_files_indexed": 0,
        "wikilinks_resolved": 0,
        "wikilinks_unresolved": 0,
    }
    md_files: list[tuple[str, Path]] = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in DOC_EXTS:
                continue
            fpath = Path(dirpath) / fname
            rel = str(fpath.relative_to(root_path)).replace("\\", "/")
            md_files.append((rel, fpath))
            count += 1
            if count >= max_files:
                break
        if count >= max_files:
            break

    if not md_files:
        return stats

    stem_map: dict[str, str] = {}
    for rel, _ in md_files:
        stem_map.setdefault(Path(rel).stem.lower(), rel)

    vault_id = _add_node(
        graph,
        GraphNode(
            id=_doc_node_id("__vault__", "vault", "__vault__"),
            kind="vault",
            name=root_path.name or "Vault",
            path="__vault__",
            group="vault",
            title=root_path.name or "Vault",
        ),
        seen,
    )

    doc_ids: dict[str, str] = {}
    folder_ids: dict[str, str] = {}

    for rel, fpath in md_files:
        top = rel.split("/")[0] if "/" in rel else None
        group = top or "root"
        doc_id = _add_node(
            graph,
            GraphNode(
                id=_doc_node_id(rel, "doc", rel),
                kind="doc",
                name=_label_of(rel),
                path=rel,
                group=group,
                slug=Path(rel).stem.lower(),
                title=_label_of(rel),
            ),
            seen,
        )
        doc_ids[rel] = doc_id
        stats["doc_files_indexed"] += 1

        if top:
            dir_key = top
            if dir_key not in folder_ids:
                folder_ids[dir_key] = _add_node(
                    graph,
                    GraphNode(
                        id=_doc_node_id(f"__dir__{dir_key}", "folder", f"__dir__{dir_key}"),
                        kind="folder",
                        name=dir_key,
                        path=f"__dir__{dir_key}",
                        group=dir_key,
                        title=dir_key,
                    ),
                    seen,
                )
            graph.edges.append(GraphEdge(source=folder_ids[dir_key], target=doc_id, kind="in_folder"))
            graph.edges.append(GraphEdge(source=vault_id, target=folder_ids[dir_key], kind="in_folder"))
        else:
            graph.edges.append(GraphEdge(source=vault_id, target=doc_id, kind="in_folder"))

    file_node_by_path = {n.path: n.id for n in graph.nodes if n.kind == "file"}

    for rel, fpath in md_files:
        src_id = doc_ids[rel]
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in WIKILINK.finditer(text):
            target_stem = m.group(1).strip().lower()
            tgt_rel = stem_map.get(target_stem)
            if tgt_rel and tgt_rel in doc_ids and tgt_rel != rel:
                graph.edges.append(GraphEdge(source=src_id, target=doc_ids[tgt_rel], kind="wikilink"))
                stats["wikilinks_resolved"] += 1
            else:
                stub_path = f"__wikilink__{target_stem}"
                stub_id = _add_node(
                    graph,
                    GraphNode(
                        id=_doc_node_id(stub_path, "wikilink_stub", stub_path),
                        kind="wikilink_stub",
                        name=target_stem,
                        path=stub_path,
                        slug=target_stem,
                        title=target_stem,
                    ),
                    seen,
                )
                graph.edges.append(GraphEdge(source=src_id, target=stub_id, kind="wikilink"))
                stats["wikilinks_unresolved"] += 1

        for m in MDLINK.finditer(text):
            raw = m.group(1)
            if raw.startswith(("http:", "https:")):
                continue
            tgt_abs = (fpath.parent / raw).resolve()
            try:
                tgt_rel = str(tgt_abs.relative_to(root_path)).replace("\\", "/")
            except ValueError:
                continue
            if tgt_rel in doc_ids and tgt_rel != rel:
                graph.edges.append(GraphEdge(source=src_id, target=doc_ids[tgt_rel], kind="md_link"))
                stats["wikilinks_resolved"] += 1

        for m in CODE_LINK.finditer(text):
            raw = m.group(1)
            tgt_abs = (fpath.parent / raw).resolve()
            try:
                tgt_rel = str(tgt_abs.relative_to(root_path)).replace("\\", "/")
            except ValueError:
                continue
            code_id = file_node_by_path.get(tgt_rel)
            if code_id:
                graph.edges.append(GraphEdge(source=src_id, target=code_id, kind="references"))

    return stats


def doc_backlinks(project_key: str, doc_ref: str, limit: int = 50) -> dict:
    from app.services.lattice.indexer import get_graph

    g = get_graph(project_key)
    if not g:
        return {"backlinks": [], "error": "graph_not_found"}
    ref_l = doc_ref.lower()
    targets = [
        n
        for n in g.nodes
        if n.kind in DOC_KINDS
        and (n.id == doc_ref or n.path == doc_ref or ref_l in n.name.lower() or ref_l in n.path.lower())
    ]
    if not targets:
        return {"backlinks": [], "error": "doc_not_found"}
    target_ids = {t.id for t in targets}
    backlinks = []
    for e in g.edges:
        if e.kind in DOC_EDGE_KINDS and e.target in target_ids and e.source not in target_ids:
            src = next((n for n in g.nodes if n.id == e.source), None)
            if src:
                backlinks.append({"source": asdict(src), "edge_kind": e.kind})
        if len(backlinks) >= limit:
            break
    return {"doc": doc_ref, "backlinks": backlinks[:limit], "count": len(backlinks)}


def filter_graph_layer(data: dict, layer: str = "combined") -> dict:
    layer = (layer or "combined").lower()
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    if layer == "code":
        code_kinds = {"file", "class", "function", "method", "import", "endpoint", "business"}
        fn = lambda n: n.get("kind") in code_kinds
    elif layer == "docs":
        fn = lambda n: n.get("kind") in DOC_KINDS
    else:
        return {**data, "layer": "combined"}
    kept_ids = {n["id"] for n in nodes if fn(n)}
    return {
        **data,
        "nodes": [n for n in nodes if n["id"] in kept_ids],
        "edges": [e for e in edges if e.get("source") in kept_ids and e.get("target") in kept_ids],
        "layer": layer,
    }

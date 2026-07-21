"""Lattice graph indexer — AST-lite + import edges for Mentrix Understand."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", "target", "coverage", ".tox", ".mypy_cache",
}

LANG_EXTS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
}


@dataclass
class GraphNode:
    id: str
    kind: str
    name: str
    path: str
    language: str = ""
    line: int | None = None


@dataclass
class GraphEdge:
    source: str
    target: str
    kind: str


@dataclass
class LatticeGraph:
    project_key: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    files_indexed: int = 0
    symbols: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_key": self.project_key,
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "files_indexed": self.files_indexed,
            "symbols": self.symbols,
            "languages": self.languages,
            "errors": self.errors,
        }


_GRAPH_CACHE: dict[str, LatticeGraph] = {}
_FILE_HASH: dict[str, str] = {}


def _cache_dir() -> Path:
    root = Path(os.getenv("LATTICE_CACHE_DIR", "./data/lattice"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _node_id(path: str, kind: str, name: str) -> str:
    return hashlib.sha1(f"{path}:{kind}:{name}".encode()).hexdigest()[:16]


def _parse_python(path: str, content: str, graph: LatticeGraph) -> None:
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        graph.errors.append(f"{path}: {exc}")
        return
    file_id = _node_id(path, "file", path)
    graph.nodes.append(GraphNode(id=file_id, kind="file", name=Path(path).name, path=path, language="python"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            nid = _node_id(path, "class", node.name)
            graph.nodes.append(GraphNode(id=nid, kind="class", name=node.name, path=path, language="python", line=node.lineno))
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nid = _node_id(path, "function", node.name)
            graph.nodes.append(GraphNode(id=nid, kind="function", name=node.name, path=path, language="python", line=node.lineno))
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1
        elif isinstance(node, ast.Import):
            for alias in node.names:
                tid = _node_id(path, "import", alias.name)
                graph.nodes.append(GraphNode(id=tid, kind="import", name=alias.name, path=path, language="python"))
                graph.edges.append(GraphEdge(source=file_id, target=tid, kind="imports"))
        elif isinstance(node, ast.ImportFrom) and node.module:
            tid = _node_id(path, "import", node.module)
            graph.nodes.append(GraphNode(id=tid, kind="import", name=node.module, path=path, language="python"))
            graph.edges.append(GraphEdge(source=file_id, target=tid, kind="imports"))


_TS_CLASS = re.compile(r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)")
_TS_FUNC = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)")
_TS_IMPORT = re.compile(r"""import\s+.*?from\s+['"]([^'"]+)['"]""")
_JAVA_CLASS = re.compile(r"(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?class\s+(\w+)")
_JAVA_METHOD = re.compile(r"(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(")
_GO_FUNC = re.compile(r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(")
_GO_IMPORT = re.compile(r'"([^"]+)"')


def _parse_regex(path: str, content: str, language: str, graph: LatticeGraph) -> None:
    file_id = _node_id(path, "file", path)
    graph.nodes.append(GraphNode(id=file_id, kind="file", name=Path(path).name, path=path, language=language))
    if language in ("typescript", "javascript"):
        for rx, kind in ((_TS_CLASS, "class"), (_TS_FUNC, "function")):
            for m in rx.finditer(content):
                nid = _node_id(path, kind, m.group(1))
                graph.nodes.append(GraphNode(id=nid, kind=kind, name=m.group(1), path=path, language=language))
                graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
                graph.symbols += 1
        for m in _TS_IMPORT.finditer(content):
            tid = _node_id(path, "import", m.group(1))
            graph.nodes.append(GraphNode(id=tid, kind="import", name=m.group(1), path=path, language=language))
            graph.edges.append(GraphEdge(source=file_id, target=tid, kind="imports"))
    elif language == "java":
        for m in _JAVA_CLASS.finditer(content):
            nid = _node_id(path, "class", m.group(1))
            graph.nodes.append(GraphNode(id=nid, kind="class", name=m.group(1), path=path, language=language))
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1
        for m in _JAVA_METHOD.finditer(content):
            if m.group(1) in ("if", "for", "while", "switch", "catch"):
                continue
            nid = _node_id(path, "method", m.group(1))
            graph.nodes.append(GraphNode(id=nid, kind="method", name=m.group(1), path=path, language=language))
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1
    elif language == "go":
        for m in _GO_FUNC.finditer(content):
            nid = _node_id(path, "function", m.group(1))
            graph.nodes.append(GraphNode(id=nid, kind="function", name=m.group(1), path=path, language=language))
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1


def ingest_path(root: str, project_key: str = "", max_files: int = 2000) -> LatticeGraph:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")
    key = project_key or str(root_path)
    graph = LatticeGraph(project_key=key)
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            lang = LANG_EXTS.get(ext)
            if not lang:
                continue
            fpath = Path(dirpath) / fname
            rel = str(fpath.relative_to(root_path)).replace("\\", "/")
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                graph.errors.append(f"{rel}: {exc}")
                continue
            digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
            cache_key = f"{key}:{rel}"
            if _FILE_HASH.get(cache_key) == digest and key in _GRAPH_CACHE:
                continue
            _FILE_HASH[cache_key] = digest
            if lang == "python":
                _parse_python(rel, content, graph)
            else:
                _parse_regex(rel, content, lang, graph)
            graph.languages[lang] = graph.languages.get(lang, 0) + 1
            count += 1
            if count >= max_files:
                graph.errors.append(f"Stopped at max_files={max_files}")
                break
        if count >= max_files:
            break
    graph.files_indexed = count
    # Deduplicate nodes by id
    seen: set[str] = set()
    uniq_nodes = []
    for n in graph.nodes:
        if n.id in seen:
            continue
        seen.add(n.id)
        uniq_nodes.append(n)
    graph.nodes = uniq_nodes
    _GRAPH_CACHE[key] = graph
    out = _cache_dir() / f"{hashlib.sha1(key.encode()).hexdigest()}.json"
    out.write_text(json.dumps(graph.to_dict()), encoding="utf-8")
    return graph


def get_graph(project_key: str) -> LatticeGraph | None:
    if project_key in _GRAPH_CACHE:
        return _GRAPH_CACHE[project_key]
    out = _cache_dir() / f"{hashlib.sha1(project_key.encode()).hexdigest()}.json"
    if out.is_file():
        data = json.loads(out.read_text(encoding="utf-8"))
        g = LatticeGraph(
            project_key=data["project_key"],
            nodes=[GraphNode(**n) for n in data.get("nodes", [])],
            edges=[GraphEdge(**e) for e in data.get("edges", [])],
            files_indexed=data.get("files_indexed", 0),
            symbols=data.get("symbols", 0),
            languages=data.get("languages", {}),
            errors=data.get("errors", []),
        )
        _GRAPH_CACHE[project_key] = g
        return g
    return None


def query_graph(project_key: str, q: str, limit: int = 50) -> list[dict[str, Any]]:
    g = get_graph(project_key)
    if not g:
        return []
    ql = q.lower()
    hits = [asdict(n) for n in g.nodes if ql in n.name.lower() or ql in n.path.lower()]
    return hits[:limit]

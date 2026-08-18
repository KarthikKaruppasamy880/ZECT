"""Lattice graph indexer — symbols, resolved imports, calls, path/explain for Mentrix."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from collections import deque
from dataclasses import asdict, dataclass, field
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
    group: str = ""
    slug: str = ""
    title: str = ""


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
    doc_files_indexed: int = 0
    wikilinks_resolved: int = 0
    wikilinks_unresolved: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_key": self.project_key,
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "files_indexed": self.files_indexed,
            "symbols": self.symbols,
            "languages": self.languages,
            "errors": self.errors,
            "doc_files_indexed": self.doc_files_indexed,
            "wikilinks_resolved": self.wikilinks_resolved,
            "wikilinks_unresolved": self.wikilinks_unresolved,
        }


_GRAPH_CACHE: dict[str, LatticeGraph] = {}
_FILE_HASH: dict[str, str] = {}


def derive_project_key(owner: str, repo_name: str) -> str:
    """Per-root Lattice key. Must match frontend deriveProjectKey(owner, repo)."""
    raw = f"{(owner or '').strip()}-{(repo_name or '').strip()}".lower()
    return re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-") or "repo"

_TS_CLASS = re.compile(r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)")
_TS_FUNC = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)")
_TS_IMPORT = re.compile(r"""import\s+.*?from\s+['"]([^'"]+)['"]""")
_TS_CALL = re.compile(r"\b([A-Za-z_][\w]*)\s*\(")
_JAVA_CLASS = re.compile(r"(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?class\s+(\w+)")
_JAVA_METHOD = re.compile(r"(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(")
_GO_FUNC = re.compile(r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(")
_FASTAPI_DECORATOR = re.compile(
    r"""@(?:app|router)\.(get|post|put|patch|delete|options|head)\(\s*['"]([^'"]+)['"]""",
    re.I,
)
_EXPRESS_ROUTE = re.compile(
    r"""(?:app|router)\.(get|post|put|patch|delete)\(\s*['"]([^'"]+)['"]""",
    re.I,
)
_FLASK_ROUTE = re.compile(
    r"""@(?:app|bp|blueprint)\.route\(\s*['"]([^'"]+)['"]""",
    re.I,
)


def _cache_dir() -> Path:
    root = Path(os.getenv("LATTICE_CACHE_DIR", "./data/lattice"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _node_id(path: str, kind: str, name: str) -> str:
    return hashlib.sha1(f"{path}:{kind}:{name}".encode()).hexdigest()[:16]


def _add_node(graph: LatticeGraph, node: GraphNode, seen: set[str]) -> str:
    if node.id not in seen:
        seen.add(node.id)
        graph.nodes.append(node)
    return node.id


def _parse_python(path: str, content: str, graph: LatticeGraph, seen: set[str]) -> None:
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        graph.errors.append(f"{path}: {exc}")
        return
    file_id = _add_node(
        graph,
        GraphNode(id=_node_id(path, "file", path), kind="file", name=Path(path).name, path=path, language="python"),
        seen,
    )
    local_funcs: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            nid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "class", node.name),
                    kind="class",
                    name=node.name,
                    path=path,
                    language="python",
                    line=node.lineno,
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mid = _add_node(
                        graph,
                        GraphNode(
                            id=_node_id(path, "function", f"{node.name}.{item.name}"),
                            kind="function",
                            name=f"{node.name}.{item.name}",
                            path=path,
                            language="python",
                            line=item.lineno,
                        ),
                        seen,
                    )
                    graph.edges.append(GraphEdge(source=nid, target=mid, kind="contains"))
                    local_funcs[item.name] = mid
                    local_funcs[f"{node.name}.{item.name}"] = mid
                    graph.symbols += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "function", node.name),
                    kind="function",
                    name=node.name,
                    path=path,
                    language="python",
                    line=node.lineno,
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            local_funcs[node.name] = nid
            graph.symbols += 1
        elif isinstance(node, ast.Import):
            for alias in node.names:
                tid = _add_node(
                    graph,
                    GraphNode(
                        id=_node_id(path, "import", alias.name),
                        kind="import",
                        name=alias.name,
                        path=path,
                        language="python",
                    ),
                    seen,
                )
                graph.edges.append(GraphEdge(source=file_id, target=tid, kind="imports"))
        elif isinstance(node, ast.ImportFrom):
            level = getattr(node, "level", 0) or 0
            mod = node.module or ""
            imp_name = f"{'.' * level}{mod}" if level else mod
            if not imp_name:
                continue
            tid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "import", imp_name),
                    kind="import",
                    name=imp_name,
                    path=path,
                    language="python",
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=tid, kind="imports"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = None
            if isinstance(node.func, ast.Name):
                callee = node.func.id
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                callee = node.func.attr
            if callee and callee in local_funcs:
                # Attribute calls from methods — link from enclosing function when possible
                continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            caller_id = local_funcs.get(node.name) or local_funcs.get(
                next((k for k in local_funcs if k.endswith(f".{node.name}")), "")
            )
            if not caller_id:
                # class methods keyed as Class.method
                for k, vid in local_funcs.items():
                    if k.endswith(f".{node.name}"):
                        caller_id = vid
                        break
            if not caller_id:
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                name = None
                if isinstance(child.func, ast.Name):
                    name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    name = child.func.attr
                if not name:
                    continue
                target = local_funcs.get(name)
                if not target:
                    for k, vid in local_funcs.items():
                        if k.endswith(f".{name}") or k == name:
                            target = vid
                            break
                if target and target != caller_id:
                    graph.edges.append(GraphEdge(source=caller_id, target=target, kind="calls"))

    for m in _FASTAPI_DECORATOR.finditer(content):
        method, route = m.group(1).upper(), m.group(2)
        ename = f"{method} {route}"
        eid = _add_node(
            graph,
            GraphNode(
                id=_node_id(path, "endpoint", ename),
                kind="endpoint",
                name=ename,
                path=path,
                language="python",
            ),
            seen,
        )
        graph.edges.append(GraphEdge(source=file_id, target=eid, kind="exposes"))
        bid = _add_node(
            graph,
            GraphNode(
                id=_node_id(path, "business", route),
                kind="business",
                name=route,
                path=path,
                language="python",
            ),
            seen,
        )
        graph.edges.append(GraphEdge(source=eid, target=bid, kind="implements"))
    for m in _FLASK_ROUTE.finditer(content):
        route = m.group(1)
        ename = f"ROUTE {route}"
        eid = _add_node(
            graph,
            GraphNode(
                id=_node_id(path, "endpoint", ename),
                kind="endpoint",
                name=ename,
                path=path,
                language="python",
            ),
            seen,
        )
        graph.edges.append(GraphEdge(source=file_id, target=eid, kind="exposes"))


def _parse_regex(path: str, content: str, language: str, graph: LatticeGraph, seen: set[str]) -> None:
    file_id = _add_node(
        graph,
        GraphNode(
            id=_node_id(path, "file", path),
            kind="file",
            name=Path(path).name,
            path=path,
            language=language,
        ),
        seen,
    )
    local: dict[str, str] = {}
    if language in ("typescript", "javascript"):
        for rx, kind in ((_TS_CLASS, "class"), (_TS_FUNC, "function")):
            for m in rx.finditer(content):
                nid = _add_node(
                    graph,
                    GraphNode(
                        id=_node_id(path, kind, m.group(1)),
                        kind=kind,
                        name=m.group(1),
                        path=path,
                        language=language,
                    ),
                    seen,
                )
                graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
                local[m.group(1)] = nid
                graph.symbols += 1
        for m in _TS_IMPORT.finditer(content):
            tid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "import", m.group(1)),
                    kind="import",
                    name=m.group(1),
                    path=path,
                    language=language,
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=tid, kind="imports"))
        # Light call edges within file
        for m in _TS_CALL.finditer(content):
            name = m.group(1)
            if name in ("if", "for", "while", "switch", "catch", "function", "return", "await"):
                continue
            if name in local:
                # attribute to file → symbol as weak call from file
                graph.edges.append(GraphEdge(source=file_id, target=local[name], kind="calls"))
        for m in _EXPRESS_ROUTE.finditer(content):
            method, route = m.group(1).upper(), m.group(2)
            ename = f"{method} {route}"
            eid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "endpoint", ename),
                    kind="endpoint",
                    name=ename,
                    path=path,
                    language=language,
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=eid, kind="exposes"))
    elif language == "java":
        for m in _JAVA_CLASS.finditer(content):
            nid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "class", m.group(1)),
                    kind="class",
                    name=m.group(1),
                    path=path,
                    language=language,
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1
        for m in _JAVA_METHOD.finditer(content):
            if m.group(1) in ("if", "for", "while", "switch", "catch"):
                continue
            nid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "method", m.group(1)),
                    kind="method",
                    name=m.group(1),
                    path=path,
                    language=language,
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1
    elif language == "go":
        for m in _GO_FUNC.finditer(content):
            nid = _add_node(
                graph,
                GraphNode(
                    id=_node_id(path, "function", m.group(1)),
                    kind="function",
                    name=m.group(1),
                    path=path,
                    language=language,
                ),
                seen,
            )
            graph.edges.append(GraphEdge(source=file_id, target=nid, kind="contains"))
            graph.symbols += 1


def _resolve_imports(graph: LatticeGraph, seen: set[str]) -> None:
    """Map relative import nodes to file nodes (imports_file edges)."""
    files_by_stem: dict[str, str] = {}
    files_by_path: dict[str, str] = {}
    for n in graph.nodes:
        if n.kind != "file":
            continue
        files_by_path[n.path] = n.id
        stem = n.path.rsplit(".", 1)[0]
        files_by_stem[stem] = n.id
        files_by_stem[stem.replace("\\", "/")] = n.id

    new_edges: list[GraphEdge] = []
    for e in graph.edges:
        if e.kind != "imports":
            continue
        imp = next((n for n in graph.nodes if n.id == e.target and n.kind == "import"), None)
        src = next((n for n in graph.nodes if n.id == e.source and n.kind == "file"), None)
        if not imp or not src:
            continue
        name = imp.name
        candidates: list[str] = []
        if name.startswith("."):
            # Python: .a / ..b.mod  or JS: ./foo / ../bar
            if name.startswith("./") or name.startswith("../"):
                base = Path(src.path).parent
                rel = name
                while rel.startswith("./"):
                    rel = rel[2:]
                ups = 0
                while rel.startswith("../"):
                    ups += 1
                    rel = rel[3:]
                cur = base
                for _ in range(ups):
                    cur = cur.parent if cur != Path(".") else cur
                target_rel = str((cur / rel).as_posix()).lstrip("./")
            else:
                level = 0
                rest = name
                while rest.startswith("."):
                    level += 1
                    rest = rest[1:]
                base = Path(src.path).parent
                for _ in range(max(0, level - 1)):
                    base = base.parent
                target_rel = str((base / rest.replace(".", "/")).as_posix()).lstrip("./") if rest else str(base.as_posix())
            for ext in ("", ".py", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js", "/__init__.py"):
                if ext == "/__init__.py":
                    candidates.append(f"{target_rel}/__init__.py")
                elif ext:
                    candidates.append(target_rel + ext)
                else:
                    candidates.append(target_rel)
        else:
            # package-style: app.services.foo → app/services/foo.py
            dotted = name.replace(".", "/")
            for ext in (".py", "/__init__.py", ".ts", ".tsx", ".js"):
                candidates.append(dotted + ext if not ext.startswith("/") else dotted + ext)

        resolved = None
        for c in candidates:
            c_norm = c.replace("\\", "/").lstrip("/")
            if c_norm in files_by_path:
                resolved = files_by_path[c_norm]
                break
            stem = c_norm.rsplit(".", 1)[0] if "." in Path(c_norm).name else c_norm
            if stem in files_by_stem:
                resolved = files_by_stem[stem]
                break
        if resolved:
            new_edges.append(GraphEdge(source=e.source, target=resolved, kind="imports_file"))

    # Dedup edges
    edge_keys = {(e.source, e.target, e.kind) for e in graph.edges}
    for e in new_edges:
        key = (e.source, e.target, e.kind)
        if key not in edge_keys:
            graph.edges.append(e)
            edge_keys.add(key)


def _node_from_dict(n: dict[str, Any]) -> GraphNode:
    fields_set = {f.name for f in GraphNode.__dataclass_fields__.values()}
    return GraphNode(**{k: v for k, v in n.items() if k in fields_set})


class LatticeCancelled(RuntimeError):
    """Cooperative cancel during lattice ingest — cache is not written."""


def ingest_path(
    root: str,
    project_key: str = "",
    max_files: int = 2000,
    index_docs: bool = True,
    cancel_check=None,
) -> LatticeGraph:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")
    key = project_key or str(root_path)
    graph = LatticeGraph(project_key=key)
    seen: set[str] = set()
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
            if cancel_check is not None and cancel_check():
                raise LatticeCancelled("lattice_cancelled")
            _FILE_HASH[cache_key] = digest
            if lang == "python":
                _parse_python(rel, content, graph, seen)
            else:
                _parse_regex(rel, content, lang, graph, seen)
            graph.languages[lang] = graph.languages.get(lang, 0) + 1
            count += 1
            if count >= max_files:
                graph.errors.append(f"Stopped at max_files={max_files}")
                break
        if count >= max_files:
            break
    graph.files_indexed = count
    _resolve_imports(graph, seen)
    if index_docs and os.getenv("LATTICE_INDEX_DOCS", "1").strip().lower() not in ("0", "false", "off"):
        from app.services.lattice.markdown_graph import ingest_markdown_graph

        doc_stats = ingest_markdown_graph(root_path, graph, seen, max_files=max_files)
        graph.doc_files_indexed = doc_stats.get("doc_files_indexed", 0)
        graph.wikilinks_resolved = doc_stats.get("wikilinks_resolved", 0)
        graph.wikilinks_unresolved = doc_stats.get("wikilinks_unresolved", 0)
    # Deduplicate call edges
    edge_keys = set()
    uniq_edges = []
    for e in graph.edges:
        k = (e.source, e.target, e.kind)
        if k in edge_keys:
            continue
        edge_keys.add(k)
        uniq_edges.append(e)
    graph.edges = uniq_edges
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
            nodes=[_node_from_dict(n) for n in data.get("nodes", [])],
            edges=[GraphEdge(**e) for e in data.get("edges", [])],
            files_indexed=data.get("files_indexed", 0),
            symbols=data.get("symbols", 0),
            languages=data.get("languages", {}),
            errors=data.get("errors", []),
            doc_files_indexed=data.get("doc_files_indexed", 0),
            wikilinks_resolved=data.get("wikilinks_resolved", 0),
            wikilinks_unresolved=data.get("wikilinks_unresolved", 0),
        )
        _GRAPH_CACHE[project_key] = g
        return g
    return None


LATTICE_STATES = (
    "NOT_CONFIGURED",
    "NOT_INDEXED",
    "INDEXING",
    "READY",
    "STALE",
    "ERROR",
    "NOT_APPLICABLE",
    "REGRESSION",
)


def get_lattice_status(
    project_key: str,
    *,
    db: Any = None,
    repository_id: int | None = None,
) -> dict[str, Any]:
    """Canonical Lattice state for Developer/PI. Never return a vague MISSING."""
    pk = (project_key or "").strip()
    if not pk:
        return {
            "state": "NOT_APPLICABLE",
            "indexed": False,
            "project_key": "",
            "reason": "no_project_key",
            "action": None,
            "action_label": "Select a project or repository",
        }
    graph = get_graph(pk)
    repo = None
    if db is not None and repository_id:
        try:
            from app.models import Repo

            repo = db.query(Repo).filter(Repo.id == repository_id).first()
        except Exception:  # noqa: BLE001
            repo = None

    clone_status = str(getattr(repo, "clone_status", "") or "")
    stats = getattr(repo, "index_stats", None) if repo is not None else None
    indexing_flag = str(stats.get("indexing") or "") if isinstance(stats, dict) else ""
    if clone_status == "cloning" or indexing_flag.lower() in {"1", "true"}:
        return {
            "state": "INDEXING",
            "indexed": False,
            "project_key": pk,
            "reason": "index_in_progress",
            "action": "wait",
            "action_label": "Indexing in progress",
            "clone_status": clone_status,
        }
    if graph and graph.errors and int(graph.files_indexed or 0) == 0:
        return {
            "state": "ERROR",
            "indexed": False,
            "project_key": pk,
            "reason": "index_failed",
            "action": "reindex",
            "action_label": "Re-index repository",
            "errors": list(graph.errors)[:8],
        }
    if not graph:
        if repo and clone_status in {"", "not_cloned"}:
            return {
                "state": "NOT_CONFIGURED",
                "indexed": False,
                "project_key": pk,
                "reason": "repo_not_cloned",
                "action": "clone_or_index",
                "action_label": "Clone or index repository",
                "repository_id": repository_id,
            }
        return {
            "state": "NOT_INDEXED",
            "indexed": False,
            "project_key": pk,
            "reason": "graph_missing",
            "action": "index_repository",
            "action_label": "Index repository",
            "repository_id": repository_id,
        }

    stale = False
    indexed_at = getattr(repo, "indexed_at", None) if repo else None
    last_pulled = getattr(repo, "last_pulled_at", None) if repo else None
    if indexed_at and last_pulled and last_pulled > indexed_at:
        stale = True
    indexed_sha = ""
    if db is not None and pk:
        try:
            from app.models import LatticeStructuralBlueprint

            bp_row = (
                db.query(LatticeStructuralBlueprint)
                .filter(LatticeStructuralBlueprint.project_key == pk)
                .first()
            )
            indexed_sha = str(getattr(bp_row, "indexed_commit_sha", "") or "")
        except Exception:  # noqa: BLE001
            indexed_sha = ""
    live_sha = ""
    local_path = str(getattr(repo, "local_path", "") or "") if repo is not None else ""
    if local_path:
        try:
            from app.services.work_items.multi_repo_context import git_head_sha

            live_sha = git_head_sha(local_path) or ""
        except Exception:  # noqa: BLE001
            live_sha = ""
    commit_stale = bool(indexed_sha and live_sha and indexed_sha[:12] != live_sha[:12])
    if commit_stale:
        stale = True
    state = "STALE" if stale else "READY"
    reason = "graph_ready"
    if commit_stale:
        reason = "commit_moved"
    elif indexed_at and last_pulled and last_pulled > indexed_at:
        reason = "pulled_after_index"
    return {
        "state": state,
        "indexed": True,
        "project_key": pk,
        "reason": reason,
        "action": "reindex" if stale else "view_intelligence",
        "action_label": "Re-index repository" if stale else "View intelligence",
        "files_indexed": graph.files_indexed,
        "symbols": graph.symbols,
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "languages": graph.languages,
        "errors": list(graph.errors)[:8],
        "indexed_at": indexed_at.isoformat() if indexed_at else None,
        "last_pulled_at": last_pulled.isoformat() if last_pulled else None,
        "repository_id": repository_id,
        "indexed_commit_sha": indexed_sha,
        "live_commit_sha": live_sha,
    }


def query_graph(
    project_key: str,
    q: str,
    limit: int = 50,
    kinds: list[str] | None = None,
) -> list[dict[str, Any]]:
    g = get_graph(project_key)
    if not g:
        return []
    ql = q.lower()
    kind_set = set(kinds) if kinds else None
    hits = []
    for n in g.nodes:
        if kind_set and n.kind not in kind_set:
            continue
        hay = " ".join(
            x for x in (n.name, n.path, n.title, n.slug, n.group) if x
        ).lower()
        if ql in hay:
            hits.append(asdict(n))
    return hits[:limit]


def _find_nodes(g: LatticeGraph, ref: str) -> list[GraphNode]:
    rl = ref.lower()
    exact = [n for n in g.nodes if n.id == ref or n.name == ref or n.path == ref]
    if exact:
        return exact
    return [n for n in g.nodes if rl in n.name.lower() or rl in n.path.lower()][:5]


def neighbors(
    project_key: str,
    node_ref: str,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    g = get_graph(project_key)
    if not g:
        return {"nodes": [], "edges": [], "error": "graph_not_found"}
    seeds = _find_nodes(g, node_ref)
    if not seeds:
        return {"nodes": [], "edges": [], "error": "node_not_found"}
    seed_ids = {s.id for s in seeds}
    adj: dict[str, list[GraphEdge]] = {}
    for e in g.edges:
        adj.setdefault(e.source, []).append(e)
        adj.setdefault(e.target, []).append(e)
    seen = set(seed_ids)
    frontier = set(seed_ids)
    kept_edges: list[GraphEdge] = []
    for _ in range(max(1, depth)):
        nxt = set()
        for nid in frontier:
            for e in adj.get(nid, []):
                other = e.target if e.source == nid else e.source
                kept_edges.append(e)
                if other not in seen:
                    seen.add(other)
                    nxt.add(other)
        frontier = nxt
        if len(seen) >= limit:
            break
    nodes = [asdict(n) for n in g.nodes if n.id in seen][:limit]
    edge_dicts = []
    ek = set()
    for e in kept_edges:
        k = (e.source, e.target, e.kind)
        if k in ek:
            continue
        ek.add(k)
        edge_dicts.append(asdict(e))
        if len(edge_dicts) >= limit * 2:
            break
    return {"seeds": [asdict(s) for s in seeds], "nodes": nodes, "edges": edge_dicts}


def find_path(
    project_key: str,
    source_ref: str,
    target_ref: str,
    max_depth: int = 8,
) -> dict[str, Any]:
    g = get_graph(project_key)
    if not g:
        return {"path": [], "edges": [], "error": "graph_not_found"}
    sources = _find_nodes(g, source_ref)
    targets = _find_nodes(g, target_ref)
    if not sources or not targets:
        return {"path": [], "edges": [], "error": "endpoint_not_found"}
    target_ids = {t.id for t in targets}
    adj: dict[str, list[tuple[str, GraphEdge]]] = {}
    for e in g.edges:
        adj.setdefault(e.source, []).append((e.target, e))
        adj.setdefault(e.target, []).append((e.source, e))  # undirected for impact

    for start in sources:
        q: deque[tuple[str, int]] = deque([(start.id, 0)])
        parent: dict[str, tuple[str | None, GraphEdge | None]] = {start.id: (None, None)}
        while q:
            cur, depth = q.popleft()
            if cur in target_ids and cur != start.id:
                node_ids = [cur]
                edges_rev: list[GraphEdge] = []
                walk = cur
                while parent[walk][0] is not None:
                    prev, edge = parent[walk]
                    if edge:
                        edges_rev.append(edge)
                    walk = prev  # type: ignore[assignment]
                    node_ids.append(walk)
                node_ids.reverse()
                edges_rev.reverse()
                id_to_node = {n.id: n for n in g.nodes}
                return {
                    "path": [asdict(id_to_node[i]) for i in node_ids if i in id_to_node],
                    "edges": [asdict(e) for e in edges_rev],
                    "length": len(node_ids) - 1,
                }
            if depth >= max_depth:
                continue
            for nxt, edge in adj.get(cur, []):
                if nxt not in parent:
                    parent[nxt] = (cur, edge)
                    q.append((nxt, depth + 1))
    return {"path": [], "edges": [], "error": "no_path"}


def explain(
    project_key: str,
    source_ref: str = "",
    target_ref: str = "",
    node_ref: str = "",
) -> dict[str, Any]:
    """Template explain: path between two refs, or 1-hop neighborhood of one node."""
    if source_ref and target_ref:
        path_info = find_path(project_key, source_ref, target_ref)
        nodes = path_info.get("path") or []
        edges = path_info.get("edges") or []
        if not nodes:
            return {
                "summary": f"No path found between '{source_ref}' and '{target_ref}'.",
                "path": path_info,
            }
        names = " → ".join(n.get("name", "?") for n in nodes)
        kinds = ", ".join(sorted({e.get("kind", "?") for e in edges}))
        return {
            "summary": f"Path ({path_info.get('length', 0)} hops): {names}. Edge kinds: {kinds}.",
            "path": path_info,
            "nodes": nodes,
            "edges": edges,
        }
    ref = node_ref or source_ref or target_ref
    if not ref:
        return {"summary": "Provide node_ref or source_ref/target_ref.", "neighbors": {}}
    nb = neighbors(project_key, ref, depth=1, limit=40)
    node_names = [n.get("name") for n in nb.get("nodes", [])][:12]
    edge_kinds = sorted({e.get("kind") for e in nb.get("edges", [])})
    return {
        "summary": (
            f"Neighborhood of '{ref}': {len(nb.get('nodes', []))} nodes, "
            f"edge kinds {edge_kinds}. Related: {', '.join(str(x) for x in node_names)}."
        ),
        "neighbors": nb,
    }


def god_nodes(project_key: str, limit: int = 20) -> list[dict[str, Any]]:
    """Highest-degree nodes (Graphify-class 'god nodes' via simple degree ranking)."""
    g = get_graph(project_key)
    if not g:
        return []
    degree: dict[str, int] = {}
    for e in g.edges:
        degree[e.source] = degree.get(e.source, 0) + 1
        degree[e.target] = degree.get(e.target, 0) + 1
    id_to_node = {n.id: n for n in g.nodes}
    ranked = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:limit]
    out = []
    for nid, deg in ranked:
        n = id_to_node.get(nid)
        if not n:
            continue
        out.append({**asdict(n), "degree": deg})
    return out


def communities(project_key: str, limit: int = 12) -> list[dict[str, Any]]:
    """Connected-component style communities (lightweight, no Leiden/Neo4j)."""
    g = get_graph(project_key)
    if not g:
        return []
    adj: dict[str, set[str]] = {}
    for e in g.edges:
        adj.setdefault(e.source, set()).add(e.target)
        adj.setdefault(e.target, set()).add(e.source)
    seen: set[str] = set()
    comps: list[list[str]] = []
    for n in g.nodes:
        if n.id in seen:
            continue
        stack = [n.id]
        comp: list[str] = []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.append(cur)
            stack.extend(adj.get(cur, set()) - seen)
        if len(comp) >= 2:
            comps.append(comp)
    comps.sort(key=len, reverse=True)
    id_to_node = {n.id: n for n in g.nodes}
    result = []
    for i, comp in enumerate(comps[:limit]):
        names = [id_to_node[c].name for c in comp if c in id_to_node][:8]
        result.append({"id": i, "size": len(comp), "sample_names": names})
    return result

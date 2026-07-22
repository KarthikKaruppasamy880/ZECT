"""Build Mentrix structural RepoBlueprint from Lattice graph + workspace heuristics."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import LatticeStructuralBlueprint
from app.services.lattice.indexer import get_graph, god_nodes, ingest_path
from app.services.lattice.tree_sitter_parse import extract_symbols, tree_sitter_available

_DB_HINTS = re.compile(
    r"sqlalchemy|psycopg|asyncpg|pymongo|\bredis\b|sqlite3|django\.db|prisma|typeorm|sequelize",
    re.I,
)
_HTTP_HINTS = re.compile(
    r"(requests\.(get|post|put|patch|delete)|httpx\.|aiohttp\.|fetch\(|axios\.)",
    re.I,
)
_CONFIG_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle", "docker-compose.yml", "Dockerfile",
    ".env.example", "tsconfig.json",
}


def _jload(s: str, default: Any) -> Any:
    try:
        return json.loads(s or "") if s else default
    except json.JSONDecodeError:
        return default


def _jdumps(obj: Any) -> str:
    return json.dumps(obj, default=str)


def _git_sha(root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if r.returncode == 0:
            return (r.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _detect_tech_stack(root: Path, languages: dict[str, int]) -> list[str]:
    stack = sorted(languages.keys())
    markers = {
        "fastapi": ["fastapi"],
        "flask": ["flask"],
        "django": ["django"],
        "react": ["react"],
        "next": ["next"],
        "express": ["express"],
        "nestjs": ["@nestjs"],
    }
    req = root / "requirements.txt"
    pkg = root / "package.json"
    blob = ""
    if req.is_file():
        blob += req.read_text(encoding="utf-8", errors="ignore").lower()
    if pkg.is_file():
        blob += pkg.read_text(encoding="utf-8", errors="ignore").lower()
    for name, needles in markers.items():
        if any(n in blob for n in needles) and name not in stack:
            stack.append(name)
    return stack


def _scan_heuristics(root: Path, max_files: int = 400) -> dict[str, list]:
    db_conns: list[dict] = []
    outbound: list[dict] = []
    configs: list[dict] = []
    count = 0
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for fname in filenames:
            rel = str((Path(dirpath) / fname).relative_to(root)).replace("\\", "/")
            if fname in _CONFIG_NAMES or fname.endswith((".yml", ".yaml", ".toml", ".ini")):
                configs.append({"path": rel, "name": fname})
            ext = Path(fname).suffix.lower()
            if ext not in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java"}:
                continue
            count += 1
            if count > max_files:
                return {
                    "database_connections": db_conns[:40],
                    "outbound_calls": outbound[:40],
                    "config_entries": configs[:60],
                }
            try:
                text = (Path(dirpath) / fname).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if _DB_HINTS.search(text):
                hits = sorted(set(m.group(0) for m in _DB_HINTS.finditer(text)))
                db_conns.append({"path": rel, "hints": hits[:8]})
            for m in _HTTP_HINTS.finditer(text):
                outbound.append({"path": rel, "pattern": m.group(0)[:80]})
                if len(outbound) >= 40:
                    break
    return {
        "database_connections": db_conns[:40],
        "outbound_calls": outbound[:40],
        "config_entries": configs[:60],
    }


def build_structural_blueprint(
    root: str,
    project_key: str,
    *,
    max_files: int = 2000,
    refresh_graph: bool = True,
) -> dict[str, Any]:
    """Ingest Lattice (optional) and assemble structural blueprint dict."""
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")
    key = project_key or str(root_path)
    if refresh_graph:
        graph = ingest_path(str(root_path), project_key=key, max_files=max_files)
    else:
        graph = get_graph(key)
        if not graph:
            graph = ingest_path(str(root_path), project_key=key, max_files=max_files)

    functions = [
        {"name": n.name, "path": n.path, "language": n.language, "line": n.line, "kind": n.kind}
        for n in graph.nodes
        if n.kind in ("function", "method")
    ]
    classes = [
        {"name": n.name, "path": n.path, "language": n.language, "line": n.line}
        for n in graph.nodes
        if n.kind == "class"
    ]
    # Optional tree-sitter enrichment (no-op if packages missing)
    if tree_sitter_available():
        seen_fn = {(f["path"], f["name"]) for f in functions}
        seen_cls = {(c["path"], c["name"]) for c in classes}
        for n in graph.nodes:
            if n.kind != "file" or not n.path:
                continue
            fpath = root_path / n.path
            if not fpath.is_file():
                continue
            for sym in extract_symbols(str(fpath)):
                key = (n.path, sym["name"])
                if sym["kind"] in ("function", "method") and key not in seen_fn:
                    functions.append(
                        {
                            "name": sym["name"],
                            "path": n.path,
                            "language": n.language,
                            "line": sym.get("line"),
                            "kind": sym["kind"],
                            "source": "tree-sitter",
                        }
                    )
                    seen_fn.add(key)
                elif sym["kind"] == "class" and key not in seen_cls:
                    classes.append(
                        {
                            "name": sym["name"],
                            "path": n.path,
                            "language": n.language,
                            "line": sym.get("line"),
                            "source": "tree-sitter",
                        }
                    )
                    seen_cls.add(key)
    api_endpoints = [
        {"name": n.name, "path": n.path, "language": n.language, "kind": "endpoint"}
        for n in graph.nodes
        if n.kind == "endpoint"
    ]
    dep: dict[str, list[str]] = defaultdict(list)
    path_by_id = {n.id: n.path for n in graph.nodes if n.kind == "file"}
    name_by_id = {n.id: n.name for n in graph.nodes}
    for e in graph.edges:
        if e.kind in ("imports", "imports_file"):
            src = path_by_id.get(e.source) or name_by_id.get(e.source, e.source)
            tgt = path_by_id.get(e.target) or name_by_id.get(e.target, e.target)
            if tgt not in dep[src]:
                dep[src].append(tgt)

    file_tree = sorted({n.path for n in graph.nodes if n.path})[:200]
    heuristics = _scan_heuristics(root_path)
    gods = god_nodes(key, limit=15)
    tech = _detect_tech_stack(root_path, graph.languages or {})
    stats = {
        "files_indexed": graph.files_indexed,
        "symbols": graph.symbols,
        "languages": graph.languages,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "functions": len(functions),
        "classes": len(classes),
        "api_endpoints": len(api_endpoints),
        "call_edges": sum(1 for e in graph.edges if e.kind == "calls"),
        "doc_files_indexed": getattr(graph, "doc_files_indexed", 0),
        "wikilinks_resolved": getattr(graph, "wikilinks_resolved", 0),
        "wikilinks_unresolved": getattr(graph, "wikilinks_unresolved", 0),
    }
    doc_files = [
        {"name": n.name, "path": n.path, "group": getattr(n, "group", "") or ""}
        for n in graph.nodes
        if n.kind == "doc"
    ][:200]
    from app.services.lattice.markdown_graph import doc_backlinks as lattice_doc_backlinks

    doc_backlinks_map: dict[str, list] = {}
    for d in doc_files[:30]:
        bl = lattice_doc_backlinks(key, d["path"], limit=8)
        if bl.get("backlinks"):
            doc_backlinks_map[d["path"]] = bl["backlinks"]
    # Lightweight business_context from endpoints + top classes (no LLM required)
    business_context: list[dict] = []
    for ep in api_endpoints[:30]:
        business_context.append(
            {
                "entry_type": "endpoint",
                "name": ep["name"],
                "file_path": ep["path"],
                "purpose": f"HTTP surface {ep['name']}",
            }
        )
    for c in classes[:20]:
        business_context.append(
            {
                "entry_type": "class",
                "name": c["name"],
                "file_path": c["path"],
                "purpose": f"Class {c['name']} in {c['path']}",
            }
        )

    return {
        "project_key": key,
        "workspace_path": str(root_path),
        "status": "synced",
        "indexed_commit_sha": _git_sha(root_path),
        "file_tree": file_tree,
        "functions": functions[:500],
        "classes": classes[:300],
        "api_endpoints": api_endpoints,
        "outbound_calls": heuristics["outbound_calls"],
        "dependency_graph": dict(list(dep.items())[:200]),
        "database_connections": heuristics["database_connections"],
        "config_entries": heuristics["config_entries"],
        "tech_stack": tech,
        "business_context": business_context,
        "god_nodes": gods,
        "stats": stats,
        "doc_files": doc_files,
        "doc_backlinks": doc_backlinks_map,
        "error": "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def persist_structural_blueprint(db: Session, blueprint: dict[str, Any]) -> LatticeStructuralBlueprint:
    key = blueprint["project_key"]
    row = (
        db.query(LatticeStructuralBlueprint)
        .filter(LatticeStructuralBlueprint.project_key == key)
        .first()
    )
    if not row:
        row = LatticeStructuralBlueprint(project_key=key)
        db.add(row)
    row.workspace_path = blueprint.get("workspace_path", "")
    row.status = blueprint.get("status", "synced")
    row.indexed_commit_sha = blueprint.get("indexed_commit_sha", "")
    row.file_tree_json = _jdumps(blueprint.get("file_tree") or [])
    row.functions_json = _jdumps(blueprint.get("functions") or [])
    row.classes_json = _jdumps(blueprint.get("classes") or [])
    row.api_endpoints_json = _jdumps(blueprint.get("api_endpoints") or [])
    row.outbound_calls_json = _jdumps(blueprint.get("outbound_calls") or [])
    row.dependency_graph_json = _jdumps(blueprint.get("dependency_graph") or {})
    row.database_connections_json = _jdumps(blueprint.get("database_connections") or [])
    row.config_entries_json = _jdumps(blueprint.get("config_entries") or [])
    row.tech_stack_json = _jdumps(blueprint.get("tech_stack") or [])
    row.business_context_json = _jdumps(blueprint.get("business_context") or [])
    row.god_nodes_json = _jdumps(blueprint.get("god_nodes") or [])
    row.stats_json = _jdumps(blueprint.get("stats") or {})
    row.error = blueprint.get("error", "")
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def row_to_dict(row: LatticeStructuralBlueprint) -> dict[str, Any]:
    return {
        "project_key": row.project_key,
        "workspace_path": row.workspace_path,
        "status": row.status,
        "indexed_commit_sha": row.indexed_commit_sha,
        "file_tree": _jload(row.file_tree_json, []),
        "functions": _jload(row.functions_json, []),
        "classes": _jload(row.classes_json, []),
        "api_endpoints": _jload(row.api_endpoints_json, []),
        "outbound_calls": _jload(row.outbound_calls_json, []),
        "dependency_graph": _jload(row.dependency_graph_json, {}),
        "database_connections": _jload(row.database_connections_json, []),
        "config_entries": _jload(row.config_entries_json, []),
        "tech_stack": _jload(row.tech_stack_json, []),
        "business_context": _jload(row.business_context_json, []),
        "god_nodes": _jload(row.god_nodes_json, []),
        "stats": _jload(row.stats_json, {}),
        "error": row.error or "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_structural_blueprint(db: Session, project_key: str) -> dict[str, Any] | None:
    row = (
        db.query(LatticeStructuralBlueprint)
        .filter(LatticeStructuralBlueprint.project_key == project_key)
        .first()
    )
    if not row:
        return None
    return row_to_dict(row)


def build_deep_prompt(blueprint: dict[str, Any]) -> str:
    """Mentrix-ready deep prompt from structural blueprint."""
    stats = blueprint.get("stats") or {}
    lines = [
        f"# Mentrix Lattice structural blueprint",
        f"**Project key:** {blueprint.get('project_key')}",
        f"**Workspace:** {blueprint.get('workspace_path')}",
        f"**Commit:** {blueprint.get('indexed_commit_sha') or '(unknown)'}",
        f"**Tech stack:** {', '.join(blueprint.get('tech_stack') or []) or '(detect via ingest)'}",
        "",
        "## Stats",
        f"- files={stats.get('files_indexed')} symbols={stats.get('symbols')} "
        f"functions={stats.get('functions')} classes={stats.get('classes')} "
        f"endpoints={stats.get('api_endpoints')} call_edges={stats.get('call_edges')} "
        f"docs={stats.get('doc_files_indexed')} wikilinks={stats.get('wikilinks_resolved')}",
        "",
        "## God nodes (highest connectivity)",
    ]
    for g in (blueprint.get("god_nodes") or [])[:12]:
        lines.append(f"- {g.get('kind')} {g.get('name')} @ {g.get('path')} (degree={g.get('degree')})")
    lines.append("")
    lines.append("## API endpoints")
    for ep in (blueprint.get("api_endpoints") or [])[:40]:
        lines.append(f"- {ep.get('name')} — {ep.get('path')}")
    if not blueprint.get("api_endpoints"):
        lines.append("- (none detected)")
    lines.append("")
    lines.append("## Key classes")
    for c in (blueprint.get("classes") or [])[:30]:
        lines.append(f"- {c.get('name')} — {c.get('path')}")
    lines.append("")
    lines.append("## Key functions")
    for f in (blueprint.get("functions") or [])[:40]:
        lines.append(f"- {f.get('name')} — {f.get('path')}")
    lines.append("")
    lines.append("## Dependency sample")
    dep = blueprint.get("dependency_graph") or {}
    for src, tgts in list(dep.items())[:25]:
        lines.append(f"- {src} → {', '.join(tgts[:6])}")
    lines.append("")
    lines.append("## Documentation graph")
    for d in (blueprint.get("doc_files") or [])[:25]:
        lines.append(f"- doc {d.get('name')} — {d.get('path')} ({d.get('group')})")
    bl_map = blueprint.get("doc_backlinks") or {}
    if bl_map:
        lines.append("")
        lines.append("## Doc backlinks (sample)")
        for path, links in list(bl_map.items())[:10]:
            names = ", ".join(l.get("source", {}).get("name", "?") for l in links[:4])
            lines.append(f"- {path} ← {names}")
    lines.append("")
    lines.append("## Business context")
    for b in (blueprint.get("business_context") or [])[:25]:
        lines.append(f"- [{b.get('entry_type')}] {b.get('name')}: {b.get('purpose')}")
    lines.append("")
    lines.append("## File tree (sample)")
    lines.append("```")
    lines.extend((blueprint.get("file_tree") or [])[:80])
    lines.append("```")
    lines.append("")
    lines.append("## Mentrix instructions")
    lines.append("1. Respect existing APIs, modules, and dependency edges above")
    lines.append("2. Prefer minimal diffs; do not invent endpoints not listed unless required")
    lines.append("3. Use Lattice path/neighbors for impact analysis before large refactors")
    lines.append("4. Mentrix Ultra Review + gates must pass before Approve → Create PR")
    return "\n".join(lines)

"""Blueprint builders for Mentrix upgrade (workspace / Lattice — no GitHub required)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_blueprint(
    goal: str,
    *,
    project_key: str = "",
    workspace: str = "",
    scout: dict | None = None,
    source_lang: str = "",
    target_lang: str = "",
) -> dict[str, Any]:
    """Build a migration blueprint prompt from local workspace + scout hits."""
    scout = scout or {}
    structural = scout.get("structural_blueprint") or {}
    lines = [
        f"# Mentrix upgrade blueprint",
        f"**Goal:** {goal[:800]}",
        f"**Project key:** {project_key or '(none)'}",
    ]
    if source_lang or target_lang:
        lines.append(f"**Languages:** {source_lang or '?'} → {target_lang or '?'}")

    if structural:
        stats = structural.get("stats") or {}
        lines.append(
            f"\n## Structural blueprint (Lattice)\n"
            f"tech={', '.join(structural.get('tech_stack') or [])} "
            f"files={stats.get('files_indexed')} endpoints={stats.get('api_endpoints')} "
            f"functions={stats.get('functions')} classes={stats.get('classes')}"
        )
        eps = structural.get("api_endpoints") or []
        if eps:
            lines.append("\n## API endpoints")
            for ep in eps[:30]:
                lines.append(f"- {ep.get('name')} — {ep.get('path')}")
        dep = structural.get("dependency_graph") or {}
        if dep:
            lines.append("\n## Dependency graph (sample)")
            for src, tgts in list(dep.items())[:20]:
                lines.append(f"- {src} → {', '.join(tgts[:6])}")
        gods = structural.get("god_nodes") or []
        if gods:
            lines.append("\n## God nodes")
            for g in gods[:10]:
                lines.append(
                    f"- {g.get('kind')} {g.get('name')} @ {g.get('path')} (degree={g.get('degree')})"
                )
        notes = scout.get("explain_notes") or []
        if notes:
            lines.append("\n## Lattice explain notes")
            for note in notes[:5]:
                lines.append(f"- {note}")
        funcs = structural.get("functions") or []
        if funcs:
            lines.append("\n## Top symbols")
            for f in funcs[:25]:
                lines.append(f"- {f.get('name')} — {f.get('path')}")

    root = Path(workspace) if workspace else None
    tree: list[str] = []
    if root and root.is_dir() and not structural.get("file_tree"):
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        for p in sorted(root.rglob("*"))[:120]:
            if any(part in skip for part in p.parts):
                continue
            if p.is_file():
                try:
                    tree.append(str(p.relative_to(root)).replace("\\", "/"))
                except ValueError:
                    continue
        lines.append("\n## Workspace tree (sample)")
        lines.append("```")
        lines.extend(tree[:80])
        lines.append("```")
    elif structural.get("file_tree"):
        tree = list(structural.get("file_tree") or [])[:80]
        lines.append("\n## Workspace tree (from Lattice blueprint)")
        lines.append("```")
        lines.extend(tree)
        lines.append("```")

    graph_hits = scout.get("graph_hits") or []
    if graph_hits and not structural:
        lines.append("\n## Lattice symbols")
        for h in graph_hits[:25]:
            path = h.get("path") or h.get("file") or ""
            name = h.get("name") or h.get("symbol") or ""
            lines.append(f"- {path} :: {name}")

    summary = scout.get("graph_summary") or {}
    if summary and not structural:
        lines.append(
            f"\n## Graph summary\nfiles={summary.get('files_indexed')} "
            f"symbols={summary.get('symbols')} langs={summary.get('languages')}"
        )

    lines.append(
        "\n## Mentrix instructions\n"
        "1. Inventory APIs and module boundaries from the structural blueprint\n"
        "2. Port one module/phase at a time\n"
        "3. Preserve behavior; add tests + API evals\n"
        "4. Mentrix Ultra Review must pass before PR\n"
    )
    prompt = "\n".join(lines)
    # Design contract — re-verified after Build (required_files filled from build output)
    mentions: list[str] = ["Mentrix"]
    for h in graph_hits[:5]:
        name = h.get("name") or h.get("symbol") or ""
        if name and len(str(name)) >= 3:
            mentions.append(str(name))

    acceptance = [
        "Mentrix upgrade placeholder or ported module present",
        "Preserve behavior with tests or API evals",
        f"Address upgrade: {goal[:80]}",
    ]

    design_contract = {
        "required_files": [],  # populated from files_written after Build
        "required_mentions": mentions[:12],
        "acceptance_criteria": acceptance,
    }

    return {
        "prompt": prompt,
        "token_estimate": len(prompt) // 4,
        "files_sampled": tree[:80],
        "phase_map": [
            "inventory",
            "port_modules",
            "tests",
            "api_eval",
            "ultra_review",
            "approve_pr",
        ],
        "source_lang": source_lang,
        "target_lang": target_lang,
        "design_contract": design_contract,
    }

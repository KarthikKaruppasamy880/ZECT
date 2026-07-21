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
    lines = [
        f"# Mentrix upgrade blueprint",
        f"**Goal:** {goal[:800]}",
        f"**Project key:** {project_key or '(none)'}",
    ]
    if source_lang or target_lang:
        lines.append(f"**Languages:** {source_lang or '?'} → {target_lang or '?'}")

    root = Path(workspace) if workspace else None
    tree: list[str] = []
    if root and root.is_dir():
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

    graph_hits = scout.get("graph_hits") or []
    if graph_hits:
        lines.append("\n## Lattice symbols")
        for h in graph_hits[:25]:
            path = h.get("path") or h.get("file") or ""
            name = h.get("name") or h.get("symbol") or ""
            lines.append(f"- {path} :: {name}")

    summary = scout.get("graph_summary") or {}
    if summary:
        lines.append(
            f"\n## Graph summary\nfiles={summary.get('files_indexed')} "
            f"symbols={summary.get('symbols')} langs={summary.get('languages')}"
        )

    lines.append(
        "\n## Mentrix instructions\n"
        "1. Inventory APIs and module boundaries\n"
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

"""Developer composer @mentions -> real ProvenanceItems.

Every mention resolves against a real, existing data source (Lattice, PLAN.md
store, App Runner output, test results, skills registry, etc) rather than a
second retrieval system -- resolved items feed the same
MentrixContextEngine.build(extra_items=...) budget/truncation gate every
other context source already goes through. A mention that can't be resolved
returns a ProvenanceItem saying so (verification_state="unresolved") instead
of silently vanishing -- the whole point of a truthful "Context Used" is that
failures show up too.

Syntax: "@type" (no argument) or "@type:value" (value is the token up to the
next whitespace). Supported types:
  @file:<path> @folder:<path> @symbol:<name> @references:<name>
  @repo:<id> @plan:<id> @diff @terminal:<process_id> @error @test
  @lattice:<query> @skill:<id_or_name> @rule
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.work_items.context_engine import ProvenanceItem

_MENTION_RE = re.compile(
    r"@(file|folder|symbol|references|repo|plan|diff|terminal|error|test|lattice|skill|rule)(?::(\S+))?"
)

RULE_FILENAMES = ("ZECT.md", "AGENTS.md")
RULE_DIRS = (".zect/rules", ".cursor/rules")


def find_mentions(text: str) -> list[tuple[str, str]]:
    """Returns [(type, value_or_empty), ...] in the order they appear."""
    return [(m.group(1), m.group(2) or "") for m in _MENTION_RE.finditer(text or "")]


def _unresolved(mtype: str, value: str, reason: str) -> ProvenanceItem:
    return ProvenanceItem(
        source_type=f"mention:{mtype}",
        source_id=value or mtype,
        content=f"@{mtype}{':' + value if value else ''} could not be resolved: {reason}",
        verification_state="unresolved",
        selection_reason="mention_resolution_failed",
    )


def _resolve_file(value: str, *, workspace: Path) -> ProvenanceItem:
    from app.services.coding_engine.mentrix_agent_tools import execute_tool

    if not value:
        return _unresolved("file", value, "path required")
    out = execute_tool("read_file", {"path": value}, workspace=workspace)
    if not out.get("ok"):
        return _unresolved("file", value, str(out.get("error") or "not found"))
    return ProvenanceItem(
        source_type="mention:file",
        source_id=value,
        content=out.get("content") or "",
        verification_state="workspace_file",
        freshness="current",
        selection_reason="user_mentioned",
    )


def _resolve_folder(value: str, *, workspace: Path) -> ProvenanceItem:
    from app.services.coding_engine.mentrix_agent_tools import execute_tool

    out = execute_tool("list_dir", {"path": value or "."}, workspace=workspace)
    if not out.get("ok"):
        return _unresolved("folder", value, str(out.get("error") or "not found"))
    entries = out.get("entries") or []
    listing = "\n".join(f"{'d' if e['is_dir'] else 'f'} {e['path']}" for e in entries)
    return ProvenanceItem(
        source_type="mention:folder",
        source_id=value or ".",
        content=listing,
        verification_state="workspace_dir",
        freshness="current",
        selection_reason="user_mentioned",
    )


def _resolve_symbol_or_references(mtype: str, value: str, *, project_key: str) -> ProvenanceItem:
    from app.services.lattice.indexer import explain, query_graph

    if not value:
        return _unresolved(mtype, value, "name required")
    if not project_key:
        return _unresolved(mtype, value, "no Lattice project_key for this workspace")
    hits = query_graph(project_key, value, limit=10)
    if not hits:
        return _unresolved(mtype, value, "no Lattice match")
    result = explain(project_key, node_ref=hits[0]["id"])
    return ProvenanceItem(
        source_type=f"mention:{mtype}",
        source_id=value,
        content=result.get("summary") or "",
        verification_state="lattice_structural",
        freshness="indexed",
        retrieval_score=1.0 / len(hits),
        selection_reason="user_mentioned",
    )


def _resolve_lattice(value: str, *, project_key: str) -> ProvenanceItem:
    from app.services.lattice.indexer import query_graph

    if not project_key:
        return _unresolved("lattice", value, "no Lattice project_key for this workspace")
    hits = query_graph(project_key, value, limit=10)
    if not hits:
        return _unresolved("lattice", value, "no match")
    content = "\n".join(f"{h.get('kind')} {h.get('name')} ({h.get('path')})" for h in hits)
    return ProvenanceItem(
        source_type="mention:lattice",
        source_id=value or "query",
        content=content,
        verification_state="lattice_structural",
        freshness="indexed",
        selection_reason="user_mentioned",
    )


def _resolve_repo(value: str, *, db: Any) -> ProvenanceItem:
    from app.services.work_items.multi_repo_context import repo_binding

    if db is None:
        return _unresolved("repo", value, "no database session available")
    try:
        repo_id = int(value)
    except (TypeError, ValueError):
        return _unresolved("repo", value, "repo id must be numeric")
    binding = repo_binding(db, repo_id)
    if not binding.get("authorized", True) and binding.get("freshness") == "unauthorized":
        return _unresolved("repo", value, "repository not found or not authorized")
    content = (
        f"{binding.get('label')} @ {binding.get('repository_ref')} "
        f"({binding.get('base_commit_sha', '')[:12]})"
    )
    return ProvenanceItem(
        source_type="mention:repo",
        source_id=value,
        content=content,
        repository=value,
        commit_sha=str(binding.get("base_commit_sha") or ""),
        verification_state="repo_binding",
        freshness=str(binding.get("freshness") or "unknown"),
        selection_reason="user_mentioned",
    )


def _resolve_plan(value: str) -> ProvenanceItem:
    from app.services.coding_engine.plan_store import load_plan

    if not value:
        return _unresolved("plan", value, "plan id required")
    try:
        plan = load_plan(value)
    except FileNotFoundError:
        return _unresolved("plan", value, "no PLAN.md with that id")
    return ProvenanceItem(
        source_type="mention:plan",
        source_id=value,
        content=plan.get("markdown") or "",
        verification_state="plan_store",
        freshness="current",
        selection_reason="user_mentioned",
    )


def _resolve_diff(*, workspace: Path) -> ProvenanceItem:
    from app.services.coding_engine.lifecycle import _collect_diff

    diff = _collect_diff(workspace)
    if not diff:
        return _unresolved("diff", "", "no unstaged changes in this workspace")
    return ProvenanceItem(
        source_type="mention:diff",
        source_id="workspace",
        content=diff,
        verification_state="git_diff",
        freshness="current",
        selection_reason="user_mentioned",
    )


def _resolve_terminal(value: str) -> ProvenanceItem:
    from app.domains.workspace.app_runner import get_output_sync

    if not value:
        return _unresolved("terminal", value, "process id required")
    out = get_output_sync(value, offset=0, limit=200)
    if not out:
        return _unresolved("terminal", value, "unknown process id")
    content = "\n".join(out.get("lines") or [])
    return ProvenanceItem(
        source_type="mention:terminal",
        source_id=value,
        content=f"$ {out.get('cmd')}\n{content}",
        verification_state="terminal_output",
        freshness="current" if out.get("running") else "final",
        selection_reason="user_mentioned",
    )


def _resolve_test(*, work_item_id: int | None) -> ProvenanceItem:
    from app.services.work_items.artifact_store import ArtifactStore

    if not work_item_id:
        return _unresolved("test", "", "no active work item for this mission")
    store = ArtifactStore(work_item_id)
    results = store.read_json("TEST_RESULTS.json", default=None)
    if not results:
        return _unresolved("test", "", "no recorded test results yet")
    return ProvenanceItem(
        source_type="mention:test",
        source_id=str(work_item_id),
        content=str(results)[:3000],
        verification_state="test_results",
        freshness="current",
        selection_reason="user_mentioned",
    )


def _resolve_error(*, work_item_id: int | None) -> ProvenanceItem:
    """No dedicated error log exists -- derive the most recent failure from
    the same TEST_RESULTS.json/REVIEW.json artifacts @test and Ultra Review
    already write, rather than building a second failure-tracking store."""
    from app.services.work_items.artifact_store import ArtifactStore

    if not work_item_id:
        return _unresolved("error", "", "no active work item for this mission")
    store = ArtifactStore(work_item_id)
    for name in ("TEST_RESULTS.json", "REVIEW.json"):
        data = store.read_json(name, default=None)
        if not data:
            continue
        failed = data if isinstance(data, dict) and not data.get("ok", True) else None
        if failed:
            return ProvenanceItem(
                source_type="mention:error",
                source_id=name,
                content=str(failed)[:3000],
                verification_state="derived_from_artifact",
                freshness="current",
                selection_reason="user_mentioned",
            )
    return _unresolved("error", "", "no recorded failure in TEST_RESULTS.json or REVIEW.json")


def _resolve_skill(value: str, *, db: Any) -> ProvenanceItem:
    if db is None:
        return _unresolved("skill", value, "no database session available")
    from app.models import SkillDefinition

    q = db.query(SkillDefinition).filter(SkillDefinition.is_active == True)  # noqa: E712
    row = None
    if value:
        try:
            row = q.filter(SkillDefinition.id == int(value)).first()
        except (TypeError, ValueError):
            row = None
        if not row:
            row = q.filter(SkillDefinition.name.ilike(f"%{value}%")).first()
    if not row:
        return _unresolved("skill", value, "no matching active skill")
    manifest = row.manifest or {}
    content = f"{row.name}: {row.description or ''}\n{manifest.get('template', '')}".strip()
    return ProvenanceItem(
        source_type="mention:skill",
        source_id=str(row.id),
        content=content,
        verification_state="skills_registry",
        freshness="current",
        selection_reason="user_mentioned",
    )


def load_workspace_rules(workspace: Path) -> str:
    """Concatenate ZECT.md/AGENTS.md/.zect/rules/*/.cursor/rules/* content,
    if any exists under the workspace root, most-specific-looking first.
    Deliberately flat (no per-path hierarchy) for a first pass. Shared by
    the on-demand @rule mention (below) and the standing RULES/SKILLS
    prompt layer in coding_engine_mentrix.py -- one rule loader, not two.
    Returns "" when nothing is found (never raises)."""
    found: list[str] = []
    for name in RULE_FILENAMES:
        p = workspace / name
        if p.is_file():
            found.append(f"# {name}\n{p.read_text(encoding='utf-8', errors='replace')[:4000]}")
    for d in RULE_DIRS:
        dir_path = workspace / d
        if dir_path.is_dir():
            for rule_file in sorted(dir_path.glob("*")):
                if rule_file.is_file():
                    found.append(
                        f"# {d}/{rule_file.name}\n"
                        f"{rule_file.read_text(encoding='utf-8', errors='replace')[:4000]}"
                    )
    return "\n\n".join(found)[:8000]


def _resolve_rule(*, workspace: Path) -> ProvenanceItem:
    content = load_workspace_rules(workspace)
    if not content:
        return _unresolved("rule", "", "no ZECT.md/AGENTS.md/.zect/rules/.cursor/rules found")
    return ProvenanceItem(
        source_type="mention:rule",
        source_id="workspace_rules",
        content=content,
        verification_state="rules_file",
        freshness="current",
        selection_reason="user_mentioned",
    )


def resolve_mentions(
    text: str,
    *,
    workspace: Path,
    project_key: str = "",
    work_item_id: int | None = None,
    db: Any = None,
) -> list[ProvenanceItem]:
    """Parse every @mention in `text` and resolve it against real data.
    Never raises -- an individual resolver failure becomes an unresolved
    ProvenanceItem, not a broken composer."""
    items: list[ProvenanceItem] = []
    for mtype, value in find_mentions(text):
        try:
            if mtype == "file":
                items.append(_resolve_file(value, workspace=workspace))
            elif mtype == "folder":
                items.append(_resolve_folder(value, workspace=workspace))
            elif mtype in ("symbol", "references"):
                items.append(_resolve_symbol_or_references(mtype, value, project_key=project_key))
            elif mtype == "lattice":
                items.append(_resolve_lattice(value, project_key=project_key))
            elif mtype == "repo":
                items.append(_resolve_repo(value, db=db))
            elif mtype == "plan":
                items.append(_resolve_plan(value))
            elif mtype == "diff":
                items.append(_resolve_diff(workspace=workspace))
            elif mtype == "terminal":
                items.append(_resolve_terminal(value))
            elif mtype == "test":
                items.append(_resolve_test(work_item_id=work_item_id))
            elif mtype == "error":
                items.append(_resolve_error(work_item_id=work_item_id))
            elif mtype == "skill":
                items.append(_resolve_skill(value, db=db))
            elif mtype == "rule":
                items.append(_resolve_rule(workspace=workspace))
            else:
                items.append(_unresolved(mtype, value, "unknown mention type"))
        except Exception as exc:  # noqa: BLE001 -- a bad mention must never break the whole message
            items.append(_unresolved(mtype, value, f"{type(exc).__name__}: {exc}"))
    return items

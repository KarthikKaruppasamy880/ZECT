"""Multi-repo authorized context assembly for Mentrix Developer ASK/PLAN/AGENT."""

from __future__ import annotations

import subprocess
from typing import Any

from sqlalchemy.orm import Session

from app.models import Repo
from app.services.work_items.context_engine import ContextPack, MentrixContextEngine


def resolve_authorized_repository_ids(
    db: Session,
    *,
    project_id: int | None,
    repository_ids: list[int] | None,
    repository_id: int | None,
) -> list[int]:
    """Return repo ids authorized for the project (deduped, order preserved)."""
    ordered: list[int] = []
    for rid in list(repository_ids or []):
        if rid and rid not in ordered:
            ordered.append(int(rid))
    if repository_id:
        # The primary repo must be first regardless of where (or whether) it
        # already sits in repository_ids -- an authorized-but-not-first
        # match used to leave merge_context_packs()'s packs[0] pointing at
        # the wrong repo even though the true primary was "authorized"
        # (finding A2 / CP-01).
        rid0 = int(repository_id)
        if rid0 in ordered:
            ordered.remove(rid0)
        ordered.insert(0, rid0)
    if not ordered:
        return []
    if project_id is None:
        return ordered[:12]
    allowed = {int(r.id) for r in db.query(Repo).filter(Repo.project_id == project_id).all()}
    return [rid for rid in ordered if rid in allowed]


def repo_binding(db: Session, repository_id: int) -> dict[str, Any]:
    """Identity snapshot for one attached repository."""
    r = db.query(Repo).filter(Repo.id == repository_id).first()
    if not r:
        return {
            "repository_id": repository_id,
            "authorized": False,
            "label": f"repo_id={repository_id}",
            "repository_ref": "",
            "base_commit_sha": "",
            "local_path": "",
            "freshness": "unauthorized",
        }
    ref = (r.clone_branch or r.default_branch or "main").strip()
    sha = _head_sha(r.local_path) if r.local_path else ""
    freshness = "ready" if sha else ("stale" if r.local_path else "missing")
    return {
        "repository_id": int(r.id),
        "authorized": True,
        "label": f"{r.owner}/{r.repo_name}",
        "repository_ref": ref,
        "base_commit_sha": sha,
        "local_path": r.local_path or "",
        "freshness": freshness,
        "mandatory": True,
    }


def git_head_sha(local_path: str | None) -> str:
    """Public alias for live git HEAD (no allowlist; used by evidence freshness)."""
    return _head_sha(local_path)


def _head_sha(local_path: str | None) -> str:
    if not local_path:
        return ""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=local_path,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:  # noqa: BLE001
        return ""


def merge_context_packs(
    packs: list[ContextPack],
    *,
    token_budget: int = 8000,
    primary_repository_id: int | None = None,
) -> ContextPack:
    """Merge per-repo packs into one bounded ContextPack (provenance preserved per item).

    The merged pack's own repository_id/ref/base_commit_sha (what ASK's
    "Context Used" reports) must identify by the caller's authoritative
    primary_repository_id, not by list position -- packs[0] used to always
    win regardless of which repo the user actually had active, which is
    what made Context Used lie about the grounded repo (finding A2 / CP-01).
    Falls back to packs[0] only when no primary id is given or it doesn't
    match any pack, so existing single-repo callers are unaffected.
    """
    engine = MentrixContextEngine(token_budget=token_budget)
    merged_items = []
    repo_ids: list[int | None] = []
    for pack in packs:
        repo_ids.append(pack.repository_id)
        merged_items.extend(pack.items)
    # Rebuild under shared budget — items already scored; trim from tail if over budget
    primary = packs[0] if packs else ContextPack()
    if primary_repository_id is not None:
        for pack in packs:
            if pack.repository_id == int(primary_repository_id):
                primary = pack
                break
    out = ContextPack(
        work_item_id=primary.work_item_id,
        repository_id=primary.repository_id,
        repository_ref=primary.repository_ref,
        base_commit_sha=primary.base_commit_sha,
        token_budget=token_budget,
    )
    used = 0
    for item in merged_items:
        tc = item.token_count or max(1, len(item.content) // 4)
        if used + tc > token_budget:
            break
        out.items.append(item)
        used += tc
    out.token_used = used
    return out


def build_affected_repos_manifest(bindings: list[dict[str, Any]], *, worktree_root: str = "") -> dict[str, Any]:
    """EXECUTION_MANIFEST fragment: affected repos + per-repo ops."""
    ops: list[dict[str, Any]] = []
    for i, b in enumerate(bindings, start=1):
        rid = int(b["repository_id"])
        wt = b.get("worktree_path") or (f"{worktree_root}/repo-{rid}" if worktree_root else "")
        ops.append(
            {
                "id": f"OP-{i}-repo-{rid}",
                "repository_id": rid,
                "repository_ref": b.get("repository_ref") or "",
                "base_commit_sha": b.get("base_commit_sha") or "",
                "worktree_path": wt,
                "mandatory": bool(b.get("mandatory", True)),
                "status": "pending",
            }
        )
    return {
        "affected_repos": bindings,
        "operations": ops,
        "mandatory_operation_ids": [o["id"] for o in ops if o.get("mandatory")],
        "requirement_ids": [],
        "acceptance_ids": [],
    }

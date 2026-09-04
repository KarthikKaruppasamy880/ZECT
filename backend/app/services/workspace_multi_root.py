"""Multi-root Developer Workspace helpers — path jail, search identity, no disk delete."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.allowed_paths import path_under_allowed_roots
from app.models import Repo


SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}


def resolved_under(candidate: str | Path, root: str | Path) -> Path:
    """Resolve candidate and require it to be root or a descendant. Symlinks are resolved."""
    base = path_under_allowed_roots(str(root))
    target = Path(candidate)
    if not target.is_absolute():
        target = base / target
    resolved = path_under_allowed_roots(str(target))
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="path_outside_root") from exc
    return resolved


def relpaths_inside_repo(repo_path: str, files: Iterable[str]) -> list[str]:
    """Normalize git pathspecs so they cannot escape the bound repo (sibling / .. / flags).

    ``repo_path`` must already be validated by git_ops (allowed roots). This helper
    only jails pathspecs inside that directory after symlink resolve.
    """
    repo = Path(repo_path).resolve()
    out: list[str] = []
    for raw in files:
        name = str(raw or "").strip()
        if not name:
            continue
        if name.startswith("-"):
            raise HTTPException(status_code=400, detail="invalid_pathspec")
        as_path = Path(name)
        if as_path.is_absolute() or ".." in as_path.parts:
            raise HTTPException(status_code=400, detail="path_outside_repo")
        resolved = (repo / as_path).resolve()
        try:
            rel = resolved.relative_to(repo)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="path_outside_repo") from exc
        out.append(str(rel).replace("\\", "/"))
    return out


def reject_force_git_args(args: list[str]) -> None:
    blocked = {"--force", "-f", "--force-with-lease"}
    if any(a in blocked for a in args):
        raise HTTPException(status_code=400, detail="force_git_rejected")


def repo_identity_envelope(db: Session, repo: Repo, *, path: str = "", symbol: str = "") -> dict[str, Any]:
    from app.services.repo_onboarding import repo_git_identity

    ident = repo_git_identity(db, repo.id)
    return {
        "project_id": repo.project_id,
        "workspace_id": f"project:{repo.project_id}",
        "repo_id": repo.id,
        "commit_sha": ident.get("head_sha") or "",
        "path": path,
        "symbol": symbol,
        "owner": repo.owner,
        "repo_name": repo.repo_name,
        "root_label": f"{repo.owner}/{repo.repo_name}",
        "root_state": ident.get("root_state") or "ERROR",
        "local_path": repo.local_path,
    }


def cloned_repos_for_ids(db: Session, repo_ids: list[int]) -> list[Repo]:
    if not repo_ids:
        return []
    rows = db.query(Repo).filter(Repo.id.in_(repo_ids)).all()
    by_id = {r.id: r for r in rows}
    ordered: list[Repo] = []
    for rid in repo_ids:
        repo = by_id.get(int(rid))
        if repo:
            ordered.append(repo)
    return ordered


def search_workspace(
    db: Session,
    *,
    pattern: str,
    scope: str,
    repo_ids: list[int],
    active_repo_id: int | None = None,
    current_file: str | None = None,
    max_results: int = 80,
) -> dict[str, Any]:
    """Grep authorized roots. Every hit carries root/repo identity. Unavailable roots are skipped."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise HTTPException(status_code=400, detail="invalid_pattern") from exc

    scope_n = (scope or "workspace").strip().lower()
    if scope_n not in {"file", "root", "workspace"}:
        raise HTTPException(status_code=400, detail="invalid_scope")

    repos = cloned_repos_for_ids(db, repo_ids)
    if scope_n == "root" and active_repo_id:
        repos = [r for r in repos if r.id == int(active_repo_id)]
    if scope_n == "file":
        repos = [r for r in repos if active_repo_id and r.id == int(active_repo_id)]

    hits: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    cap = max(1, min(int(max_results or 80), 200))

    for repo in repos:
        if not repo.local_path:
            skipped.append({"repo_id": repo.id, "reason": "ROOT_UNAVAILABLE", "error": "missing_local_path"})
            continue
        try:
            root = path_under_allowed_roots(repo.local_path)
        except ValueError:
            skipped.append({"repo_id": repo.id, "reason": "unauthorized"})
            continue
        if not root.is_dir():
            skipped.append({"repo_id": repo.id, "reason": "ROOT_UNAVAILABLE", "error": "path_not_found"})
            continue

        envelope = repo_identity_envelope(db, repo)
        if scope_n == "file":
            if not current_file:
                continue
            try:
                files = [resolved_under(current_file, root)]
            except HTTPException:
                skipped.append({"repo_id": repo.id, "reason": "file_outside_root"})
                continue
            if not files[0].is_file():
                continue
            _scan_files(files, root, regex, envelope, hits, cap)
        else:
            _walk_root(root, regex, envelope, hits, cap)
        if len(hits) >= cap:
            break

    return {
        "ok": True,
        "scope": scope_n,
        "pattern": pattern,
        "hits": hits,
        "skipped": skipped,
        "truncated": len(hits) >= cap,
        "semantic_cross_repo_references": False,
        "limitation": "Symbols and search are per-root identity tagged; semantic cross-repo references are not merged.",
    }


def workspace_problems(db: Session, *, repo_ids: list[int]) -> dict[str, Any]:
    """Real lint/typecheck diagnostics (see services/workspace/problems.py)
    across every authorized root -- same repo_id -> local_path -> allowed-
    roots jail as search_workspace, so this never runs a tool against a
    path the caller wasn't handed."""
    from app.services.workspace.problems import collect_workspace_problems

    repos = cloned_repos_for_ids(db, repo_ids)
    problems: list[dict[str, Any]] = []
    checked_tools: set[str] = set()
    skipped: list[dict[str, Any]] = []

    for repo in repos:
        if not repo.local_path:
            skipped.append({"repo_id": repo.id, "reason": "ROOT_UNAVAILABLE", "error": "missing_local_path"})
            continue
        try:
            root = path_under_allowed_roots(repo.local_path)
        except ValueError:
            skipped.append({"repo_id": repo.id, "reason": "unauthorized"})
            continue
        if not root.is_dir():
            skipped.append({"repo_id": repo.id, "reason": "ROOT_UNAVAILABLE", "error": "path_not_found"})
            continue

        envelope = repo_identity_envelope(db, repo)
        result = collect_workspace_problems(root)
        checked_tools.update(result["checked"])
        for problem in result["problems"]:
            raw_file = str(problem.get("file") or "")
            abs_candidate = Path(raw_file)
            if not abs_candidate.is_absolute():
                abs_candidate = root / raw_file
            try:
                rel = abs_candidate.resolve().relative_to(root)
            except ValueError:
                rel = Path(raw_file)
            problems.append(
                {
                    **problem,
                    "path": str(rel).replace("\\", "/"),
                    "abs_path": str(abs_candidate),
                    "repo_id": repo.id,
                    "root_label": envelope.get("root_label"),
                }
            )

    return {
        "ok": True,
        "problems": problems,
        "checked": sorted(checked_tools),
        "skipped": skipped,
    }


def _scan_files(
    files: list[Path],
    root: Path,
    regex: re.Pattern[str],
    envelope: dict[str, Any],
    hits: list[dict[str, Any]],
    cap: int,
) -> None:
    for fpath in files:
        if len(hits) >= cap:
            return
        try:
            if fpath.stat().st_size > 1_000_000:
                continue
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        rel = str(fpath.relative_to(root)).replace("\\", "/")
        for i, line in enumerate(text.split("\n"), 1):
            if regex.search(line):
                hits.append(
                    {
                        **envelope,
                        "path": rel,
                        "abs_path": str(fpath),
                        "line": i,
                        "content": line.strip()[:200],
                    }
                )
                if len(hits) >= cap:
                    return


def _walk_root(
    root: Path,
    regex: re.Pattern[str],
    envelope: dict[str, Any],
    hits: list[dict[str, Any]],
    cap: int,
) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        files = [Path(dirpath) / name for name in filenames if not name.startswith(".")]
        _scan_files(files, root, regex, envelope, hits, cap)
        if len(hits) >= cap:
            return

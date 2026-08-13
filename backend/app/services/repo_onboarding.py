"""Repository onboarding helpers — open local / discover / attach / safe checkout / PR worktrees.

Reuses Phase 6 Repo + Project model and allowed_paths. No second catalog.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.infrastructure.allowed_paths import allowed_roots, path_under_allowed_roots
from app.models import Project, Repo
from app.services.repo_clone import WORKSPACE_ROOT, _run_git


def _git(cwd: str | Path, args: list[str], timeout: int = 30) -> dict[str, Any]:
    return _run_git(str(cwd), args, timeout=timeout)


def inspect_git_repo(raw_path: str) -> dict[str, Any]:
    """Validate path is a git repo under allowed roots; return identity."""
    p = path_under_allowed_roots(raw_path)
    if not p.is_dir():
        return {"ok": False, "error": "path_not_found"}
    if not (p / ".git").exists():
        return {"ok": False, "error": "not_a_git_repository"}

    branch = _git(p, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = _git(p, ["rev-parse", "HEAD"])
    status = _git(p, ["status", "--porcelain"])
    remote = _git(p, ["remote", "get-url", "origin"])
    origin = remote["stdout"] if remote["exit_code"] == 0 else ""
    dirty = bool((status["stdout"] or "").strip()) if status["exit_code"] == 0 else True
    owner, name = _parse_origin(origin)
    if not name:
        name = p.name
    if not owner:
        owner = "local"
    return {
        "ok": True,
        "local_path": str(p),
        "name": name,
        "owner": owner,
        "origin_url": origin,
        "branch": branch["stdout"] if branch["exit_code"] == 0 else "",
        "head_sha": head["stdout"] if head["exit_code"] == 0 else "",
        "dirty": dirty,
        "clean": not dirty,
    }


def _parse_origin(url: str) -> tuple[str, str]:
    u = (url or "").strip()
    if not u:
        return "", ""
    # git@github.com:owner/repo.git
    m = re.match(r"git@[^:]+:([^/]+)/([^/]+?)(?:\.git)?$", u)
    if m:
        return m.group(1), m.group(2)
    # https://github.com/owner/repo.git
    try:
        parsed = urlparse(u)
        parts = [x for x in (parsed.path or "").strip("/").split("/") if x]
        if len(parts) >= 2:
            return parts[0], parts[1].removesuffix(".git")
    except Exception:
        pass
    return "", ""


def parse_git_url(url: str) -> dict[str, str]:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("invalid_git_url")
    # Local/file remotes used in acceptance — never require GitHub shape
    if raw.startswith("file:") or os.path.isdir(raw) or raw.endswith(".git"):
        try:
            parsed = urlparse(raw) if raw.startswith("file:") else None
            path = parsed.path if parsed else raw
            if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]  # /C:/... → C:/...
            name = Path(path).name.removesuffix(".git") or "repo"
            return {"owner": "local", "repo_name": name, "clone_url": raw}
        except Exception as e:
            raise ValueError("invalid_git_url") from e
    owner, name = _parse_origin(raw)
    if not owner or not name:
        raise ValueError("invalid_git_url")
    return {"owner": owner, "repo_name": name, "clone_url": raw}


def find_existing_repo(db: Session, *, local_path: str = "", owner: str = "", repo_name: str = "") -> Repo | None:
    if local_path:
        try:
            norm = str(Path(local_path).resolve())
        except Exception:
            norm = local_path
        for r in db.query(Repo).filter(Repo.local_path.isnot(None)).all():
            try:
                if r.local_path and str(Path(r.local_path).resolve()) == norm:
                    return r
            except Exception:
                if (r.local_path or "") == local_path:
                    return r
        return None
    if owner and repo_name:
        return (
            db.query(Repo)
            .filter(Repo.owner == owner, Repo.repo_name == repo_name)
            .order_by(Repo.id.asc())
            .first()
        )
    return None


def register_local_repo(
    db: Session,
    *,
    project_id: int,
    local_path: str,
    role: str = "",
) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"ok": False, "error": "project_not_found"}
    info = inspect_git_repo(local_path)
    if not info.get("ok"):
        return {"ok": False, **info}

    # Prefer exact path match; owner/name match only when path also matches or existing has no path
    by_path = find_existing_repo(db, local_path=info["local_path"])
    by_name = find_existing_repo(db, owner=info["owner"], repo_name=info["name"])
    existing = by_path
    if not existing and by_name:
        same_path = False
        if by_name.local_path:
            try:
                same_path = str(Path(by_name.local_path).resolve()) == info["local_path"]
            except Exception:
                same_path = by_name.local_path == info["local_path"]
        if same_path or not by_name.local_path:
            existing = by_name

    if existing:
        existing.local_path = info["local_path"]
        existing.clone_status = "cloned"
        existing.clone_branch = info["branch"] or existing.clone_branch or "main"
        existing.last_pulled_at = datetime.now(timezone.utc)
        moved = existing.project_id != project_id
        if moved:
            existing.project_id = project_id
        db.commit()
        db.refresh(existing)
        return {
            "ok": True,
            "repo_id": existing.id,
            "reused": True,
            "moved": moved,
            "identity": info,
        }

    repo = Repo(
        project_id=project_id,
        owner=info["owner"],
        repo_name=info["name"],
        default_branch=info["branch"] or "main",
        clone_status="cloned",
        local_path=info["local_path"],
        clone_branch=info["branch"] or "main",
        last_pulled_at=datetime.now(timezone.utc),
    )
    if hasattr(Repo, "workspace_branch"):
        repo.workspace_branch = info["branch"] or "main"
    db.add(repo)
    db.commit()
    db.refresh(repo)
    out = {"ok": True, "repo_id": repo.id, "reused": False, "identity": info}
    if role:
        out["role"] = role
    return out


def attach_existing_repo(db: Session, *, project_id: int, repo_id: int) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"ok": False, "error": "project_not_found"}
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"ok": False, "error": "repo_not_found"}
    if repo.project_id == project_id:
        return {"ok": True, "repo_id": repo.id, "already_attached": True}
    # Prevent accidental duplicate (owner/name) under same project
    dup = (
        db.query(Repo)
        .filter(
            Repo.project_id == project_id,
            Repo.owner == repo.owner,
            Repo.repo_name == repo.repo_name,
            Repo.id != repo.id,
        )
        .first()
    )
    if dup:
        return {"ok": False, "error": "duplicate_repo_in_project", "existing_repo_id": dup.id}
    repo.project_id = project_id
    db.commit()
    db.refresh(repo)
    return {"ok": True, "repo_id": repo.id, "attached": True}


def discover_local_repos(db: Session, *, root: str, max_depth: int = 3) -> dict[str, Any]:
    """Scan an explicit user-approved root (must be under allowed_roots)."""
    base = path_under_allowed_roots(root)
    if not base.is_dir():
        return {"ok": False, "error": "root_not_found", "repos": []}

    found: list[dict[str, Any]] = []
    base_depth = len(base.parts)
    for dirpath, dirnames, _filenames in os.walk(base):
        p = Path(dirpath)
        depth = len(p.parts) - base_depth
        if depth > max_depth:
            dirnames[:] = []
            continue
        # Skip heavy dirs
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox"}]
        if (p / ".git").exists():
            info = inspect_git_repo(str(p))
            if not info.get("ok"):
                continue
            existing = find_existing_repo(
                db, local_path=info["local_path"], owner=info["owner"], repo_name=info["name"]
            )
            found.append(
                {
                    **info,
                    "registered": bool(existing),
                    "repo_id": existing.id if existing else None,
                    "project_id": existing.project_id if existing else None,
                }
            )
            # Do not descend into nested git repos
            dirnames[:] = []
        if len(found) >= 50:
            break
    return {"ok": True, "root": str(base), "repos": found, "count": len(found), "allowed_roots": allowed_roots()}


def clone_from_url(
    db: Session,
    *,
    project_id: int,
    git_url: str,
    destination: str = "",
    branch: str = "",
    token: str | None = None,
) -> dict[str, Any]:
    from app.services.repo_clone import clone_repo

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"ok": False, "error": "project_not_found"}
    parsed = parse_git_url(git_url)
    existing = find_existing_repo(db, owner=parsed["owner"], repo_name=parsed["repo_name"])
    if existing and existing.local_path and os.path.isdir(existing.local_path):
        if existing.project_id != project_id:
            existing.project_id = project_id
            db.commit()
        return {
            "ok": True,
            "repo_id": existing.id,
            "reused": True,
            "local_path": existing.local_path,
            "clone_status": existing.clone_status,
        }

    dest = destination.strip()
    if dest:
        dest_path = path_under_allowed_roots(dest)
        dest_path.mkdir(parents=True, exist_ok=True)
        target = dest_path / parsed["repo_name"]
    else:
        target = Path(WORKSPACE_ROOT) / parsed["owner"] / parsed["repo_name"]
        target.parent.mkdir(parents=True, exist_ok=True)

    repo = existing or Repo(
        project_id=project_id,
        owner=parsed["owner"],
        repo_name=parsed["repo_name"],
        default_branch=branch or "main",
    )
    if not existing:
        db.add(repo)
        db.flush()
    else:
        repo.project_id = project_id

    # Point clone into chosen destination by pre-setting local_path expectation via env-compatible path
    # clone_repo computes workspace from WORKSPACE_ROOT; if destination provided, clone manually then register.
    if dest:
        if target.exists() and (target / ".git").exists():
            repo.local_path = str(target.resolve())
            repo.clone_status = "cloned"
            info = inspect_git_repo(str(target))
            repo.clone_branch = info.get("branch") or branch or "main"
            db.commit()
            db.refresh(repo)
            return {"ok": True, "repo_id": repo.id, "reused": True, "local_path": repo.local_path}

        url = parsed["clone_url"]
        # Never log token
        env_url = url
        if token and url.startswith("https://"):
            env_url = url.replace("https://", f"https://x-access-token:{token}@", 1)
        proc = subprocess.run(
            ["git", "clone", "--depth", "1"] + ([ "-b", branch] if branch else []) + [env_url, str(target)],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "clone_failed")[:500]
            # Redact token if any
            if token:
                err = err.replace(token, "***")
            return {"ok": False, "error": err}
        repo.local_path = str(target.resolve())
        repo.clone_status = "cloned"
        info = inspect_git_repo(str(target))
        repo.clone_branch = info.get("branch") or branch or "main"
        db.commit()
        db.refresh(repo)
        return {"ok": True, "repo_id": repo.id, "reused": False, "local_path": repo.local_path, "identity": info}

    result = clone_repo(db, repo.id, branch=branch or None, shallow=True, token=token)
    if result.get("status") == "error":
        return {"ok": False, "error": result.get("error") or "clone_failed"}
    return {"ok": True, "repo_id": repo.id, "reused": False, **result}


def repo_git_identity(db: Session, repo_id: int) -> dict[str, Any]:
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"ok": False, "error": "repo_not_found"}
    if not repo.local_path:
        return {
            "ok": True,
            "repo_id": repo.id,
            "cloned": False,
            "branch": repo.clone_branch or repo.default_branch,
            "head_sha": "",
            "dirty": False,
            "clean": True,
            "local_path": None,
        }
    info = inspect_git_repo(repo.local_path)
    if not info.get("ok"):
        return {"ok": False, "repo_id": repo.id, **info}
    return {"ok": True, "repo_id": repo.id, "cloned": True, **info}


def safe_checkout(
    db: Session,
    *,
    repo_id: int,
    branch: str,
    action: str = "require_clean",
) -> dict[str, Any]:
    """Checkout with dirty protection. action: require_clean | stash | force_discard (explicit only)."""
    from app.services.repo_clone import checkout_branch

    ident = repo_git_identity(db, repo_id)
    if not ident.get("ok") or not ident.get("cloned"):
        return {"ok": False, "error": ident.get("error") or "not_cloned"}

    dirty = bool(ident.get("dirty"))
    if dirty and action == "require_clean":
        return {
            "ok": False,
            "error": "dirty_working_tree",
            "dirty": True,
            "branch": ident.get("branch"),
            "head_sha": ident.get("head_sha"),
            "choices": ["cancel", "stash", "force_discard"],
        }

    path = ident["local_path"]
    if dirty and action == "stash":
        st = _git(path, ["stash", "push", "-u", "-m", "zect-safe-checkout"])
        if st["exit_code"] != 0:
            return {"ok": False, "error": st["stderr"] or "stash_failed", "dirty": True}
    elif dirty and action == "force_discard":
        # Explicit authorization required by caller — hard reset is intentional
        _git(path, ["reset", "--hard", "HEAD"])
        _git(path, ["clean", "-fd"])
    elif dirty:
        return {"ok": False, "error": "unknown_action", "choices": ["cancel", "stash", "force_discard"]}

    result = checkout_branch(db, repo_id, branch)
    if result.get("status") == "error":
        return {"ok": False, "error": result.get("error") or "checkout_failed"}
    after = repo_git_identity(db, repo_id)
    return {
        "ok": True,
        "branch": after.get("branch"),
        "head_sha": after.get("head_sha"),
        "dirty": after.get("dirty"),
        "stashed": dirty and action == "stash",
        "pi_hint": "STALE",
    }


def ensure_pr_worktree(
    db: Session,
    *,
    repo_id: int,
    pr_number: int,
    head_branch: str,
    head_sha: str = "",
) -> dict[str, Any]:
    """Create or reuse an isolated worktree for a PR without switching main checkout."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo or not repo.local_path:
        return {"ok": False, "error": "repo_not_cloned"}
    main = path_under_allowed_roots(repo.local_path)
    wt_root = main.parent / f"{main.name}-worktrees"
    wt_root.mkdir(parents=True, exist_ok=True)
    wt_path = wt_root / f"pr-{int(pr_number)}"

    # Fetch
    _git(main, ["fetch", "--all"], timeout=90)

    if wt_path.exists() and (wt_path / ".git").exists():
        info = inspect_git_repo(str(wt_path))
        return {
            "ok": True,
            "reused": True,
            "worktree_path": str(wt_path.resolve()),
            "branch": info.get("branch"),
            "head_sha": info.get("head_sha"),
            "pr_number": pr_number,
            "main_path": str(main),
            "main_unchanged": True,
        }

    # Resolve to a commit SHA first so local-only branches work without origin/*.
    resolve_order = [x for x in [head_sha, head_branch, f"origin/{head_branch}"] if x]
    start_sha = ""
    for ref in resolve_order:
        rev = _git(main, ["rev-parse", "--verify", ref])
        if rev["exit_code"] == 0 and rev["stdout"]:
            start_sha = rev["stdout"]
            break
    if not start_sha:
        return {"ok": False, "error": f"cannot_resolve_ref:{'|'.join(resolve_order)}"}

    wt_branch = f"zect-pr-{int(pr_number)}"
    if wt_path.exists():
        # Incomplete leftover from a prior failed attempt
        import shutil

        shutil.rmtree(wt_path, ignore_errors=True)

    add = _git(
        main,
        ["worktree", "add", "-B", wt_branch, str(wt_path), start_sha],
        timeout=60,
    )
    if add["exit_code"] != 0:
        # Detached fallback (still isolated; does not switch main checkout)
        if wt_path.exists():
            import shutil

            shutil.rmtree(wt_path, ignore_errors=True)
        add = _git(
            main,
            ["worktree", "add", "--detach", str(wt_path), start_sha],
            timeout=60,
        )
        if add["exit_code"] != 0:
            return {"ok": False, "error": (add["stderr"] or add["stdout"] or "worktree_add_failed")[:500]}

    info = inspect_git_repo(str(wt_path))
    main_after = inspect_git_repo(str(main))
    return {
        "ok": True,
        "reused": False,
        "worktree_path": str(wt_path.resolve()),
        "branch": info.get("branch"),
        "head_sha": info.get("head_sha"),
        "pr_number": pr_number,
        "main_path": str(main),
        "main_branch": main_after.get("branch"),
        "main_unchanged": True,
    }


def ensure_agent_worktree(
    db: Session,
    *,
    repo_id: int,
    work_item_id: int,
    head_branch: str = "",
    head_sha: str = "",
    worktree_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create or reuse an isolated AGENT worktree without switching the main checkout.

    Prefers a sibling of the clone: ``{clone}-worktrees/wi-{work_item_id}``.
    Callers may pass ``worktree_path`` (e.g. artifact ``store.root/worktrees/repo-{id}``)
    which is still added via ``git worktree add`` from the clone HEAD SHA.
    Dirty files on the main checkout are left untouched.
    """
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo or not repo.local_path:
        return {"ok": False, "error": "repo_not_cloned"}
    try:
        main = path_under_allowed_roots(repo.local_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)[:300]}

    if worktree_path:
        wt_path = Path(worktree_path)
        wt_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        wt_root = main.parent / f"{main.name}-worktrees"
        wt_root.mkdir(parents=True, exist_ok=True)
        wt_path = wt_root / f"wi-{int(work_item_id)}"

    main_before = inspect_git_repo(str(main))
    _git(main, ["fetch", "--all"], timeout=90)
    _git(main, ["worktree", "prune"], timeout=30)

    if wt_path.exists() and (wt_path / ".git").exists():
        info = inspect_git_repo(str(wt_path))
        main_after = inspect_git_repo(str(main))
        return {
            "ok": True,
            "reused": True,
            "worktree_path": str(wt_path.resolve()),
            "branch": info.get("branch"),
            "head_sha": info.get("head_sha"),
            "base_commit_sha": head_sha or main_before.get("head_sha") or "",
            "work_item_id": work_item_id,
            "repository_id": repo_id,
            "main_path": str(main),
            "main_branch": main_after.get("branch"),
            "main_head_sha": main_after.get("head_sha"),
            "main_unchanged": True,
        }

    resolve_order = [
        x
        for x in [
            head_sha,
            "HEAD",
            head_branch,
            f"origin/{head_branch}" if head_branch else "",
        ]
        if x
    ]
    start_sha = ""
    for ref in resolve_order:
        rev = _git(main, ["rev-parse", "--verify", ref])
        if rev["exit_code"] == 0 and rev["stdout"]:
            start_sha = rev["stdout"]
            break
    if not start_sha:
        return {"ok": False, "error": f"cannot_resolve_ref:{'|'.join(resolve_order)}"}

    wt_branch = f"zect-wi-{int(work_item_id)}-repo-{int(repo_id)}"
    if wt_path.exists():
        import shutil

        shutil.rmtree(wt_path, ignore_errors=True)

    add = _git(
        main,
        ["worktree", "add", "-B", wt_branch, str(wt_path), start_sha],
        timeout=60,
    )
    if add["exit_code"] != 0:
        if wt_path.exists():
            import shutil

            shutil.rmtree(wt_path, ignore_errors=True)
        add = _git(
            main,
            ["worktree", "add", "--detach", str(wt_path), start_sha],
            timeout=60,
        )
        if add["exit_code"] != 0:
            return {"ok": False, "error": (add["stderr"] or add["stdout"] or "worktree_add_failed")[:500]}

    info = inspect_git_repo(str(wt_path))
    main_after = inspect_git_repo(str(main))
    return {
        "ok": True,
        "reused": False,
        "worktree_path": str(wt_path.resolve()),
        "branch": info.get("branch") or wt_branch,
        "head_sha": info.get("head_sha") or start_sha,
        "base_commit_sha": start_sha,
        "work_item_id": work_item_id,
        "repository_id": repo_id,
        "main_path": str(main),
        "main_branch": main_after.get("branch"),
        "main_head_sha": main_after.get("head_sha"),
        "main_unchanged": main_after.get("head_sha") == main_before.get("head_sha"),
    }

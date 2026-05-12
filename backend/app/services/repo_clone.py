"""Repo Clone Service — clone, pull, branch, delete local repo workspaces."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Repo

WORKSPACE_ROOT = os.getenv("ZECT_WORKSPACE_ROOT", "/opt/zect-workspaces")
MAX_CLONE_TIMEOUT = 300  # 5 minutes
MAX_DISK_QUOTA_MB = 5000  # 5 GB per workspace root


def _workspace_path(owner: str, repo_name: str) -> str:
    safe_owner = owner.replace("/", "_").replace("..", "")
    safe_repo = repo_name.replace("/", "_").replace("..", "")
    return os.path.join(WORKSPACE_ROOT, safe_owner, safe_repo)


def _run_git(cwd: str, args: list[str], timeout: int = 60) -> dict:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "Command timed out"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


def _get_clone_url(owner: str, repo_name: str, token: Optional[str] = None) -> str:
    if token:
        return f"https://{token}@github.com/{owner}/{repo_name}.git"
    return f"https://github.com/{owner}/{repo_name}.git"


def _compute_disk_usage(path: str) -> float:
    """Return disk usage in MB for a directory."""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return round(total / (1024 * 1024), 2)


def _count_repo_stats(path: str) -> dict:
    """Count files and lines in a cloned repo for stats."""
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".nuxt"}
    ext_map = {
        ".py": "python", ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript",
        ".java": "java", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp",
        ".cs": "csharp", ".swift": "swift", ".kt": "kotlin",
        ".html": "html", ".css": "css", ".scss": "scss",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".md": "markdown", ".sql": "sql", ".sh": "shell",
    }
    total_files = 0
    total_lines = 0
    languages: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            lang = ext_map.get(ext)
            if not lang:
                continue
            total_files += 1
            try:
                if os.path.getsize(fpath) > 2_000_000:
                    continue
                with open(fpath, "r", errors="replace") as f:
                    line_count = sum(1 for _ in f)
                total_lines += line_count
                languages[lang] = languages.get(lang, 0) + line_count
            except (OSError, PermissionError):
                pass

    return {
        "total_files": total_files,
        "total_lines": total_lines,
        "languages": languages,
    }


def clone_repo(
    db: Session,
    repo_id: int,
    branch: Optional[str] = None,
    shallow: bool = True,
    token: Optional[str] = None,
) -> dict:
    """Clone a GitHub repo into the workspace directory. Updates Repo model."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found", "status": "error"}

    workspace = _workspace_path(repo.owner, repo.repo_name)
    clone_branch = branch or repo.default_branch or "main"

    # If already cloned, return status
    if repo.clone_status == "cloned" and repo.local_path and os.path.isdir(repo.local_path):
        return {
            "status": "already_cloned",
            "local_path": repo.local_path,
            "branch": repo.clone_branch,
            "message": "Repo is already cloned. Use pull to update or delete to re-clone.",
        }

    # Mark as cloning
    repo.clone_status = "cloning"
    repo.clone_error = None
    db.commit()

    # Create workspace directory
    os.makedirs(os.path.dirname(workspace), exist_ok=True)

    # Remove existing dir if any (re-clone scenario)
    if os.path.exists(workspace):
        shutil.rmtree(workspace, ignore_errors=True)

    # Build clone command
    clone_url = _get_clone_url(repo.owner, repo.repo_name, token)
    cmd = ["clone", "--branch", clone_branch]
    if shallow:
        cmd.extend(["--depth", "1"])
    cmd.extend([clone_url, workspace])

    result = _run_git("/tmp", cmd, timeout=MAX_CLONE_TIMEOUT)

    if result["exit_code"] != 0:
        repo.clone_status = "error"
        repo.clone_error = result["stderr"][:500]
        db.commit()
        return {"error": result["stderr"], "status": "error"}

    # Success — update repo model
    disk_mb = _compute_disk_usage(workspace)
    stats = _count_repo_stats(workspace)

    repo.clone_status = "cloned"
    repo.local_path = workspace
    repo.clone_branch = clone_branch
    repo.clone_depth = 1 if shallow else None
    repo.disk_usage_mb = disk_mb
    repo.last_pulled_at = datetime.now(timezone.utc)
    repo.clone_error = None
    repo.total_files = stats["total_files"]
    repo.total_lines = stats["total_lines"]
    repo.index_stats = stats
    db.commit()

    return {
        "status": "cloned",
        "local_path": workspace,
        "branch": clone_branch,
        "disk_usage_mb": disk_mb,
        "stats": stats,
    }


def pull_repo(db: Session, repo_id: int, token: Optional[str] = None) -> dict:
    """Pull latest changes for a cloned repo."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found", "status": "error"}
    if repo.clone_status != "cloned" or not repo.local_path:
        return {"error": "Repo is not cloned", "status": "error"}
    if not os.path.isdir(repo.local_path):
        repo.clone_status = "error"
        repo.clone_error = "Clone directory missing"
        db.commit()
        return {"error": "Clone directory missing on disk", "status": "error"}

    # If shallow, unshallow first for full pull
    if repo.clone_depth == 1:
        _run_git(repo.local_path, ["fetch", "--unshallow"], timeout=120)
        repo.clone_depth = None

    result = _run_git(repo.local_path, ["pull", "origin", repo.clone_branch or "main"], timeout=120)
    if result["exit_code"] != 0:
        return {"error": result["stderr"], "status": "error"}

    # Refresh stats
    disk_mb = _compute_disk_usage(repo.local_path)
    stats = _count_repo_stats(repo.local_path)

    repo.disk_usage_mb = disk_mb
    repo.last_pulled_at = datetime.now(timezone.utc)
    repo.total_files = stats["total_files"]
    repo.total_lines = stats["total_lines"]
    repo.index_stats = stats
    repo.clone_status = "cloned"
    db.commit()

    return {
        "status": "pulled",
        "output": result["stdout"],
        "disk_usage_mb": disk_mb,
        "stats": stats,
    }


def checkout_branch(db: Session, repo_id: int, branch: str) -> dict:
    """Checkout a specific branch in the cloned repo."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo or repo.clone_status != "cloned" or not repo.local_path:
        return {"error": "Repo is not cloned", "status": "error"}

    # Fetch all branches first
    _run_git(repo.local_path, ["fetch", "--all"], timeout=60)

    result = _run_git(repo.local_path, ["checkout", branch], timeout=30)
    if result["exit_code"] != 0:
        # Try creating tracking branch
        result = _run_git(repo.local_path, ["checkout", "-b", branch, f"origin/{branch}"], timeout=30)
        if result["exit_code"] != 0:
            return {"error": result["stderr"], "status": "error"}

    repo.clone_branch = branch
    stats = _count_repo_stats(repo.local_path)
    repo.total_files = stats["total_files"]
    repo.total_lines = stats["total_lines"]
    repo.index_stats = stats
    db.commit()

    return {"status": "checked_out", "branch": branch, "stats": stats}


def list_branches(db: Session, repo_id: int) -> dict:
    """List branches in the cloned repo."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo or repo.clone_status != "cloned" or not repo.local_path:
        return {"error": "Repo is not cloned", "status": "error"}

    # Fetch remotes
    _run_git(repo.local_path, ["fetch", "--all"], timeout=60)

    # Get current branch
    current = _run_git(repo.local_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    current_branch = current["stdout"] if current["exit_code"] == 0 else ""

    # Get all branches
    local_result = _run_git(repo.local_path, ["branch", "--format=%(refname:short)"])
    remote_result = _run_git(repo.local_path, ["branch", "-r", "--format=%(refname:short)"])

    local_branches = [b for b in local_result["stdout"].split("\n") if b] if local_result["exit_code"] == 0 else []
    remote_branches = []
    if remote_result["exit_code"] == 0:
        for b in remote_result["stdout"].split("\n"):
            if b and "HEAD" not in b:
                # Strip "origin/" prefix for display
                name = b.replace("origin/", "") if b.startswith("origin/") else b
                if name not in local_branches:
                    remote_branches.append(name)

    return {
        "current": current_branch,
        "local": local_branches,
        "remote": remote_branches,
    }


def delete_clone(db: Session, repo_id: int) -> dict:
    """Delete a cloned repo from disk and reset tracking."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found", "status": "error"}

    if repo.local_path and os.path.exists(repo.local_path):
        shutil.rmtree(repo.local_path, ignore_errors=True)

    repo.clone_status = "not_cloned"
    repo.local_path = None
    repo.clone_branch = None
    repo.clone_depth = None
    repo.disk_usage_mb = 0.0
    repo.last_pulled_at = None
    repo.indexed_at = None
    repo.index_stats = {}
    repo.clone_error = None
    repo.total_files = 0
    repo.total_lines = 0
    db.commit()

    return {"status": "deleted", "message": "Clone removed from disk"}


def get_clone_status(db: Session, repo_id: int) -> dict:
    """Get the current clone status for a repo."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found"}

    return {
        "repo_id": repo.id,
        "owner": repo.owner,
        "repo_name": repo.repo_name,
        "clone_status": repo.clone_status or "not_cloned",
        "local_path": repo.local_path,
        "clone_branch": repo.clone_branch,
        "clone_depth": repo.clone_depth,
        "disk_usage_mb": repo.disk_usage_mb or 0.0,
        "last_pulled_at": str(repo.last_pulled_at) if repo.last_pulled_at else None,
        "indexed_at": str(repo.indexed_at) if repo.indexed_at else None,
        "index_stats": repo.index_stats or {},
        "clone_error": repo.clone_error,
        "total_files": repo.total_files or 0,
        "total_lines": repo.total_lines or 0,
    }

"""Per-run isolated coding-engine workspaces (git worktrees).

Stage A isolation: one worktree per run under ZECT_ENGINE_WORKSPACE_ROOT
(or a temp dir under allowlisted roots). Docker isolation is Stage D.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.infrastructure.allowed_paths import path_under_allowed_roots


class WorkspaceError(ValueError):
    """Invalid repo path, git failure, or allowlist violation."""


@dataclass
class ProvisionedWorkspace:
    workspace_id: str
    path: str
    branch: str
    repo_path: str
    artifact_dir: str


def _engine_root() -> Path:
    raw = (os.getenv("ZECT_ENGINE_WORKSPACE_ROOT") or "").strip()
    if raw:
        root = Path(raw).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return path_under_allowed_roots(str(root))
    # Fall back to a temp directory (always under system temp = allowlisted).
    root = Path(tempfile.gettempdir()) / "zect-engine-workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return path_under_allowed_roots(str(root))


def _artifact_root() -> Path:
    root = _engine_root() / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _ensure_git_repo(repo: Path) -> None:
    probe = _run_git(repo, "rev-parse", "--is-inside-work-tree", check=False)
    if probe.returncode != 0 or (probe.stdout or "").strip() != "true":
        raise WorkspaceError(f"Not a git repository: {repo}")


def provision_worktree(*, repo_path: str, run_id: str | None = None) -> ProvisionedWorkspace:
    """Create an isolated git worktree for a coding-engine run."""
    repo = path_under_allowed_roots(repo_path)
    if not repo.is_dir():
        raise WorkspaceError(f"Repository path does not exist: {repo}")
    _ensure_git_repo(repo)

    workspace_id = (run_id or str(uuid4())).strip() or str(uuid4())
    # Sanitize for branch/path fragments
    safe_id = "".join(c if c.isalnum() or c in "-_" else "-" for c in workspace_id)[:64]
    branch = f"zect/run-{safe_id}"
    dest = _engine_root() / f"run-{safe_id}"
    if dest.exists():
        raise WorkspaceError(f"Workspace path already exists: {dest}")

    # Prefer branching from HEAD; create orphan branch name via worktree -b
    add = _run_git(
        repo,
        "worktree",
        "add",
        "-b",
        branch,
        str(dest),
        "HEAD",
        check=False,
    )
    if add.returncode != 0:
        raise WorkspaceError(
            f"git worktree add failed: {(add.stderr or add.stdout or '').strip()}"
        )

    artifact_dir = _artifact_root() / safe_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return ProvisionedWorkspace(
        workspace_id=safe_id,
        path=str(dest.resolve()),
        branch=branch,
        repo_path=str(repo.resolve()),
        artifact_dir=str(artifact_dir.resolve()),
    )


def _capture_patch(workspace_path: Path, artifact_dir: Path) -> str | None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    diff = _run_git(workspace_path, "diff", "HEAD", check=False)
    staged = _run_git(workspace_path, "diff", "--cached", check=False)
    untracked = _run_git(workspace_path, "ls-files", "--others", "--exclude-standard", check=False)
    body_parts = []
    if (diff.stdout or "").strip():
        body_parts.append(diff.stdout)
    if (staged.stdout or "").strip():
        body_parts.append("# staged\n" + staged.stdout)
    if (untracked.stdout or "").strip():
        body_parts.append("# untracked\n" + untracked.stdout)
    if not body_parts:
        # Still write an empty marker so dispose always leaves an artifact trail
        patch_path = artifact_dir / "changes.patch"
        patch_path.write_text("# no local changes\n", encoding="utf-8")
        return str(patch_path)
    patch_path = artifact_dir / "changes.patch"
    patch_path.write_text("\n".join(body_parts), encoding="utf-8")
    return str(patch_path)


def dispose_worktree(
    *,
    workspace_id: str,
    repo_path: str | None = None,
    workspace_path: str | None = None,
    preserve_artifacts: bool = True,
) -> dict:
    """Remove a worktree; optionally preserve a patch under artifacts/ first."""
    safe_id = "".join(c if c.isalnum() or c in "-_" else "-" for c in (workspace_id or "").strip())[:64]
    if not safe_id:
        raise WorkspaceError("workspace_id is required")

    dest = Path(workspace_path).resolve() if workspace_path else (_engine_root() / f"run-{safe_id}")
    if workspace_path:
        dest = path_under_allowed_roots(str(dest))
    else:
        # Ensure dest is under engine root
        dest = path_under_allowed_roots(str(dest))

    artifact_dir = _artifact_root() / safe_id
    patch_file = None
    if preserve_artifacts and dest.is_dir():
        try:
            patch_file = _capture_patch(dest, artifact_dir)
        except Exception:
            patch_file = None

    repo: Path | None = None
    if repo_path:
        repo = path_under_allowed_roots(repo_path)
    elif dest.is_dir():
        # Discover main repo from worktree metadata if possible
        probe = _run_git(dest, "rev-parse", "--git-common-dir", check=False)
        if probe.returncode == 0 and (probe.stdout or "").strip():
            common = Path(probe.stdout.strip())
            if not common.is_absolute():
                common = (dest / common).resolve()
            # common-dir is often <repo>/.git — parent is repo root for normal repos
            candidate = common.parent if common.name == ".git" else common
            try:
                repo = path_under_allowed_roots(str(candidate))
            except ValueError:
                repo = None

    removed = False
    if repo and dest.exists():
        rm = _run_git(repo, "worktree", "remove", "--force", str(dest), check=False)
        removed = rm.returncode == 0
        # Drop the task branch if it exists and is unused
        _run_git(repo, "branch", "-D", f"zect/run-{safe_id}", check=False)

    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
        removed = True or removed

    return {
        "workspace_id": safe_id,
        "removed": bool(removed or not dest.exists()),
        "artifact_patch": patch_file,
        "artifact_dir": str(artifact_dir) if artifact_dir.exists() else None,
    }

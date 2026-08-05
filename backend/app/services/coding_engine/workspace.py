"""Per-run isolated coding-engine workspaces (git worktrees + optional Docker).

Default isolation is git worktree (works without Docker). When
ZECT_CODING_ENGINE_ISOLATION=docker|auto and Docker is available, a restricted
bind-mount sandbox container is started alongside the worktree (Stage D).
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
from app.services.coding_engine.isolation import resolve_isolation


class WorkspaceError(ValueError):
    """Invalid repo path, git failure, or allowlist violation."""


@dataclass
class ProvisionedWorkspace:
    workspace_id: str
    path: str
    branch: str
    repo_path: str
    artifact_dir: str
    isolation: str = "worktree"
    container_id: str | None = None
    sandbox_image: str | None = None
    isolation_note: str | None = None


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
        isolation="worktree",
    )


def provision_isolated_workspace(*, repo_path: str, run_id: str | None = None) -> ProvisionedWorkspace:
    """Provision a worktree, then optionally wrap it in a Docker sandbox.

    If Docker was requested but unavailable, falls back to worktree unless
    ZECT_CODING_ENGINE_ISOLATION_STRICT=1 (then raises WorkspaceError).
    """
    plan = resolve_isolation()
    if plan["isolation"] == "unavailable":
        raise WorkspaceError(
            "ZECT_CODING_ENGINE_ISOLATION=docker requires a working Docker daemon "
            "(set ZECT_CODING_ENGINE_ISOLATION=worktree or install Docker/Rancher)."
        )

    ws = provision_worktree(repo_path=repo_path, run_id=run_id)
    ws.isolation_note = plan.get("detail")

    if plan["isolation"] != "docker":
        ws.isolation = "worktree"
        return ws

    try:
        from app.services.coding_engine.docker_sandbox import start_workspace_sandbox

        box = start_workspace_sandbox(host_workspace=ws.path, run_id=ws.workspace_id)
        ws.isolation = "docker"
        ws.container_id = box.container_id
        ws.sandbox_image = box.image
        ws.isolation_note = "docker_ok"
    except Exception as exc:  # noqa: BLE001
        if plan.get("isolation_requested") == "docker" and (
            (os.getenv("ZECT_CODING_ENGINE_ISOLATION_STRICT") or "").strip().lower()
            in ("1", "true", "yes", "on")
        ):
            dispose_worktree(
                workspace_id=ws.workspace_id,
                repo_path=ws.repo_path,
                workspace_path=ws.path,
                preserve_artifacts=False,
            )
            raise WorkspaceError(f"docker_sandbox_failed:{exc}") from exc
        ws.isolation = "worktree"
        ws.isolation_note = f"docker_start_failed_fallback_worktree:{exc}"
    return ws


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


def dispose_isolated_workspace(
    *,
    workspace_id: str,
    repo_path: str | None = None,
    workspace_path: str | None = None,
    container_id: str | None = None,
    preserve_artifacts: bool = True,
) -> dict:
    """Stop optional Docker sandbox, then dispose worktree + preserve patch."""
    if container_id:
        try:
            from app.services.coding_engine.docker_sandbox import stop_workspace_sandbox

            stop_workspace_sandbox(container_id)
        except Exception:
            pass
    result = dispose_worktree(
        workspace_id=workspace_id,
        repo_path=repo_path,
        workspace_path=workspace_path,
        preserve_artifacts=preserve_artifacts,
    )
    result["container_stopped"] = bool(container_id)
    return result

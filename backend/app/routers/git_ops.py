"""Git Operations API — autonomous git add, commit, push, branch, status, PR creation.

Closes the "Git Operations" gap vs Devin: ZECT can now perform git
operations autonomously instead of only via the GitHub API.
"""

import os
import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/git", tags=["git-ops"])

ALLOWED_ROOTS = ["/home", "/tmp", "/var", "/opt"]


def _validate_repo(path: str) -> str:
    """Validate that path is a git repo under allowed roots."""
    from pathlib import Path
    p = Path(path).resolve()
    if not any(str(p).startswith(root) for root in ALLOWED_ROOTS):
        raise HTTPException(status_code=403, detail="Access denied: path not allowed")
    if not (p / ".git").is_dir():
        raise HTTPException(status_code=400, detail="Not a git repository")
    return str(p)


def _run_git(repo_path: str, args: list[str], timeout: int = 30) -> dict:
    """Run a git command and return stdout/stderr/exit_code."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "Command timed out"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


# ── Models ────────────────────────────────────────────────────────────────

class GitStatusResponse(BaseModel):
    branch: str
    clean: bool
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    ahead: int
    behind: int


class GitCommitRequest(BaseModel):
    repo_path: str
    message: str
    files: list[str] | None = None  # None = all staged; list = specific files to add first


class GitPushRequest(BaseModel):
    repo_path: str
    remote: str = "origin"
    branch: str | None = None  # None = current branch


class GitBranchRequest(BaseModel):
    repo_path: str
    branch_name: str
    checkout: bool = True
    from_branch: str | None = None


class GitCheckoutRequest(BaseModel):
    repo_path: str
    branch: str


class GitDiffResponse(BaseModel):
    diff: str
    files_changed: int
    insertions: int
    deletions: int


class GitLogEntry(BaseModel):
    hash: str
    short_hash: str
    author: str
    date: str
    message: str


class CreatePRRequest(BaseModel):
    repo_path: str
    title: str
    body: str = ""
    head_branch: str | None = None  # None = current branch
    base_branch: str = "main"
    owner: str | None = None
    repo_name: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/status")
def git_status(repo_path: str):
    """Get git status: branch, staged, modified, untracked files."""
    path = _validate_repo(repo_path)

    # Get current branch
    branch_result = _run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_result["stdout"].strip() if branch_result["exit_code"] == 0 else "unknown"

    # Get status
    status_result = _run_git(path, ["status", "--porcelain"])
    lines = status_result["stdout"].strip().split("\n") if status_result["stdout"].strip() else []

    staged, modified, untracked = [], [], []
    for line in lines:
        if not line:
            continue
        x, y = line[0], line[1]
        fname = line[3:]
        if x in ("A", "M", "D", "R"):
            staged.append(fname)
        if y == "M":
            modified.append(fname)
        elif y == "?":
            untracked.append(fname)

    # Get ahead/behind
    ahead, behind = 0, 0
    ab_result = _run_git(path, ["rev-list", "--left-right", "--count", f"{branch}...origin/{branch}"])
    if ab_result["exit_code"] == 0:
        parts = ab_result["stdout"].strip().split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    return GitStatusResponse(
        branch=branch,
        clean=len(staged) == 0 and len(modified) == 0 and len(untracked) == 0,
        staged=staged,
        modified=modified,
        untracked=untracked,
        ahead=ahead,
        behind=behind,
    )


@router.post("/add")
def git_add(repo_path: str, files: list[str] | None = None):
    """Stage files. If files is None, stages all changes."""
    path = _validate_repo(repo_path)
    if files:
        result = _run_git(path, ["add"] + files)
    else:
        result = _run_git(path, ["add", "-A"])

    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=f"git add failed: {result['stderr']}")
    return {"status": "ok", "message": result["stdout"] or "Files staged"}


@router.post("/commit")
def git_commit(req: GitCommitRequest):
    """Commit staged changes (or add+commit specific files)."""
    path = _validate_repo(req.repo_path)

    # Optionally add specific files first
    if req.files:
        add_result = _run_git(path, ["add"] + req.files)
        if add_result["exit_code"] != 0:
            raise HTTPException(status_code=500, detail=f"git add failed: {add_result['stderr']}")

    result = _run_git(path, ["commit", "-m", req.message])
    if result["exit_code"] != 0:
        if "nothing to commit" in result["stdout"] + result["stderr"]:
            return {"status": "nothing_to_commit", "message": "Nothing to commit, working tree clean"}
        raise HTTPException(status_code=500, detail=f"git commit failed: {result['stderr']}")

    return {"status": "committed", "message": result["stdout"].strip()}


@router.post("/push")
def git_push(req: GitPushRequest):
    """Push commits to remote."""
    path = _validate_repo(req.repo_path)
    branch = req.branch
    if not branch:
        br = _run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        branch = br["stdout"].strip()

    result = _run_git(path, ["push", req.remote, branch], timeout=60)
    if result["exit_code"] != 0:
        # Try with -u for new branches
        result = _run_git(path, ["push", "-u", req.remote, branch], timeout=60)
        if result["exit_code"] != 0:
            raise HTTPException(status_code=500, detail=f"git push failed: {result['stderr']}")

    return {"status": "pushed", "remote": req.remote, "branch": branch, "output": result["stdout"] + result["stderr"]}


@router.post("/branch")
def git_branch(req: GitBranchRequest):
    """Create a new branch, optionally checkout."""
    path = _validate_repo(req.repo_path)

    args = ["checkout", "-b", req.branch_name]
    if req.from_branch:
        args.append(req.from_branch)

    if not req.checkout:
        args = ["branch", req.branch_name]
        if req.from_branch:
            args.append(req.from_branch)

    result = _run_git(path, args)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=f"git branch failed: {result['stderr']}")

    return {"status": "created", "branch": req.branch_name, "checked_out": req.checkout}


@router.post("/checkout")
def git_checkout(req: GitCheckoutRequest):
    """Checkout an existing branch."""
    path = _validate_repo(req.repo_path)
    result = _run_git(path, ["checkout", req.branch])
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=f"git checkout failed: {result['stderr']}")
    return {"status": "checked_out", "branch": req.branch}


@router.get("/diff")
def git_diff(repo_path: str, staged: bool = False):
    """Get the current diff."""
    path = _validate_repo(repo_path)
    args = ["diff"]
    if staged:
        args.append("--staged")

    result = _run_git(path, args)
    diff = result["stdout"]

    # Get stats
    stat_args = ["diff", "--stat"]
    if staged:
        stat_args.append("--staged")
    stat_result = _run_git(path, stat_args)

    files_changed, insertions, deletions = 0, 0, 0
    stat_lines = stat_result["stdout"].strip().split("\n")
    if stat_lines:
        summary = stat_lines[-1]
        import re
        fc = re.search(r"(\d+) files? changed", summary)
        ins = re.search(r"(\d+) insertions?", summary)
        dels = re.search(r"(\d+) deletions?", summary)
        if fc:
            files_changed = int(fc.group(1))
        if ins:
            insertions = int(ins.group(1))
        if dels:
            deletions = int(dels.group(1))

    return GitDiffResponse(
        diff=diff,
        files_changed=files_changed,
        insertions=insertions,
        deletions=deletions,
    )


@router.get("/log")
def git_log(repo_path: str, limit: int = 20):
    """Get recent commit log."""
    path = _validate_repo(repo_path)
    result = _run_git(path, ["log", f"--max-count={limit}", "--format=%H|%h|%an|%ai|%s"])
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=f"git log failed: {result['stderr']}")

    entries = []
    for line in result["stdout"].strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 4)
        if len(parts) == 5:
            entries.append(GitLogEntry(
                hash=parts[0], short_hash=parts[1],
                author=parts[2], date=parts[3], message=parts[4],
            ))
    return entries


@router.get("/branches")
def git_branches(repo_path: str):
    """List all branches."""
    path = _validate_repo(repo_path)
    result = _run_git(path, ["branch", "-a", "--format=%(refname:short)|%(objectname:short)|%(upstream:short)"])
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=f"git branch failed: {result['stderr']}")

    current_result = _run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
    current = current_result["stdout"].strip()

    branches = []
    for line in result["stdout"].strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        name = parts[0]
        branches.append({
            "name": name,
            "short_hash": parts[1] if len(parts) > 1 else "",
            "upstream": parts[2] if len(parts) > 2 else "",
            "current": name == current,
        })
    return {"current": current, "branches": branches}


@router.post("/pull")
def git_pull(repo_path: str, remote: str = "origin"):
    """Pull latest changes from remote."""
    path = _validate_repo(repo_path)
    result = _run_git(path, ["pull", remote], timeout=60)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=f"git pull failed: {result['stderr']}")
    return {"status": "pulled", "output": result["stdout"] + result["stderr"]}


@router.post("/create-pr")
def create_pull_request(req: CreatePRRequest):
    """Create a GitHub PR using the GitHub API (via PyGithub)."""
    path = _validate_repo(req.repo_path)

    # Determine owner/repo from remote URL if not provided
    owner = req.owner
    repo_name = req.repo_name
    if not owner or not repo_name:
        remote_result = _run_git(path, ["remote", "get-url", "origin"])
        if remote_result["exit_code"] != 0:
            raise HTTPException(status_code=400, detail="Cannot determine remote URL")
        url = remote_result["stdout"].strip()
        # Parse owner/repo from URL (https://github.com/owner/repo.git or git@github.com:owner/repo.git)
        import re
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        if not m:
            raise HTTPException(status_code=400, detail=f"Cannot parse owner/repo from: {url}")
        owner = m.group(1)
        repo_name = m.group(2)

    # Determine head branch
    head = req.head_branch
    if not head:
        br = _run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        head = br["stdout"].strip()

    # Use PyGithub to create PR
    try:
        from app import github_service
        pr = github_service.create_pull_request(
            owner=owner,
            repo=repo_name,
            title=req.title,
            body=req.body,
            head=head,
            base=req.base_branch,
        )
        return {
            "status": "created",
            "pr_number": pr.get("number"),
            "pr_url": pr.get("html_url"),
            "title": req.title,
            "head": head,
            "base": req.base_branch,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create PR: {e}")


@router.post("/stash")
def git_stash(repo_path: str, pop: bool = False):
    """Stash or pop stashed changes."""
    path = _validate_repo(repo_path)
    args = ["stash", "pop"] if pop else ["stash"]
    result = _run_git(path, args)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=f"git stash failed: {result['stderr']}")
    return {"status": "popped" if pop else "stashed", "output": result["stdout"]}

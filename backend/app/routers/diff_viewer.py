"""Diff Viewer API — side-by-side diff for code review.

Provides unified and side-by-side diffs for:
- Two code strings
- Git commits
- PR file changes
"""

import os
import difflib
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/diff", tags=["diff-viewer"])


class StringDiffRequest(BaseModel):
    left: str
    right: str
    left_label: str = "Original"
    right_label: str = "Modified"
    context_lines: int = 3


class GitDiffRequest(BaseModel):
    owner: str
    repo: str
    base: str  # commit SHA or branch
    head: str  # commit SHA or branch


class FileDiffRequest(BaseModel):
    file_path: str
    repo_path: str
    commit_a: str = "HEAD~1"
    commit_b: str = "HEAD"


def _compute_diff(left: str, right: str, left_label: str, right_label: str, context: int) -> dict:
    """Compute unified and side-by-side diff."""
    left_lines = left.splitlines(keepends=True)
    right_lines = right.splitlines(keepends=True)

    # Unified diff
    unified = list(difflib.unified_diff(
        left_lines, right_lines,
        fromfile=left_label, tofile=right_label,
        n=context,
    ))

    # Side-by-side diff
    differ = difflib.SequenceMatcher(None, left_lines, right_lines)
    side_by_side = []
    line_num_left = 0
    line_num_right = 0

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                line_num_left += 1
                line_num_right += 1
                side_by_side.append({
                    "type": "equal",
                    "left_line": line_num_left,
                    "right_line": line_num_right,
                    "left": left_lines[i1 + k].rstrip("\n"),
                    "right": right_lines[j1 + k].rstrip("\n"),
                })
        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                left_text = left_lines[i1 + k].rstrip("\n") if k < (i2 - i1) else ""
                right_text = right_lines[j1 + k].rstrip("\n") if k < (j2 - j1) else ""
                if k < (i2 - i1):
                    line_num_left += 1
                if k < (j2 - j1):
                    line_num_right += 1
                side_by_side.append({
                    "type": "modified",
                    "left_line": line_num_left if k < (i2 - i1) else None,
                    "right_line": line_num_right if k < (j2 - j1) else None,
                    "left": left_text,
                    "right": right_text,
                })
        elif tag == "delete":
            for k in range(i2 - i1):
                line_num_left += 1
                side_by_side.append({
                    "type": "deleted",
                    "left_line": line_num_left,
                    "right_line": None,
                    "left": left_lines[i1 + k].rstrip("\n"),
                    "right": "",
                })
        elif tag == "insert":
            for k in range(j2 - j1):
                line_num_right += 1
                side_by_side.append({
                    "type": "added",
                    "left_line": None,
                    "right_line": line_num_right,
                    "left": "",
                    "right": right_lines[j1 + k].rstrip("\n"),
                })

    stats = {
        "additions": sum(
            1 for row in side_by_side
            if row["type"] in ("added", "modified") and row["right"]
        ),
        "deletions": sum(
            1 for row in side_by_side
            if row["type"] in ("deleted", "modified") and row["left"]
        ),
        "total_left_lines": len(left_lines),
        "total_right_lines": len(right_lines),
    }

    return {
        "unified": "".join(unified),
        "side_by_side": side_by_side,
        "stats": stats,
    }


@router.post("/compare")
def compare_strings(req: StringDiffRequest):
    """Compare two code strings and return unified + side-by-side diff."""
    return _compute_diff(req.left, req.right, req.left_label, req.right_label, req.context_lines)


@router.post("/git")
def git_diff(req: GitDiffRequest):
    """Get diff between two git refs via GitHub API."""
    import requests
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"} if token else {}

    url = f"https://api.github.com/repos/{req.owner}/{req.repo}/compare/{req.base}...{req.head}"
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch git diff")

    data = resp.json()
    files = []
    for f in data.get("files", []):
        patch = f.get("patch", "")
        files.append({
            "filename": f.get("filename", ""),
            "status": f.get("status", ""),
            "additions": f.get("additions", 0),
            "deletions": f.get("deletions", 0),
            "changes": f.get("changes", 0),
            "patch": patch,
        })

    return {
        "base": req.base,
        "head": req.head,
        "total_commits": data.get("total_commits", 0),
        "files_changed": len(files),
        "files": files,
        "stats": {
            "additions": sum(f["additions"] for f in files),
            "deletions": sum(f["deletions"] for f in files),
        },
    }


@router.post("/file")
def file_diff(req: FileDiffRequest):
    """Get diff of a specific file between two commits in a local repo."""
    repo_path = req.repo_path
    if not os.path.isdir(repo_path):
        raise HTTPException(status_code=404, detail="Repository path not found")

    try:
        result_a = subprocess.run(
            ["git", "show", f"{req.commit_a}:{req.file_path}"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        result_b = subprocess.run(
            ["git", "show", f"{req.commit_b}:{req.file_path}"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        )

        left = result_a.stdout if result_a.returncode == 0 else ""
        right = result_b.stdout if result_b.returncode == 0 else ""

        return _compute_diff(
            left, right,
            f"{req.file_path} ({req.commit_a})",
            f"{req.file_path} ({req.commit_b})",
            3,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Git command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

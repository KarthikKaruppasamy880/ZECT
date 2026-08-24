"""Authorized-root git pull/sync — never starts a coding mission."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

_PULL_INTENT = re.compile(
    r"(pull|sync|fast[-\s]?forward|ff-only|latest).{0,120}(zoas|zaf|clone|root|repo|workspace)",
    re.I | re.S,
)
_PULL_SHORT = re.compile(r"\b(git\s+pull|pull latest|sync clones?|update clones?)\b", re.I)


def is_pull_sync_intent(goal: str) -> bool:
    text = (goal or "").strip()
    if not text:
        return False
    return bool(_PULL_INTENT.search(text) or _PULL_SHORT.search(text))


def ff_pull_root(repo_path: str, *, remote: str = "origin") -> dict[str, Any]:
    """Fast-forward only pull on an authorized workspace path."""
    from app.infrastructure.allowed_paths import path_under_allowed_roots

    root = path_under_allowed_roots(repo_path)
    result = subprocess.run(
        ["git", "pull", "--ff-only", remote],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=90,
    )
    return {
        "ok": result.returncode == 0,
        "path": str(root),
        "exit_code": result.returncode,
        "stdout": (result.stdout or "")[-2000:],
        "stderr": (result.stderr or "")[-1000:],
        "lattice_stale": True,
    }


def sync_authorized_roots(roots: list[dict[str, Any]]) -> dict[str, Any]:
    pulled: list[dict[str, Any]] = []
    for row in roots:
        path = str(row.get("path") or row.get("local_path") or row.get("source_path") or "").strip()
        if not path:
            continue
        item = ff_pull_root(path)
        item["label"] = row.get("label") or row.get("repo_name") or Path(path).name
        item["repository_id"] = row.get("id") or row.get("repository_id")
        pulled.append(item)
    ok = bool(pulled) and all(p.get("ok") for p in pulled)
    return {
        "ok": ok,
        "mission_created": False,
        "phase": "synced",
        "status": "pulled" if ok else "pull_failed",
        "lattice_stale": True,
        "no_auto_merge": True,
        "roots": pulled,
        "message": "Pulled authorized roots (ff-only). Lattice is STALE until re-index. No coding mission started.",
    }

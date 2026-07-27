"""Filesystem roots allowed for local repo/file/git operations."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_ROOTS = ["/home", "/tmp", "/var", "/opt"]


def allowed_roots() -> list[str]:
    roots = list(_DEFAULT_ROOTS)
    workspace = os.getenv("ZECT_WORKSPACE_ROOT", "").strip()
    if workspace:
        roots.append(str(Path(workspace).resolve()))
    mentrix_ws = os.getenv("MENTRIX_WORKSPACE", "").strip()
    if mentrix_ws:
        roots.append(str(Path(mentrix_ws).resolve()))
    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for root in roots:
        norm = str(Path(root).resolve()) if root else root
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def path_under_allowed_roots(raw: str) -> Path:
    p = Path(raw).resolve()
    roots = allowed_roots()
    if not any(str(p).startswith(root) for root in roots):
        raise ValueError(f"Access denied: path must be under {roots}")
    return p

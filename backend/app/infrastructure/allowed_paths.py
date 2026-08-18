"""Filesystem roots allowed for local repo/file/git operations."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# POSIX-only — kept for existing Linux/macOS deployments that rely on them.
_DEFAULT_ROOTS = ["/home", "/tmp", "/var", "/opt"]


def _cross_platform_defaults() -> list[str]:
    """The POSIX defaults above never match a resolved Windows path, so a
    fresh Windows install with no ZECT_WORKSPACE_ROOT set had File Explorer/
    Git Ops/Diff Viewer silently unable to reach anything. Path.home() and
    the system temp dir resolve correctly on every platform and are the same
    kind of "your own stuff, not the whole filesystem" boundary the POSIX
    list was already going for.
    """
    try:
        return [str(Path.home()), str(Path(tempfile.gettempdir()))]
    except Exception:
        return []


def allowed_roots() -> list[str]:
    roots = list(_DEFAULT_ROOTS) + _cross_platform_defaults()
    workspace = os.getenv("ZECT_WORKSPACE_ROOT", "").strip()
    if workspace:
        roots.append(str(Path(workspace).resolve()))
    mentrix_ws = os.getenv("MENTRIX_WORKSPACE", "").strip()
    if mentrix_ws:
        roots.append(str(Path(mentrix_ws).resolve()))
    engine_ws = os.getenv("ZECT_ENGINE_WORKSPACE_ROOT", "").strip()
    if engine_ws:
        roots.append(str(Path(engine_ws).resolve()))
    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for root in roots:
        norm = str(Path(root).resolve()) if root else root
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def is_path_under_root(candidate: Path, root: Path) -> bool:
    """True iff resolved candidate is root or a descendant.

    String prefix is not enough: ``C:\\tmp\\ws-evil`` starts with ``C:\\tmp\\ws``.
    Symlinks are evaluated after ``Path.resolve()`` so a jail-escape link fails.
    """
    try:
        resolved = candidate.resolve()
        root_resolved = root.resolve()
    except OSError:
        return False
    try:
        resolved.relative_to(root_resolved)
        return True
    except ValueError:
        pass
    if os.name == "nt":
        child = os.path.normcase(os.path.normpath(str(resolved)))
        parent = os.path.normcase(os.path.normpath(str(root_resolved)))
        if child == parent:
            return True
        return child.startswith(parent + os.sep)
    return False


def path_under_allowed_roots(raw: str) -> Path:
    p = Path(raw).resolve()
    roots = allowed_roots()
    if not any(is_path_under_root(p, Path(root)) for root in roots):
        raise ValueError(f"Access denied: path must be under {roots}")
    return p

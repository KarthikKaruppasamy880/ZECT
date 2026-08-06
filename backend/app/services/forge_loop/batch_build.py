"""Batched Mentrix Build helpers — files_expected + human batch gates."""

from __future__ import annotations

import os
from typing import Any

MENTRIX_BUILD_BATCH_SIZE = max(1, int(os.getenv("MENTRIX_BUILD_BATCH_SIZE", "6")))
MENTRIX_MAX_FILES_PER_RUN = max(1, int(os.getenv("MENTRIX_MAX_FILES_PER_RUN", "40")))


def normalize_file_paths(paths: list[Any] | None) -> list[str]:
    out: list[str] = []
    for p in paths or []:
        s = str(p or "").strip().replace("\\", "/")
        if not s or s.startswith("(") or s in out:
            continue
        out.append(s)
    return out


def collect_files_expected(plan: dict[str, Any] | None) -> list[str]:
    """Prefer plan.files_expected; else union of step.files."""
    if not plan:
        return []
    top = plan.get("files_expected")
    if isinstance(top, list) and top:
        return normalize_file_paths(top)[:MENTRIX_MAX_FILES_PER_RUN]
    collected: list[Any] = []
    for step in plan.get("steps") or []:
        if isinstance(step, dict):
            collected.extend(step.get("files") or [])
    return normalize_file_paths(collected)[:MENTRIX_MAX_FILES_PER_RUN]


def chunk_files(files: list[str], size: int | None = None) -> list[list[str]]:
    if not files:
        return []
    n = max(1, size or MENTRIX_BUILD_BATCH_SIZE)
    return [files[i : i + n] for i in range(0, len(files), n)]


def attach_files_expected(plan: dict[str, Any], extra: list[str] | None = None) -> dict[str, Any]:
    """Mutate/return plan with a stable files_expected list."""
    merged = list(collect_files_expected(plan))
    for p in normalize_file_paths(extra):
        if p not in merged:
            merged.append(p)
    merged = merged[:MENTRIX_MAX_FILES_PER_RUN]
    plan = dict(plan or {})
    plan["files_expected"] = merged
    return plan

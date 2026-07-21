"""Map LLM-reported lines to PR diff hunks for accurate inline comments."""

from __future__ import annotations

import re
from typing import Any

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


def parse_new_file_line_ranges(patch: str) -> list[tuple[int, int]]:
    """Return inclusive (start, end) line ranges on the new file side of a patch."""
    ranges: list[tuple[int, int]] = []
    if not patch:
        return ranges
    for m in _HUNK_RE.finditer(patch):
        start = int(m.group(1))
        count = int(m.group(2) or "1")
        ranges.append((start, start + max(count, 1) - 1))
    return ranges


def clamp_finding_line(file_path: str, line: int | None, files: list[dict[str, Any]]) -> int | None:
    """Clamp a finding line to a valid new-side line in the matching file patch."""
    if line is None or line <= 0:
        return None
    for f in files:
        if f.get("filename") != file_path:
            continue
        ranges = parse_new_file_line_ranges(f.get("patch") or "")
        if not ranges:
            return line
        for start, end in ranges:
            if start <= line <= end:
                return line
        # Nearest line in any hunk
        best = ranges[0][0]
        best_dist = abs(line - best)
        for start, end in ranges:
            for cand in (start, end):
                d = abs(line - cand)
                if d < best_dist:
                    best, best_dist = cand, d
        return best
    return line


def chunk_files_for_review(files: list[dict[str, Any]], max_chars: int = 12000) -> list[list[dict[str, Any]]]:
    """Split PR files into chunks so large diffs are not truncated silently."""
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    size = 0
    for f in files:
        patch_len = len(f.get("patch") or "")
        if current and size + patch_len > max_chars:
            chunks.append(current)
            current, size = [], 0
        current.append(f)
        size += patch_len
    if current:
        chunks.append(current)
    return chunks or [[]]

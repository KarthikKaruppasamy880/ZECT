"""Semantic chunking for Build's retrieval index.

Boundary-aware: reuses auto_indexer's per-language function/class regex patterns
to split files at real code boundaries (one function/class per chunk) rather than
arbitrary fixed line counts. Falls back to overlapping fixed-size line chunks for
unrecognized languages or files where no boundaries were found, so nothing is
silently skipped.
"""

from __future__ import annotations

from app.services.auto_indexer import PATTERNS

MAX_CHUNK_LINES = 150  # oversized boundary chunks (e.g. a huge class) get sub-split
FALLBACK_CHUNK_LINES = 60
FALLBACK_OVERLAP_LINES = 10


def _line_of(content: str, char_pos: int) -> int:
    return content.count("\n", 0, char_pos) + 1


def _fixed_size_chunks(content: str, start_line: int = 1) -> list[dict]:
    lines = content.split("\n")
    if not lines:
        return []
    chunks: list[dict] = []
    i = 0
    while i < len(lines):
        end = min(i + FALLBACK_CHUNK_LINES, len(lines))
        chunk_lines = lines[i:end]
        chunks.append({
            "content": "\n".join(chunk_lines),
            "line_start": start_line + i,
            "line_end": start_line + end - 1,
            "symbol_name": None,
        })
        if end == len(lines):
            break
        i += FALLBACK_CHUNK_LINES - FALLBACK_OVERLAP_LINES
    return chunks


def chunk_file(content: str, language: str) -> list[dict]:
    """Split file content into semantic chunks.

    Returns list of {content, line_start, line_end, symbol_name}.
    """
    if not content.strip():
        return []

    patterns = PATTERNS.get(language, {})
    boundary_patterns = [p for k, p in patterns.items() if k in ("function", "class")]
    if not boundary_patterns:
        return _fixed_size_chunks(content)

    # Collect all function/class match start positions with their names, sorted.
    boundaries: list[tuple[int, str]] = []
    for pattern in boundary_patterns:
        for match in pattern.finditer(content):
            name = match.group(1).strip() if match.groups() else ""
            boundaries.append((match.start(), name))
    boundaries.sort(key=lambda b: b[0])

    if not boundaries:
        return _fixed_size_chunks(content)

    chunks: list[dict] = []
    total_lines = content.count("\n") + 1
    for idx, (pos, name) in enumerate(boundaries):
        chunk_start_char = pos
        chunk_end_char = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(content)
        chunk_text = content[chunk_start_char:chunk_end_char]
        line_start = _line_of(content, chunk_start_char)
        line_end = line_start + chunk_text.count("\n")

        if chunk_text.count("\n") + 1 > MAX_CHUNK_LINES:
            for sub in _fixed_size_chunks(chunk_text, start_line=line_start):
                sub["symbol_name"] = name or None
                chunks.append(sub)
        else:
            chunks.append({
                "content": chunk_text,
                "line_start": line_start,
                "line_end": min(line_end, total_lines),
                "symbol_name": name or None,
            })

    # Anything before the first boundary (imports, module docstring, constants)
    # is real content too — don't silently drop it.
    first_pos = boundaries[0][0]
    if first_pos > 0:
        preamble = content[:first_pos]
        if preamble.strip():
            chunks.insert(0, {
                "content": preamble,
                "line_start": 1,
                "line_end": _line_of(content, first_pos) - 1 or 1,
                "symbol_name": None,
            })

    return chunks

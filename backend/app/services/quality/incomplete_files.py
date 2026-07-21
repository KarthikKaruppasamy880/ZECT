"""Refuse-incomplete gate — expected vs written files + deny-list placeholders."""

from __future__ import annotations

import re
from typing import Any

_DENY_PATTERNS = [
    re.compile(r"\bTODO\b"),
    re.compile(r"\bFIXME\b"),
    re.compile(r"NotImplementedError"),
    re.compile(r"pass\s*#\s*implement", re.I),
    re.compile(r"raise\s+NotImplemented"),
    re.compile(r"\.\.\.\s*(#|$)"),
]


def check_incomplete_files(
    *,
    files_expected: list[str] | None,
    files_written: list[str] | None,
    file_contents: dict[str, str] | None = None,
    generated_code: str = "",
) -> dict[str, Any]:
    """Return ok=False when files missing, empty, truncated, or deny-listed."""
    expected = [f for f in (files_expected or []) if f]
    written = [f for f in (files_written or []) if f]
    blockers: list[str] = []

    if expected:
        missing = [f for f in expected if f not in written]
        if missing:
            blockers.append(f"missing_files:{','.join(missing[:8])}")

    contents = dict(file_contents or {})
    if generated_code and not contents and written:
        contents[written[0]] = generated_code
    elif generated_code and not contents:
        contents["(generated)"] = generated_code

    for path, text in contents.items():
        if text is None or not str(text).strip():
            blockers.append(f"empty_file:{path}")
            continue
        # Heuristic truncation: ends mid-token / unclosed fence
        stripped = str(text).rstrip()
        if not stripped:
            blockers.append(f"empty_file:{path}")
        elif stripped.endswith("```") or stripped.endswith("\\"):
            blockers.append(f"truncated:{path}")
        for pat in _DENY_PATTERNS:
            if pat.search(str(text)):
                blockers.append(f"deny_placeholder:{path}")
                break

    return {
        "ok": len(blockers) == 0,
        "files_expected": expected,
        "files_written": written,
        "blockers": blockers,
        "gate": "incomplete_files",
    }

"""Real lint/typecheck diagnostics for the Developer Workspace Problems panel.

Previously the panel only ever showed the last mission's error string plus
the list of git-changed paths -- no actual linter/compiler integration, so a
repo with real lint or type errors showed nothing wrong. Each tool here is
invoked directly (not via a package.json script, unlike the CI-oriented
quality gate in coding_engine/lifecycle.py) so its structured JSON/line
output can be parsed into file/line/column diagnostics. A tool is skipped
(returns None) when the repo has no matching config or the binary isn't on
PATH, so an unconfigured repo reports "nothing checked", not "nothing wrong".
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

_TSC_LINE_RE = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\): (?P<severity>error|warning) (?P<code>TS\d+): (?P<message>.+)$"
)
_MYPY_LINE_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<col>\d+))?: (?P<severity>error|warning|note): (?P<message>.+)$"
)


def _pyproject_has_section(pyproject: Path, section: str) -> bool:
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return f"[{section}]" in text


def _node_bin(root: Path, name: str) -> str | None:
    base = root / "node_modules" / ".bin" / name
    for candidate in (base, base.with_suffix(".cmd")):
        if candidate.is_file():
            return str(candidate)
    return None


def _ruff_problems(root: Path) -> list[dict[str, Any]] | None:
    configured = (
        (root / "ruff.toml").is_file()
        or (root / ".ruff.toml").is_file()
        or _pyproject_has_section(root / "pyproject.toml", "tool.ruff")
    )
    if not configured or not shutil.which("ruff"):
        return None
    try:
        completed = subprocess.run(
            ["ruff", "check", "--output-format=json", "."],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return [{"tool": "ruff", "severity": "error", "file": "", "line": 0, "column": 0, "message": "ruff check timed out"}]
    try:
        rows = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return []
    problems: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        loc = row.get("location") or {}
        problems.append(
            {
                "tool": "ruff",
                "severity": "error",
                "file": str(row.get("filename") or ""),
                "line": int(loc.get("row") or 0),
                "column": int(loc.get("column") or 0),
                "message": f"{row.get('code') or ''} {row.get('message') or ''}".strip(),
            }
        )
    return problems


def _mypy_problems(root: Path) -> list[dict[str, Any]] | None:
    configured = (
        (root / "mypy.ini").is_file()
        or (root / ".mypy.ini").is_file()
        or _pyproject_has_section(root / "pyproject.toml", "tool.mypy")
    )
    if not configured or not shutil.which("mypy"):
        return None
    try:
        completed = subprocess.run(
            ["mypy", ".", "--no-color-output"], cwd=str(root), capture_output=True, text=True, timeout=90
        )
    except subprocess.TimeoutExpired:
        return [{"tool": "mypy", "severity": "error", "file": "", "line": 0, "column": 0, "message": "mypy timed out"}]
    problems: list[dict[str, Any]] = []
    for line in (completed.stdout or "").splitlines():
        m = _MYPY_LINE_RE.match(line.strip())
        if not m:
            continue
        problems.append(
            {
                "tool": "mypy",
                "severity": m.group("severity"),
                "file": m.group("file"),
                "line": int(m.group("line")),
                "column": int(m.group("col") or 0),
                "message": m.group("message"),
            }
        )
    return problems


def _eslint_problems(root: Path) -> list[dict[str, Any]] | None:
    has_cfg = any(
        (root / name).is_file()
        for name in (
            "eslint.config.js",
            "eslint.config.mjs",
            "eslint.config.cjs",
            ".eslintrc",
            ".eslintrc.js",
            ".eslintrc.cjs",
            ".eslintrc.json",
            ".eslintrc.yml",
        )
    )
    binary = _node_bin(root, "eslint")
    if not has_cfg or not binary:
        return None
    try:
        completed = subprocess.run(
            [binary, ".", "--format", "json"], cwd=str(root), capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return [{"tool": "eslint", "severity": "error", "file": "", "line": 0, "column": 0, "message": "eslint timed out"}]
    try:
        rows = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return []
    problems: list[dict[str, Any]] = []
    for file_result in rows if isinstance(rows, list) else []:
        file_path = str(file_result.get("filePath") or "")
        for msg in file_result.get("messages") or []:
            problems.append(
                {
                    "tool": "eslint",
                    "severity": "error" if msg.get("severity") == 2 else "warning",
                    "file": file_path,
                    "line": int(msg.get("line") or 0),
                    "column": int(msg.get("column") or 0),
                    "message": f"{msg.get('ruleId') or ''} {msg.get('message') or ''}".strip(),
                }
            )
    return problems


def _tsc_problems(root: Path) -> list[dict[str, Any]] | None:
    has_cfg = (root / "tsconfig.json").is_file()
    binary = _node_bin(root, "tsc")
    if not has_cfg or not binary:
        return None
    try:
        completed = subprocess.run(
            [binary, "--noEmit", "--pretty", "false"], cwd=str(root), capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return [{"tool": "tsc", "severity": "error", "file": "", "line": 0, "column": 0, "message": "tsc timed out"}]
    problems: list[dict[str, Any]] = []
    for line in (completed.stdout or "").splitlines():
        m = _TSC_LINE_RE.match(line.strip())
        if not m:
            continue
        problems.append(
            {
                "tool": "tsc",
                "severity": m.group("severity"),
                "file": m.group("file"),
                "line": int(m.group("line")),
                "column": int(m.group("col")),
                "message": f"{m.group('code')} {m.group('message')}".strip(),
            }
        )
    return problems


def collect_workspace_problems(root: Path) -> dict[str, Any]:
    """Run every applicable diagnostic tool against ``root`` and return a
    flat, sorted list of findings plus which tools actually ran."""
    root = Path(root)
    results = {
        "ruff": _ruff_problems(root),
        "mypy": _mypy_problems(root),
        "eslint": _eslint_problems(root),
        "tsc": _tsc_problems(root),
    }
    checked = [name for name, res in results.items() if res is not None]
    problems: list[dict[str, Any]] = []
    for res in results.values():
        if res:
            problems.extend(res)
    problems.sort(key=lambda p: (str(p.get("file") or ""), int(p.get("line") or 0)))
    return {"problems": problems, "checked": checked, "count": len(problems)}

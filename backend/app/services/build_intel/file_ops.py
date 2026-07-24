"""Shared file-write safety + diff helpers for Build — used by the single-file
and multi-file generate/apply paths so this logic exists in exactly one place.
"""

from __future__ import annotations

from pathlib import Path


def diff_against_existing(repo_local_path: str, file_path: str, generated_code: str) -> tuple[bool, dict | None]:
    """Returns (file_existed, diff). diff is diff_viewer._compute_diff's output
    (unified + side_by_side + stats), or None when the file doesn't exist yet."""
    from app.routers.diff_viewer import _compute_diff

    target = Path(repo_local_path) / file_path
    if not target.is_file():
        return False, None
    old_content = target.read_text(encoding="utf-8", errors="replace")
    diff = _compute_diff(old_content, generated_code, f"{file_path} (current)", f"{file_path} (generated)", 3)
    return True, diff


def safe_resolve_target(repo_local_path: str, file_path: str) -> Path:
    """Resolve file_path against the repo root, raising ValueError if it escapes
    the workspace (path traversal, e.g. "../../etc/passwd")."""
    root = Path(repo_local_path).resolve()
    target = (root / file_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("file_path escapes the repo workspace")
    return target


def write_file(repo_local_path: str, file_path: str, code: str) -> Path:
    """Path-safety-checked write. Raises ValueError on traversal attempts."""
    target = safe_resolve_target(repo_local_path, file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code, encoding="utf-8")
    return target


def check_rule_violations(db, code: str, language: str) -> list[dict]:
    """Free, deterministic pre-check against active Rules Engine rules — run
    before a human ever reviews the diff, so blocking patterns (secrets in
    code, eval() usage, etc.) surface immediately rather than after apply."""
    from app.routers.rules_engine import RuleEvalRequest, evaluate_rules

    results = evaluate_rules(RuleEvalRequest(code=code, language=language or "text"), db=db)
    return [r.model_dump() for r in results if r.matched]

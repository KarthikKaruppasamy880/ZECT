"""Coding Agent PLAN.md persistence — .zect/plans is working scratch, not committed by default.

Plans belong to the repository they plan changes for: when a workspace is
known, the plan is written to ``<workspace>/.zect/plans/<slug>.plan.md`` so it
shows up in that repo's Explorer/Monaco next to the code it describes (and is
gitignored via :func:`ensure_zect_ignored`). Without a workspace, plans fall
back to the ZECT-install-local root, which is also where plans written before
this became workspace-aware still live and are still readable.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")
_PLAN_SUFFIX = ".plan.md"


def ensure_zect_ignored(repo_root: Path) -> None:
    """Keep ``.zect/`` out of the user's commits — it is agent scratch, not
    source. Shared with the worktree-isolation path in lifecycle.py."""
    gi = repo_root / ".gitignore"
    try:
        text = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    except OSError:
        return
    if ".zect/" in text.splitlines() or text.endswith(".zect/\n") or ".zect/\n" in text:
        return
    suffix = "" if not text or text.endswith("\n") else "\n"
    try:
        gi.write_text(text + suffix + ".zect/\n", encoding="utf-8")
    except OSError:
        return


def _install_root() -> Path:
    env = (os.environ.get("ZECT_PLAN_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[4] / ".zect" / "plans").resolve()


def _root(workspace: str = "") -> Path:
    ws = (workspace or "").strip()
    if ws:
        return (Path(ws).expanduser() / ".zect" / "plans").resolve()
    return _install_root()


def slugify(text: str) -> str:
    s = _SAFE.sub("-", (text or "plan").strip().lower()).strip("-")
    return (s or "plan")[:48]


def plan_slug(work_item_or_run: str, title: str = "") -> str:
    return f"{slugify(work_item_or_run)}-{slugify(title or 'coding')}"


def plan_path(work_item_or_run: str, title: str = "", workspace: str = "") -> Path:
    return _root(workspace) / f"{plan_slug(work_item_or_run, title)}{_PLAN_SUFFIX}"


def save_plan(
    *,
    work_item_or_run: str,
    title: str,
    markdown: str,
    meta: dict[str, Any] | None = None,
    workspace: str = "",
) -> dict[str, Any]:
    body = (markdown or "").strip()
    if not body:
        raise ValueError("plan_empty")
    dest = plan_path(work_item_or_run, title, workspace)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if (workspace or "").strip():
        ensure_zect_ignored(Path(workspace).expanduser().resolve())
    envelope = {
        "id": _plan_id(dest),
        "work_item_or_run": work_item_or_run,
        "title": title,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {**(meta or {}), **({"workspace": workspace} if workspace else {})},
    }
    header = "<!-- zect-plan " + json.dumps(envelope, default=str) + " -->\n"
    dest.write_text(header + body + "\n", encoding="utf-8")
    return {"ok": True, "path": str(dest), "markdown": body, **envelope}


def _plan_id(path: Path) -> str:
    """``1-coding.plan.md`` -> ``1-coding`` (``Path.stem`` alone would leave
    the ``.plan`` half behind)."""
    name = path.name
    if name.endswith(_PLAN_SUFFIX):
        return name[: -len(_PLAN_SUFFIX)]
    return path.stem


def _candidate_paths(plan_id: str, workspace: str) -> list[Path]:
    """Workspace-local first, then the install-local fallback, and in each
    root both the current ``.plan.md`` and the pre-existing ``.md`` naming."""
    slug = slugify(plan_id)
    roots = [_root(workspace)] if (workspace or "").strip() else []
    roots.append(_install_root())
    out: list[Path] = []
    for root in roots:
        out.extend([root / f"{slug}{_PLAN_SUFFIX}", root / f"{slug}.md"])
        if root.is_dir():
            out.extend(sorted(root.glob(f"{slug}*.md")))
    return out


def load_plan(plan_id: str, workspace: str = "") -> dict[str, Any]:
    dest = next((p for p in _candidate_paths(plan_id, workspace) if p.is_file()), None)
    if dest is None:
        raise FileNotFoundError("plan_not_found")
    raw = dest.read_text(encoding="utf-8")
    meta: dict[str, Any] = {"id": _plan_id(dest), "path": str(dest)}
    body = raw
    if raw.startswith("<!-- zect-plan "):
        end = raw.find(" -->")
        if end > 0:
            try:
                meta.update(json.loads(raw[len("<!-- zect-plan ") : end]))
            except json.JSONDecodeError:
                pass
            body = raw[end + 4 :].lstrip("\n")
    return {**meta, "ok": True, "markdown": body.strip()}


def list_plans(limit: int = 40, workspace: str = "") -> list[dict[str, Any]]:
    root = _root(workspace)
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for p in sorted(root.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            rows.append(load_plan(_plan_id(p), workspace))
        except (OSError, FileNotFoundError):
            continue
    return rows

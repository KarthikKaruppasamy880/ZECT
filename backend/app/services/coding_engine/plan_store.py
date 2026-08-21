"""Coding Agent PLAN.md persistence — .zect/plans is working scratch, not committed by default."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def _root() -> Path:
    env = (os.environ.get("ZECT_PLAN_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[4] / ".zect" / "plans").resolve()


def slugify(text: str) -> str:
    s = _SAFE.sub("-", (text or "plan").strip().lower()).strip("-")
    return (s or "plan")[:48]


def plan_path(work_item_or_run: str, title: str = "") -> Path:
    stem = f"{slugify(work_item_or_run)}-{slugify(title or 'coding')}"
    return _root() / f"{stem}.md"


def save_plan(
    *,
    work_item_or_run: str,
    title: str,
    markdown: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dest = plan_path(work_item_or_run, title)
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = (markdown or "").strip()
    if not body:
        raise ValueError("plan_empty")
    envelope = {
        "id": dest.stem,
        "work_item_or_run": work_item_or_run,
        "title": title,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
    }
    header = "<!-- zect-plan " + json.dumps(envelope, default=str) + " -->\n"
    dest.write_text(header + body + "\n", encoding="utf-8")
    return {"ok": True, "id": dest.stem, "path": str(dest), "markdown": body, **envelope}


def load_plan(plan_id: str) -> dict[str, Any]:
    dest = _root() / f"{slugify(plan_id)}.md"
    if not dest.is_file():
        matches = list(_root().glob(f"{slugify(plan_id)}*.md")) if _root().is_dir() else []
        if not matches:
            raise FileNotFoundError("plan_not_found")
        dest = matches[0]
    raw = dest.read_text(encoding="utf-8")
    meta: dict[str, Any] = {"id": dest.stem, "path": str(dest)}
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


def list_plans(limit: int = 40) -> list[dict[str, Any]]:
    root = _root()
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for p in sorted(root.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            rows.append(load_plan(p.stem))
        except OSError:
            continue
    return rows

"""Prepare PR: one Mentrix Delivery run per WorkItem + coding mission. No auto-merge."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_TERMINAL = frozenset({"completed", "failed", "cancelled", "pr_created"})


def _store() -> Path:
    env = (os.environ.get("ZECT_SHIP_HANDOFF_PATH") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[3] / "data" / "ship_handoffs.json").resolve()


def _load() -> list[dict[str, Any]]:
    p = _store()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save(rows: list[dict[str, Any]]) -> None:
    p = _store()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def find_open_handoff(work_item_id: int | None, coding_mission_id: str) -> dict[str, Any] | None:
    mid = (coding_mission_id or "").strip()
    for row in _load():
        if str(row.get("coding_mission_id") or "") != mid:
            continue
        if work_item_id is not None and int(row.get("work_item_id") or 0) != int(work_item_id):
            continue
        if str(row.get("status") or "") not in _TERMINAL:
            return row
    return None


def register_handoff(
    *,
    work_item_id: int | None,
    coding_mission_id: str,
    delivery_run_id: int,
    status: str = "running",
) -> dict[str, Any]:
    mid = (coding_mission_id or "").strip()
    if not mid:
        raise ValueError("coding_mission_id_required")
    existing = find_open_handoff(work_item_id, mid)
    if existing:
        return {
            "ok": False,
            "error": "duplicate_delivery_run",
            "handoff": existing,
        }
    row = {
        "work_item_id": work_item_id,
        "coding_mission_id": mid,
        "delivery_run_id": int(delivery_run_id),
        "status": status,
    }
    rows = _load()
    rows.append(row)
    _save(rows)
    return {"ok": True, "handoff": row}


def mark_handoff_status(delivery_run_id: int, status: str) -> None:
    rows = _load()
    for row in rows:
        if int(row.get("delivery_run_id") or 0) == int(delivery_run_id):
            row["status"] = status
    _save(rows)

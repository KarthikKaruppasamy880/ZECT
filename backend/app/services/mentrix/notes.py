"""Local Mentrix Companion notes/records (runtime data, not secrets)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NOTES_DIR = Path(__file__).resolve().parents[3] / "data" / "mentrix_notes"


def _ensure_dir() -> Path:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return NOTES_DIR


def list_notes(limit: int = 50) -> list[dict[str, Any]]:
    root = _ensure_dir()
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return items


def add_note(text: str, tags: list[str] | None = None) -> dict[str, Any]:
    root = _ensure_dir()
    note = {
        "id": str(uuid.uuid4()),
        "text": (text or "").strip()[:4000],
        "tags": tags or ["mentrix"],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    (root / f"{note['id']}.json").write_text(json.dumps(note, indent=2), encoding="utf-8")
    return note

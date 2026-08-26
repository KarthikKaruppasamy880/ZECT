"""Persisted GenerationJob progress for Present Studio (in-memory; multi-worker safe enough for dev)."""

from __future__ import annotations

import threading
import time
from typing import Any

_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}

STAGES = (
    "QUEUED",
    "UNDERSTANDING",
    "STORY_PLANNING",
    "LAYOUT_PLANNING",
    "CONTENT_GENERATION",
    "VISUAL_COMPOSITION",
    "QUALITY_CHECK",
    "REPAIRING",
    "FINAL_QUALITY_CHECK",
    "COMPLETE",
    "NEEDS_REVIEW",
    "FAILED",
)


def create_job(*, job_id: str, requested_slide_count: int, user_id: str = "anon") -> dict[str, Any]:
    row = {
        "generation_job_id": job_id,
        "requested_slide_count": int(requested_slide_count),
        "user_id": str(user_id),
        "stage": "QUEUED",
        "progress_label": "Queued",
        "started_at": time.time(),
        "updated_at": time.time(),
        "events": [{"stage": "QUEUED", "ts": time.time()}],
        "cancelled": False,
    }
    with _LOCK:
        _JOBS[job_id] = row
    return dict(row)


def set_stage(job_id: str, stage: str, *, label: str = "", detail: str = "") -> None:
    with _LOCK:
        row = _JOBS.get(job_id)
        if not row:
            return
        row["stage"] = stage
        row["progress_label"] = label or stage.replace("_", " ").title()
        row["updated_at"] = time.time()
        if detail:
            row["detail"] = detail[:400]
        row.setdefault("events", []).append({"stage": stage, "label": row["progress_label"], "ts": time.time()})
        _JOBS[job_id] = row


def complete_job(job_id: str, *, outcome: str, path: str = "", quality: dict[str, Any] | None = None) -> None:
    stage = "COMPLETE" if outcome == "COMPLETE" else "NEEDS_REVIEW" if outcome == "NEEDS_REVIEW" else "FAILED"
    with _LOCK:
        row = _JOBS.get(job_id)
        if not row:
            return
        row["stage"] = stage
        row["outcome"] = outcome
        row["path"] = path
        row["quality"] = quality or {}
        row["updated_at"] = time.time()
        row.setdefault("events", []).append({"stage": stage, "ts": time.time()})
        _JOBS[job_id] = row


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _JOBS.get(job_id)
        return dict(row) if row else None


__all__ = ["STAGES", "complete_job", "create_job", "get_job", "set_stage"]

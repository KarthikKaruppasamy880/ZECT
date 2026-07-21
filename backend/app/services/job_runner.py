"""Lightweight in-process job runner for Lattice ingest / Mentrix background work."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None


_JOBS: dict[str, Job] = {}
_LOCK = threading.Lock()


def submit(kind: str, fn: Callable[[], dict[str, Any]]) -> Job:
    job = Job(id=str(uuid.uuid4()), kind=kind)

    def _run() -> None:
        with _LOCK:
            job.status = "running"
        try:
            result = fn()
            with _LOCK:
                job.result = result or {}
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:  # noqa: BLE001 — surface to job status
            with _LOCK:
                job.error = str(exc)
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc).isoformat()

    with _LOCK:
        _JOBS[job.id] = job
    threading.Thread(target=_run, daemon=True).start()
    return job


def get_job(job_id: str) -> Job | None:
    with _LOCK:
        return _JOBS.get(job_id)

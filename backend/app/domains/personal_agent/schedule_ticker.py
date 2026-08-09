"""In-process schedule due ticker — real set-and-forget for Mentrix schedules."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

_log = logging.getLogger("zect.schedule_ticker")
_stop = threading.Event()
_thread: threading.Thread | None = None


def schedule_tick_seconds() -> float:
    raw = (os.getenv("ZECT_SCHEDULE_TICK_SECONDS") or "60").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 60.0


def _tick_once() -> int:
    from app.infrastructure.database import SessionLocal
    from app.domains.personal_agent.schedule_executor import run_due_schedules

    db = SessionLocal()
    try:
        runs = run_due_schedules(db)
        return len(runs or [])
    except Exception:  # noqa: BLE001
        _log.exception("schedule tick failed")
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return 0
    finally:
        db.close()


def _loop() -> None:
    while not _stop.wait(timeout=schedule_tick_seconds() or 60.0):
        if schedule_tick_seconds() <= 0:
            continue
        n = _tick_once()
        if n:
            _log.info("schedule tick ran %s due job(s)", n)


def start_schedule_ticker() -> None:
    """Start background due-runner (no-op if tick seconds is 0 or already started)."""
    global _thread
    if schedule_tick_seconds() <= 0:
        _log.info("schedule ticker disabled (ZECT_SCHEDULE_TICK_SECONDS=0)")
        return
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="zect-schedule-ticker", daemon=True)
    _thread.start()
    _log.info("schedule ticker started (every %ss)", schedule_tick_seconds())


def stop_schedule_ticker() -> None:
    _stop.set()


def compute_next_cron_run(cron_expression: str, *, from_dt: Any = None) -> Any:
    """Return next UTC datetime for a 5-field cron expression, or None."""
    if not (cron_expression or "").strip():
        return None
    try:
        from croniter import croniter
        from datetime import datetime, timezone

        base = from_dt or datetime.now(timezone.utc)
        if getattr(base, "tzinfo", None) is None:
            base = base.replace(tzinfo=timezone.utc)
        itr = croniter(cron_expression.strip(), base)
        nxt = itr.get_next(datetime)
        if getattr(nxt, "tzinfo", None) is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        return nxt
    except Exception:  # noqa: BLE001
        return None

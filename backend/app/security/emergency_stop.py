"""Global emergency-stop control (Phase 5 Stage D).

Reuses Setting row + Mentrix cancel + App Runner stop — no new engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import MentrixRun, Setting

EMERGENCY_STOP_KEY = "emergency_stop"


def ensure_emergency_stop_setting(db: Session) -> Setting:
    row = db.query(Setting).filter(Setting.key == EMERGENCY_STOP_KEY).first()
    if row:
        return row
    row = Setting(
        key=EMERGENCY_STOP_KEY,
        value="false",
        setting_type="toggle",
        label="Global Emergency Stop",
        description="When enabled, blocks new Mentrix runs, App Runner execute/start, and GitHub auto-review webhooks; cancels in-flight Mentrix runs.",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def is_emergency_stop_active(db: Session) -> bool:
    row = ensure_emergency_stop_setting(db)
    return str(row.value or "").strip().lower() in ("true", "1", "on", "yes")


def require_not_emergency_stopped(db: Session) -> None:
    if is_emergency_stop_active(db):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Global emergency stop is active — new runs and host commands are blocked",
        )


def set_emergency_stop(db: Session, active: bool) -> Setting:
    row = ensure_emergency_stop_setting(db)
    row.value = "true" if active else "false"
    db.commit()
    db.refresh(row)
    return row


def cancel_open_mentrix_runs(db: Session) -> int:
    rows = (
        db.query(MentrixRun)
        .filter(MentrixRun.status.in_(("running", "pending", "awaiting_approval", "needs_human")))
        .all()
    )
    n = 0
    now = datetime.now(timezone.utc)
    for run in rows:
        run.status = "cancelled"
        run.current_agent = "emergency_stop"
        run.next_step = "Cancelled by global emergency stop"
        # best-effort timestamp fields if present
        if hasattr(run, "updated_at"):
            try:
                run.updated_at = now
            except Exception:
                pass
        n += 1
    if n:
        db.commit()
    return n


def stop_all_app_runner_processes() -> int:
    try:
        from app.domains.workspace import app_runner

        return int(app_runner.stop_all_processes())
    except Exception:
        return 0


def engage_emergency_stop(db: Session) -> dict[str, Any]:
    set_emergency_stop(db, True)
    cancelled = cancel_open_mentrix_runs(db)
    stopped = stop_all_app_runner_processes()
    return {
        "active": True,
        "mentrix_runs_cancelled": cancelled,
        "app_runner_stopped": stopped,
    }


def clear_emergency_stop(db: Session) -> dict[str, Any]:
    set_emergency_stop(db, False)
    return {"active": False}

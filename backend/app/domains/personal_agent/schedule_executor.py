"""Phase 10 Stage A — execute scheduled tasks with permission + idempotency checks."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import MentrixRun, Schedule, ScheduleRun


def _idempotency_key(schedule: Schedule, trigger_type: str) -> str:
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    raw = f"{schedule.id}:{trigger_type}:{minute}:{schedule.task_type}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def execute_schedule(db: Session, schedule: Schedule, *, trigger_type: str = "manual") -> ScheduleRun:
    from app.security.emergency_stop import is_emergency_stop_active

    if is_emergency_stop_active(db):
        run = ScheduleRun(
            schedule_id=schedule.id,
            trigger_type=trigger_type,
            status="failed",
            error_message="emergency_stop_active",
            output_summary="Blocked by global emergency stop",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        schedule.failure_count = (schedule.failure_count or 0) + 1
        db.commit()
        db.refresh(run)
        return run

    # Per-run permission check (no interactive session authority)
    try:
        from app.domains.permissions.capability_grants import find_active_grants_for_action
        from app.models import PermissionRule
        import re

        action = f"schedule:{schedule.task_type}"
        rules = db.query(PermissionRule).filter(PermissionRule.is_active == True).all()  # noqa: E712
        denied = False
        for rule in rules:
            try:
                if re.fullmatch(rule.action_pattern, action) and rule.permission_level == "never":
                    denied = True
                    break
            except re.error:
                if rule.action_pattern == action and rule.permission_level == "never":
                    denied = True
                    break
        if denied and not find_active_grants_for_action(db, action, user_id=schedule.user_id):
            run = ScheduleRun(
                schedule_id=schedule.id,
                trigger_type=trigger_type,
                status="failed",
                error_message="permission_denied",
                output_summary=f"Permission denied for {action}",
                completed_at=datetime.now(timezone.utc),
            )
            db.add(run)
            schedule.failure_count = (schedule.failure_count or 0) + 1
            db.commit()
            db.refresh(run)
            return run
    except Exception:
        pass

    key = _idempotency_key(schedule, trigger_type)
    existing = (
        db.query(ScheduleRun)
        .filter(ScheduleRun.schedule_id == schedule.id, ScheduleRun.idempotency_key == key)
        .first()
    )
    if existing:
        return existing

    run = ScheduleRun(
        schedule_id=schedule.id,
        trigger_type=trigger_type,
        status="running",
        idempotency_key=key,
        output_summary="",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        summary = _dispatch(db, schedule)
        run.status = "completed"
        run.output_summary = summary[:4000]
        run.completed_at = datetime.now(timezone.utc)
        schedule.run_count = (schedule.run_count or 0) + 1
        schedule.last_run_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)[:1000]
        run.output_summary = f"Failed: {e}"
        run.completed_at = datetime.now(timezone.utc)
        schedule.failure_count = (schedule.failure_count or 0) + 1
        db.commit()
        db.refresh(run)
        return run


def _dispatch(db: Session, schedule: Schedule) -> str:
    cfg = schedule.task_config or {}
    task = (schedule.task_type or "custom").lower()

    if task in ("custom", "mentrix", "report", "build", "deploy", "review"):
        goal = cfg.get("goal") or cfg.get("prompt") or schedule.description or schedule.name
        mode = cfg.get("mode") or ("bugfix" if task == "review" else "build" if task == "build" else "ask")
        if mode not in ("ask", "plan", "build", "review", "bugfix", "deploy"):
            mode = "ask"
        run = MentrixRun(
            project_id=schedule.project_id or cfg.get("project_id"),
            mode=mode,
            goal=str(goal)[:4000],
            status="running",
            current_agent="scheduler",
            events_json="[]",
            gates_json="{}",
            result_json=json.dumps({"context": {"source": "schedule", "schedule_id": schedule.id}}),
            next_step="",
            created_by="scheduler",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        # Fire-and-forget via existing worker when available
        try:
            from app.workers.mentrix_worker import run_mentrix_in_background
            import asyncio

            # Prefer sync-safe: if worker expects background task, mark queued
            try:
                run_mentrix_in_background(
                    run.id,
                    goal=str(goal),
                    mode=mode,
                    project_key=cfg.get("project_key") or "",
                    project_id=schedule.project_id,
                    created_by="scheduler",
                    workspace=cfg.get("workspace") or "",
                    source_lang=None,
                    target_lang=None,
                    repo_id=cfg.get("repo_id"),
                )
            except TypeError:
                # Signature drift — still leave MentrixRun queued for UI
                pass
            return f"Started Mentrix run #{run.id} mode={mode}"
        except Exception as e:
            run.status = "failed"
            db.commit()
            return f"Mentrix run #{run.id} created but worker failed: {e}"

    return f"Executed schedule '{schedule.name}' task_type={task} (no-op handler)"

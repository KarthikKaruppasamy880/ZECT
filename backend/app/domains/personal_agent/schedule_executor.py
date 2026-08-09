"""Phase 10 Stage A — execute scheduled tasks with permission + idempotency checks."""

from __future__ import annotations

import hashlib
import json
import os
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

    # PA-9: schedule-scoped limited grants (task_config.grants)
    try:
        from app.services.mentrix.skill_governance import (
            schedule_grants_from_config,
            schedule_tool_permitted,
        )

        grants = schedule_grants_from_config(schedule.task_config if isinstance(schedule.task_config, dict) else {})
        tool_hint = str((schedule.task_config or {}).get("tool") or schedule.task_type or "")
        ok_grant, grant_reason = schedule_tool_permitted(grants, tool_hint)
        if not ok_grant:
            run = ScheduleRun(
                schedule_id=schedule.id,
                trigger_type=trigger_type,
                status="failed",
                error_message=grant_reason,
                output_summary=f"Schedule grant denied: {grant_reason}",
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
        schedule.retry_count = (getattr(schedule, "retry_count", 0) or 0) + 1
        max_attempts = int(getattr(schedule, "max_attempts", 3) or 0)
        if max_attempts > 0 and schedule.retry_count >= max_attempts:
            schedule.is_active = False
            run.output_summary = (run.output_summary or "") + " (paused: max_attempts reached)"
        db.commit()
        db.refresh(run)
        return run


def list_due_schedules(db: Session) -> list[Schedule]:
    """Active schedules whose next_run_at is due (or once/interval heuristic)."""
    now = datetime.now(timezone.utc)

    def _aware(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    due: list[Schedule] = []
    for s in db.query(Schedule).filter(Schedule.is_active == True).all():  # noqa: E712
        max_attempts = int(getattr(s, "max_attempts", 3) or 0)
        retry_count = int(getattr(s, "retry_count", 0) or 0)
        if max_attempts > 0 and retry_count >= max_attempts:
            continue
        next_run = _aware(s.next_run_at)
        if next_run and next_run <= now:
            due.append(s)
            continue
        scheduled_time = _aware(s.scheduled_time)
        if s.schedule_type == "once" and scheduled_time and scheduled_time <= now and not s.last_run_at:
            due.append(s)
            continue
        if s.schedule_type == "interval" and s.interval_minutes:
            if not s.last_run_at:
                due.append(s)
            else:
                last = _aware(s.last_run_at)
                elapsed = (now - last).total_seconds() / 60.0  # type: ignore[operator]
                if elapsed >= float(s.interval_minutes):
                    due.append(s)
    return due


def run_due_schedules(db: Session) -> list[ScheduleRun]:
    results = []
    for sched in list_due_schedules(db):
        results.append(execute_schedule(db, sched, trigger_type="scheduled"))
        # Advance next_run_at for interval / cron jobs
        if sched.schedule_type == "interval" and sched.interval_minutes:
            from datetime import timedelta

            sched.next_run_at = datetime.now(timezone.utc) + timedelta(minutes=int(sched.interval_minutes))
            db.commit()
        elif sched.schedule_type == "cron" or (sched.cron_expression or "").strip():
            from app.domains.personal_agent.schedule_ticker import compute_next_cron_run

            nxt = compute_next_cron_run(sched.cron_expression or "")
            if nxt is not None:
                sched.next_run_at = nxt
                db.commit()
        elif sched.schedule_type == "once":
            sched.is_active = False
            db.commit()
    return results


def _dispatch(db: Session, schedule: Schedule) -> str:
    cfg = schedule.task_config or {}
    task = (schedule.task_type or "custom").lower()

    # Prefer playbook pipeline when playbook_id is set
    if schedule.playbook_id:
        from app.domains.personal_agent.playbook_executor import execute_playbook
        from app.models import Playbook

        pb = db.query(Playbook).filter(Playbook.id == schedule.playbook_id).first()
        if not pb:
            raise RuntimeError(f"Playbook #{schedule.playbook_id} not found")
        variables = cfg.get("variables") or cfg.get("variables_used") or {}
        prun = execute_playbook(
            db,
            pb,
            variables_used=variables if isinstance(variables, dict) else {},
            user_id=schedule.user_id,
            project_id=schedule.project_id or pb.project_id,
        )
        return (
            f"Playbook '{pb.name}' run #{prun.id} status={prun.status} "
            f"steps={prun.steps_completed}/{prun.total_steps}"
        )

    if task in ("coding", "coding_agent", "code"):
        from app.adapters.coding_runtime import get_mentrix_native_runtime

        goal = cfg.get("goal") or cfg.get("prompt") or schedule.description or schedule.name
        ws = (cfg.get("workspace") or os.getenv("MENTRIX_WORKSPACE") or "").strip()
        if not ws:
            raise RuntimeError("coding schedule requires task_config.workspace or MENTRIX_WORKSPACE")
        rt = get_mentrix_native_runtime()
        sid = rt.start_run(
            str(goal),
            workspace=ws,
            auto_approve_edits=bool(cfg.get("auto_approve_edits", True)),
            project_id=schedule.project_id or cfg.get("project_id"),
            skill_id=cfg.get("skill_id"),
            project_key=cfg.get("project_key"),
        )
        return f"Started Mentrix Coding Agent session {sid}"

    if task in ("custom", "mentrix", "report", "build", "deploy", "review", "ask", "plan", "bugfix", "upgrade"):
        goal = cfg.get("goal") or cfg.get("prompt") or schedule.description or schedule.name
        mode = cfg.get("mode") or (
            "bugfix"
            if task == "review"
            else "build"
            if task == "build"
            else "ask"
            if task in ("custom", "mentrix", "report", "ask")
            else task
            if task in ("plan", "bugfix", "upgrade", "deploy")
            else "ask"
        )
        if mode not in ("ask", "plan", "build", "review", "bugfix", "deploy", "upgrade"):
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
        try:
            from app.workers.mentrix_worker import run_mentrix_in_background

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
                pass
            return f"Started Mentrix run #{run.id} mode={mode}"
        except Exception as e:
            run.status = "failed"
            db.commit()
            raise RuntimeError(f"Mentrix run #{run.id} created but worker failed: {e}") from e

    raise RuntimeError(f"Unknown schedule task_type={task!r} — set playbook_id or a supported task_type")

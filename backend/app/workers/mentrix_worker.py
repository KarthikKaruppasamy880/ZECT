"""Mentrix background workers — ForgeLoop runs outside the HTTP request cycle."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.infrastructure.database import SessionLocal
from app.models import MentrixRun
from app.services.coding_engine.mentrix_bridge import (
    cleanup_coding_engine_slice,
    prepare_coding_engine_slice,
)
from app.services.forge_loop.orchestrator import run_mentrix


def run_mentrix_in_background(
    run_id: int,
    *,
    goal: str,
    mode: str,
    project_key: str,
    project_id: int | None,
    created_by: str,
    workspace: str,
    source_lang: str,
    target_lang: str,
    repo_id: int | None,
) -> None:
    """Runs the full ForgeLoop pipeline outside the request/response cycle
    (Phase 1 finding: this used to run entirely inside the POST /runs request
    handler, blocking that HTTP connection for however long scout/blueprint/
    plan/build/review took — minutes for a real multi-step build). Opens its
    own DB session rather than reusing the request's, since that one is torn
    down once the response is sent and this can run far longer than that.

    Phase 2 Stage C: when ZECT_CODING_ENGINE=remote, provision an isolated
    worktree and run the coding-engine slice first, then continue ForgeLoop
    against that worktree. Mock provider leaves this path as a no-op.
    """
    db = SessionLocal()
    engine_slice = None
    try:
        run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
        if not run:
            return
        try:
            engine_slice = prepare_coding_engine_slice(
                db,
                run,
                goal=goal,
                workspace=workspace or "",
                mode=mode,
            )
            effective_workspace = (
                engine_slice.engine_workspace_path
                if engine_slice.active and engine_slice.engine_workspace_path
                else workspace
            )
            run_mentrix(
                db,
                goal=goal,
                mode=mode,
                project_key=project_key,
                project_id=project_id,
                created_by=created_by,
                workspace=effective_workspace or "",
                source_lang=source_lang,
                target_lang=target_lang,
                repo_id=repo_id,
                existing_run=run,
            )
        except Exception as exc:  # noqa: BLE001 — must never leave a run stuck "running" forever
            run.status = "failed"
            events = json.loads(run.events_json or "[]")
            events.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "agent": "orchestrator",
                "message": f"Run failed: {exc}",
                "event": "error",
            })
            run.events_json = json.dumps(events)
            db.commit()
    finally:
        if engine_slice is not None:
            cleanup_coding_engine_slice(engine_slice)
        db.close()


def deliver_mission_in_background(run_id: int, mission_id: str) -> None:
    """Ships an already Developer-reviewed coding_engine Mission: git
    commit/push/PR only (lifecycle.approve_git) -- never re-plans, never
    re-builds, never runs ForgeLoop. This is the Mentrix Delivery path for
    a `coding_mission_id`-backed run (see
    app/domains/agent_run/mentrix.py::start_run) -- distinct from the
    goal-string ForgeLoop pipeline above, which remains for non-Mission
    asks. Delivery consuming the SAME Mission rather than independently
    re-planning/re-building is a governance requirement, not a style
    choice: see ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md
    Phase A.
    """
    from app.services.coding_engine.lifecycle import approve_git
    from app.services.coding_engine.ship_handoff import mark_handoff_status

    db = SessionLocal()
    try:
        run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
        if not run:
            return
        try:
            shipped = approve_git(mission_id, commit=True, push=True)
        except (ValueError, KeyError) as exc:
            run.status = "failed"
            run.events_json = json.dumps(
                [
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "agent": "delivery",
                        "message": f"Delivery blocked: {exc}",
                        "event": "error",
                    }
                ]
            )
            db.commit()
            mark_handoff_status(run_id, "failed")
            return

        blocked = shipped.get("phase") == "blocked" or shipped.get("status") == "blocked"
        run.status = "failed" if blocked else "completed"
        run.current_agent = "delivery"
        ctx = json.loads(run.result_json or "{}").get("context", {})
        run.result_json = json.dumps({"mission": shipped, "context": ctx})
        run.events_json = json.dumps(
            [
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "agent": "delivery",
                    "message": (
                        f"Mission {mission_id} {'blocked' if blocked else 'shipped'}: "
                        f"phase={shipped.get('phase')}"
                    ),
                    "event": "delivery_blocked" if blocked else "delivery_complete",
                }
            ]
        )
        db.commit()
        mark_handoff_status(run_id, run.status)
    finally:
        db.close()

"""Mentrix background workers — ForgeLoop runs outside the HTTP request cycle."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.infrastructure.database import SessionLocal
from app.models import MentrixRun
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
    """
    db = SessionLocal()
    try:
        run = db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
        if not run:
            return
        try:
            run_mentrix(
                db,
                goal=goal,
                mode=mode,
                project_key=project_key,
                project_id=project_id,
                created_by=created_by,
                workspace=workspace,
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
        db.close()

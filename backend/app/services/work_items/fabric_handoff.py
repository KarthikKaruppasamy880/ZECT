"""Fabric handoff from approved WorkItem / PLAN.md."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.domains.work_items.status import STATUS_PLAN_APPROVED, STATUS_EXECUTING
from app.services.work_items.artifact_store import ArtifactStore


def fabric_handoff_from_work_item(
    db: Session,
    *,
    work_item_id: int,
    workspace: str = "",
    text: str = "",
    auto_approve_edits: bool = True,
) -> dict[str, Any]:
    """Classify + run Fabric using approved plan context (reuses Fabric domain)."""
    wi = wi_svc.get_work_item(db, work_item_id)
    if wi.status not in (STATUS_PLAN_APPROVED, STATUS_EXECUTING):
        return {"ok": False, "error": "plan_not_approved", "status": wi.status}
    if not wi.approved_plan_hash or wi.approved_plan_hash != wi.plan_hash:
        return {"ok": False, "error": "plan_hash_mismatch", "status": wi.status}

    store = ArtifactStore(wi.id)
    plan = store.read_plan()
    goal = (text or plan or wi.title or "")[:2000]
    if not goal.strip():
        return {"ok": False, "error": "empty_goal"}

    from app.domains.fabric.router import classify_text
    from app.adapters.coding_runtime import get_mentrix_native_runtime
    from urllib.parse import quote
    import os

    classified = classify_text(db, goal, require_active=True)
    if classified.get("refuse"):
        return {"ok": False, "error": "fabric_refuse", **classified}

    ws = (
        (workspace or wi.worktree_path or "").strip()
        or (os.getenv("MENTRIX_WORKSPACE") or "").strip()
        or (os.getenv("ZECT_WORKSPACE_ROOT") or "").strip()
    )
    if not ws:
        return {"ok": False, "error": "workspace_required", **classified}

    rt = get_mentrix_native_runtime()
    sessions = []
    for sid in classified.get("surfaces_required") or ["default"]:
        run_id = rt.start_run(
            f"[WorkItem {wi.id} surface={sid}] {goal}",
            workspace=ws,
            auto_approve_edits=auto_approve_edits,
        )
        sessions.append(
            {
                "surface_id": sid,
                "session_id": run_id,
                "navigate": f"/workspace?session={quote(run_id)}",
            }
        )

    wi.worktree_path = ws
    if wi.status == STATUS_PLAN_APPROVED:
        wi_svc.transition_status(db, wi.id, STATUS_EXECUTING, reason="fabric_handoff", actor="fabric")
    else:
        db.commit()

    return {
        "ok": True,
        "work_item_id": wi.id,
        "sessions": sessions,
        "classified": classified,
        "workspace": ws,
    }

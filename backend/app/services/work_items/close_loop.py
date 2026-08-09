"""Close-loop after EvidenceVerifier READY_TO_SHIP — Jira/Camunda/PR hooks."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.domains.work_items.events import append_event
from app.domains.work_items.status import STATUS_PR_CREATED, STATUS_READY_TO_SHIP


def close_external_loop(
    db: Session,
    *,
    work_item_id: int,
    pr_url: str = "",
    jira_comment: str = "",
    jira_transition_id: str = "",
    camunda_complete: bool = False,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Notify external systems after READY_TO_SHIP. Idempotent-ish via events."""
    wi = wi_svc.get_work_item(db, work_item_id)
    if wi.status != STATUS_READY_TO_SHIP and wi.status != STATUS_PR_CREATED:
        return {"ok": False, "error": "work_item_not_ready_to_ship", "status": wi.status}

    results: dict[str, Any] = {"work_item_id": wi.id, "dry_run": dry_run, "actions": []}

    if pr_url:
        results["actions"].append({"type": "pr_url", "url": pr_url})
        if not dry_run:
            wi = wi_svc.transition_status(
                db,
                wi.id,
                STATUS_PR_CREATED,
                reason=f"pr:{pr_url}",
                allow_gate=True,
                actor="close_loop",
            )

    if wi.source == "jira" and wi.external_id:
        body = jira_comment or f"Mentrix WorkItem #{wi.id} READY_TO_SHIP. PR={pr_url or 'n/a'}"
        action: dict[str, Any] = {"type": "jira_comment", "issue": wi.external_id, "body": body[:500]}
        if dry_run:
            action["status"] = "dry_run"
        else:
            try:
                from app.adapters import jira as jira_adapter

                out = jira_adapter.execute(
                    "add_comment",
                    {"issue_key": wi.external_id, "body": body},
                    config={},
                    enabled=True,
                )
                action["result"] = out
                if jira_transition_id:
                    tr = jira_adapter.execute(
                        "transition_issue",
                        {"issue_key": wi.external_id, "transition_id": jira_transition_id},
                        config={},
                        enabled=True,
                    )
                    action["transition"] = tr
            except Exception as exc:  # noqa: BLE001
                action["error"] = str(exc)[:300]
        results["actions"].append(action)

    if wi.source == "camunda" and wi.external_id and camunda_complete:
        action = {"type": "camunda_complete", "task_id": wi.external_id}
        if dry_run:
            action["status"] = "dry_run"
        else:
            try:
                from app.adapters import camunda_client
                import httpx

                base = camunda_client._base_url()  # noqa: SLF001
                if not base:
                    action["error"] = "camunda_not_configured"
                else:
                    with httpx.Client(timeout=30.0, auth=camunda_client._auth()) as client:  # noqa: SLF001
                        r = client.post(f"{base}/task/{wi.external_id}/complete", json={})
                        action["status_code"] = r.status_code
                        action["ok"] = r.status_code < 400
            except Exception as exc:  # noqa: BLE001
                action["error"] = str(exc)[:300]
        results["actions"].append(action)

    append_event(
        db,
        work_item_id=wi.id,
        event_type="external_close_loop",
        payload=results,
        commit=True,
    )
    results["ok"] = True
    results["work_item"] = wi_svc.serialize_work_item(wi_svc.get_work_item(db, wi.id))
    return results

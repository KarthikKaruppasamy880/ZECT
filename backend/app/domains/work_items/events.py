"""Append-only WorkItemEvent writers — no update/delete."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import WorkItemEvent


class WorkItemEventMutationError(RuntimeError):
    """Raised when callers attempt to mutate or delete events."""


def append_event(
    db: Session,
    *,
    work_item_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
    commit: bool = False,
) -> WorkItemEvent:
    ev = WorkItemEvent(
        work_item_id=work_item_id,
        event_type=event_type,
        payload_json=json.dumps(payload or {}, default=str),
    )
    db.add(ev)
    if commit:
        db.commit()
        db.refresh(ev)
    else:
        db.flush()
    return ev


def forbid_event_update(_event_id: int) -> None:
    raise WorkItemEventMutationError("WorkItemEvent is append-only; updates are forbidden")


def forbid_event_delete(_event_id: int) -> None:
    raise WorkItemEventMutationError("WorkItemEvent is append-only; deletes are forbidden")

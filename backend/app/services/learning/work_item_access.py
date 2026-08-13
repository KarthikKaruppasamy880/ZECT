"""WorkItem ownership checks for Learning handoff (M2)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser
from app.models import WorkItem


def resolve_owned_work_item(
    db: Session,
    work_item_id: int,
    current_user: CurrentUser,
    *,
    leak_safe: bool = True,
) -> WorkItem:
    """Return WorkItem only if the authenticated user may access it.

    Unauthorized IDs → 404 (no title/context leak) when leak_safe=True.
    """
    wi = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not wi:
        raise HTTPException(404, "work_item_not_found")

    identity = (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or ""
    ).strip().lower()
    role = str(getattr(current_user, "role", "") or "").lower()
    created = str(wi.created_by or "").strip().lower()
    is_admin = role in ("admin", "lead", "executive")
    uid = getattr(current_user, "user_id", None)

    allowed = False
    if is_admin:
        allowed = True
    elif created and identity and created == identity:
        allowed = True
    elif created and uid is not None and created == str(uid):
        allowed = True

    if not allowed:
        # Never return title/description for foreign WorkItems
        raise HTTPException(404 if leak_safe else 403, "work_item_not_found")
    return wi

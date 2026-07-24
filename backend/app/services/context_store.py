"""Context Store — shared save/load over ContextStoreEntry.

Extracted out of routers/context_management.py so non-HTTP callers (the HLD
generator, Build's context injection) can read/write the same store in-process
without a round-trip through their own FastAPI app — one persistence path for
both the UI-facing /api/context/* endpoints and internal phase-to-phase reuse.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ContextStoreEntry


def save(db: Session, user_id: int | None, page: str, key: str, value: str) -> None:
    row = (
        db.query(ContextStoreEntry)
        .filter(ContextStoreEntry.user_id == user_id, ContextStoreEntry.page == page, ContextStoreEntry.key == key)
        .first()
    )
    if row:
        row.value = value
    else:
        db.add(ContextStoreEntry(user_id=user_id, page=page, key=key, value=value))
    db.commit()


def load(db: Session, user_id: int | None, page: str, keys: list[str] | None = None) -> dict[str, str]:
    query = db.query(ContextStoreEntry).filter(ContextStoreEntry.user_id == user_id, ContextStoreEntry.page == page)
    if keys:
        query = query.filter(ContextStoreEntry.key.in_(keys))
    return {r.key: r.value for r in query.all()}

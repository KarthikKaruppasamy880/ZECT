"""Companion preferred display name helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import UserPreference


def preferred_name_from_email(email: str) -> str:
    local = (email or "").split("@")[0].strip()
    if not local:
        return ""
    # karthik.karuppasamy → Karthik
    part = local.replace("_", ".").split(".")[0]
    return part[:1].upper() + part[1:] if part else ""


def resolve_preferred_name(
    db: Session | None,
    *,
    user_id: int | None = None,
    email: str = "",
) -> str:
    if db is not None and user_id is not None:
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if pref:
            comm = pref.communication or {}
            if isinstance(comm, dict):
                name = (comm.get("preferred_name") or "").strip()
                if name:
                    return name
    return preferred_name_from_email(email)


def set_preferred_name(db: Session, user_id: int, name: str) -> dict:
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not pref:
        pref = UserPreference(user_id=user_id, communication={"preferred_name": name.strip()})
        db.add(pref)
    else:
        comm = dict(pref.communication or {})
        comm["preferred_name"] = name.strip()
        pref.communication = comm
    db.commit()
    db.refresh(pref)
    return {
        "user_id": user_id,
        "preferred_name": (pref.communication or {}).get("preferred_name") or "",
    }

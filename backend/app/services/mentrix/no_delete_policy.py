"""Central no-delete policy (PA-1 / SAFETY_POLICY).

UI hiding is not enough — every desktop/file delete path must refuse here or in
Electron main. Companion and Electron both call through this module where possible.
"""

from __future__ import annotations

from typing import Any


DELETE_NEVER_ALLOWED = "delete_never_allowed"

_DELETE_INTENTS = frozenset(
    {
        "desktop_delete",
        "delete_file",
        "delete",
        "unlink",
        "rmdir",
        "trash_empty",
        "empty_trash",
    }
)


def is_delete_intent(intent: str | None) -> bool:
    name = (intent or "").strip().lower()
    if name in _DELETE_INTENTS:
        return True
    if "delete" in name and "undelete" not in name:
        return True
    return False


def refuse_delete(*, intent: str = "", detail: str = "") -> dict[str, Any]:
    """Hard refuse payload — never ok=True."""
    return {
        "ok": False,
        "error": DELETE_NEVER_ALLOWED,
        "intent": intent or "delete",
        "detail": (detail or "")[:500],
        "note": "Mentrix never deletes files, empties Trash, or unlinks paths.",
    }

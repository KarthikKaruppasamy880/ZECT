"""Optional Mentrix IMAP inbox digest (read-only). SMTP alone cannot read mail."""

from __future__ import annotations

import email
import imaplib
import os
from email.header import decode_header
from typing import Any


def _decode_subj(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return str(raw)
    parts = decode_header(raw)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(str(text))
    return "".join(out)


def imap_configured() -> bool:
    return bool(
        os.getenv("MENTRIX_IMAP_HOST", "").strip()
        and os.getenv("MENTRIX_IMAP_USER", "").strip()
        and os.getenv("MENTRIX_IMAP_PASSWORD", "").strip()
    )


def fetch_inbox_digest(limit: int = 8) -> dict[str, Any]:
    """Fetch recent message subjects via IMAP when MENTRIX_IMAP_* is set."""
    host = os.getenv("MENTRIX_IMAP_HOST", "").strip()
    user = os.getenv("MENTRIX_IMAP_USER", "").strip()
    password = os.getenv("MENTRIX_IMAP_PASSWORD", "").strip()
    port = int(os.getenv("MENTRIX_IMAP_PORT", "993") or "993")
    folder = os.getenv("MENTRIX_IMAP_FOLDER", "INBOX").strip() or "INBOX"

    if not host or not user or not password:
        return {
            "ok": True,
            "configured": False,
            "items": [],
            "spoken_summary": (
                "Email inbox is not configured. Set MENTRIX_IMAP_HOST, MENTRIX_IMAP_USER, "
                "and MENTRIX_IMAP_PASSWORD in backend/.env for Mentrix digests. SMTP alone can only send."
            ),
            "note": "Set MENTRIX_IMAP_* in backend/.env for inbox digests",
        }

    items: list[dict[str, str]] = []
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        mail.select(folder, readonly=True)
        _status, data = mail.search(None, "ALL")
        ids = (data[0] or b"").split()
        for mid in reversed(ids[-limit:]):
            _s, msg_data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
            msg = email.message_from_bytes(raw if isinstance(raw, bytes) else bytes(raw))
            items.append(
                {
                    "subject": _decode_subj(msg.get("Subject")),
                    "from": _decode_subj(msg.get("From")),
                    "date": _decode_subj(msg.get("Date")),
                }
            )
        mail.logout()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "configured": True,
            "items": [],
            "error": type(exc).__name__,
            "spoken_summary": f"Could not read email inbox: {type(exc).__name__}.",
            "note": str(exc)[:200],
        }

    if not items:
        spoken = "Your Mentrix email inbox has no recent messages."
    else:
        bits = [f"{it.get('subject') or 'no subject'} from {it.get('from') or 'unknown'}" for it in items[:5]]
        spoken = "Recent email: " + "; ".join(bits) + "."

    return {
        "ok": True,
        "configured": True,
        "items": items,
        "spoken_summary": spoken,
        "note": f"{len(items)} recent message(s)",
        "board": {
            "type": "table",
            "title": "Email digest",
            "data": {
                "columns": ["subject", "from", "date"],
                "rows": [[it.get("subject"), it.get("from"), it.get("date")] for it in items],
            },
        },
    }

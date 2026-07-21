"""MCP email adapter — SMTP outbound (Wave 1)."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any


def list_tools() -> list[dict[str, str]]:
    return [
        {"name": "send_email", "description": "Send email via SMTP"},
        {"name": "status", "description": "Email / SMTP configuration status"},
    ]


def execute(tool_name: str, arguments: dict, config: dict | None = None, enabled: bool = True) -> dict[str, Any]:
    config = config or {}
    if not enabled:
        return {"error": "email adapter disabled", "dry_run": True}

    if tool_name == "status":
        host = config.get("smtp_host") or os.getenv("SMTP_HOST", "")
        return {
            "configured": bool(host),
            "smtp_host": host or None,
            "from": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or None,
        }

    if tool_name != "send_email":
        raise ValueError(f"Unknown email tool: {tool_name}")

    host = config.get("smtp_host") or os.getenv("SMTP_HOST", "")
    if not host:
        return {"sent": False, "message": "SMTP_HOST not set — email not sent", "dry_run": True}

    to = arguments.get("to") or arguments.get("recipient") or ""
    subject = arguments.get("subject") or "Mentrix notification"
    body = arguments.get("body") or arguments.get("text") or ""
    if not to:
        return {"sent": False, "error": "to/recipient required"}

    port = int(config.get("smtp_port") or os.getenv("SMTP_PORT", "587"))
    user = config.get("smtp_user") or os.getenv("SMTP_USER", "")
    password = config.get("smtp_password") or os.getenv("SMTP_PASSWORD", "")
    from_addr = config.get("smtp_from") or os.getenv("SMTP_FROM", user or "noreply@zect.local")

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)
    return {"sent": True, "to": to, "subject": subject}

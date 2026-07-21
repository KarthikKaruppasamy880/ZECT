"""Email integration (SMTP / Graph-ready) for Mentrix Integrator."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/api/email", tags=["email"])


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str


@router.get("/status")
def status(_user: CurrentUser = Depends(get_current_user)):
    provider = os.getenv("EMAIL_PROVIDER", "smtp")
    configured = bool(os.getenv("SMTP_HOST") or os.getenv("AZURE_TENANT_ID"))
    return {"provider": provider, "configured": configured}


@router.post("/send")
def send_email(req: SendEmailRequest, _user: CurrentUser = Depends(get_current_user)):
    host = os.getenv("SMTP_HOST", "")
    if not host:
        return {
            "status": "dry_run",
            "message": "SMTP_HOST not set — email not sent",
            "preview": req.model_dump(),
        }
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", user or "noreply@zect.local")
    msg = EmailMessage()
    msg["Subject"] = req.subject
    msg["From"] = from_addr
    msg["To"] = req.to
    msg.set_content(req.body)
    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"SMTP send failed: {exc}") from exc
    return {"status": "sent", "to": req.to}

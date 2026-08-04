"""Slack Integration — Configure Slack notifications and bot commands."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import SlackConfig
from app.security.vault import vault

router = APIRouter(prefix="/api/slack", tags=["slack"])

# bot_token_encrypted was previously assigned the raw plaintext token despite
# its name — nothing in the codebase currently reads it back (real Slack
# calls go through app.services.mcp.hub's SLACK_BOT_TOKEN/MCPServerConfig-
# backed path), so encrypting here is a pure hardening change.
_cipher = Fernet(vault.get_key())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SlackConfigCreate(BaseModel):
    bot_token: str
    workspace_name: str = ""
    default_channel: str = "#zect-notifications"
    notify_on_review: bool = True
    notify_on_deploy: bool = True
    notify_on_budget_alert: bool = True


class SlackConfigOut(BaseModel):
    id: int
    workspace_name: str
    default_channel: str
    notify_on_review: bool
    notify_on_deploy: bool
    notify_on_budget_alert: bool
    is_active: bool
    created_at: str


class SlackStatus(BaseModel):
    configured: bool
    workspace_name: str
    default_channel: str
    is_active: bool
    notify_on_review: bool
    notify_on_deploy: bool
    notify_on_budget_alert: bool


class SlackNotification(BaseModel):
    channel: str = ""
    message: str
    notification_type: str = "info"  # info, warning, error, success


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=SlackStatus)
def get_slack_status(db: Session = Depends(get_db)):
    """Check Slack integration status."""
    config = db.query(SlackConfig).filter(SlackConfig.is_active == True).first()
    if not config:
        return SlackStatus(
            configured=False, workspace_name="", default_channel="",
            is_active=False, notify_on_review=False, notify_on_deploy=False,
            notify_on_budget_alert=False,
        )
    return SlackStatus(
        configured=True,
        workspace_name=config.workspace_name or "",
        default_channel=config.default_channel or "",
        is_active=config.is_active,
        notify_on_review=config.notify_on_review,
        notify_on_deploy=config.notify_on_deploy,
        notify_on_budget_alert=config.notify_on_budget_alert,
    )


@router.post("/config", response_model=SlackConfigOut)
def configure_slack(req: SlackConfigCreate, db: Session = Depends(get_db)):
    """Configure Slack integration."""
    existing = db.query(SlackConfig).first()
    if existing:
        existing.bot_token_encrypted = _cipher.encrypt(req.bot_token.encode()).decode()
        existing.workspace_name = req.workspace_name
        existing.default_channel = req.default_channel
        existing.notify_on_review = req.notify_on_review
        existing.notify_on_deploy = req.notify_on_deploy
        existing.notify_on_budget_alert = req.notify_on_budget_alert
        existing.is_active = True
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        config = existing
    else:
        config = SlackConfig(
            bot_token_encrypted=_cipher.encrypt(req.bot_token.encode()).decode(),
            workspace_name=req.workspace_name,
            default_channel=req.default_channel,
            notify_on_review=req.notify_on_review,
            notify_on_deploy=req.notify_on_deploy,
            notify_on_budget_alert=req.notify_on_budget_alert,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return SlackConfigOut(
        id=config.id,
        workspace_name=config.workspace_name or "",
        default_channel=config.default_channel or "",
        notify_on_review=config.notify_on_review,
        notify_on_deploy=config.notify_on_deploy,
        notify_on_budget_alert=config.notify_on_budget_alert,
        is_active=config.is_active,
        created_at=config.created_at.isoformat() if config.created_at else "",
    )


@router.post("/notify")
def send_notification(req: SlackNotification, db: Session = Depends(get_db)):
    """Send a real Slack notification via the MCP slack adapter (SLACK_BOT_TOKEN
    or the slack server's config.token) — no longer a simulated always-success stub."""
    from app.services.mcp.hub import execute_tool

    config = db.query(SlackConfig).filter(SlackConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=400, detail="Slack not configured.")
    channel = req.channel or config.default_channel

    outcome = execute_tool(
        db,
        server_id="slack",
        tool_name="send_message",
        arguments={"channel": channel, "text": req.message},
    )
    result = outcome.get("result") or {}
    if outcome.get("status") != "success" or result.get("status") in ("disabled", "not_configured"):
        raise HTTPException(
            status_code=502,
            detail=result.get("message") or result.get("error") or "Slack send failed — check SLACK_BOT_TOKEN / MCP slack server config",
        )

    return {
        "sent": True,
        "channel": channel,
        "message": req.message,
        "notification_type": req.notification_type,
    }


@router.delete("/config")
def disconnect_slack(db: Session = Depends(get_db)):
    """Disconnect Slack integration."""
    config = db.query(SlackConfig).first()
    if config:
        config.is_active = False
        db.commit()
    return {"disconnected": True}

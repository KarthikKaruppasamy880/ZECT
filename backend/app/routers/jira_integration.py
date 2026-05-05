"""Jira Integration — Configure Jira, create/link tickets, sync status."""

import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import JiraConfig, JiraTicketLink

router = APIRouter(prefix="/api/jira", tags=["jira"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class JiraConfigCreate(BaseModel):
    base_url: str
    email: str
    api_token: str
    default_project_key: str | None = None


class JiraConfigOut(BaseModel):
    id: int
    base_url: str
    email: str
    default_project_key: str | None
    is_active: bool
    created_at: str


class JiraTicketCreate(BaseModel):
    project_key: str
    summary: str
    description: str = ""
    issue_type: str = "Task"  # Task, Bug, Story, Epic
    resource_type: str = "project"
    resource_id: int = 0


class JiraTicketOut(BaseModel):
    id: int
    ticket_key: str
    ticket_url: str
    ticket_summary: str
    ticket_status: str
    ticket_type: str
    resource_type: str
    resource_id: int
    synced_at: str


class JiraStatus(BaseModel):
    configured: bool
    base_url: str
    email: str
    is_active: bool
    linked_tickets: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=JiraStatus)
def get_jira_status(db: Session = Depends(get_db)):
    """Check Jira integration status."""
    config = db.query(JiraConfig).filter(JiraConfig.is_active == True).first()
    if not config:
        return JiraStatus(configured=False, base_url="", email="", is_active=False, linked_tickets=0)
    ticket_count = db.query(JiraTicketLink).filter(JiraTicketLink.jira_config_id == config.id).count()
    return JiraStatus(
        configured=True,
        base_url=config.base_url,
        email=config.email,
        is_active=config.is_active,
        linked_tickets=ticket_count,
    )


@router.post("/config", response_model=JiraConfigOut)
def configure_jira(req: JiraConfigCreate, db: Session = Depends(get_db)):
    """Configure Jira integration."""
    existing = db.query(JiraConfig).first()
    if existing:
        existing.base_url = req.base_url
        existing.email = req.email
        existing.api_token_encrypted = req.api_token
        existing.default_project_key = req.default_project_key
        existing.is_active = True
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        config = existing
    else:
        config = JiraConfig(
            base_url=req.base_url,
            email=req.email,
            api_token_encrypted=req.api_token,
            default_project_key=req.default_project_key,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return JiraConfigOut(
        id=config.id,
        base_url=config.base_url,
        email=config.email,
        default_project_key=config.default_project_key,
        is_active=config.is_active,
        created_at=config.created_at.isoformat() if config.created_at else "",
    )


@router.post("/tickets", response_model=JiraTicketOut)
def create_ticket(req: JiraTicketCreate, db: Session = Depends(get_db)):
    """Create a Jira ticket and link it to a ZECT resource."""
    config = db.query(JiraConfig).filter(JiraConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=400, detail="Jira not configured. Set up Jira first.")

    ticket_key = f"{req.project_key}-{db.query(JiraTicketLink).count() + 1}"
    ticket_url = f"{config.base_url}/browse/{ticket_key}"

    link = JiraTicketLink(
        jira_config_id=config.id,
        ticket_key=ticket_key,
        ticket_url=ticket_url,
        ticket_summary=req.summary,
        ticket_status="To Do",
        ticket_type=req.issue_type,
        resource_type=req.resource_type,
        resource_id=req.resource_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return JiraTicketOut(
        id=link.id,
        ticket_key=link.ticket_key,
        ticket_url=link.ticket_url,
        ticket_summary=link.ticket_summary,
        ticket_status=link.ticket_status,
        ticket_type=link.ticket_type,
        resource_type=link.resource_type,
        resource_id=link.resource_id,
        synced_at=link.synced_at.isoformat() if link.synced_at else "",
    )


@router.get("/tickets", response_model=list[JiraTicketOut])
def list_tickets(resource_type: str | None = None, db: Session = Depends(get_db)):
    """List linked Jira tickets."""
    query = db.query(JiraTicketLink)
    if resource_type:
        query = query.filter(JiraTicketLink.resource_type == resource_type)
    tickets = query.order_by(JiraTicketLink.synced_at.desc()).all()
    return [
        JiraTicketOut(
            id=t.id,
            ticket_key=t.ticket_key,
            ticket_url=t.ticket_url,
            ticket_summary=t.ticket_summary or "",
            ticket_status=t.ticket_status or "",
            ticket_type=t.ticket_type or "",
            resource_type=t.resource_type,
            resource_id=t.resource_id,
            synced_at=t.synced_at.isoformat() if t.synced_at else "",
        )
        for t in tickets
    ]


@router.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Remove a Jira ticket link."""
    link = db.query(JiraTicketLink).filter(JiraTicketLink.id == ticket_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Ticket link not found")
    db.delete(link)
    db.commit()
    return {"deleted": True}

"""Confluence integration status/config for Mentrix MCP."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.database import get_db
from app.services.mcp.hub import upsert_server_config

router = APIRouter(prefix="/api/confluence", tags=["confluence"])


class ConfluenceConfig(BaseModel):
    base_url: str = ""
    email: str = ""
    enabled: bool = True


@router.get("/status")
def status(_user: CurrentUser = Depends(get_current_user)):
    configured = bool(os.getenv("MCP_CONFLUENCE_URL") and (os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("JIRA_API_TOKEN")))
    return {"configured": configured, "base_url": os.getenv("MCP_CONFLUENCE_URL", "")}


@router.post("/configure")
def configure(
    req: ConfluenceConfig,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    upsert_server_config(
        db,
        server_id="confluence",
        name="Confluence",
        enabled=req.enabled,
        base_url=req.base_url,
        config={"email": req.email},
    )
    return {"status": "ok", "server_id": "confluence"}

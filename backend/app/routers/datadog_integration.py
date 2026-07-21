"""Datadog integration for Mentrix Ops."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import CurrentUser, get_current_user
from app.database import get_db
from app.services.mcp.hub import upsert_server_config

router = APIRouter(prefix="/api/datadog", tags=["datadog"])


class DatadogConfig(BaseModel):
    site: str = "datadoghq.com"
    enabled: bool = True


@router.get("/status")
def status(_user: CurrentUser = Depends(get_current_user)):
    return {
        "configured": bool(os.getenv("DATADOG_API_KEY") and os.getenv("DATADOG_APP_KEY")),
        "site": os.getenv("DATADOG_SITE", "datadoghq.com"),
    }


@router.post("/configure")
def configure(
    req: DatadogConfig,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    upsert_server_config(
        db,
        server_id="datadog",
        name="Datadog",
        enabled=req.enabled,
        config={"site": req.site},
    )
    return {"status": "ok", "server_id": "datadog"}

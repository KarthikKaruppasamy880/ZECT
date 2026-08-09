"""Mentrix Process API — Camunda REST behind ZECT branding."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.adapters import camunda_client as camunda
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.allowed_paths import path_under_allowed_roots

router = APIRouter(prefix="/api/process", tags=["mentrix-process"])


class DeployIn(BaseModel):
    path: Optional[str] = None
    content_b64: Optional[str] = None
    name: str = "process.bpmn"


class StartIn(BaseModel):
    process_key: str = Field(..., min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
def process_status(_user: CurrentUser = Depends(get_current_user)):
    return camunda.process_engine_status()


@router.post("/deploy")
def process_deploy(req: DeployIn, _user: CurrentUser = Depends(get_current_user)):
    import base64

    content = None
    path = None
    if req.path:
        try:
            path = str(path_under_allowed_roots(req.path))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"path_not_allowlisted:{exc}") from exc
    elif req.content_b64:
        content = base64.b64decode(req.content_b64)
    else:
        raise HTTPException(400, "path_or_content_required")
    result = camunda.deploy_bpmn(file_path=path, content=content, name=req.name)
    if not result.get("ok"):
        raise HTTPException(502 if result.get("error") != "camunda_not_configured" else 503, result)
    return result


@router.post("/start")
def process_start(req: StartIn, _user: CurrentUser = Depends(get_current_user)):
    result = camunda.start_process(req.process_key, req.variables or None)
    if not result.get("ok"):
        raise HTTPException(502 if result.get("error") != "camunda_not_configured" else 503, result)
    return result


@router.get("/incidents")
def process_incidents(max_results: int = 50, _user: CurrentUser = Depends(get_current_user)):
    result = camunda.list_incidents(max_results=max_results)
    if not result.get("ok"):
        raise HTTPException(502 if result.get("error") != "camunda_not_configured" else 503, result)
    return result


@router.get("/cockpit-url")
def cockpit_url(_user: CurrentUser = Depends(get_current_user)):
    st = camunda.process_engine_status()
    url = (st.get("cockpit_url") or "").strip()
    if not url:
        raise HTTPException(404, "ZECT_CAMUNDA_COCKPIT_URL unset")
    return {"ok": True, "url": url, "provider": "mentrix_process"}

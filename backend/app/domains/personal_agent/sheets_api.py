"""Mentrix Sheets HTTP — generate / import / export / save workbook JSON."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication
from app.services.mentrix import sheets as svc

router = APIRouter(prefix="/api/mentrix/sheets", tags=["mentrix-sheets"])


class GenerateIn(BaseModel):
    prompt: str = Field(..., min_length=1)
    project_id: int | None = None


class SaveIn(BaseModel):
    path: str
    workbook: dict[str, Any]


@router.post("/generate")
@require_authentication
def sheets_generate(body: GenerateIn, current_user: CurrentUser = Depends(get_current_user)):
    try:
        wb = svc.generate_workbook(body.prompt, project_id=body.project_id)
    except ValueError as exc:
        code = str(exc)
        status = 409 if code == "llm_offline" else 400
        raise HTTPException(status_code=status, detail=code) from exc
    return {"ok": True, "workbook": wb}


@router.post("/import")
@require_authentication
async def sheets_import(file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)):
    data = await file.read()
    try:
        wb = svc.workbook_from_xlsx(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "workbook": wb}


@router.post("/export")
@require_authentication
def sheets_export(body: dict[str, Any], current_user: CurrentUser = Depends(get_current_user)):
    raw = svc.workbook_to_xlsx(body.get("workbook") or body)
    return Response(
        content=raw,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="mentrix-sheet.xlsx"'},
    )


@router.post("/save")
@require_authentication
def sheets_save(body: SaveIn, current_user: CurrentUser = Depends(get_current_user)):
    try:
        path = svc.resolve_workbook_path(body.path)
        svc.save_workbook(path, body.workbook)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "path": str(path)}

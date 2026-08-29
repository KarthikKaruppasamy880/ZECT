"""Mentrix Multi-Surface Fabric — classify / refuse / Coding Agent handoff."""

from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import get_db
from app.models import FabricSurface

router = APIRouter(prefix="/api/fabric", tags=["fabric"])

_SEED = [
    {
        "surface_id": "ngc",
        "label": "NGC rules/config",
        "keywords": ["ngc", "authorized signatory", "rules", "config"],
        "active": True,
    },
    {
        "surface_id": "bpm_pi",
        "label": "BPM PI / Camunda",
        "keywords": ["bpm", "bpmn", "camunda", "process", "workflow"],
        "active": True,
    },
    {
        "surface_id": "cds",
        "label": "CDS contracts",
        "keywords": ["cds", "contract", "cross-system data"],
        "active": False,
    },
    {
        "surface_id": "tango",
        "label": "Tango platform",
        "keywords": ["tango", "platform service"],
        "active": False,
    },
]


class SurfaceIn(BaseModel):
    surface_id: str = Field(..., min_length=1)
    label: str = ""
    project_key: str = ""
    workspace: str = ""
    repo_hints: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    active: bool = False
    config_json: dict = Field(default_factory=dict)


class SurfaceUpdate(BaseModel):
    label: Optional[str] = None
    project_key: Optional[str] = None
    workspace: Optional[str] = None
    repo_hints: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    active: Optional[bool] = None
    config_json: Optional[dict] = None


class ClassifyIn(BaseModel):
    text: str = Field(..., min_length=1)
    require_active: bool = True


class RunIn(BaseModel):
    text: str = Field(..., min_length=1)
    workspace: str = ""
    auto_approve_edits: bool = True
    require_active: bool = True


def _to_dict(s: FabricSurface) -> dict[str, Any]:
    return {
        "id": s.id,
        "surface_id": s.surface_id,
        "label": s.label or "",
        "project_key": s.project_key or "",
        "workspace": s.workspace or "",
        "repo_hints": s.repo_hints or [],
        "keywords": s.keywords or [],
        "active": bool(s.active),
        "config_json": s.config_json or {},
    }


def ensure_seed_surfaces(db: Session) -> None:
    if db.query(FabricSurface).count() > 0:
        return
    for row in _SEED:
        db.add(
            FabricSurface(
                surface_id=row["surface_id"],
                label=row["label"],
                keywords=row["keywords"],
                active=row["active"],
                repo_hints=[],
                config_json={},
            )
        )
    db.commit()


def classify_text(db: Session, text: str, *, require_active: bool = True) -> dict[str, Any]:
    ensure_seed_surfaces(db)
    q = db.query(FabricSurface)
    surfaces = q.all()
    low = text.lower()
    matched: list[dict[str, Any]] = []
    required_ids: list[str] = []
    for s in surfaces:
        kws = [str(k).lower() for k in (s.keywords or []) if str(k).strip()]
        hit = any(k in low for k in kws) or s.surface_id.lower() in low
        if not hit:
            continue
        required_ids.append(s.surface_id)
        matched.append(_to_dict(s))
    # De-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for sid in required_ids:
        if sid not in seen:
            seen.add(sid)
            ordered.append(sid)
    missing: list[str] = []
    if require_active:
        for sid in ordered:
            row = next((m for m in matched if m["surface_id"] == sid), None)
            if row and not row.get("active"):
                missing.append(sid)
    return {
        "surfaces_required": ordered,
        "missing_surfaces": missing,
        "matched": matched,
        "ok": len(missing) == 0 and len(ordered) > 0,
        "refuse": len(missing) > 0 or len(ordered) == 0,
        "checklist": (
            [f"Activate or register surface: {m}" for m in missing]
            if missing
            else (["No surfaces matched — refine goal or register keywords"] if not ordered else [])
        ),
    }


@router.get("/surfaces")
def list_surfaces(db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    ensure_seed_surfaces(db)
    items = db.query(FabricSurface).order_by(FabricSurface.surface_id).all()
    return {"items": [_to_dict(s) for s in items], "total": len(items)}


@router.post("/surfaces")
def create_surface(
    data: SurfaceIn,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    ensure_seed_surfaces(db)
    if db.query(FabricSurface).filter(FabricSurface.surface_id == data.surface_id).first():
        raise HTTPException(400, "surface_id_exists")
    row = FabricSurface(
        surface_id=data.surface_id.strip(),
        label=data.label,
        project_key=data.project_key,
        workspace=data.workspace,
        repo_hints=data.repo_hints,
        keywords=data.keywords,
        active=data.active,
        config_json=data.config_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


@router.patch("/surfaces/{surface_id}")
def update_surface(
    surface_id: str,
    data: SurfaceUpdate,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    row = db.query(FabricSurface).filter(FabricSurface.surface_id == surface_id).first()
    if not row:
        raise HTTPException(404, "surface_not_found")
    for field in ("label", "project_key", "workspace", "repo_hints", "keywords", "active", "config_json"):
        val = getattr(data, field)
        if val is not None:
            setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


@router.post("/classify")
def classify(req: ClassifyIn, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    return classify_text(db, req.text, require_active=req.require_active)


@router.post("/run")
def run_fabric(req: RunIn, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)):
    """Refuse if missing surfaces; else start Mentrix Coding Agent per slice."""
    result = classify_text(db, req.text, require_active=req.require_active)
    if result.get("refuse"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "fabric_refuse",
                "checklist": result.get("checklist") or [],
                "missing_surfaces": result.get("missing_surfaces") or [],
                "surfaces_required": result.get("surfaces_required") or [],
            },
        )
    from app.adapters.coding_runtime import get_mentrix_native_runtime

    rt = get_mentrix_native_runtime()
    default_ws = (
        (req.workspace or "").strip()
        or (os.getenv("MENTRIX_WORKSPACE") or "").strip()
        or (os.getenv("ZECT_WORKSPACE_ROOT") or "").strip()
    )
    sessions: list[dict[str, Any]] = []
    for sid in result["surfaces_required"]:
        surf = db.query(FabricSurface).filter(FabricSurface.surface_id == sid).first()
        ws = (surf.workspace if surf and surf.workspace else default_ws).strip()
        if not ws:
            raise HTTPException(400, detail={"error": "workspace_required", "surface_id": sid})
        goal = (
            f"[Mentrix Fabric surface={sid}] {req.text}\n"
            "Modernize/implement for this surface only; respect Lattice/Blueprint context."
        )
        try:
            run_id = rt.start_run(
                goal,
                workspace=ws,
                auto_approve_edits=req.auto_approve_edits,
                project_key=(surf.project_key if surf else "") or None,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, detail={"error": str(exc), "surface_id": sid}) from exc
        nav = f"/workspace?session={quote(run_id)}&goal={quote(goal[:160])}"
        sessions.append({"surface_id": sid, "session_id": run_id, "workspace": ws, "navigate": nav})
    return {
        "ok": True,
        "sessions": sessions,
        "surfaces_required": result["surfaces_required"],
        "engine": "mentrix_native",
    }

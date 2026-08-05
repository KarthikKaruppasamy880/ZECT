"""Phase 7 Stage A — file organize dry-run / approve / SHA-256 move / rollback.

Operates only under path-allowlisted roots. No auto-delete.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.allowed_paths import path_under_allowed_roots
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication, log_audit
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/file-organize", tags=["file-organize"])

_PLANS: dict[str, dict] = {}


class PlanRequest(BaseModel):
    source_dir: str
    dest_dir: str
    patterns: list[str] = Field(default_factory=lambda: ["*"])
    dry_run: bool = True


class ApproveRequest(BaseModel):
    plan_id: str
    execute: bool = True


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _match(name: str, patterns: list[str]) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(name, p) for p in patterns)


@router.post("/plan")
@require_authentication
def create_plan(
    req: PlanRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        src = Path(path_under_allowed_roots(req.source_dir))
        dest = Path(path_under_allowed_roots(req.dest_dir))
    except Exception as e:
        raise HTTPException(400, f"Path not allowlisted: {e}") from e
    if not src.is_dir():
        raise HTTPException(400, "source_dir must be an existing directory")

    moves = []
    for p in sorted(src.iterdir()):
        if not p.is_file():
            continue
        if not _match(p.name, req.patterns or ["*"]):
            continue
        target = dest / p.name
        moves.append(
            {
                "from": str(p),
                "to": str(target),
                "sha256": _sha256(p),
                "bytes": p.stat().st_size,
            }
        )

    plan_id = uuid.uuid4().hex[:12]
    plan = {
        "plan_id": plan_id,
        "source_dir": str(src),
        "dest_dir": str(dest),
        "dry_run": True,
        "moves": moves,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "planned",
        "rollback": [],
    }
    _PLANS[plan_id] = plan
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="file_organize_plan",
        resource_type="file_organize",
        details={"plan_id": plan_id, "count": len(moves)},
    )
    return plan


@router.post("/approve")
@require_authentication
def approve_plan(
    req: ApproveRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _PLANS.get(req.plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if not req.execute:
        plan["status"] = "rejected"
        return plan

    dest = Path(plan["dest_dir"])
    dest.mkdir(parents=True, exist_ok=True)
    rollback = []
    errors = []
    for item in plan["moves"]:
        src = Path(item["from"])
        dst = Path(item["to"])
        try:
            if not src.exists():
                errors.append({"file": str(src), "error": "missing"})
                continue
            if _sha256(src) != item["sha256"]:
                errors.append({"file": str(src), "error": "hash_mismatch"})
                continue
            if dst.exists():
                errors.append({"file": str(dst), "error": "dest_exists"})
                continue
            shutil.move(str(src), str(dst))
            rollback.append({"from": str(dst), "to": str(src), "sha256": item["sha256"]})
        except Exception as e:
            errors.append({"file": str(src), "error": str(e)})

    plan["status"] = "executed" if not errors else "executed_with_errors"
    plan["dry_run"] = False
    plan["rollback"] = rollback
    plan["errors"] = errors
    plan["executed_at"] = datetime.now(timezone.utc).isoformat()
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="file_organize_execute",
        resource_type="file_organize",
        details={"plan_id": req.plan_id, "moved": len(rollback), "errors": len(errors)},
    )
    return plan


@router.post("/rollback")
@require_authentication
def rollback_plan(
    plan_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _PLANS.get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    restored = []
    for item in reversed(plan.get("rollback") or []):
        src = Path(item["from"])
        dst = Path(item["to"])
        try:
            if src.exists() and not dst.exists():
                shutil.move(str(src), str(dst))
                restored.append(item)
        except Exception:
            continue
    plan["status"] = "rolled_back"
    plan["restored"] = restored
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="file_organize_rollback",
        resource_type="file_organize",
        details={"plan_id": plan_id, "restored": len(restored)},
    )
    return plan


@router.get("/{plan_id}")
@require_authentication
def get_plan(plan_id: str, current_user: CurrentUser = Depends(get_current_user)):
    plan = _PLANS.get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan

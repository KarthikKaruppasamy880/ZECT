"""HTTP API for WorkItems + Mentrix Developer routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.domains.work_items.events import forbid_event_delete, forbid_event_update
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import get_db

router = APIRouter(prefix="/api/work-items", tags=["work-items"])
developer_router = APIRouter(prefix="/api/mentrix/developer", tags=["mentrix-developer"])


class WorkItemCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    source: str = "user"
    external_id: str = ""
    project_id: Optional[int] = None
    repository_id: Optional[int] = None
    repository_ref: str = ""
    base_commit_sha: str = ""
    requirements: list[Any] = Field(default_factory=list)
    acceptance: list[Any] = Field(default_factory=list)


class TransitionIn(BaseModel):
    status: str
    reason: str = ""


@router.post("")
def create_work_item(
    body: WorkItemCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    wi = wi_svc.create_work_item(
        db,
        title=body.title,
        description=body.description,
        source=body.source,
        external_id=body.external_id,
        project_id=body.project_id,
        repository_id=body.repository_id,
        repository_ref=body.repository_ref,
        base_commit_sha=body.base_commit_sha,
        requirements=body.requirements,
        acceptance=body.acceptance,
        created_by=getattr(user, "email", "") or getattr(user, "username", "") or "",
    )
    return wi_svc.serialize_work_item(wi)


@router.get("")
def list_work_items(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items = wi_svc.list_work_items(db, project_id=project_id, status=status, limit=limit)
    return {"items": [wi_svc.serialize_work_item(w) for w in items]}


@router.get("/{work_item_id}")
def get_work_item(
    work_item_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    return wi_svc.serialize_work_item(wi_svc.get_work_item(db, work_item_id))


@router.get("/{work_item_id}/events")
def get_events(
    work_item_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    return {"events": [wi_svc.serialize_event(e) for e in wi_svc.list_events(db, work_item_id)]}


@router.post("/{work_item_id}/transition")
def transition(
    work_item_id: int,
    body: TransitionIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    wi = wi_svc.transition_status(
        db,
        work_item_id,
        body.status,
        reason=body.reason,
        allow_gate=False,
        actor=getattr(user, "email", "") or "user",
    )
    return wi_svc.serialize_work_item(wi)


@router.put("/{work_item_id}/events/{event_id}")
def mutate_event_forbidden(work_item_id: int, event_id: int, _user: CurrentUser = Depends(get_current_user)):
    try:
        forbid_event_update(event_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=405, detail=str(exc)) from exc


@router.delete("/{work_item_id}/events/{event_id}")
def delete_event_forbidden(work_item_id: int, event_id: int, _user: CurrentUser = Depends(get_current_user)):
    try:
        forbid_event_delete(event_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=405, detail=str(exc)) from exc


# ---- Mentrix Developer API ----


class AskIn(BaseModel):
    question: str
    work_item_id: Optional[int] = None
    project_id: Optional[int] = None
    repository_id: Optional[int] = None
    repository_ref: str = ""
    base_commit_sha: str = ""


class PlanIn(BaseModel):
    goal: str
    work_item_id: Optional[int] = None
    project_id: Optional[int] = None
    repository_id: Optional[int] = None
    repository_ref: str = ""
    base_commit_sha: str = ""
    constraints: str = ""


class ApprovePlanIn(BaseModel):
    work_item_id: int


class AgentIn(BaseModel):
    work_item_id: int
    goal: str = ""
    workspace: str = ""


@developer_router.post("/ask")
def developer_ask(
    body: AskIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.developer_service import MentrixDeveloperService

    return MentrixDeveloperService(db).ask(
        question=body.question,
        work_item_id=body.work_item_id,
        project_id=body.project_id,
        repository_id=body.repository_id,
        repository_ref=body.repository_ref,
        base_commit_sha=body.base_commit_sha,
        actor=getattr(user, "email", "") or "",
    )


@developer_router.post("/plan")
def developer_plan(
    body: PlanIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.developer_service import MentrixDeveloperService

    return MentrixDeveloperService(db).plan(
        goal=body.goal,
        work_item_id=body.work_item_id,
        project_id=body.project_id,
        repository_id=body.repository_id,
        repository_ref=body.repository_ref,
        base_commit_sha=body.base_commit_sha,
        constraints=body.constraints,
        actor=getattr(user, "email", "") or "",
    )


@developer_router.post("/approve-plan")
def developer_approve_plan(
    body: ApprovePlanIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.developer_service import MentrixDeveloperService

    return MentrixDeveloperService(db).approve_plan(
        work_item_id=body.work_item_id,
        actor=getattr(user, "email", "") or "",
    )


@developer_router.post("/agent/start")
def developer_start_agent(
    body: AgentIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.developer_service import MentrixDeveloperService

    return MentrixDeveloperService(db).start_agent(
        work_item_id=body.work_item_id,
        goal=body.goal,
        workspace=body.workspace,
        actor=getattr(user, "email", "") or "",
    )


@developer_router.post("/agent/continue")
def developer_continue_agent(
    body: AgentIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.developer_service import MentrixDeveloperService

    return MentrixDeveloperService(db).continue_agent(
        work_item_id=body.work_item_id,
        goal=body.goal,
        actor=getattr(user, "email", "") or "",
    )


@developer_router.post("/agent/cancel")
def developer_cancel_agent(
    body: AgentIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.developer_service import MentrixDeveloperService

    return MentrixDeveloperService(db).cancel_agent(
        work_item_id=body.work_item_id,
        actor=getattr(user, "email", "") or "",
    )


@developer_router.post("/resume")
def developer_resume(
    body: ApprovePlanIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.developer_service import MentrixDeveloperService

    return MentrixDeveloperService(db).resume(
        work_item_id=body.work_item_id,
        actor=getattr(user, "email", "") or "",
    )

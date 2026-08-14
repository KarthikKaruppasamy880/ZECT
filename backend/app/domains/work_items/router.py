"""HTTP API for WorkItems + Mentrix Developer routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.domains.work_items.events import forbid_event_delete, forbid_event_update
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import get_db
from app.models import Project, WorkItem

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


SAMPLE_PROCESS_TITLE = "Fix Failed Order Validation"
SAMPLE_PROCESS_EXTERNAL = "SAMPLE-ORDER-VALIDATION"


@router.post("/sample-process")
def create_sample_process(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Isolated SAMPLE Camunda-style process → WorkItem. Never completes a live engine task."""
    try:
        project = db.query(Project).filter(Project.name == "ZECT Sample Processes").first()
        if not project:
            project = Project(
                name="ZECT Sample Processes",
                description="Isolated SAMPLE fixtures for Process → WorkItem demos. Not production Camunda.",
                team="ZECT",
                status="active",
                current_stage="plan",
            )
            db.add(project)
            db.flush()
        existing = (
            db.query(WorkItem)
            .filter(
                WorkItem.external_id == SAMPLE_PROCESS_EXTERNAL,
                WorkItem.source == "camunda",
            )
            .first()
        )
        if existing:
            return {
                "ok": True,
                "created": False,
                "project_id": project.id,
                "work_item": wi_svc.serialize_work_item(existing),
                "note": "Existing SAMPLE process WorkItem reused. External task text is untrusted.",
            }
        wi = wi_svc.create_work_item(
            db,
            title=SAMPLE_PROCESS_TITLE,
            description=(
                "[untrusted-external] SAMPLE incident: order validation failed in checkout. "
                "Review → investigate → plan → human approval → agent → tests → review → evidence. "
                "Do not complete production Camunda tasks."
            ),
            source="camunda",
            external_id=SAMPLE_PROCESS_EXTERNAL,
            project_id=project.id,
            created_by=getattr(user, "email", "") or getattr(user, "username", "") or "",
            requirements=["Investigate failing validation", "Propose fix", "Human approval before AGENT"],
            acceptance=["Tests pass", "Evidence recorded", "WorkItem READY_TO_SHIP only after verifiers"],
        )
        return {
            "ok": True,
            "created": True,
            "project_id": project.id,
            "work_item": wi_svc.serialize_work_item(wi),
            "note": "SAMPLE fixture only. Ticket text is untrusted external context.",
        }
    except IntegrityError:
        db.rollback()
        project = db.query(Project).filter(Project.name == "ZECT Sample Processes").first()
        existing = (
            db.query(WorkItem)
            .filter(
                WorkItem.external_id == SAMPLE_PROCESS_EXTERNAL,
                WorkItem.source == "camunda",
            )
            .first()
        )
        if project and existing:
            return {
                "ok": True,
                "created": False,
                "project_id": project.id,
                "work_item": wi_svc.serialize_work_item(existing),
                "note": "Existing SAMPLE process WorkItem reused. External task text is untrusted.",
            }
        raise


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
    repository_ids: list[int] = Field(default_factory=list)
    repository_ref: str = ""
    base_commit_sha: str = ""


class PlanIn(BaseModel):
    goal: str
    work_item_id: Optional[int] = None
    project_id: Optional[int] = None
    repository_id: Optional[int] = None
    repository_ids: list[int] = Field(default_factory=list)
    repository_ref: str = ""
    base_commit_sha: str = ""
    constraints: str = ""


class ApprovePlanIn(BaseModel):
    work_item_id: int


class AgentIn(BaseModel):
    work_item_id: int
    goal: str = ""
    workspace: str = ""
    deterministic: bool = False


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
        repository_ids=body.repository_ids or None,
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
        repository_ids=body.repository_ids or None,
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
        deterministic=body.deterministic,
    )


@developer_router.get("/work-items/{work_item_id}/multi-repo-status")
def developer_multi_repo_status(
    work_item_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.artifact_store import ArtifactStore
    from app.services.work_items.multi_repo_agent import read_multi_repo_status

    wi = wi_svc.get_work_item(db, work_item_id)
    store = ArtifactStore(wi.id)
    return read_multi_repo_status(store, work_item_id=wi.id, wi_status=wi.status or "")


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


class IngestIn(BaseModel):
    source: str = Field(..., min_length=1)
    external_id: str = Field(..., min_length=1)
    raw: Optional[dict] = None
    project_id: Optional[int] = None
    repository_id: Optional[int] = None
    repository_ref: str = ""
    base_commit_sha: str = ""
    require_repo: bool = True


@router.post("/ingest")
def ingest_external(
    body: IngestIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    from app.domains.work_items.ingest import ingest_work_item

    return ingest_work_item(
        db,
        source=body.source,
        external_id=body.external_id,
        raw=body.raw,
        project_id=body.project_id,
        repository_id=body.repository_id,
        repository_ref=body.repository_ref,
        base_commit_sha=body.base_commit_sha,
        created_by=getattr(user, "email", "") or "",
        require_repo=body.require_repo,
    )


class FabricHandoffIn(BaseModel):
    work_item_id: int
    workspace: str = ""
    text: str = ""


@developer_router.post("/fabric-handoff")
def fabric_handoff(
    body: FabricHandoffIn,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.fabric_handoff import fabric_handoff_from_work_item

    return fabric_handoff_from_work_item(
        db,
        work_item_id=body.work_item_id,
        workspace=body.workspace,
        text=body.text,
    )


class CloseLoopIn(BaseModel):
    work_item_id: int
    pr_url: str = ""
    jira_comment: str = ""
    jira_transition_id: str = ""
    camunda_complete: bool = False
    dry_run: bool = True


@developer_router.post("/close-loop")
def close_loop(
    body: CloseLoopIn,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.close_loop import close_external_loop

    return close_external_loop(
        db,
        work_item_id=body.work_item_id,
        pr_url=body.pr_url,
        jira_comment=body.jira_comment,
        jira_transition_id=body.jira_transition_id,
        camunda_complete=body.camunda_complete,
        dry_run=body.dry_run,
    )


@developer_router.get("/project-intelligence")
def project_intelligence(
    project_id: Optional[int] = None,
    project_key: str = "",
    repository_id: Optional[int] = None,
    repository_ids: str = "",
    query: str = "",
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.services.work_items.multi_repo_context import repo_binding, resolve_authorized_repository_ids
    from app.services.work_items.project_intelligence import ProjectIntelligenceService

    pi = ProjectIntelligenceService()
    ids_raw = [int(x) for x in repository_ids.split(",") if x.strip().isdigit()]
    authorized = resolve_authorized_repository_ids(
        db,
        project_id=project_id,
        repository_ids=ids_raw or None,
        repository_id=repository_id,
    )
    if len(authorized) > 1:
        repos_out = []
        for rid in authorized:
            binding = repo_binding(db, rid)
            snap = pi.snapshot(
                project_id=project_id,
                project_key=project_key,
                repository_id=rid,
                db=db,
                query=query,
            )
            repos_out.append({**binding, "project_intelligence": snap.to_dict()})
        primary = pi.snapshot(
            project_id=project_id,
            project_key=project_key,
            repository_id=authorized[0],
            db=db,
            query=query,
        )
        out = primary.to_dict()
        out["repositories"] = repos_out
        out["multi_repo"] = True
        return out

    snap = pi.snapshot(
        project_id=project_id,
        project_key=project_key,
        repository_id=repository_id,
        db=db,
        query=query,
    )
    return snap.to_dict()

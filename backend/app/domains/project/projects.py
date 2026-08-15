from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.models import Project, Repo
from app.schemas import ProjectCreate, ProjectUpdate, ProjectOut
from app.services.fixture_isolation import (
    PROVENANCE_TEST,
    PROVENANCE_USER,
    audit_projects,
    cleanup_proven_test_projects,
    in_pytest,
    is_fixture_project_name,
    keep_cleanup_projects,
    should_hide_project,
    tag_projects_by_ids,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


class FixtureTagBody(BaseModel):
    ids: list[int] = Field(default_factory=list)
    test_run_id: str = ""


class FixtureCleanupBody(BaseModel):
    dry_run: bool = True


class FixtureKeepCleanupBody(BaseModel):
    keep_ids: list[int] = Field(default_factory=list)
    dry_run: bool = True


@router.get("", response_model=list[ProjectOut])
def list_projects(
    status: str | None = None,
    exclude_fixtures: bool = Query(False),
    exclude_name_candidates: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    rows = query.order_by(Project.updated_at.desc()).all()
    if exclude_fixtures:
        hide_names = True if exclude_name_candidates is None else bool(exclude_name_candidates)
        rows = [
            p
            for p in rows
            if not should_hide_project(p, exclude_name_candidates=hide_names)
        ]
    return rows


@router.get("/fixtures/audit")
def fixtures_audit(db: Session = Depends(get_db)):
    return audit_projects(db)


@router.post("/fixtures/tag")
def fixtures_tag(body: FixtureTagBody, db: Session = Depends(get_db)):
    if not in_pytest() and not (body.test_run_id or "").strip():
        raise HTTPException(status_code=400, detail="test_run_id_required")
    rid = (body.test_run_id or "").strip() or "manual-tag"
    return tag_projects_by_ids(db, body.ids, test_run_id=rid)


@router.post("/fixtures/cleanup")
def fixtures_cleanup(body: FixtureCleanupBody | None = None, db: Session = Depends(get_db)):
    dry = True if body is None else bool(body.dry_run)
    return cleanup_proven_test_projects(db, dry_run=dry)


@router.post("/fixtures/keep-cleanup")
def fixtures_keep_cleanup(body: FixtureKeepCleanupBody, db: Session = Depends(get_db)):
    if not list(body.keep_ids or []):
        raise HTTPException(status_code=400, detail="keep_ids_required")
    return keep_cleanup_projects(db, list(body.keep_ids), dry_run=bool(body.dry_run))


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    provenance = (data.provenance or PROVENANCE_USER).strip().lower() or PROVENANCE_USER
    test_run_id = (data.test_run_id or "").strip()
    if provenance == PROVENANCE_TEST:
        if not in_pytest() and not test_run_id:
            raise HTTPException(status_code=403, detail="test_provenance_requires_test_run_id")
        if not test_run_id:
            test_run_id = "pytest"
    else:
        provenance = PROVENANCE_USER
        test_run_id = ""
    project = Project(
        name=data.name,
        description=data.description,
        team=data.team,
        current_stage=data.current_stage,
        provenance=provenance,
        test_run_id=test_run_id,
    )
    db.add(project)
    db.flush()
    for r in data.repos:
        repo = Repo(
            project_id=project.id,
            owner=r.owner,
            repo_name=r.repo_name,
            default_branch=r.default_branch,
        )
        db.add(repo)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


@router.post("/{project_id}/repos", response_model=ProjectOut)
def add_repo_to_project(project_id: int, repo_data: dict, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Attach existing registered repo without duplication
    if repo_data.get("repo_id"):
        from app.services.repo_onboarding import attach_existing_repo

        out = attach_existing_repo(db, project_id=project_id, repo_id=int(repo_data["repo_id"]))
        if not out.get("ok"):
            raise HTTPException(400, detail=out)
        db.refresh(project)
        return project

    owner = repo_data.get("owner", "")
    repo_name = repo_data.get("repo_name", "")
    if owner and repo_name:
        from app.services.repo_onboarding import find_existing_repo

        existing = find_existing_repo(db, owner=owner, repo_name=repo_name)
        if existing and existing.project_id == project_id:
            return project
        if existing:
            existing.project_id = project_id
            db.commit()
            db.refresh(project)
            return project

    repo = Repo(
        project_id=project_id,
        owner=owner,
        repo_name=repo_name,
        default_branch=repo_data.get("default_branch", "main"),
    )
    db.add(repo)
    db.commit()
    db.refresh(project)
    return project

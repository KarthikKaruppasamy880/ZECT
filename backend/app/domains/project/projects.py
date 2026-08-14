from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.models import Project, Repo
from app.schemas import ProjectCreate, ProjectUpdate, ProjectOut
import re

router = APIRouter(prefix="/api/projects", tags=["projects"])

DEMO_NAMES = frozenset(
    {
        "Policy Admin Modernization",
        "Claims Processing API",
        "Agent Portal Redesign",
        "Underwriting Rules Engine",
        "Customer Notifications Service",
        "Document Intelligence Pipeline",
    }
)
FIXTURE_NAME = re.compile(
    r"^(Phase6\b|zect-r36-|r36-live-|Repo Onboard |Onboarding Test|LIVE_E2E\b)",
    re.I,
)


def is_fixture_project_name(name: str) -> bool:
    n = (name or "").strip()
    return n in DEMO_NAMES or bool(FIXTURE_NAME.search(n))


@router.get("", response_model=list[ProjectOut])
def list_projects(
    status: str | None = None,
    exclude_fixtures: bool = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    rows = query.order_by(Project.updated_at.desc()).all()
    if exclude_fixtures:
        rows = [p for p in rows if not is_fixture_project_name(p.name or "")]
    return rows


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=data.name,
        description=data.description,
        team=data.team,
        current_stage=data.current_stage,
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

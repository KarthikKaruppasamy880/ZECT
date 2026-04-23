from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, Repo
from app.schemas import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    return query.order_by(Project.updated_at.desc()).all()


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
    repo = Repo(
        project_id=project_id,
        owner=repo_data.get("owner", ""),
        repo_name=repo_data.get("repo_name", ""),
        default_branch=repo_data.get("default_branch", "main"),
    )
    db.add(repo)
    db.commit()
    db.refresh(project)
    return project

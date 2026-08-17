"""Multi-root IDE: search identity, git sibling jail, runner bound-root, no disk delete."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database import Base
from app.models import Project, Repo
from app.domains.repository import git_ops
from app.domains.workspace.app_runner import ExecuteRequest, _reject_command_escape, _validate_cwd
from app.services.workspace_multi_root import relpaths_inside_repo, search_workspace


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path, *, name: str, extra: str | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    (root / f"{name}.txt").write_text(f"{name}-content\n", encoding="utf-8")
    if extra:
        (root / extra).write_text(f"shared {name}\n", encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@zect.local")
    _git(root, "config", "user.name", "ZECT Test")
    _git(root, "add", ".")
    _git(root, "commit", "-m", f"init {name}")
    return root


@pytest.fixture()
def allowed_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(root))
    return root


@pytest.fixture()
def mem_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    project = Project(name="ws", description="", team="t", current_stage="ask", status="active")
    db.add(project)
    db.commit()
    db.refresh(project)
    return db


def _register(db: Session, project: Project, path: Path, name: str) -> Repo:
    repo = Repo(
        project_id=project.id,
        owner="local",
        repo_name=name,
        default_branch="main",
        clone_status="cloned",
        local_path=str(path.resolve()),
        clone_branch="main",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def test_search_tags_duplicate_filenames_with_root_identity(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    a = _init_repo(allowed_root / "zect", name="zect", extra="shared.txt")
    b = _init_repo(allowed_root / "zoas", name="zoas", extra="shared.txt")
    ra = _register(mem_db, project, a, "zect")
    rb = _register(mem_db, project, b, "zoas")
    out = search_workspace(
        mem_db,
        pattern="shared",
        scope="workspace",
        repo_ids=[ra.id, rb.id],
        max_results=20,
    )
    labels = sorted({h["root_label"] for h in out["hits"]})
    assert labels == ["local/zect", "local/zoas"]
    assert all(h["repo_id"] in {ra.id, rb.id} for h in out["hits"])
    assert all(h["project_id"] == project.id for h in out["hits"])
    assert out["semantic_cross_repo_references"] is False


def test_search_skips_unavailable_and_unauthorized_roots(allowed_root: Path, mem_db: Session, monkeypatch: pytest.MonkeyPatch):
    project = mem_db.query(Project).first()
    missing = _register(mem_db, project, allowed_root / "gone", "gone")
    missing.local_path = str((allowed_root / "does-not-exist").resolve())
    mem_db.commit()
    out = search_workspace(mem_db, pattern="x", scope="workspace", repo_ids=[missing.id])
    assert out["hits"] == []
    assert out["skipped"][0]["reason"] == "ROOT_UNAVAILABLE"


def test_git_add_rejects_sibling_repo_path(allowed_root: Path):
    a = _init_repo(allowed_root / "alpha", name="alpha")
    b = _init_repo(allowed_root / "beta", name="beta")
    (b / "secret.txt").write_text("secret\n", encoding="utf-8")
    with pytest.raises(HTTPException) as exc:
        relpaths_inside_repo(str(a), [str(b / "secret.txt")])
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        git_ops.git_add(str(a), files=["../beta/secret.txt"])


def test_git_status_on_a_does_not_mutate_b(allowed_root: Path):
    a = _init_repo(allowed_root / "alpha", name="alpha")
    b = _init_repo(allowed_root / "beta", name="beta")
    head_b = subprocess.run(["git", "rev-parse", "HEAD"], cwd=b, capture_output=True, text=True, check=True).stdout.strip()
    (a / "dirty.txt").write_text("a-only\n", encoding="utf-8")
    st_a = git_ops.git_status(str(a))
    st_b = git_ops.git_status(str(b))
    assert st_a.clean is False
    assert st_b.clean is True
    head_b_after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=b, capture_output=True, text=True, check=True).stdout.strip()
    assert head_b_after == head_b
    assert not (b / "dirty.txt").exists()


def test_git_push_rejects_force_remote_name(allowed_root: Path):
    a = _init_repo(allowed_root / "alpha", name="alpha")
    with pytest.raises(HTTPException) as exc:
        git_ops.git_push(git_ops.GitPushRequest(repo_path=str(a), remote="--force"))
    assert exc.value.status_code == 400


def test_runner_bound_root_rejects_escape(allowed_root: Path):
    a = _init_repo(allowed_root / "alpha", name="alpha")
    b = _init_repo(allowed_root / "beta", name="beta")
    with pytest.raises(HTTPException) as exc:
        _validate_cwd(str(b), bound_root=str(a))
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        _reject_command_escape("cd .. && echo hi", str(a))
    cwd = _validate_cwd(str(a), bound_root=str(a))
    assert Path(cwd).resolve() == a.resolve()


def test_execute_request_accepts_bound_root_field():
    req = ExecuteRequest(command="echo hi", cwd="/tmp/x", bound_root="/tmp/x")
    assert req.bound_root == "/tmp/x"


def test_search_truncates_and_skips_unauthorized(allowed_root: Path, mem_db: Session, monkeypatch: pytest.MonkeyPatch):
    project = mem_db.query(Project).first()
    a = _init_repo(allowed_root / "zect", name="zect")
    (a / "many.txt").write_text("hit\n" * 50, encoding="utf-8")
    ra = _register(mem_db, project, a, "zect")
    out = search_workspace(mem_db, pattern="hit", scope="workspace", repo_ids=[ra.id], max_results=5)
    assert out["truncated"] is True
    assert len(out["hits"]) == 5


def test_git_checkout_on_a_leaves_b_head(allowed_root: Path):
    a = _init_repo(allowed_root / "alpha", name="alpha")
    b = _init_repo(allowed_root / "beta", name="beta")
    head_b = subprocess.run(["git", "rev-parse", "HEAD"], cwd=b, capture_output=True, text=True, check=True).stdout.strip()
    git_ops.git_checkout(git_ops.GitCheckoutRequest(repo_path=str(a), branch="main"))
    st_a = git_ops.git_status(str(a))
    st_b = git_ops.git_status(str(b))
    assert st_a.branch == "main"
    assert st_b.clean is True
    head_b_after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=b, capture_output=True, text=True, check=True).stdout.strip()
    assert head_b_after == head_b

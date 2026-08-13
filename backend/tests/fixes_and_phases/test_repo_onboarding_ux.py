"""Repo onboarding UX — inspect, register, discover, safe checkout, PR worktrees, API."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database import Base, SessionLocal
from app.models import Project, Repo
from app.services.repo_onboarding import (
    attach_existing_repo,
    discover_local_repos,
    ensure_pr_worktree,
    inspect_git_repo,
    register_local_repo,
    repo_git_identity,
    safe_checkout,
)


# ---------------------------------------------------------------------------
# Git + DB helpers (isolated from the real ZECT working copy)
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(root: Path, *, initial_branch: str = "main") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("init\n", encoding="utf-8")
    _git(root, "init", "-b", initial_branch)
    _git(root, "config", "user.email", "test@zect.local")
    _git(root, "config", "user.name", "ZECT Test")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "init")
    return root


def _create_branch(repo: Path, branch: str, *, filename: str, content: str) -> str:
    _git(repo, "checkout", "-b", branch)
    (repo / filename).write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", f"commit on {branch}")
    return branch


def _current_branch(repo: Path) -> str:
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _head_sha(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


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
    SessionLocalMem = sessionmaker(bind=engine)
    session = SessionLocalMem()
    project = Project(name="Onboarding Test", team="Alpha", status="active")
    session.add(project)
    session.commit()
    session.refresh(project)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def shared_db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_project(db: Session, *, suffix: str = "") -> Project:
    tag = suffix or uuid.uuid4().hex[:8]
    project = Project(name=f"Repo Onboard {tag}", team="Alpha", status="active")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _register_repo(db: Session, project: Project, repo_path: Path) -> Repo:
    out = register_local_repo(db, project_id=project.id, local_path=str(repo_path))
    assert out["ok"] is True
    repo = db.query(Repo).filter(Repo.id == out["repo_id"]).first()
    assert repo is not None
    return repo


# ---------------------------------------------------------------------------
# 1. inspect_git_repo / register_local_repo
# ---------------------------------------------------------------------------


def test_inspect_git_repo_validates_and_returns_identity(allowed_root: Path):
    repo_path = _init_git_repo(allowed_root / "owner" / "demo")
    info = inspect_git_repo(str(repo_path))
    assert info["ok"] is True
    assert info["local_path"] == str(repo_path.resolve())
    assert info["name"] == "demo"
    assert info["owner"] == "local"
    assert info["branch"] == "main"
    assert info["head_sha"]
    assert info["clean"] is True
    assert info["dirty"] is False


def test_register_local_repo_binds_to_project(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    repo_path = _init_git_repo(allowed_root / "bind-me")
    out = register_local_repo(mem_db, project_id=project.id, local_path=str(repo_path))
    assert out["ok"] is True
    assert out["reused"] is False
    repo = mem_db.query(Repo).filter(Repo.id == out["repo_id"]).first()
    assert repo.project_id == project.id
    assert repo.clone_status == "cloned"
    assert repo.local_path == str(repo_path.resolve())


def test_register_local_repo_reuses_without_duplicate(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    repo_path = _init_git_repo(allowed_root / "once-only")
    first = register_local_repo(mem_db, project_id=project.id, local_path=str(repo_path))
    second = register_local_repo(mem_db, project_id=project.id, local_path=str(repo_path))
    assert first["ok"] and second["ok"]
    assert first["repo_id"] == second["repo_id"]
    assert second["reused"] is True
    assert mem_db.query(Repo).count() == 1


def test_inspect_git_repo_rejects_non_git_directory(allowed_root: Path):
    plain = allowed_root / "not-git"
    plain.mkdir()
    info = inspect_git_repo(str(plain))
    assert info["ok"] is False
    assert info["error"] == "not_a_git_repository"


# ---------------------------------------------------------------------------
# 2. attach_existing_repo
# ---------------------------------------------------------------------------


def test_attach_existing_repo_without_duplicate(allowed_root: Path, mem_db: Session):
    project_a = Project(name="Project A", team="Alpha", status="active")
    project_b = Project(name="Project B", team="Beta", status="active")
    mem_db.add_all([project_a, project_b])
    mem_db.commit()
    mem_db.refresh(project_a)
    mem_db.refresh(project_b)

    repo_path = _init_git_repo(allowed_root / "attach-target")
    repo = _register_repo(mem_db, project_a, repo_path)

    out = attach_existing_repo(mem_db, project_id=project_b.id, repo_id=repo.id)
    assert out["ok"] is True
    assert out.get("attached") is True
    mem_db.refresh(repo)
    assert repo.project_id == project_b.id


def test_attach_existing_repo_already_attached_is_idempotent(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    repo_path = _init_git_repo(allowed_root / "already-here")
    repo = _register_repo(mem_db, project, repo_path)

    out = attach_existing_repo(mem_db, project_id=project.id, repo_id=repo.id)
    assert out["ok"] is True
    assert out.get("already_attached") is True


def test_attach_existing_repo_duplicate_repo_in_project(allowed_root: Path, mem_db: Session):
    project_a = Project(name="Dup A", team="Alpha", status="active")
    project_b = Project(name="Dup B", team="Beta", status="active")
    mem_db.add_all([project_a, project_b])
    mem_db.commit()
    mem_db.refresh(project_a)
    mem_db.refresh(project_b)

    repo_a_path = _init_git_repo(allowed_root / "dup-a")
    repo_b_path = _init_git_repo(allowed_root / "dup-b")
    repo_a = _register_repo(mem_db, project_a, repo_a_path)
    repo_b = _register_repo(mem_db, project_b, repo_b_path)

    # Force same owner/name under different projects to simulate catalog collision.
    repo_b.owner = repo_a.owner
    repo_b.repo_name = repo_a.repo_name
    mem_db.commit()

    out = attach_existing_repo(mem_db, project_id=project_b.id, repo_id=repo_a.id)
    assert out["ok"] is False
    assert out["error"] == "duplicate_repo_in_project"
    assert out["existing_repo_id"] == repo_b.id


# ---------------------------------------------------------------------------
# 3. discover_local_repos
# ---------------------------------------------------------------------------


def test_discover_local_repos_finds_nested_repos(allowed_root: Path, mem_db: Session):
    root = allowed_root / "scan-root"
    root.mkdir()
    top = _init_git_repo(root / "top-repo")
    nested = _init_git_repo(root / "nested" / "deep" / "inner-repo")

    out = discover_local_repos(mem_db, root=str(root), max_depth=4)
    assert out["ok"] is True
    paths = {r["local_path"] for r in out["repos"]}
    assert str(top.resolve()) in paths
    assert str(nested.resolve()) in paths
    assert out["count"] == 2
    assert str(allowed_root.resolve()) in out["allowed_roots"]


def test_discover_local_repos_rejects_path_outside_allowed_roots(mem_db: Session):
    with pytest.raises(ValueError, match="Access denied"):
        discover_local_repos(mem_db, root="/__zect_not_allowed__/outside")


# ---------------------------------------------------------------------------
# 4. safe_checkout
# ---------------------------------------------------------------------------


def test_safe_checkout_require_clean_blocks_dirty_tree(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    repo_path = _init_git_repo(allowed_root / "dirty-checkout")
    _create_branch(repo_path, "dev", filename="dev.txt", content="dev branch\n")
    _git(repo_path, "checkout", "main")
    (repo_path / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

    repo = _register_repo(mem_db, project, repo_path)
    before_branch = _current_branch(repo_path)

    out = safe_checkout(mem_db, repo_id=repo.id, branch="dev", action="require_clean")
    assert out["ok"] is False
    assert out["error"] == "dirty_working_tree"
    assert out["dirty"] is True
    assert _current_branch(repo_path) == before_branch


def test_safe_checkout_stash_allows_switch_and_updates_branch(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    repo_path = _init_git_repo(allowed_root / "stash-checkout")
    _create_branch(repo_path, "dev", filename="dev.txt", content="dev branch\n")
    _git(repo_path, "checkout", "main")
    main_sha = _head_sha(repo_path)
    (repo_path / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

    repo = _register_repo(mem_db, project, repo_path)
    out = safe_checkout(mem_db, repo_id=repo.id, branch="dev", action="stash")
    assert out["ok"] is True
    assert out["stashed"] is True
    assert out["branch"] == "dev"
    assert _current_branch(repo_path) == "dev"
    assert _head_sha(repo_path) != main_sha

    ident = repo_git_identity(mem_db, repo.id)
    assert ident["branch"] == "dev"
    assert ident["head_sha"] == _head_sha(repo_path)


# ---------------------------------------------------------------------------
# 5. ensure_pr_worktree
# ---------------------------------------------------------------------------


def test_ensure_pr_worktree_creates_isolated_worktree(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    repo_path = _init_git_repo(allowed_root / "pr-main")
    feature_sha = _head_sha(repo_path)
    _create_branch(repo_path, "feature", filename="feature.txt", content="feature work\n")
    _git(repo_path, "checkout", "main")
    main_branch_before = _current_branch(repo_path)
    main_sha_before = _head_sha(repo_path)

    repo = _register_repo(mem_db, project, repo_path)
    out = ensure_pr_worktree(
        mem_db,
        repo_id=repo.id,
        pr_number=7,
        head_branch="feature",
        head_sha=feature_sha,
    )
    assert out["ok"] is True
    assert out["reused"] is False
    wt_path = Path(out["worktree_path"])
    assert wt_path.is_dir()
    assert (wt_path / ".git").exists()
    assert _current_branch(repo_path) == main_branch_before
    assert _head_sha(repo_path) == main_sha_before
    assert _current_branch(wt_path).startswith("zect-pr-")
    assert _head_sha(wt_path) != ""


def test_ensure_pr_worktree_reuses_existing_worktree(allowed_root: Path, mem_db: Session):
    project = mem_db.query(Project).first()
    repo_path = _init_git_repo(allowed_root / "pr-reuse")
    _create_branch(repo_path, "feature", filename="feature.txt", content="feature\n")
    _git(repo_path, "checkout", "main")
    repo = _register_repo(mem_db, project, repo_path)

    first = ensure_pr_worktree(mem_db, repo_id=repo.id, pr_number=3, head_branch="feature")
    second = ensure_pr_worktree(mem_db, repo_id=repo.id, pr_number=3, head_branch="feature")
    assert first["ok"] and second["ok"]
    assert first["reused"] is False
    assert second["reused"] is True
    assert first["worktree_path"] == second["worktree_path"]


# ---------------------------------------------------------------------------
# 6. Path traversal / outside allowed roots
# ---------------------------------------------------------------------------


def test_inspect_git_repo_rejects_path_outside_allowed_roots():
    with pytest.raises(ValueError, match="Access denied"):
        inspect_git_repo("/__zect_not_allowed__/outside")


def test_register_local_repo_rejects_path_outside_allowed_roots(mem_db: Session):
    project = mem_db.query(Project).first()
    with pytest.raises(ValueError, match="Access denied"):
        register_local_repo(mem_db, project_id=project.id, local_path="/__zect_not_allowed__/outside")


def test_register_local_repo_rejects_path_traversal_outside_root(
    allowed_root: Path, mem_db: Session, monkeypatch: pytest.MonkeyPatch
):
    """Resolved path must stay under allowed roots even when input uses traversal."""
    outside = allowed_root.parent / "outside-repo"
    _init_git_repo(outside)
    project = mem_db.query(Project).first()
    # Restrict roots to workspace only (tmp_path siblings are otherwise allowed by default).
    monkeypatch.setattr(
        "app.infrastructure.allowed_paths.allowed_roots",
        lambda: [str(allowed_root.resolve())],
    )
    with pytest.raises(ValueError, match="Access denied"):
        register_local_repo(mem_db, project_id=project.id, local_path=str(outside))


# ---------------------------------------------------------------------------
# FastAPI API tests
# ---------------------------------------------------------------------------


def test_api_register_local(authed_client, allowed_root: Path, shared_db: Session):
    project = _make_project(shared_db, suffix="api-reg")
    repo_path = _init_git_repo(allowed_root / f"api-register-{uuid.uuid4().hex[:8]}")

    resp = authed_client.post(
        "/api/repos/register-local",
        json={"project_id": project.id, "local_path": str(repo_path), "role": "primary"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["repo_id"]
    assert body["identity"]["local_path"] == str(repo_path.resolve())

    again = authed_client.post(
        "/api/repos/register-local",
        json={"project_id": project.id, "local_path": str(repo_path)},
    )
    assert again.status_code == 200, again.text
    assert again.json()["reused"] is True
    assert again.json()["repo_id"] == body["repo_id"]


def test_api_register_local_rejects_outside_roots(authed_client, shared_db: Session):
    """Outside-root paths are rejected with HTTP 403."""
    project = _make_project(shared_db, suffix="api-deny")
    resp = authed_client.post(
        "/api/repos/register-local",
        json={"project_id": project.id, "local_path": "/__zect_not_allowed__/outside"},
    )
    assert resp.status_code == 403


def test_api_discover(authed_client, allowed_root: Path, shared_db: Session):
    root = allowed_root / "api-discover"
    root.mkdir()
    found = _init_git_repo(root / "found-one")
    _init_git_repo(root / "sub" / "found-two")

    resp = authed_client.post(
        "/api/repos/discover",
        json={"root": str(root), "max_depth": 3},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    paths = {r["local_path"] for r in body["repos"]}
    assert str(found.resolve()) in paths
    assert body["count"] >= 2


def test_api_discover_rejects_outside_roots(authed_client):
    resp = authed_client.post(
        "/api/repos/discover",
        json={"root": "/__zect_not_allowed__/outside", "max_depth": 2},
    )
    assert resp.status_code == 403


def test_api_checkout_dirty_action(authed_client, allowed_root: Path, shared_db: Session):
    project = _make_project(shared_db, suffix="api-co")
    repo_path = _init_git_repo(allowed_root / f"api-checkout-{uuid.uuid4().hex[:8]}")
    _create_branch(repo_path, "dev", filename="dev.txt", content="dev\n")
    _git(repo_path, "checkout", "main")
    (repo_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    repo = _register_repo(shared_db, project, repo_path)
    shared_db.refresh(repo)
    assert repo.local_path == str(repo_path.resolve())

    blocked = authed_client.post(
        f"/api/repos/{repo.id}/checkout",
        json={"branch": "dev", "dirty_action": "require_clean"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["error"] == "dirty_working_tree"

    ok = authed_client.post(
        f"/api/repos/{repo.id}/checkout",
        json={"branch": "dev", "dirty_action": "stash"},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["ok"] is True
    assert body["branch"] == "dev"
    assert body["stashed"] is True
    assert _current_branch(repo_path) == "dev"


def test_api_pr_worktree(authed_client, allowed_root: Path, shared_db: Session):
    project = _make_project(shared_db, suffix="api-wt")
    repo_path = _init_git_repo(allowed_root / f"api-worktree-{uuid.uuid4().hex[:8]}")
    feature_sha = _head_sha(repo_path)
    _create_branch(repo_path, "feature", filename="feature.txt", content="feature\n")
    _git(repo_path, "checkout", "main")
    main_branch = _current_branch(repo_path)
    repo = _register_repo(shared_db, project, repo_path)

    resp = authed_client.post(
        f"/api/repos/{repo.id}/pr-worktree",
        json={"pr_number": 99, "head_branch": "feature", "head_sha": feature_sha},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["worktree_path"]
    assert Path(body["worktree_path"]).is_dir()
    assert _current_branch(repo_path) == main_branch

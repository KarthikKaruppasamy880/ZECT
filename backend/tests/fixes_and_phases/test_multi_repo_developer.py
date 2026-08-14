"""Multi-repo Developer ASK/PLAN/AGENT (R3 + R3.5)."""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import Project, Repo
from app.services.mentrix.engineering_agents.acceptance_verifier import AcceptanceVerifier
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.developer_service import MentrixDeveloperService
from app.services.work_items.evidence_verifier import EvidenceVerifier
from app.services.work_items.multi_repo_context import (
    build_affected_repos_manifest,
    resolve_authorized_repository_ids,
)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return (out.stdout or "").strip()


def _init_git_repo(root: Path, *, name: str = "repo") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@zect.local"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT Test"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"init {name}"], cwd=root, check=True, capture_output=True)
    return root


def _head(path: Path) -> str:
    return _git(path, "rev-parse", "HEAD")


def _seed_project_with_repos(db: Session, *, suffix: str | None = None) -> tuple[Project, Repo, Repo]:
    tag = suffix or uuid.uuid4().hex[:8]
    p = Project(name=f"multi-r3-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r1 = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main")
    r2 = Repo(project_id=p.id, owner="acme", repo_name="beta", default_branch="main")
    db.add_all([r1, r2])
    db.commit()
    db.refresh(p)
    db.refresh(r1)
    db.refresh(r2)
    return p, r1, r2


def _env_agent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    monkeypatch.setenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


def test_resolve_authorized_filters_foreign_repo(db: Session):
    p, r1, r2 = _seed_project_with_repos(db)
    other = Repo(project_id=p.id, owner="acme", repo_name="gamma", default_branch="main")
    db.add(other)
    db.commit()
    foreign = Repo(project_id=99999, owner="x", repo_name="foreign", default_branch="main")
    db.add(foreign)
    db.commit()
    ids = resolve_authorized_repository_ids(
        db,
        project_id=p.id,
        repository_ids=[r1.id, r2.id, foreign.id],
        repository_id=None,
    )
    assert r1.id in ids and r2.id in ids
    assert foreign.id not in ids


def test_ask_multi_repo_context_by_repository(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r1, r2 = _seed_project_with_repos(db)
    svc = MentrixDeveloperService(db)
    out = svc.ask(
        question="Cross-repo impact?",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    assert out.get("context_by_repository")
    assert len(out["context_by_repository"]) == 2
    assert len(out.get("affected_repos") or []) == 2
    assert "context_pack" in out


def test_plan_writes_execution_manifest_with_affected_repos(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    p, r1, r2 = _seed_project_with_repos(db)
    svc = MentrixDeveloperService(db)
    out = svc.plan(
        goal="Ship cross-repo feature",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    assert "Affected repositories" in (out.get("plan") or "")
    assert len(out.get("affected_repos") or []) == 2
    manifest = out.get("execution_manifest") or {}
    assert len(manifest.get("operations") or []) == 2
    store = ArtifactStore(out["work_item_id"])
    on_disk = store.read_json("EXECUTION_MANIFEST.json", default={})
    assert len(on_disk.get("affected_repos") or []) == 2


def test_acceptance_verifier_blocks_mandatory_failed_repo_op(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    wid = 42
    manifest = build_affected_repos_manifest(
        [
            {"repository_id": 1, "mandatory": True, "status": "ready"},
            {"repository_id": 2, "mandatory": True, "status": "failed"},
        ]
    )
    manifest["operations"][1]["status"] = "failed"
    store = ArtifactStore(wid)
    store.write_json("EXECUTION_MANIFEST.json", manifest)
    store.write_json("EVIDENCE.json", [])
    av = AcceptanceVerifier(db, wid)
    out = av.verify(ship=False)
    assert out["ready_to_ship"] is False
    assert any("mandatory_repo" in e for e in out.get("errors") or [])


def test_acceptance_verifier_blocks_pending_blocked_stale(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    store = ArtifactStore(4301)
    for st in ("pending", "blocked", "stale", "failed"):
        manifest = build_affected_repos_manifest(
            [
                {"repository_id": 10, "mandatory": True, "status": "pass"},
                {"repository_id": 11, "mandatory": True, "status": st},
            ]
        )
        manifest["operations"][0]["status"] = "completed"
        manifest["operations"][1]["status"] = st
        store.write_json("EXECUTION_MANIFEST.json", manifest)
        store.write_json("TEST_RESULTS.json", {"ok": st == "pass"})
        store.write_json("EVIDENCE.json", [])
        out = AcceptanceVerifier(db, 4301).verify(ship=False)
        assert out["ready_to_ship"] is False, st
        assert any("mandatory_repo" in e or "incomplete_manifest" in e for e in out.get("errors") or [])


def test_start_agent_creates_isolated_worktrees(db: Session, tmp_path, monkeypatch):
    _env_agent(monkeypatch, tmp_path)
    p, r1, r2 = _seed_project_with_repos(db, suffix="wt")
    alpha = _init_git_repo(tmp_path / "alpha", name="alpha")
    beta = _init_git_repo(tmp_path / "beta", name="beta")
    (alpha / "dirty-main.txt").write_text("leave me\n", encoding="utf-8")
    r1.local_path = str(alpha)
    r2.local_path = str(beta)
    db.commit()
    main_a = _head(alpha)
    main_b = _head(beta)
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Isolated worktrees",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    wid = planned["work_item_id"]
    svc.approve_plan(work_item_id=wid, actor="test@zect.local")
    agent = svc.start_agent(work_item_id=wid, deterministic=True)
    wts = agent.get("worktrees") or []
    assert len(wts) == 2
    paths = [Path(w["worktree_path"]) for w in wts]
    for wt in paths:
        assert wt.is_dir()
        assert (wt / "mentrix_p0_agent_marker.py").exists()
        assert wt.resolve() != alpha.resolve()
        assert wt.resolve() != beta.resolve()
    assert _head(alpha) == main_a
    assert _head(beta) == main_b
    assert (alpha / "dirty-main.txt").read_text(encoding="utf-8") == "leave me\n"
    assert not (alpha / "mentrix_p0_agent_marker.py").exists()
    assert not (beta / "mentrix_p0_agent_marker.py").exists()
    for pr in agent.get("pull_requests") or []:
        assert pr.get("pr_status") == "local_branch_only"
        assert not pr.get("pr_url")


def test_one_repo_test_fail_does_not_hide_sibling(db: Session, tmp_path, monkeypatch):
    _env_agent(monkeypatch, tmp_path)
    p, r1, r2 = _seed_project_with_repos(db, suffix="fail")
    alpha = _init_git_repo(tmp_path / "alpha-pass", name="alpha")
    beta = _init_git_repo(tmp_path / "beta-fail", name="beta")
    tests = beta / "tests"
    tests.mkdir()
    (tests / "test_boom.py").write_text("def test_boom():\n    assert False\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=beta, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "failing test"], cwd=beta, check=True, capture_output=True)
    r1.local_path = str(alpha)
    r2.local_path = str(beta)
    db.commit()
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Do not hide sibling failure",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    wid = planned["work_item_id"]
    svc.approve_plan(work_item_id=wid)
    agent = svc.start_agent(work_item_id=wid, deterministic=True)
    by = (agent.get("tests") or {}).get("by_repository") or {}
    assert str(r1.id) in by and str(r2.id) in by
    assert by[str(r1.id)].get("ok") is True
    assert by[str(r2.id)].get("ok") is False
    assert agent["tests"]["ok"] is False
    assert agent.get("ready_to_ship") is False
    store = ArtifactStore(wid)
    disk = store.read_json("TEST_RESULTS.json", default={})
    assert disk.get("ok") is False
    assert disk["by_repository"][str(r2.id)]["ok"] is False
    assert disk["by_repository"][str(r1.id)]["ok"] is True


def test_frontend_blocked_others_pass_not_ready(db: Session, tmp_path, monkeypatch):
    _env_agent(monkeypatch, tmp_path)
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"multi-r35-fe-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    shared = Repo(project_id=p.id, owner="acme", repo_name="shared", default_branch="main")
    backend = Repo(project_id=p.id, owner="acme", repo_name="backend", default_branch="main")
    frontend = Repo(project_id=p.id, owner="acme", repo_name="frontend", default_branch="main")
    db.add_all([shared, backend, frontend])
    db.commit()
    db.refresh(shared)
    db.refresh(backend)
    db.refresh(frontend)
    shared.local_path = str(_init_git_repo(tmp_path / "shared", name="shared"))
    backend.local_path = str(_init_git_repo(tmp_path / "backend", name="backend"))
    frontend.local_path = None
    db.commit()
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="shared+backend pass, frontend blocked",
        project_id=p.id,
        repository_ids=[shared.id, backend.id, frontend.id],
        actor="test@zect.local",
    )
    wid = planned["work_item_id"]
    svc.approve_plan(work_item_id=wid)
    agent = svc.start_agent(work_item_id=wid, deterministic=True)
    by = (agent.get("tests") or {}).get("by_repository") or {}
    assert by[str(shared.id)].get("ok") is True
    assert by[str(backend.id)].get("ok") is True
    assert by[str(frontend.id)].get("ok") is False
    assert by[str(frontend.id)].get("status") == "blocked"
    assert agent.get("ready_to_ship") is False
    statuses = {int(r["repository_id"]): r.get("status") for r in agent.get("affected_repos") or []}
    assert statuses.get(frontend.id) == "blocked"
    assert statuses.get(shared.id) == "pass"
    assert statuses.get(backend.id) == "pass"


def test_pr_head_change_invalidates_stale_evidence(db: Session, tmp_path, monkeypatch):
    _env_agent(monkeypatch, tmp_path)
    p, r1, r2 = _seed_project_with_repos(db, suffix="stale")
    alpha = _init_git_repo(tmp_path / "alpha-stale", name="alpha")
    beta = _init_git_repo(tmp_path / "beta-stale", name="beta")
    r1.local_path = str(alpha)
    r2.local_path = str(beta)
    db.commit()
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Stale evidence after HEAD move",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    wid = planned["work_item_id"]
    svc.approve_plan(work_item_id=wid)
    agent = svc.start_agent(work_item_id=wid, deterministic=True)
    wts = agent.get("worktrees") or []
    assert wts
    wt = Path(wts[0]["worktree_path"])
    (wt / "drift.txt").write_text("head moved\n", encoding="utf-8")
    subprocess.run(["git", "add", "drift.txt"], cwd=wt, check=True, capture_output=True)
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "ZECT Test"
    env["GIT_AUTHOR_EMAIL"] = "test@zect.local"
    env["GIT_COMMITTER_NAME"] = "ZECT Test"
    env["GIT_COMMITTER_EMAIL"] = "test@zect.local"
    subprocess.run(["git", "commit", "-m", "drift"], cwd=wt, check=True, capture_output=True, env=env)
    av = AcceptanceVerifier(db, wid).verify(ship=False)
    assert av["ready_to_ship"] is False
    assert any("stale" in e for e in av.get("errors") or [])


def test_evidence_verifier_stale_head_direct():
    ev = EvidenceVerifier()
    result = ev.verify(
        mandatory_operation_ids=["OP-1-repo-1"],
        requirement_ids=[],
        acceptance_ids=[],
        evidence=[
            {
                "id": "t1",
                "type": "TEST_RESULT",
                "operation_id": "OP-1-repo-1",
                "payload": {"head_sha": "aaa111", "repository_id": 1, "ok": True},
            }
        ],
        current_heads={"1": "bbb222"},
    )
    assert result.ready_to_ship is False
    assert any("stale_evidence" in e for e in result.errors)


def test_redact_secrets_strips_github_tokens():
    from app.services.work_items.multi_repo_agent import _redact_secrets

    raw = (
        "fatal: https://x-access-token:gho_NotARealToken123@github.com/acme/r.git "
        "Authentication failed Bearer gho_NotARealToken123 "
        "http.extraHeader=AUTHORIZATION: bearer gho_NotARealToken123"
    )
    out = _redact_secrets(raw)
    assert "gho_NotARealToken123" not in out
    assert "[redacted]" in out


def test_git_push_github_uses_extraheader_not_origin_rewrite(tmp_path, monkeypatch):
    from app.services.work_items.multi_repo_agent import _git_push_github

    calls = []

    class Fake:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return Fake()

    monkeypatch.setattr("app.services.work_items.multi_repo_agent.subprocess.run", fake_run)
    out = _git_push_github(
        tmp_path,
        origin="https://github.com/acme/widget.git",
        branch="zect-wi-1",
        token="gho_NotARealToken123",
    )
    assert out["ok"] is True
    cmd = calls[0]
    joined = " ".join(cmd)
    assert "http.extraHeader=" in joined
    assert "gho_NotARealToken123" in joined  # passed to git, not stored in origin
    assert "x-access-token" not in joined
    assert "https://github.com/acme/widget.git" in joined


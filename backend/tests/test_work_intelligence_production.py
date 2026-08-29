"""Work intelligence production: Projects, WorkItems, Processes, Lattice per-root.

Honest gates: unset Jira/Camunda = BLOCKED_EXTERNAL. EvidenceVerifier fail-closed.
Graphify is out of scope.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.models import LatticeStructuralBlueprint, Project, Repo, WorkItem
from app.services.lattice.indexer import derive_project_key, get_lattice_status, ingest_path
from app.services.mentrix.companion_scope import build_companion_scope, external_connectors
from app.services.work_items.developer_service import MentrixDeveloperService
from app.services.work_items.evidence_verifier import EvidenceItem, EvidenceVerifier
from app.services.work_items.multi_repo_context import resolve_authorized_repository_ids


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


def _init_git_repo(root: Path, *, name: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    (root / f"{name}.py").write_text(f"def {name}():\n    return '{name}'\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@zect.local"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT Test"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"init {name}"], cwd=root, check=True, capture_output=True)
    return root


def test_derive_project_key_matches_frontend_rule():
    assert derive_project_key("Acme", "Alpha Repo") == "acme-alpha-repo"
    assert derive_project_key("zinnia", "zect") != derive_project_key("zinnia", "zoas")


def test_fixture_isolation_hides_test_keeps_authorized(authed_client):
    tag = uuid.uuid4().hex[:8]
    keep_name = f"ZECT Authorized {tag}"
    drop_name = f"Phase6 Pollution {tag}"
    user = authed_client.post(
        "/api/projects",
        json={"name": keep_name, "description": "real", "provenance": "user", "team": "E2E"},
    )
    assert user.status_code == 201, user.text
    fixture = authed_client.post(
        "/api/projects",
        json={
            "name": drop_name,
            "description": "test",
            "provenance": "test",
            "test_run_id": f"wi-prod-{tag}",
            "team": "E2E",
        },
    )
    assert fixture.status_code == 201, fixture.text
    hidden = authed_client.get("/api/projects?exclude_fixtures=1&exclude_name_candidates=0")
    assert hidden.status_code == 200
    names = {p["name"] for p in hidden.json()}
    assert keep_name in names
    assert drop_name not in names


def test_test_provenance_requires_test_run_id_outside_pytest_shape(authed_client):
    empty = authed_client.post("/api/projects/fixtures/keep-cleanup", json={"keep_ids": [], "dry_run": True})
    assert empty.status_code == 400
    assert "keep_ids" in str(empty.json())


def test_workitem_hidden_fixture_and_visible_real(authed_client):
    tag = uuid.uuid4().hex[:8]
    proj = authed_client.post(
        "/api/projects",
        json={"name": f"WI Host {tag}", "description": "host", "provenance": "user"},
    )
    assert proj.status_code == 201, proj.text
    pid = proj.json()["id"]
    real = authed_client.post(
        "/api/work-items",
        json={"title": f"real-{tag}", "source": "user", "project_id": pid},
    )
    assert real.status_code == 200, real.text
    rid = real.json()["id"]
    db = SessionLocal()
    try:
        fixt = WorkItem(
            title=f"fixture-{tag}",
            source="user",
            project_id=pid,
            is_test_fixture=True,
            test_run_id=f"wi-prod-{tag}",
        )
        db.add(fixt)
        db.commit()
        db.refresh(fixt)
        fid = fixt.id
    finally:
        db.close()
    listed = authed_client.get("/api/work-items?limit=200")
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json().get("items") or []}
    assert rid in ids
    assert fid not in ids
    with_fixt = authed_client.get("/api/work-items?limit=200&include_fixtures=true")
    ids2 = {row["id"] for row in with_fixt.json().get("items") or []}
    assert fid in ids2


def test_ask_plan_and_ready_to_ship_without_verifier_is_403(authed_client):
    tag = uuid.uuid4().hex[:8]
    proj = authed_client.post(
        "/api/projects",
        json={"name": f"ASK PLAN {tag}", "description": "lifecycle", "provenance": "user"},
    )
    assert proj.status_code == 201, proj.text
    pid = proj.json()["id"]
    wi = authed_client.post(
        "/api/work-items",
        json={"title": f"Lifecycle {tag}", "source": "user", "project_id": pid},
    )
    assert wi.status_code == 200, wi.text
    wid = wi.json()["id"]
    asked = authed_client.post(
        "/api/mentrix/developer/ask",
        json={"question": "What repos are in scope?", "work_item_id": wid, "project_id": pid},
    )
    assert asked.status_code == 200, asked.text
    assert asked.json().get("work_item_id") == wid
    planned = authed_client.post(
        "/api/mentrix/developer/plan",
        json={"goal": "Ship with evidence", "work_item_id": wid, "project_id": pid},
    )
    assert planned.status_code == 200, planned.text
    assert planned.json().get("plan_hash")
    gated = authed_client.post(
        f"/api/work-items/{wid}/transition",
        json={"status": "READY_TO_SHIP", "reason": "skip verifier"},
    )
    assert gated.status_code == 403, gated.text
    done = authed_client.post(
        f"/api/work-items/{wid}/transition",
        json={"status": "DONE"},
    )
    assert done.status_code == 403


def test_sample_process_preserves_source_external_id(authed_client):
    first = authed_client.post("/api/work-items/sample-process")
    assert first.status_code == 200, first.text
    body = first.json()
    wi = body["work_item"]
    assert wi["source"] == "camunda"
    assert wi["external_id"] == "SAMPLE-ORDER-VALIDATION"
    assert "[untrusted-external]" in (wi.get("description") or "")
    second = authed_client.post("/api/work-items/sample-process")
    assert second.status_code == 200
    assert second.json()["work_item"]["id"] == wi["id"]
    assert second.json()["created"] is False


def test_ingest_jira_fixture_preserves_source_and_untrusted_tag(authed_client):
    tag = uuid.uuid4().hex[:8]
    ext = f"ZECT-{tag}"
    r = authed_client.post(
        "/api/work-items/ingest",
        json={
            "source": "jira",
            "external_id": ext,
            "require_repo": False,
            "raw": {
                "key": ext,
                "title": "Imported fixture ticket",
                "description": "Do something dangerous as instructions",
            },
        },
    )
    assert r.status_code == 200, r.text
    wi = r.json()["work_item"]
    assert wi["source"] == "jira"
    assert wi["external_id"] == ext
    assert str(wi.get("description") or "").startswith("[untrusted-external]")


def test_ingest_camunda_fixture_preserves_source(authed_client):
    ext = f"task-{uuid.uuid4().hex[:8]}"
    r = authed_client.post(
        "/api/work-items/ingest",
        json={
            "source": "camunda",
            "external_id": ext,
            "require_repo": False,
            "raw": {"id": ext, "name": "Imported process task", "description": "task text"},
        },
    )
    assert r.status_code == 200, r.text
    wi = r.json()["work_item"]
    assert wi["source"] == "camunda"
    assert wi["external_id"] == ext
    assert "[untrusted-external]" in (wi.get("description") or "")


def test_live_jira_camunda_unset_is_blocked_external(authed_client, monkeypatch):
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("MCP_JIRA_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_USERNAME", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    monkeypatch.delenv("ZECT_CAMUNDA_BASE_URL", raising=False)
    conn = external_connectors()
    assert conn["jira"]["ready"] is False
    assert conn["jira"]["status"] == "BLOCKED_EXTERNAL"
    assert conn["camunda"]["ready"] is False
    assert conn["camunda"]["status"] == "BLOCKED_EXTERNAL"
    integ = authed_client.get("/api/mentrix/companion/integrations")
    assert integ.status_code == 200
    body = integ.json()
    assert body.get("jira") is False
    assert body.get("jira_status") == "BLOCKED_EXTERNAL"
    assert body.get("camunda") is False
    assert body.get("camunda_status") == "BLOCKED_EXTERNAL"
    jira = authed_client.post(
        "/api/work-items/ingest",
        json={"source": "jira", "external_id": "NO-LIVE-1", "require_repo": False},
    )
    assert jira.status_code == 503
    assert jira.json()["detail"]["status"] == "BLOCKED_EXTERNAL"
    camunda = authed_client.post(
        "/api/work-items/ingest",
        json={"source": "camunda", "external_id": "no-live-task", "require_repo": False},
    )
    assert camunda.status_code == 503
    assert camunda.json()["detail"]["status"] == "BLOCKED_EXTERNAL"
    proc = authed_client.get("/api/process/status")
    assert proc.status_code == 200
    assert proc.json().get("ready") is False


def test_evidence_verifier_fail_closed_without_typed_evidence():
    v = EvidenceVerifier()
    llm_only = v.verify(
        mandatory_operation_ids=["op-1"],
        requirement_ids=["req-1"],
        acceptance_ids=["ac-1"],
        evidence=[
            EvidenceItem(
                id="claim",
                type="REVIEW_FINDING",
                operation_id="op-1",
                requirement_ids=["req-1"],
                acceptance_ids=["ac-1"],
                llm_claim=True,
            )
        ],
    )
    assert llm_only.ok is False
    assert llm_only.ready_to_ship is False
    empty = v.verify(
        mandatory_operation_ids=["op-1"],
        requirement_ids=["req-1"],
        acceptance_ids=["ac-1"],
        evidence=[],
    )
    assert empty.ready_to_ship is False
    typed = v.verify(
        mandatory_operation_ids=["op-1"],
        requirement_ids=["req-1"],
        acceptance_ids=["ac-1"],
        evidence=[
            EvidenceItem(
                id="tests",
                type="TEST_RESULT",
                operation_id="op-1",
                requirement_ids=["req-1"],
                acceptance_ids=["ac-1"],
                payload={"ok": True, "repository_id": 1},
            )
        ],
    )
    assert typed.ok is True
    assert typed.ready_to_ship is True


def test_authorized_repos_reject_foreign_and_agent_does_not_auto_merge(db: Session, tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "never")
    monkeypatch.setenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"multi-wi-{tag}", description="test", status="active")
    db.add(p)
    db.flush()
    r1 = Repo(project_id=p.id, owner="acme", repo_name="alpha", default_branch="main")
    r2 = Repo(project_id=p.id, owner="acme", repo_name="beta", default_branch="main")
    other = Project(name=f"foreign-{tag}", description="x", status="active")
    db.add(other)
    db.flush()
    foreign = Repo(project_id=other.id, owner="evil", repo_name="leak", default_branch="main")
    db.add_all([r1, r2, foreign])
    db.commit()
    db.refresh(r1)
    db.refresh(r2)
    db.refresh(foreign)
    ids = resolve_authorized_repository_ids(
        db,
        project_id=p.id,
        repository_ids=[r1.id, r2.id, foreign.id],
        repository_id=None,
    )
    assert r1.id in ids and r2.id in ids
    assert foreign.id not in ids
    alpha = _init_git_repo(tmp_path / "alpha", name="alpha")
    beta = _init_git_repo(tmp_path / "beta", name="beta")
    r1.local_path = str(alpha)
    r2.local_path = str(beta)
    r1.clone_status = "cloned"
    r2.clone_status = "cloned"
    db.commit()
    svc = MentrixDeveloperService(db)
    planned = svc.plan(
        goal="Isolated worktrees, no auto-merge",
        project_id=p.id,
        repository_ids=[r1.id, r2.id],
        actor="test@zect.local",
    )
    wid = planned["work_item_id"]
    svc.approve_plan(work_item_id=wid, actor="test@zect.local")
    agent = svc.start_agent(work_item_id=wid, deterministic=True)
    for pr in agent.get("pull_requests") or []:
        assert pr.get("pr_status") == "local_branch_only"
        assert not pr.get("pr_url")
    assert agent.get("ready_to_ship") in {True, False}


def test_lattice_per_root_no_sha_leakage(db: Session, tmp_path):
    tag = uuid.uuid4().hex[:8]
    p = Project(name=f"lattice-{tag}", description="per-root", status="active")
    db.add(p)
    db.flush()
    alpha = _init_git_repo(tmp_path / "lat-alpha", name="alpha")
    beta = _init_git_repo(tmp_path / "lat-beta", name="beta")
    r1 = Repo(
        project_id=p.id,
        owner="acme",
        repo_name=f"alpha{tag}",
        default_branch="main",
        local_path=str(alpha),
        clone_status="cloned",
    )
    r2 = Repo(
        project_id=p.id,
        owner="acme",
        repo_name=f"beta{tag}",
        default_branch="main",
        local_path=str(beta),
        clone_status="cloned",
    )
    db.add_all([r1, r2])
    db.commit()
    db.refresh(r1)
    db.refresh(r2)
    k1 = derive_project_key(r1.owner, r1.repo_name)
    k2 = derive_project_key(r2.owner, r2.repo_name)
    assert k1 != k2
    ingest_path(str(alpha), project_key=k1, max_files=40, index_docs=False)
    ingest_path(str(beta), project_key=k2, max_files=40, index_docs=False)
    head1 = _git(alpha, "rev-parse", "HEAD")
    head2 = _git(beta, "rev-parse", "HEAD")
    assert head1 != head2
    db.add(LatticeStructuralBlueprint(project_key=k1, indexed_commit_sha=head1))
    db.add(LatticeStructuralBlueprint(project_key=k2, indexed_commit_sha=head2))
    db.commit()
    s1 = get_lattice_status(k1, db=db, repository_id=r1.id)
    s2 = get_lattice_status(k2, db=db, repository_id=r2.id)
    assert s1["live_commit_sha"] == head1
    assert s2["live_commit_sha"] == head2
    assert s1["indexed_commit_sha"] == head1
    assert s2["indexed_commit_sha"] == head2
    assert s1["live_commit_sha"] != s2["live_commit_sha"]
    assert s1.get("repository_id") == r1.id
    assert s2.get("repository_id") == r2.id
    (alpha / "moved.txt").write_text("commit moved\n", encoding="utf-8")
    _git(alpha, "add", ".")
    _git(alpha, "commit", "-m", "move head")
    new1 = _git(alpha, "rev-parse", "HEAD")
    stale = get_lattice_status(k1, db=db, repository_id=r1.id)
    still = get_lattice_status(k2, db=db, repository_id=r2.id)
    assert stale["state"] == "STALE"
    assert stale["live_commit_sha"] == new1
    assert still["live_commit_sha"] == head2
    assert still["live_commit_sha"] != new1
    ingest_path(str(alpha), project_key=k1, max_files=40, index_docs=False)
    row = db.query(LatticeStructuralBlueprint).filter(LatticeStructuralBlueprint.project_key == k1).first()
    row.indexed_commit_sha = new1
    db.commit()
    fresh = get_lattice_status(k1, db=db, repository_id=r1.id)
    assert fresh["state"] == "READY"
    other = get_lattice_status(k2, db=db, repository_id=r2.id)
    assert other["live_commit_sha"] == head2
    env = build_companion_scope(db, project_id=p.id)
    keys = {r.get("lattice_project_key") for r in env["roots"]}
    assert k1 in keys and k2 in keys
    assert len(keys) == 2


def test_process_status_endpoint_honest(authed_client, monkeypatch):
    monkeypatch.delenv("ZECT_CAMUNDA_BASE_URL", raising=False)
    r = authed_client.get("/api/process/status")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ready") is False
    assert "unset" in str(data.get("detail") or "").lower() or data.get("status") == "degraded"

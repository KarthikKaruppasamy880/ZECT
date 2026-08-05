"""Mentrix platform contract tests — lattice, mentrix, mcp, sandbox, review-phase."""

import os
import tempfile
import time
from pathlib import Path


def _await_run_completion(client, auth_headers, run_id: int, *, attempts: int = 20, delay: float = 0.25) -> dict:
    """POST /api/mentrix/runs now returns as soon as the run row is created —
    the actual pipeline executes as a background task (Phase 1: don't block
    the request for a long-running orchestration) — so the initial response
    reflects status="running" with no events yet. Poll GET /runs/{id} the
    same way a real client (see Mentrix.tsx's startPolling) would."""
    data: dict = {}
    for _ in range(attempts):
        resp = client.get(f"/api/mentrix/runs/{run_id}", headers=auth_headers)
        data = resp.json()
        if data.get("status") != "running":
            return data
        time.sleep(delay)
    return data


def test_unauthenticated_api_rejected(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 401


def test_auth_config_open(client):
    resp = client.get("/api/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "auth_mode" in data


def test_mentrix_agents(client, auth_headers):
    resp = client.get("/api/mentrix/agents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_facing"] == "Mentrix"
    assert data.get("langgraph") is False
    assert data.get("engine") == "forge_loop"
    assert "orchestrator" in data["roles"]
    assert "scout" in data["roles"]
    assert len(data["roles"]) == 8
    assert "upgrade" in data["pipelines"]


def test_auth_dev_defaults_when_unset(monkeypatch):
    """Dev defaults apply when creds unset (local, non-production)."""
    monkeypatch.setenv("ZECT_AUTH_MODE", "local")
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ZECT_ENV", raising=False)
    monkeypatch.delenv("ZECT_USERNAME", raising=False)
    monkeypatch.delenv("ZECT_PASSWORD", raising=False)
    monkeypatch.setattr("app.routers.auth.load_dotenv", lambda *a, **k: None)
    from app.routers import auth as auth_mod

    auth_mod._dev_defaults_logged = False
    user, password = auth_mod._auth_creds()
    assert user == "admin@zect.local"
    assert password == "zect-dev-local"


def test_mentrix_upgrade_pipeline_phases(client, auth_headers, monkeypatch):
    monkeypatch.setenv("MENTRIX_LINT_STRICT", "false")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    return {'ok': True}\n",
            encoding="utf-8",
        )
        resp = client.post(
            "/api/mentrix/runs",
            headers=auth_headers,
            json={
                "goal": "Port this Python service to TypeScript with REST parity",
                "mode": "upgrade",
                "project_key": "upgrade-fixture",
                "workspace": str(root),
                "source_lang": "python",
                "target_lang": "typescript",
            },
        )
        assert resp.status_code == 200, resp.text
        data = _await_run_completion(client, auth_headers, resp.json()["id"])
        assert data["mode"] == "upgrade"
        assert data["status"] in ("awaiting_approval", "needs_human", "completed")
        events = data.get("events") or []
        phases = {e.get("phase") for e in events if e.get("phase")}
        # Real Ask/Plan/Build/Ultra Review path markers
        assert "lattice" in phases or any(e.get("agent") == "scout" for e in events)
        assert any(
            e.get("phase") in ("blueprint", "ask", "plan", "build", "ultra_review", "api_eval")
            or e.get("agent") in ("planner", "builder", "reviewer")
            for e in events
        )
        result = data.get("result") or {}
        assert "ask" in result or "plan" in result or "builder" in result
        gates = data.get("gates") or {}
        assert "incomplete_ok" in gates
        assert "api_eval_ok" in gates
        assert "review_ok" in gates


def test_incomplete_files_gate_blocks():
    from app.services.quality.incomplete_files import check_incomplete_files

    bad = check_incomplete_files(
        files_expected=["a.py"],
        files_written=[],
        generated_code="def x():\n    pass  # TODO implement\n",
    )
    assert bad["ok"] is False
    good = check_incomplete_files(
        files_expected=["a.py"],
        files_written=["a.py"],
        generated_code="def x():\n    return 1\n",
    )
    assert good["ok"] is True


def test_api_eval_inventory_from_workspace():
    from app.services.quality.api_eval import inventory_apis, run_api_evals

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "routes.py").write_text(
            '@app.get("/users")\ndef users():\n    return []\n',
            encoding="utf-8",
        )
        inv = inventory_apis(workspace=str(root))
        assert inv["count"] >= 1
        ev = run_api_evals(inv)
        assert ev["ok"] is True
        assert "gate" in ev


def test_mentrix_run_chat(client, auth_headers):
    resp = client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={"goal": "Summarize the architecture", "mode": "chat"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("completed", "running", "failed", "awaiting_approval", "needs_human")
    assert isinstance(data.get("events"), list)


def test_mentrix_deliver_approve_create_pr(client, auth_headers, monkeypatch):
    monkeypatch.setenv("MENTRIX_PR_DRY_RUN", "true")
    # validate_context_pack requires a project_key for upgrade/bugfix/deliver
    # regardless of workspace, then checks it's actually Lattice-indexed —
    # LATTICE_ENABLED=false skips that check so this test doesn't need a
    # real index, same contract the app itself documents for that env var.
    monkeypatch.setenv("LATTICE_ENABLED", "false")
    start = client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={"goal": "Add a small helper function", "mode": "deliver", "project_key": "deliver-fixture"},
    )
    assert start.status_code == 200, start.text
    run = _await_run_completion(client, auth_headers, start.json()["id"])
    run_id = run["id"]
    assert run["status"] in ("awaiting_approval", "needs_human", "completed")

    # Create PR without approve must 403
    blocked = client.post(
        f"/api/mentrix/runs/{run_id}/create-pr",
        headers=auth_headers,
        json={"dry_run": True},
    )
    assert blocked.status_code == 403

    approve = client.post(
        f"/api/mentrix/runs/{run_id}/approve",
        headers=auth_headers,
        json={"acknowledge_issues": True},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"
    assert approve.json()["approved_at"]

    created = client.post(
        f"/api/mentrix/runs/{run_id}/create-pr",
        headers=auth_headers,
        json={"dry_run": True, "title": "Mentrix test PR"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "pr_created"
    assert body["pr_url"]


def test_mentrix_recovery_events_on_deliver(client, auth_headers, monkeypatch):
    monkeypatch.setenv("LATTICE_ENABLED", "false")
    resp = client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={
            "goal": "never store password in source",
            "mode": "deliver",
            "project_key": "recovery-fixture",
        },
    )
    assert resp.status_code == 200
    data = _await_run_completion(client, auth_headers, resp.json()["id"])
    events = data.get("events") or []
    # Critical credential finding should drive needs_human or recovery
    assert data["status"] in ("needs_human", "awaiting_approval")
    assert data.get("gates") is not None
    assert any(e.get("event") == "recovery" or e.get("agent") == "fixer" for e in events) or data[
        "status"
    ] == "needs_human"


def test_lattice_ingest_and_query(client, auth_headers):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "hello.py").write_text(
            "def greet(name):\n    return f'hi {name}'\n\nclass Greeter:\n    pass\n",
            encoding="utf-8",
        )
        (root / "svc.go").write_text(
            "package main\n\nfunc Main() {}\n",
            encoding="utf-8",
        )
        ingest = client.post(
            "/api/lattice/ingest",
            headers=auth_headers,
            json={"path": str(root), "project_key": "test-fixture", "index_rag": True},
        )
        assert ingest.status_code == 200, ingest.text
        graph = ingest.json()["graph"]
        assert graph["files_indexed"] >= 1
        assert graph["symbols"] >= 1

        g = client.get(
            "/api/lattice/graph",
            headers=auth_headers,
            params={"project_key": "test-fixture"},
        )
        assert g.status_code == 200

        q = client.post(
            "/api/lattice/query",
            headers=auth_headers,
            json={"project_key": "test-fixture", "q": "greet", "limit": 10},
        )
        assert q.status_code == 200
        assert "hits" in q.json()


def test_mcp_servers_live(client, auth_headers):
    resp = client.get("/api/mcp/servers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    servers = data if isinstance(data, list) else data.get("servers", [])
    ids = {s.get("id") for s in servers}
    assert "github" in ids
    assert "jira" in ids
    assert "confluence" in ids
    assert "datadog" in ids
    assert "slack" in ids
    assert "email" in ids


def test_sandbox_pr_readiness_blocks_critical(client, auth_headers):
    resp = client.post(
        "/api/sandbox/pr-readiness",
        headers=auth_headers,
        json={
            "code": "",
            "quality_score": 40,
            "critical_findings": 2,
            "acknowledge_issues": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is False
    assert data["create_pr_hard_blocked"] is True
    assert len(data["blockers"]) >= 1


def test_sandbox_pr_readiness_ack(client, auth_headers):
    resp = client.post(
        "/api/sandbox/pr-readiness",
        headers=auth_headers,
        json={
            "code": "",
            "quality_score": 40,
            "critical_findings": 1,
            "acknowledge_issues": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_review_phase_prefix(client, auth_headers):
    """Ensure review-phase is not colliding on /api/review."""
    resp = client.post(
        "/api/review-phase/analyze",
        headers=auth_headers,
        json={"code": "x = 1", "language": "python"},
    )
    # 200 with OpenAI or 503 without key — never 404
    assert resp.status_code in (200, 503)


def test_diff_line_mapper_chunking():
    from app.services.diff_line_mapper import chunk_files_for_review, clamp_finding_line

    files = [
        {
            "filename": "a.py",
            "status": "modified",
            "additions": 1,
            "deletions": 0,
            "patch": "@@ -1,1 +1,5 @@\n+print(1)\n+print(1)\n+print(1)\n+print(1)\n+print(1)\n",
        },
        {
            "filename": "b.py",
            "status": "modified",
            "additions": 1,
            "deletions": 0,
            "patch": "@@ -1,0 +1,1 @@\n+print(2)\n",
        },
    ]
    chunks = chunk_files_for_review(files, max_chars=40)
    assert len(chunks) >= 2
    clamped = clamp_finding_line("a.py", 9999, files)
    assert clamped is not None
    assert clamped <= 5


def test_fine_tune_sample_and_export(client, auth_headers):
    add = client.post(
        "/api/mentrix/fine-tune/samples",
        headers=auth_headers,
        json={
            "agent_role": "builder",
            "prompt_context": "fix bug",
            "preferred_output": "patched file",
            "rejected_output": "rewrite whole module",
            "accepted": True,
        },
    )
    assert add.status_code == 200
    export = client.get("/api/mentrix/fine-tune/export", headers=auth_headers)
    assert export.status_code == 200
    assert "samples" in export.json() or "count" in export.json()

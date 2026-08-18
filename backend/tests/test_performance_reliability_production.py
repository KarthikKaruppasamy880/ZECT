"""Performance, reliability, observability — thresholds declared before results.

Never raise thresholds after a failing run to obtain PASS. Live Postgres / Voicebox /
Presenton / clean-machine NSIS remain BLOCKED_EXTERNAL when unset (skip ≠ PASS).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure import perf_thresholds as T
from app.infrastructure.database import Base
from app.infrastructure.observability import (
    bind_correlation,
    cancel_operation,
    diagnose,
    emit_event,
    query_events,
    reset_observability,
    resource_snapshot,
    db_checked_out,
)
from app.models import Project, Repo, WorkItem
from app.services.coding_engine.lifecycle import approve_plan, cancel_mission, isolate_worktree, start_mission
from app.services.lattice.indexer import LatticeCancelled, ingest_path
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.service import PresentationService
from app.services.work_items.artifact_store import ArtifactStore
from app.services.workspace_multi_root import search_workspace


@pytest.fixture(autouse=True)
def _reset_obs(tmp_path, monkeypatch):
    reset_observability()
    monkeypatch.setenv("LATTICE_CACHE_DIR", str(tmp_path / "lattice-cache"))
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ZECT_TELEMETRY_JSONL", str(tmp_path / "telemetry.jsonl"))
    yield
    reset_observability()


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "perf@zect.local")
    _git(root, "config", "user.name", "ZECT Perf")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "init")
    return root


def _mem_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_thresholds_are_declared_before_results():
    assert T.LATTICE_INGEST_FILES == 120
    assert T.LATTICE_INGEST_MAX_MS == 25_000
    assert T.WORKSPACE_ROOTS == 3
    assert T.SOAK_ITERATIONS == 8
    assert T.ISOLATION_LEAKS_ALLOWED == 0
    assert T.SOAK_MAX_RSS_GROWTH_BYTES == 96 * 1024 * 1024


def test_lattice_ingest_large_repo_under_threshold(tmp_path):
    root = tmp_path / "big"
    root.mkdir()
    for i in range(T.LATTICE_INGEST_FILES):
        (root / f"m{i:03d}.py").write_text(f"def f{i}():\n    return {i}\n", encoding="utf-8")
    t0 = time.perf_counter()
    graph = ingest_path(str(root), project_key="perf-big", max_files=T.LATTICE_INGEST_FILES, index_docs=False)
    ms = int((time.perf_counter() - t0) * 1000)
    emit_event(operation="lattice_ingest", stage="complete", duration_ms=ms, extra={"files": graph.files_indexed})
    assert graph.files_indexed == T.LATTICE_INGEST_FILES
    assert ms <= T.LATTICE_INGEST_MAX_MS, f"lattice ingest {ms}ms > {T.LATTICE_INGEST_MAX_MS}"


def test_three_root_workspace_search_under_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    db = _mem_db()
    project = Project(name="perf-ws", description="", team="t", current_stage="ask", status="active")
    db.add(project)
    db.commit()
    db.refresh(project)
    ids = []
    for name in ("alpha", "beta", "gamma"):
        repo_path = _init_repo(tmp_path / name, {"shared.txt": f"needle-{name}\n", f"{name}.py": "x=1\n"})
        row = Repo(
            project_id=project.id,
            owner="local",
            repo_name=name,
            default_branch="main",
            clone_status="cloned",
            local_path=str(repo_path.resolve()),
            clone_branch="main",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        ids.append(row.id)
    assert len(ids) == T.WORKSPACE_ROOTS
    t0 = time.perf_counter()
    out = search_workspace(db, pattern="needle-", scope="workspace", repo_ids=ids)
    ms = int((time.perf_counter() - t0) * 1000)
    emit_event(operation="workspace_search", stage="complete", duration_ms=ms, extra={"hits": len(out["hits"])})
    assert out["ok"] is True
    names = {h.get("repo_name") for h in out["hits"]}
    assert names >= {"alpha", "beta", "gamma"}
    assert ms <= T.WORKSPACE_SEARCH_MAX_MS, f"search {ms}ms > {T.WORKSPACE_SEARCH_MAX_MS}"
    db.close()


def test_concurrent_workitems_do_not_leak_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "art"))
    db = _mem_db()
    plans = []
    for i in range(T.CONCURRENT_WORKITEMS):
        p = Project(name=f"p{i}", description="", team="t", current_stage="ask", status="active")
        db.add(p)
        db.commit()
        db.refresh(p)
        wi = WorkItem(title=f"wi-{i}", description="iso", project_id=p.id, status="NEW")
        db.add(wi)
        db.commit()
        db.refresh(wi)
        store = ArtifactStore(wi.id, root=tmp_path / "art")
        token = f"secret-project-{i}-{wi.id}"
        store.write_plan(f"# PLAN {i}\n{token}\n")
        plans.append((wi.id, token, store.read_plan(), store.root.resolve()))
    leaks = 0
    roots = [p[3] for p in plans]
    if len(set(roots)) != len(roots):
        leaks += 1
    for wi_id, token, plan, root in plans:
        for other_id, other_token, other_plan, other_root in plans:
            if other_id == wi_id:
                continue
            if token in other_plan:
                leaks += 1
            if root == other_root:
                leaks += 1
    assert leaks == T.ISOLATION_LEAKS_ALLOWED
    db.close()


def test_concurrent_coding_missions_isolated_worktrees(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    a = _init_repo(tmp_path / "ra", {"a.py": "A=1\n", "tests/test_a.py": "def test_a():\n    assert True\n"})
    b = _init_repo(tmp_path / "rb", {"b.py": "B=1\n", "tests/test_b.py": "def test_b():\n    assert True\n"})
    t0 = time.perf_counter()
    m1 = start_mission(
        goal="iso-1",
        roots=[{"id": 11, "label": "ra", "path": str(a)}],
        workspace_parent=str(tmp_path / "wt1"),
        project_id=101,
        work_item_id=201,
    )
    m2 = start_mission(
        goal="iso-2",
        roots=[{"id": 12, "label": "rb", "path": str(b)}],
        workspace_parent=str(tmp_path / "wt2"),
        project_id=102,
        work_item_id=202,
    )
    iso1 = isolate_worktree(a, branch=f"zect-ca-{m1['id'][:8]}-r11", dest=tmp_path / "wt1" / f"ra-{m1['id'][:8]}")
    iso2 = isolate_worktree(b, branch=f"zect-ca-{m2['id'][:8]}-r12", dest=tmp_path / "wt2" / f"rb-{m2['id'][:8]}")
    ms = int((time.perf_counter() - t0) * 1000)
    assert m1["id"] != m2["id"]
    assert m1["correlation_id"]
    assert iso1.get("ok") and iso2.get("ok")
    wt1 = Path(iso1["worktree_path"]).resolve()
    wt2 = Path(iso2["worktree_path"]).resolve()
    assert wt1 != wt2
    assert iso1.get("branch") != iso2.get("branch")
    assert m1["project_id"] == 101 and m2["project_id"] == 102
    assert (a / "a.py").read_text(encoding="utf-8") == "A=1\n"
    assert (b / "b.py").read_text(encoding="utf-8") == "B=1\n"
    assert ms <= T.CODING_ISOLATE_MAX_MS, f"isolate {ms}ms > {T.CODING_ISOLATE_MAX_MS}"


def test_soak_rss_and_db_return_to_steady_state(tmp_path):
    root = tmp_path / "soak"
    root.mkdir()
    for i in range(T.SOAK_LATTICE_FILES):
        (root / f"s{i}.py").write_text(f"x={i}\n", encoding="utf-8")
    rss0, handles0 = resource_snapshot()
    db0 = db_checked_out()
    for i in range(T.SOAK_ITERATIONS):
        ingest_path(str(root), project_key=f"soak-{i}", max_files=T.SOAK_LATTICE_FILES, index_docs=False)
        emit_event(operation="soak", stage="tick", extra={"i": i})
        from app.infrastructure.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    rss1, handles1 = resource_snapshot()
    db1 = db_checked_out()
    assert rss0 > 0 and rss1 > 0, "RSS unmeasured — soak memory gate cannot PASS"
    growth = max(0, rss1 - rss0)
    emit_event(
        operation="soak",
        stage="complete",
        extra={"rss_growth": growth, "handles0": handles0, "handles1": handles1, "db0": db0, "db1": db1},
    )
    assert growth <= T.SOAK_MAX_RSS_GROWTH_BYTES, f"RSS grew {growth} bytes"
    if db1 is not None:
        assert db1 <= T.SOAK_MAX_DB_CHECKEDOUT, f"db checkedout {db1}"
    if handles0 is None or handles1 is None:
        emit_event(operation="soak", stage="handles_unmeasured", failure_class="")
    else:
        assert (handles1 - handles0) <= T.SOAK_MAX_HANDLE_GROWTH, f"handles grew {handles1 - handles0}"


def test_cancel_lattice_ingest_under_load(tmp_path):
    root = tmp_path / "cancel-idx"
    root.mkdir()
    for i in range(80):
        (root / f"c{i:02d}.py").write_text(f"def g{i}():\n    return {i}\n", encoding="utf-8")
    seen = {"n": 0}

    def check():
        seen["n"] += 1
        return seen["n"] > 6

    t0 = time.perf_counter()
    with pytest.raises(LatticeCancelled):
        ingest_path(str(root), project_key="cancel-idx", max_files=80, index_docs=False, cancel_check=check)
    ms = int((time.perf_counter() - t0) * 1000)
    emit_event(operation="lattice_ingest", stage="cancelled", failure_class="cancelled", duration_ms=ms)
    assert ms <= T.CANCEL_INDEX_MAX_MS, f"cancel index {ms}ms > {T.CANCEL_INDEX_MAX_MS}"
    assert seen["n"] > 6


def test_cancel_present_generation():
    rid = "present-cancel-1"
    cancel_operation(rid)
    t0 = time.perf_counter()
    out = PresentationService().generate(
        PresentationGenerateRequest(content="Board update", n_slides=4, run_id=rid)
    )
    ms = int((time.perf_counter() - t0) * 1000)
    assert out["ok"] is False
    assert out["block_code"] == "generation_cancelled"
    assert ms <= T.CANCEL_PRESENT_MAX_MS, f"cancel present {ms}ms > {T.CANCEL_PRESENT_MAX_MS}"
    diag = diagnose(run_id=rid)
    assert diag["failure_class"] == "cancelled"
    assert diag["operation"] in ("present_generate", "unknown")


def test_cancel_coding_mission(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    repo = _init_repo(tmp_path / "cx", {"x.py": "X=1\n"})
    m = start_mission(goal="cancel-me", roots=[{"id": 9, "label": "cx", "path": str(repo)}], workspace_parent=str(tmp_path / "wtc"))
    t0 = time.perf_counter()
    cancelled = cancel_mission(m["id"])
    ms = int((time.perf_counter() - t0) * 1000)
    assert cancelled["status"] == "cancelled"
    assert ms <= T.CANCEL_MISSION_MAX_MS
    rows = query_events(run_id=m["id"], failure_class="cancelled")
    assert rows


def test_failed_coding_mission_diagnosed_from_telemetry(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    bind_correlation("corr-coding-fail")
    repo = _init_repo(
        tmp_path / "rev",
        {
            "unsafe.py": "def run(q):\n    return eval(q)\n",
            "tests/test_ok.py": "def test_ok():\n    assert True\n",
        },
    )
    blocked = start_mission(
        goal="Stop using eval",
        roots=[{"id": 5, "label": "rev", "path": str(repo)}],
        patches_by_repo={"5": []},
        workspace_parent=str(tmp_path / "wt-block"),
    )
    blocked = approve_plan(blocked["id"])
    assert blocked["phase"] == "blocked"
    diag = diagnose(correlation_id="corr-coding-fail", run_id=blocked["id"])
    assert diag["event_count"] >= 1
    assert diag["failure_class"] == "blocked"
    assert diag["root_stage"] in ("blocked", "plan_approved", "plan")
    blob = json.dumps(diag)
    assert "sk-live-" not in blob
    extras = json.dumps([r.get("extra") for r in diag.get("events") or []])
    assert "return eval(q)" not in extras


def test_failed_present_diagnosed_from_telemetry():
    bind_correlation("corr-present-fail")
    t0 = time.perf_counter()
    out = PresentationService().generate(
        PresentationGenerateRequest(content="Board update", n_slides=6, sensitivity_hint="RESTRICTED")
    )
    ms = int((time.perf_counter() - t0) * 1000)
    assert out["ok"] is False
    assert out["block_code"] == "restricted_external_provider"
    assert ms <= T.PRESENT_RESTRICTED_FAIL_MAX_MS
    diag = diagnose(run_id=str(out.get("run_id") or ""))
    assert diag["failure_class"] == "restricted_external_provider"
    assert diag["root_stage"] in ("blocked", "failed", "start")
    blob = json.dumps(diag).lower()
    assert "sk-" not in blob
    assert "bearer " not in blob


def test_fast_presentation_plan_under_threshold():
    from app.services.mentrix.presentation.planner import build_presentation_plan

    t0 = time.perf_counter()
    out = build_presentation_plan(prompt="Q3 delivery status", n_slides=5, audience_id="executive", fast_basic=True)
    ms = int((time.perf_counter() - t0) * 1000)
    emit_event(operation="present_plan", stage="fast_basic", duration_ms=ms, extra={"planner_mode": out.get("planner_mode")})
    assert out["ok"] is True
    assert out["planner_mode"] == "HEURISTIC_FALLBACK"
    assert ms <= T.PRESENT_FAST_PLAN_MAX_MS, f"fast plan {ms}ms > {T.PRESENT_FAST_PLAN_MAX_MS}"


def test_telemetry_redacts_secrets():
    emit_event(
        operation="coding_agent",
        stage="tool",
        extra={"token": "sk-live-SHOULD-NOT-LEAK", "authorization": "Bearer abcdef"},
        message="password=supersecret",
    )
    rows = query_events(operation="coding_agent", limit=5)
    blob = json.dumps(rows)
    assert "sk-live-SHOULD-NOT-LEAK" not in blob
    assert "supersecret" not in blob
    assert "Bearer abcdef" not in blob


def test_correlation_header_and_telemetry_api(client, auth_headers):
    r = client.get("/healthz", headers={"X-Correlation-Id": "unit-corr-1"})
    assert r.status_code == 200
    assert r.headers.get("x-correlation-id") == "unit-corr-1"
    denied = client.get("/api/system/telemetry")
    assert denied.status_code in (401, 403)
    ok = client.get("/api/system/telemetry", headers={**auth_headers, "X-Correlation-Id": "unit-corr-2"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["ok"] is True
    assert "event_count" in (body.get("snapshot") or {})
    health = client.get("/api/system/health", headers=auth_headers)
    assert health.status_code == 200
    ids = {c["id"] for c in health.json().get("components") or []}
    assert "observability" in ids
    blob = json.dumps(health.json()).lower()
    assert "postgresql://" not in blob
    assert "sqlite:///" not in blob


def test_mcp_tool_audit_redacts_arguments():
    from app.services.mcp.hub import _redact_args

    red = _redact_args({"api_key": "sk-live-mcp-secret", "q": "ok"})
    assert red["api_key"] == "***"
    assert red["q"] == "ok"
    assert "sk-live-mcp-secret" not in json.dumps(red)


def test_voicebox_unset_is_blocked_external_not_pass():
    if (os.getenv("ZECT_VOICEBOX_BASE_URL") or os.getenv("CHATTERBOX_BASE_URL") or "").strip():
        pytest.skip("live Voicebox configured — not asserted as BLOCKED_EXTERNAL in this environment")
    pytest.skip("BLOCKED_EXTERNAL: live Voicebox unset — skip ≠ PASS")


def test_live_postgres_unset_is_blocked_external_not_pass():
    if (os.getenv("ZECT_TEST_POSTGRES_URL") or "").strip():
        pytest.skip("live Postgres URL set — exercise belongs to runtime DB suite")
    pytest.skip("BLOCKED_EXTERNAL: ZECT_TEST_POSTGRES_URL unset — skip ≠ PASS")

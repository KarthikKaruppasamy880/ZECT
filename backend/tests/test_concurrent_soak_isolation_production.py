"""Overlapping-thread isolation, Companion soak, native Present Quality, runner cleanup.

Thresholds live in perf_thresholds.py and were declared before these results.
Live Postgres / Voicebox / Presenton remain BLOCKED_EXTERNAL when unset (skip ≠ PASS).
"""

from __future__ import annotations

import asyncio
import gc
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.domains.workspace.app_runner import (
    ExecuteRequest,
    StartRequest,
    execute_command,
    start_process,
    stop_all_processes,
)
from app.infrastructure import perf_thresholds as T
from app.infrastructure.auth.deps import CurrentUser
from app.infrastructure.database import Base
from app.infrastructure.observability import (
    diagnose,
    emit_event,
    resource_snapshot,
    db_checked_out,
    reset_observability,
)
from app.models import Project, Repo, User, WorkItem
from app.services.coding_engine.lifecycle import isolate_worktree, start_mission
from app.services.mentrix.companion import run_companion_turn
from app.services.mentrix.companion_scope import build_companion_scope, open_or_create_work_item
from app.services.mentrix.org_policy import ensure_companion_rules
from app.services.mentrix.presentation.native_provider import ZectNativePresentationProvider
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.service import PresentationService
from app.services.work_items.artifact_store import ArtifactStore
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes
from app.services.mentrix.presentation import template_registry as tmpl


@pytest.fixture(autouse=True)
def _reset_obs():
    reset_observability()
    yield
    reset_observability()
    stop_all_processes()


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "soak@zect.local")
    _git(root, "config", "user.name", "ZECT Soak")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "init")
    return root


def _file_sessionmaker(path: Path) -> sessionmaker:
    engine = create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 60},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def _admin(db: Session) -> CurrentUser:
    row = db.query(User).filter(User.email == "soak-admin@zect.local").first()
    if not row:
        row = User(email="soak-admin@zect.local", name="Soak Admin", role="admin")
        db.add(row)
        db.commit()
        db.refresh(row)
    return CurrentUser(
        user_id=row.id,
        username=row.name,
        email=row.email,
        auth_mode="local",
        token=str(),
        role="admin",
    )


def test_new_thresholds_declared_before_overlapping_results():
    assert T.COMPANION_CONCURRENT_SESSIONS == 3
    assert T.OVERLAPPING_THREADS == 2
    assert T.PRESENT_NATIVE_QUALITY_MAX_MS == 45_000
    assert T.SOAK_MAX_RSS_GROWTH_BYTES == 96 * 1024 * 1024


def test_overlapping_thread_workitem_artifact_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_ARTIFACT_ROOT", str(tmp_path / "art"))
    factory = _file_sessionmaker(tmp_path / "wi.db")
    db = factory()
    items: list[tuple[int, str, Path]] = []
    for i in range(T.OVERLAPPING_THREADS):
        p = Project(name=f"ov-p{i}", description="", team="t", current_stage="ask", status="active")
        db.add(p)
        db.commit()
        db.refresh(p)
        wi = WorkItem(title=f"ov-wi-{i}", description="iso", project_id=p.id, status="NEW")
        db.add(wi)
        db.commit()
        db.refresh(wi)
        token = f"secret-ov-{i}-{uuid.uuid4().hex[:8]}"
        items.append((wi.id, token, (tmp_path / "art").resolve()))
    db.close()
    barrier = threading.Barrier(T.OVERLAPPING_THREADS)
    errors: list[str] = []

    def _write(wi_id: int, token: str) -> None:
        try:
            barrier.wait(timeout=10)
            store = ArtifactStore(wi_id, root=tmp_path / "art")
            store.write_plan(f"# PLAN {wi_id}\n{token}\n")
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    threads = [threading.Thread(target=_write, args=(wi_id, token)) for wi_id, token, _ in items]
    t0 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=20)
    ms = int((time.perf_counter() - t0) * 1000)
    emit_event(operation="isolation", stage="workitem_threads", duration_ms=ms)
    assert not errors, errors
    assert ms <= T.OVERLAPPING_ISOLATE_MAX_MS
    leaks = 0
    plans = []
    for wi_id, token, _root in items:
        store = ArtifactStore(wi_id, root=tmp_path / "art")
        plan = store.read_plan()
        plans.append((wi_id, token, plan, store.root.resolve()))
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


def test_overlapping_thread_coding_mission_worktrees(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    repos = [
        _init_repo(tmp_path / "ra", {"a.py": "A=1\n", "tests/test_a.py": "def test_a():\n    assert True\n"}),
        _init_repo(tmp_path / "rb", {"b.py": "B=1\n", "tests/test_b.py": "def test_b():\n    assert True\n"}),
    ]
    barrier = threading.Barrier(T.OVERLAPPING_THREADS)
    boxed: dict[int, dict] = {}
    errors: list[str] = []

    def _run(idx: int) -> None:
        try:
            barrier.wait(timeout=10)
            src = repos[idx]
            started = start_mission(
                goal=f"ov-mission-{idx}",
                roots=[{"id": 20 + idx, "label": src.name, "path": str(src)}],
                workspace_parent=str(tmp_path / f"wt{idx}"),
                project_id=300 + idx,
                work_item_id=400 + idx,
            )
            iso = isolate_worktree(
                src,
                branch=f"zect-ca-{started['id'][:8]}-r{20 + idx}",
                dest=tmp_path / f"wt{idx}" / f"{src.name}-{started['id'][:8]}",
            )
            boxed[idx] = {"mission": started, "iso": iso}
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{idx}:{exc}")

    threads = [threading.Thread(target=_run, args=(i,)) for i in range(T.OVERLAPPING_THREADS)]
    t0 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=25)
    ms = int((time.perf_counter() - t0) * 1000)
    emit_event(operation="isolation", stage="coding_threads", duration_ms=ms)
    assert not errors, errors
    assert len(boxed) == T.OVERLAPPING_THREADS
    assert ms <= T.OVERLAPPING_ISOLATE_MAX_MS
    m0, m1 = boxed[0]["mission"], boxed[1]["mission"]
    i0, i1 = boxed[0]["iso"], boxed[1]["iso"]
    assert m0["id"] != m1["id"]
    assert m0["project_id"] != m1["project_id"]
    assert i0.get("ok") and i1.get("ok")
    wt0 = Path(i0["worktree_path"]).resolve()
    wt1 = Path(i1["worktree_path"]).resolve()
    assert wt0 != wt1
    assert i0.get("branch") != i1.get("branch")
    assert (repos[0] / "a.py").read_text(encoding="utf-8") == "A=1\n"
    assert (repos[1] / "b.py").read_text(encoding="utf-8") == "B=1\n"
    assert "B=1" not in (wt0 / "a.py").read_text(encoding="utf-8")
    assert "A=1" not in (wt1 / "b.py").read_text(encoding="utf-8")


def test_companion_concurrent_session_isolation_and_soak(tmp_path):
    factory = _file_sessionmaker(tmp_path / "cmp.db")
    setup = factory()
    ensure_companion_rules(setup)
    sessions: list[tuple[int, str]] = []
    for i in range(T.COMPANION_CONCURRENT_SESSIONS):
        token = f"CMPISO{i}{uuid.uuid4().hex[:6]}"
        p = Project(name=token, description="companion-soak", team="e2e", status="active")
        setup.add(p)
        setup.flush()
        r = Repo(
            project_id=p.id,
            owner="zinnia",
            repo_name=f"root-{token}",
            local_path=str(tmp_path / token),
            clone_status="cloned",
        )
        setup.add(r)
        setup.commit()
        setup.refresh(p)
        sessions.append((p.id, token))
    setup.close()

    def _one(project_id: int, token: str) -> dict:
        db = factory()
        try:
            env = build_companion_scope(db, project_id=project_id)
            created = open_or_create_work_item(
                db, env, title=f"Work {token}", created_by="soak@zect.local"
            )
            turn = run_companion_turn(db, "What's my Mentrix Delivery status?", project_id=project_id)
            return {"env": env, "created": created, "turn": turn, "token": token, "project_id": project_id}
        finally:
            db.close()

    rss0, _h0 = resource_snapshot()
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=T.COMPANION_CONCURRENT_SESSIONS) as pool:
        futs = [pool.submit(_one, pid, tok) for pid, tok in sessions]
        rows = [f.result(timeout=40) for f in futs]
    ms = int((time.perf_counter() - t0) * 1000)
    gc.collect()
    rss1, _h1 = resource_snapshot()
    emit_event(
        operation="companion_soak",
        stage="complete",
        duration_ms=ms,
        extra={"rss0": rss0, "rss1": rss1, "n": len(rows)},
    )
    assert ms <= T.COMPANION_CONCURRENT_MAX_MS, f"companion soak {ms}ms > {T.COMPANION_CONCURRENT_MAX_MS}"
    assert len(rows) == T.COMPANION_CONCURRENT_SESSIONS
    verify = factory()
    try:
        for row in rows:
            assert row["created"].get("ok") is True
            assert row["created"].get("work_item_id")
            assert row["env"].get("project_id") == row["project_id"]
            blob = json.dumps({"env": row["env"], "created": row["created"], "turn": row["turn"]})
            for other_pid, other_token in sessions:
                if other_pid == row["project_id"]:
                    continue
                assert other_token not in blob
            wi = verify.query(WorkItem).filter(WorkItem.id == int(row["created"]["work_item_id"])).one()
            assert wi.project_id == row["project_id"]
            assert row["token"] in (wi.title or "")
    finally:
        verify.close()
    if rss0 > 0 and rss1 > 0:
        assert (rss1 - rss0) <= T.SOAK_MAX_RSS_GROWTH_BYTES, f"companion soak RSS grew {rss1 - rss0}"


@pytest.mark.asyncio
async def test_overlapping_terminal_runner_isolation_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    a = tmp_path / "term-a"
    b = tmp_path / "term-b"
    a.mkdir()
    b.mkdir()
    (a / "marker.txt").write_text("ALPHA-TERM-MARK", encoding="utf-8")
    (b / "marker.txt").write_text("BETA-TERM-MARK", encoding="utf-8")
    factory = _file_sessionmaker(tmp_path / "runner.db")
    db = factory()
    user = _admin(db)
    py = sys.executable
    read_cmd = f'"{py}" -c "print(open(\'marker.txt\',encoding=\'utf-8\').read())"'
    hang_cmd = (
        f'"{py}" -c "print(open(\'marker.txt\',encoding=\'utf-8\').read()); '
        f'import time; time.sleep(8)"'
    )
    rss0, handles0 = resource_snapshot()
    t0 = time.perf_counter()
    exec_a, exec_b = await asyncio.gather(
        execute_command(
            ExecuteRequest(command=read_cmd, cwd=str(a), bound_root=str(a), timeout=15),
            current_user=user,
            db=db,
        ),
        execute_command(
            ExecuteRequest(command=read_cmd, cwd=str(b), bound_root=str(b), timeout=15),
            current_user=user,
            db=db,
        ),
    )
    started = await asyncio.gather(
        start_process(
            StartRequest(command=hang_cmd, cwd=str(a), bound_root=str(a), label="term-a"),
            current_user=user,
            db=db,
        ),
        start_process(
            StartRequest(command=hang_cmd, cwd=str(b), bound_root=str(b), label="term-b"),
            current_user=user,
            db=db,
        ),
    )
    ms = int((time.perf_counter() - t0) * 1000)
    assert "ALPHA-TERM-MARK" in (exec_a.get("stdout") or "")
    assert "BETA-TERM-MARK" not in (exec_a.get("stdout") or "")
    assert "BETA-TERM-MARK" in (exec_b.get("stdout") or "")
    assert "ALPHA-TERM-MARK" not in (exec_b.get("stdout") or "")
    assert exec_a.get("cwd") != exec_b.get("cwd")
    ids = [str(s.get("id") or "") for s in started]
    assert len(set(ids)) == T.TERMINAL_CONCURRENT
    stopped = stop_all_processes()
    assert stopped >= 1
    emit_event(operation="terminal_soak", stage="complete", duration_ms=ms, extra={"stopped": stopped})
    assert ms <= T.TERMINAL_SOAK_MAX_MS, f"terminal soak {ms}ms > {T.TERMINAL_SOAK_MAX_MS}"
    gc.collect()
    rss1, handles1 = resource_snapshot()
    if rss0 > 0 and rss1 > 0:
        assert (rss1 - rss0) <= T.SOAK_MAX_RSS_GROWTH_BYTES
    if handles0 is not None and handles1 is not None:
        assert (handles1 - handles0) <= T.SOAK_MAX_HANDLE_GROWTH
    db.close()


def test_native_present_quality_generate_load_and_diagnose(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path / "templates"))
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path / "assets"))
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    monkeypatch.setattr(
        "app.services.mentrix.presentation.native_provider.default_pptx_save_dir",
        lambda: tmp_path / "decks",
    )
    (tmp_path / "decks").mkdir()
    tmpl.import_canonical_master(
        "zinnia-executive-v1",
        make_master_pptx_bytes(),
        name="Zinnia Executive",
        filename="exec.pptx",
    )
    rss0, _h0 = resource_snapshot()
    durations: list[int] = []
    last = None
    with patch("app.services.presenton_client.generate_presentation") as gen:
        with patch(
            "app.services.phases.llm_phase._chat",
            return_value={"ok": False, "error": "offline", "content": "", "telemetry": {}},
        ):
            for i in range(T.PRESENT_NATIVE_QUALITY_LOAD):
                t0 = time.perf_counter()
                out = PresentationService(provider=ZectNativePresentationProvider()).generate(
                    PresentationGenerateRequest(
                        content="Executive delivery status for claims API and Lattice indexing",
                        n_slides=T.PRESENT_NATIVE_QUALITY_SLIDES,
                        ui_template_choice="zinnia-executive-v1",
                        audience_id="executive",
                        filename=f"quality-load-{i}.pptx",
                        user_id="7",
                        fast_basic=False,
                        require_llm=False,
                    )
                )
                ms = int((time.perf_counter() - t0) * 1000)
                durations.append(ms)
                last = out
                emit_event(
                    operation="present_quality",
                    stage="generate",
                    duration_ms=ms,
                    run_id=str(out.get("run_id") or ""),
                    extra={"i": i, "ok": bool(out.get("ok"))},
                )
                assert out["ok"] is True, out
                assert Path(str(out.get("path") or "")).is_file()
                assert ms <= T.PRESENT_NATIVE_QUALITY_MAX_MS, f"native quality {ms}ms > {T.PRESENT_NATIVE_QUALITY_MAX_MS}"
        gen.assert_not_called()
    assert last is not None
    diag = diagnose(run_id=str(last.get("run_id") or ""))
    assert diag["event_count"] >= 1
    blob = json.dumps(diag).lower()
    assert "sk-" not in blob
    gc.collect()
    rss1, _h1 = resource_snapshot()
    if rss0 > 0 and rss1 > 0:
        assert (rss1 - rss0) <= T.SOAK_MAX_RSS_GROWTH_BYTES, f"present quality RSS grew {rss1 - rss0}"
    assert max(durations) <= T.PRESENT_NATIVE_QUALITY_MAX_MS


def test_resources_return_to_baseline_after_concurrent_load(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("LATTICE_CACHE_DIR", str(tmp_path / "lattice-cache"))
    from app.services.lattice.indexer import ingest_path

    root = tmp_path / "burst"
    root.mkdir()
    for i in range(T.SOAK_LATTICE_FILES):
        (root / f"b{i}.py").write_text(f"x={i}\n", encoding="utf-8")
    rss0, handles0 = resource_snapshot()
    db0 = db_checked_out()
    t0 = time.perf_counter()
    barrier = threading.Barrier(2)
    errors: list[str] = []

    def _ingest() -> None:
        try:
            barrier.wait(timeout=10)
            ingest_path(str(root), project_key="burst-a", max_files=T.SOAK_LATTICE_FILES, index_docs=False)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    def _ingest_b() -> None:
        try:
            barrier.wait(timeout=10)
            ingest_path(str(root), project_key="burst-b", max_files=T.SOAK_LATTICE_FILES, index_docs=False)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    threads = [threading.Thread(target=_ingest), threading.Thread(target=_ingest_b)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=30)
    ms = int((time.perf_counter() - t0) * 1000)
    assert not errors, errors
    assert ms <= T.CONCURRENT_LOAD_SOAK_MAX_MS
    gc.collect()
    rss1, handles1 = resource_snapshot()
    db1 = db_checked_out()
    emit_event(
        operation="concurrent_load",
        stage="complete",
        duration_ms=ms,
        extra={"rss0": rss0, "rss1": rss1, "db0": db0, "db1": db1},
    )
    assert rss0 > 0 and rss1 > 0, "RSS unmeasured — concurrent-load return-to-baseline cannot PASS"
    assert (rss1 - rss0) <= T.SOAK_MAX_RSS_GROWTH_BYTES, f"RSS grew {rss1 - rss0}"
    if db1 is not None:
        assert db1 <= T.SOAK_MAX_DB_CHECKEDOUT
    if handles0 is not None and handles1 is not None:
        assert (handles1 - handles0) <= T.SOAK_MAX_HANDLE_GROWTH


def test_live_presenton_unset_is_blocked_external_not_pass():
    if (os.getenv("PRESENTON_BASE_URL") or "").strip():
        pytest.skip("live Presenton configured — not asserted as BLOCKED_EXTERNAL here")
    pytest.skip("BLOCKED_EXTERNAL: PRESENTON_BASE_URL unset — skip ≠ PASS")

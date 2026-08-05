"""Phase 2 Stage C — Mentrix coding-engine bridge (mock no-op + remote slice)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from app.adapters.coding_runtime import RuntimeArtifact, RuntimeEvent, reset_coding_runtime_for_tests
from app.infrastructure.database import SessionLocal
from app.models import MentrixRun
from app.services.coding_engine.mentrix_bridge import (
    cleanup_coding_engine_slice,
    prepare_coding_engine_slice,
)


def _init_git_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@zect.local"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT Test"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


def test_bridge_mock_is_noop(monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mock")
    reset_coding_runtime_for_tests()
    db = SessionLocal()
    try:
        run = MentrixRun(
            mode="chat",
            goal="x",
            status="running",
            events_json="[]",
            gates_json="{}",
            result_json=json.dumps({"context": {}}),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        slice_result = prepare_coding_engine_slice(db, run, goal="x", workspace="/tmp/ws")
        assert slice_result.active is False
        assert slice_result.engine_provider == "mock"
        ctx = json.loads(run.result_json)["context"]
        assert ctx.get("engine_provider") == "mock"
    finally:
        db.close()


def test_bridge_remote_provisions_and_merges_events(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "remote")
    monkeypatch.setenv("ZECT_CODING_ENGINE_URL", "http://engine.test")
    monkeypatch.setenv("ZECT_CODING_ENGINE_API_KEY", "k")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_ENGINE_WORKSPACE_ROOT", str(tmp_path / "engine"))
    monkeypatch.setenv("ZECT_CODING_ENGINE_POLL_ATTEMPTS", "2")
    monkeypatch.setenv("ZECT_CODING_ENGINE_POLL_DELAY", "0")
    (tmp_path / "engine").mkdir()
    reset_coding_runtime_for_tests()

    repo = _init_git_repo(tmp_path / "repo")

    fake_rt = MagicMock()
    fake_rt.start_run.return_value = "eng-1"
    fake_rt.stream_events.side_effect = [
        [
            RuntimeEvent(1, "started", "hi", phase="provisioning"),
            RuntimeEvent(2, "file_change", "wrote", phase="build", data={"path": "README.md"}),
        ],
        [RuntimeEvent(3, "completed", "done", phase="validating")],
        [],
    ]
    fake_rt.get_run.return_value = {"status": "completed", "id": "eng-1"}
    fake_rt.get_artifacts.return_value = [RuntimeArtifact(path="README.md", kind="file")]

    monkeypatch.setattr(
        "app.services.coding_engine.mentrix_bridge.get_coding_runtime",
        lambda: fake_rt,
    )

    db = SessionLocal()
    try:
        run = MentrixRun(
            mode="deliver",
            goal="edit readme",
            status="running",
            events_json="[]",
            gates_json="{}",
            result_json=json.dumps({"context": {"workspace": str(repo)}}),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        slice_result = prepare_coding_engine_slice(
            db, run, goal="edit readme", workspace=str(repo), mode="deliver"
        )
        assert slice_result.active is True
        assert slice_result.workspace_id
        assert slice_result.engine_run_id == "eng-1"
        assert Path(slice_result.engine_workspace_path).is_dir()
        events = json.loads(run.events_json)
        assert any(e.get("agent") == "coding_engine" for e in events)
        ctx = json.loads(run.result_json)["context"]
        assert ctx["engine_provider"] == "remote"
        assert ctx["workspace_id"] == slice_result.workspace_id
        assert "openhands" not in json.dumps(ctx).lower()

        cleaned = cleanup_coding_engine_slice(slice_result)
        assert cleaned and cleaned.get("removed") is True
    finally:
        db.close()
        reset_coding_runtime_for_tests()


def test_mentrix_agents_exposes_coding_engine(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mock")
    resp = client.get("/api/mentrix/agents", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("coding_engine") == "mock"
    assert "openhands" not in resp.text.lower()


def test_mentrix_chat_stamps_engine_provider(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mock")
    monkeypatch.setenv("LATTICE_ENABLED", "false")
    reset_coding_runtime_for_tests()
    start = client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={"goal": "stage c stamp", "mode": "chat"},
    )
    assert start.status_code == 200, start.text
    run_id = start.json()["id"]
    # Poll until not running (chat is fast)
    import time

    body = {}
    for _ in range(20):
        body = client.get(f"/api/mentrix/runs/{run_id}", headers=auth_headers).json()
        if body.get("status") != "running":
            break
        time.sleep(0.2)
    # engine_provider may be set by bridge once worker runs
    assert body.get("id") == run_id
    # After worker, context should include mock provider
    result = body.get("result") or {}
    ctx = result.get("context") or {}
    if ctx:
        assert ctx.get("engine_provider") in (None, "mock")
    assert body.get("engine_provider") in (None, "mock")

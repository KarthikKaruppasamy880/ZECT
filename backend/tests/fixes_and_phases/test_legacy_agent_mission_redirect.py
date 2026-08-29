"""Legacy Agent Mode (/api/agent/run) must not remain a second independent
coding engine. A file-writing submission (mode=upgrade/bugfix + a real
workspace path) now hands off to the SAME canonical coding_engine Mission
used by Developer Workspace instead of forge_loop.orchestrator, executes in
the background so the HTTP call does not block for the whole mission, and
its history is a live projection of the canonical Mission JSON store -- not
a second run table. chat/review_only modes and missing-workspace requests
are left exactly as they were (they never wrote files either way)."""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.domains.agent_run.agent_mode import _MISSION_RUN_PREFIX


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "zect-ca@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT CA"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def _fake_build(target_file: str, content: str, gate: threading.Event | None = None):
    def _run(*, workspace, **_kwargs):
        if gate is not None:
            gate.wait(timeout=5)
        Path(workspace, target_file).write_text(content, encoding="utf-8")
        return {"ok": True, "status": "completed", "files_written": [target_file], "run_id": "fake"}

    return _run


class TestFileWritingModeRedirectsToTheRealMission:
    def test_upgrade_mode_with_workspace_creates_a_real_mission_not_forge_loop(
        self, ws, client, auth_headers
    ):
        repo = _init_repo(ws / "backend")
        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch(
                "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
                side_effect=_fake_build("calc.py", "def add(a, b):\n    return a + b\n"),
            ),
            patch("app.services.forge_loop.orchestrator.run_mentrix") as mocked_forge_loop,
        ):
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Fix add()", "stages": ["build"], "mode": "upgrade", "workspace": str(repo)},
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["run_id"].startswith(_MISSION_RUN_PREFIX)
            assert body["engine"] == "coding_engine_mission"
            assert not mocked_forge_loop.called, "file-writing legacy submissions must not use forge_loop"

            # Poll the same legacy GET endpoint until the background mission finishes.
            mission_id = body["run_id"][len(_MISSION_RUN_PREFIX) :]
            for _ in range(100):
                got = client.get(f"/api/agent/run/{_MISSION_RUN_PREFIX}{mission_id}", headers=auth_headers)
                if got.json()["status"] not in ("running",):
                    break
                time.sleep(0.05)
            final = got.json()
            assert final["status"] == "completed", final
            assert "calc.py" in final["files_written"]

    def test_post_returns_before_the_mission_finishes(self, ws, client, auth_headers):
        """The HTTP call must not block for the whole mission -- only the
        legacy /api/agent/run screen's single-await contract was ever tied to
        forge_loop's synchronous run_mentrix(); the mission-backed redirect
        must background the real execution instead of reproducing that block."""
        repo = _init_repo(ws / "backend")
        gate = threading.Event()
        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch(
                "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
                side_effect=_fake_build("calc.py", "def add(a, b):\n    return a + b\n", gate=gate),
            ),
        ):
            started = time.monotonic()
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Fix add()", "stages": ["build"], "mode": "upgrade", "workspace": str(repo)},
            )
            elapsed = time.monotonic() - started
            assert resp.status_code == 200
            assert elapsed < 4.0, "POST /api/agent/run must not block on the gated background mission"
            body = resp.json()
            assert body["status"] == "running"
            gate.set()

    def test_chat_mode_still_uses_forge_loop_unchanged(self, ws, client, auth_headers):
        with patch("app.services.forge_loop.orchestrator.run_mentrix") as mocked, patch(
            "app.services.coding_engine.lifecycle.start_mission"
        ) as mocked_mission:
            mocked.return_value = type(
                "R",
                (),
                {
                    "id": 1,
                    "status": "completed",
                    "mode": "chat",
                    "current_agent": "",
                    "events_json": "[]",
                    "result_json": "{}",
                    "gates_json": "{}",
                    "created_at": None,
                    "completed_at": None,
                },
            )()
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "What does this repo do?", "stages": ["ask"], "mode": "chat"},
            )
            assert resp.status_code == 200, resp.text
            assert mocked.called
            assert not mocked_mission.called, "chat mode must not touch the coding_engine mission path"

    def test_upgrade_mode_without_a_real_workspace_still_uses_forge_loop(self, ws, client, auth_headers):
        with patch("app.services.forge_loop.orchestrator.run_mentrix") as mocked, patch(
            "app.services.coding_engine.lifecycle.start_mission"
        ) as mocked_mission:
            mocked.return_value = type(
                "R",
                (),
                {
                    "id": 2,
                    "status": "completed",
                    "mode": "upgrade",
                    "current_agent": "",
                    "events_json": "[]",
                    "result_json": "{}",
                    "gates_json": "{}",
                    "created_at": None,
                    "completed_at": None,
                },
            )()
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Draft something", "stages": ["build"], "mode": "upgrade"},
            )
            assert resp.status_code == 200, resp.text
            assert mocked.called
            assert not mocked_mission.called, "no real workspace path -- nothing to redirect to a Mission for"


class TestMissionBackedRunsResolveToTheSameCanonicalMission:
    def test_legacy_created_run_is_visible_via_the_canonical_developer_endpoint(
        self, ws, client, auth_headers
    ):
        repo = _init_repo(ws / "backend")
        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch(
                "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
                side_effect=_fake_build("calc.py", "def add(a, b):\n    return a + b\n"),
            ),
        ):
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Fix add()", "stages": ["build"], "mode": "upgrade", "workspace": str(repo)},
            )
            run_id = resp.json()["run_id"]
            mission_id = run_id[len(_MISSION_RUN_PREFIX) :]

            for _ in range(100):
                canonical = client.get(f"/api/coding-agent/missions/{mission_id}", headers=auth_headers)
                if canonical.json()["phase"] not in ("isolating", "editing", "awaiting_plan_approval"):
                    break
                time.sleep(0.05)

        assert canonical.status_code == 200, canonical.text
        assert canonical.json()["id"] == mission_id
        assert canonical.json()["goal"] == "Fix add()"
        # The exact same mission, not a re-derived summary standing in for it.
        via_legacy = client.get(f"/api/agent/run/{run_id}", headers=auth_headers).json()
        assert via_legacy["result"]["mission"]["id"] == canonical.json()["id"]

    def test_history_list_includes_mission_backed_runs(self, ws, client, auth_headers):
        repo = _init_repo(ws / "backend")
        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch(
                "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
                side_effect=_fake_build("calc.py", "def add(a, b):\n    return a + b\n"),
            ),
        ):
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Fix add()", "stages": ["build"], "mode": "upgrade", "workspace": str(repo)},
            )
            run_id = resp.json()["run_id"]

        listing = client.get("/api/agent/runs", headers=auth_headers)
        assert listing.status_code == 200, listing.text
        run_ids = [r.get("run_id") for r in listing.json()]
        assert run_id in run_ids

    def test_cancel_mission_backed_run(self, ws, client, auth_headers):
        repo = _init_repo(ws / "backend")
        gate = threading.Event()
        with (
            patch("app.services.coding_engine.propose_patches.propose_from_plan", return_value={}),
            patch(
                "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build",
                side_effect=_fake_build("calc.py", "def add(a, b):\n    return a + b\n", gate=gate),
            ),
        ):
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Fix add()", "stages": ["build"], "mode": "upgrade", "workspace": str(repo)},
            )
            run_id = resp.json()["run_id"]
            cancelled = client.delete(f"/api/agent/run/{run_id}", headers=auth_headers)
            assert cancelled.status_code == 200, cancelled.text
            assert cancelled.json()["status"] == "cancelled"
            gate.set()
            got = client.get(f"/api/agent/run/{run_id}", headers=auth_headers)
            assert got.json()["status"] == "cancelled"

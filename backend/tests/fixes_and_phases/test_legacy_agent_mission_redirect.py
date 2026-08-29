"""Legacy Agent Mode (/api/agent/run) must not remain a second independent
coding engine. A file-writing submission (mode=upgrade/bugfix + a real
workspace path) now hands off to the SAME canonical coding_engine Mission
used by Developer Workspace instead of forge_loop.orchestrator, returns the
PLAN for a human to review (never auto-approves -- see the Phase A
governance fix in agent_mode.py), and its history is a live projection of
the canonical Mission JSON store -- not a second run table. chat/review_only
modes and missing-workspace requests are left exactly as they were (they
never wrote files either way)."""

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
            ) as mocked_build,
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
            assert body["status"] == "awaiting_approval", "must not auto-approve without a human"
            assert not mocked_build.called, "no file should be written before a human approves the PLAN"
            assert not mocked_forge_loop.called, "file-writing legacy submissions must not use forge_loop"

            mission_id = body["run_id"][len(_MISSION_RUN_PREFIX) :]
            approved = client.post(
                f"/api/coding-agent/missions/{mission_id}/approve-plan", headers=auth_headers
            )
            assert approved.status_code == 200, approved.text

            final = client.get(f"/api/agent/run/{body['run_id']}", headers=auth_headers).json()
            assert final["status"] == "completed", final
            assert "calc.py" in final["files_written"]

    def test_post_does_not_build_until_a_human_approves_the_plan(self, ws, client, auth_headers):
        """This is the exact governance bug the Phase A fix closes: the
        legacy /api/agent/run redirect used to call approve_plan_in_background()
        itself, so a file-writing mission executed with zero human
        confirmation. The POST must now return the PLAN for review only."""
        repo = _init_repo(ws / "backend")
        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build"
        ) as mocked_build:
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Fix add()", "stages": ["build"], "mode": "upgrade", "workspace": str(repo)},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "awaiting_approval"
            assert not mocked_build.called, "must not build before a human approves the PLAN"

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

            approved = client.post(
                f"/api/coding-agent/missions/{mission_id}/approve-plan", headers=auth_headers
            )
            assert approved.status_code == 200, approved.text
            canonical = client.get(f"/api/coding-agent/missions/{mission_id}", headers=auth_headers)

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

    def test_cancel_before_approval_never_builds(self, ws, client, auth_headers):
        """Cancelling a mission that's still awaiting a human's PLAN approval
        (the common case now that approval is never automatic) must not
        build anything, and must leave the run showing as cancelled."""
        repo = _init_repo(ws / "backend")
        with patch(
            "app.services.coding_engine.mentrix_native_build.run_mentrix_native_build"
        ) as mocked_build:
            resp = client.post(
                "/api/agent/run",
                headers=auth_headers,
                json={"task": "Fix add()", "stages": ["build"], "mode": "upgrade", "workspace": str(repo)},
            )
            run_id = resp.json()["run_id"]
            cancelled = client.delete(f"/api/agent/run/{run_id}", headers=auth_headers)
            assert cancelled.status_code == 200, cancelled.text
            assert cancelled.json()["status"] == "cancelled"
            assert not mocked_build.called
            got = client.get(f"/api/agent/run/{run_id}", headers=auth_headers)
            assert got.json()["status"] == "cancelled"

    def test_cancel_mission_backed_run(self, ws, client, auth_headers):
        """Cancelling a mission that a human already approved and is mid-flight
        must be reflected as cancelled once the gated build unblocks."""
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
            mission_id = run_id[len(_MISSION_RUN_PREFIX) :]

            # approve-plan blocks the caller until the mission finishes -- a
            # real human approving from the UI experiences this same block,
            # so exercise it from a background thread to be able to cancel
            # mid-flight, same as a human changing their mind mid-build.
            approve_thread = threading.Thread(
                target=client.post,
                args=(f"/api/coding-agent/missions/{mission_id}/approve-plan",),
                kwargs={"headers": auth_headers},
                daemon=True,
            )
            approve_thread.start()
            time.sleep(0.3)  # let approval pass the cancellation check and reach the gated build

            cancelled = client.delete(f"/api/agent/run/{run_id}", headers=auth_headers)
            assert cancelled.status_code == 200, cancelled.text
            assert cancelled.json()["status"] == "cancelled"
            gate.set()
            approve_thread.join(timeout=5)
            got = client.get(f"/api/agent/run/{run_id}", headers=auth_headers)
            assert got.json()["status"] == "cancelled"

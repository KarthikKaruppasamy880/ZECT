"""Mentrix Delivery must ship the SAME Developer Mission, never re-plan or
re-build it independently through ForgeLoop (Phase A governance fix --
see ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md).

Before this fix, POST /api/mentrix/runs with a coding_mission_id still
created an independent MentrixRun driven by the raw `goal` string and ran
the full ForgeLoop scout/planner/builder pipeline in the background --
never reading the Mission's actual plan/diff/evidence, and duplicating the
coding engine. Now a coding_mission_id-backed request is routed to
lifecycle.approve_git() only: git commit/push/PR of what that Mission
already built and reviewed. No auto-merge either way.
"""

from __future__ import annotations

from unittest.mock import patch


def _start_delivery(client, auth_headers, *, mission_id: str, work_item_id: int = 42):
    return client.post(
        "/api/mentrix/runs",
        headers=auth_headers,
        json={
            "goal": "Ship the reviewed change",
            "mode": "upgrade",
            "workspace": "",
            "work_item_id": work_item_id,
            "coding_mission_id": mission_id,
        },
    )


class TestDeliveryForAMissionNeverRunsForgeLoop:
    def test_never_calls_forge_loop_run_mentrix(self, client, auth_headers):
        with (
            patch("app.services.coding_engine.lifecycle.get_mission", return_value={"id": "m-1"}),
            patch(
                "app.services.coding_engine.lifecycle.approve_git",
                return_value={"id": "m-1", "phase": "ready_to_merge", "status": "ready_to_merge"},
            ) as mocked_approve_git,
            patch("app.workers.mentrix_worker.run_mentrix") as mocked_forge_loop,
        ):
            resp = _start_delivery(client, auth_headers, mission_id="m-1")
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["mode"] == "deliver_mission"
            assert not mocked_forge_loop.called, "Delivery must not run an independent coding engine"
            mocked_approve_git.assert_called_once_with("m-1", commit=True, push=True)

    def test_successful_delivery_reflects_the_shipped_mission_and_marks_the_handoff(
        self, client, auth_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("ZECT_SHIP_HANDOFF_PATH", str(tmp_path / "handoffs.json"))
        shipped = {"id": "m-2", "phase": "ready_to_merge", "status": "ready_to_merge", "ci": {"status": "local_push"}}
        with (
            patch("app.services.coding_engine.lifecycle.get_mission", return_value={"id": "m-2"}),
            patch("app.services.coding_engine.lifecycle.approve_git", return_value=shipped),
        ):
            resp = _start_delivery(client, auth_headers, mission_id="m-2", work_item_id=7)
            assert resp.status_code == 200, resp.text
            run_id = resp.json()["id"]

            got = client.get(f"/api/mentrix/runs/{run_id}", headers=auth_headers)
            assert got.status_code == 200, got.text
            final = got.json()
            assert final["status"] == "completed"
            assert final["result"]["mission"]["phase"] == "ready_to_merge"

        from app.services.coding_engine.ship_handoff import find_open_handoff

        # A completed delivery is terminal -- no longer an "open" handoff.
        assert find_open_handoff(7, "m-2") is None

    def test_delivery_blocked_when_the_mission_is_not_shippable(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_SHIP_HANDOFF_PATH", str(tmp_path / "handoffs.json"))
        with (
            patch("app.services.coding_engine.lifecycle.get_mission", return_value={"id": "m-3"}),
            patch(
                "app.services.coding_engine.lifecycle.approve_git",
                side_effect=ValueError("plan_not_approved"),
            ),
        ):
            resp = _start_delivery(client, auth_headers, mission_id="m-3", work_item_id=8)
            assert resp.status_code == 200, resp.text
            run_id = resp.json()["id"]

            got = client.get(f"/api/mentrix/runs/{run_id}", headers=auth_headers)
            final = got.json()
            assert final["status"] == "failed"
            assert "plan_not_approved" in "".join(e.get("message", "") for e in final["events"])

    def test_unknown_mission_id_is_a_clean_404_not_a_forge_loop_fallback(self, client, auth_headers):
        with (
            patch("app.services.coding_engine.lifecycle.get_mission", side_effect=KeyError("mission_not_found")),
            patch("app.workers.mentrix_worker.run_mentrix") as mocked_forge_loop,
        ):
            resp = _start_delivery(client, auth_headers, mission_id="does-not-exist")
            assert resp.status_code == 404, resp.text
            assert not mocked_forge_loop.called

    def test_duplicate_delivery_run_is_rejected(self, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_SHIP_HANDOFF_PATH", str(tmp_path / "handoffs.json"))
        with (
            patch("app.services.coding_engine.lifecycle.get_mission", return_value={"id": "m-4"}),
            patch(
                "app.services.coding_engine.lifecycle.approve_git",
                side_effect=ValueError("plan_not_approved"),
            ),
        ):
            first = _start_delivery(client, auth_headers, mission_id="m-4", work_item_id=9)
            assert first.status_code == 200, first.text

        from app.services.coding_engine.ship_handoff import mark_handoff_status

        # The blocked delivery above already got marked "failed" (terminal)
        # by the background task, which would let a retry through -- force
        # it back to "running" to simulate a delivery that is still actually
        # in flight, and confirm the duplicate guard rejects a second one.
        mark_handoff_status(first.json()["id"], "running")

        with patch("app.services.coding_engine.lifecycle.get_mission", return_value={"id": "m-4"}):
            second = _start_delivery(client, auth_headers, mission_id="m-4", work_item_id=9)
        assert second.status_code == 409, second.text
        assert second.json()["detail"]["error"] == "duplicate_delivery_run"


class TestNonMissionDeliveryIsUnchanged:
    def test_no_coding_mission_id_still_uses_forge_loop(self, client, auth_headers):
        with patch("app.workers.mentrix_worker.run_mentrix") as mocked_forge_loop:
            resp = client.post(
                "/api/mentrix/runs",
                headers=auth_headers,
                json={"goal": "Draft something", "mode": "chat"},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["mode"] == "chat"
        assert mocked_forge_loop.called, "non-Mission-backed asks must keep using ForgeLoop unchanged"

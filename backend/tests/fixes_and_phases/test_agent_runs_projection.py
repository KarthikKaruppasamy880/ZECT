"""GET /api/agent/runs must return one chronologically merged, correctly
paginated list across all three run sources (legacy agent_orchestrator,
ForgeLoop's MentrixRun, canonical Mission JSON store) -- see
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase D.

Before this fix, each source was independently queried for `limit` rows and
the three lists were concatenated with no cross-source ordering: calling
list_runs(limit=2) could return up to 6 rows, and a run newer than
everything else could still sort dead last just because its source
happened to be concatenated last.
"""

from __future__ import annotations

from unittest.mock import patch

from app.domains.agent_run.agent_mode import list_runs


def _mission_row(mission_id: str, *, created_at: str) -> dict:
    return {
        "id": mission_id,
        "goal": f"mission {mission_id}",
        "mode": "upgrade",
        "phase": "editing",
        "status": "running",
        "events": [],
        "files": [],
        "blockers": [],
        "started_at": created_at,
        "updated_at": created_at,
    }


class _FakeMentrixRun:
    def __init__(self, id_, *, created_at):
        self.id = id_
        self.goal = f"mentrix {id_}"
        self.status = "running"
        self.mode = "chat"
        self.current_agent = "orchestrator"
        self.created_at = created_at
        self.completed_at = None


def _iso(dt) -> str:
    return dt.isoformat()


class _EmptyQuery:
    def order_by(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def all(self):
        return []


class _EmptyDb:
    def query(self, *a, **kw):
        return _EmptyQuery()


class TestRunsProjectionIsChronologicallyMergedAndPaginated:
    def test_a_newer_legacy_run_sorts_ahead_of_older_mission_rows(self):
        from datetime import datetime, timedelta, timezone

        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        older_mission = _mission_row("m-old", created_at=_iso(now - timedelta(hours=2)))
        newer_legacy = {
            "id": 1,
            "run_id": "legacy-newest",
            "task": "t",
            "stages": ["ask"],
            "model": "m",
            "status": "completed",
            "current_stage_index": 0,
            "auto_advance": True,
            "total_tokens": 0,
            "created_at": _iso(now),
            "completed_at": None,
            "steps": [],
        }

        with (
            patch("app.services.coding_engine.lifecycle.list_missions", return_value=[older_mission]),
            patch("app.services.agent_orchestrator.list_agent_runs", return_value=[newer_legacy]),
        ):
            result = list_runs(limit=2, offset=0, db=_EmptyDb())

        assert [r["run_id"] for r in result] == ["legacy-newest", "mission-m-old"]

    def test_limit_is_respected_across_all_three_sources_combined(self):
        from datetime import datetime, timedelta, timezone

        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        missions = [_mission_row(f"m{i}", created_at=_iso(now - timedelta(minutes=i))) for i in range(5)]

        class _Query:
            def __init__(self, rows):
                self._rows = rows

            def order_by(self, *a, **kw):
                return self

            def limit(self, n):
                self._rows = self._rows[:n]
                return self

            def all(self):
                return self._rows

        mentrix_rows = [_FakeMentrixRun(i, created_at=now - timedelta(minutes=10 + i)) for i in range(5)]

        class _FakeDb:
            def query(self, *a, **kw):
                return _Query(mentrix_rows)

        with (
            patch("app.services.coding_engine.lifecycle.list_missions", return_value=missions),
            patch("app.services.agent_orchestrator.list_agent_runs", return_value=[]),
        ):
            result = list_runs(limit=3, offset=0, db=_FakeDb())

        assert len(result) == 3, "must return exactly `limit` rows, not up to 3x that from unioned sources"
        # The 3 most recent overall are the first 3 missions (0, 1, 2 minutes ago).
        assert [r["run_id"] for r in result] == ["mission-m0", "mission-m1", "mission-m2"]

    def test_offset_paginates_the_merged_list_not_each_source_independently(self):
        from datetime import datetime, timedelta, timezone

        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        missions = [_mission_row(f"m{i}", created_at=_iso(now - timedelta(minutes=i))) for i in range(3)]

        with (
            patch("app.services.coding_engine.lifecycle.list_missions", return_value=missions),
            patch("app.services.agent_orchestrator.list_agent_runs", return_value=[]),
        ):
            page1 = list_runs(limit=2, offset=0, db=_EmptyDb())
            page2 = list_runs(limit=2, offset=2, db=_EmptyDb())

        assert [r["run_id"] for r in page1] == ["mission-m0", "mission-m1"]
        assert [r["run_id"] for r in page2] == ["mission-m2"]

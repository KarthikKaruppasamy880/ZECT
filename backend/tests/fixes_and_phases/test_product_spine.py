"""Product spine dogfood — no-mock defaults, schedules, malware adapter, agent context."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_selected_coding_engine_defaults_native(monkeypatch):
    monkeypatch.delenv("ZECT_CODING_ENGINE", raising=False)
    from app.adapters.coding_runtime import reset_coding_runtime_for_tests, selected_coding_engine

    reset_coding_runtime_for_tests()
    assert selected_coding_engine() == "mentrix_native"


def test_compose_coding_agent_context_includes_agent_context_bits(monkeypatch):
    from app.services.coding_engine.agent_context import compose_coding_agent_context

    with patch("app.services.mentrix.companion.build_agent_context", return_value="Active skill (x): do y"):
        with patch("app.infrastructure.database.SessionLocal", side_effect=Exception("no db")):
            # Without DB, still safe empty or partial
            text = compose_coding_agent_context(goal="fix login", project_id=None, db=None)
            assert isinstance(text, str)


def test_compose_with_fake_db_calls_build_agent_context():
    from app.services.coding_engine.agent_context import compose_coding_agent_context

    db = MagicMock()
    # GeneratedOutput query chain
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    with patch(
        "app.services.mentrix.companion.build_agent_context",
        return_value="Active skill (pack): prefer typed APIs",
    ) as mocked:
        with patch(
            "app.services.rag.retriever.hybrid_retrieve",
            return_value=[],
        ):
            text = compose_coding_agent_context(goal="add endpoint", project_id=1, skill_id=2, db=db)
    mocked.assert_called()
    assert "Active skill" in text


def test_compute_next_cron_run():
    from app.domains.personal_agent.schedule_ticker import compute_next_cron_run

    nxt = compute_next_cron_run("*/5 * * * *")
    assert nxt is not None
    assert nxt.tzinfo is not None


def test_unknown_schedule_task_fails(db_session=None):
    from app.domains.personal_agent.schedule_executor import _dispatch
    from app.models import Schedule

    sched = Schedule(
        name="bad",
        description="",
        schedule_type="once",
        task_type="totally_unknown_xyz",
        task_config={},
        is_active=True,
    )
    db = MagicMock()
    with pytest.raises(RuntimeError, match="Unknown schedule task_type"):
        _dispatch(db, sched)


def test_malware_status_degraded_without_daemon(monkeypatch):
    monkeypatch.setenv("ZECT_MALWARE_SCAN_HOST", "127.0.0.1")
    monkeypatch.setenv("ZECT_MALWARE_SCAN_PORT", "1")
    monkeypatch.delenv("ZECT_MALWARE_SCAN_CLI", raising=False)
    from app.adapters.detection_malware import malware_engine_status

    with patch("app.adapters.detection_malware.shutil.which", return_value=None):
        st = malware_engine_status()
    assert st["provider"] == "zect_security_agent"
    assert st["ready"] is False
    assert "clam" not in str(st).lower()


def test_malware_parse_found():
    from app.adapters.detection_malware import _parse_scan_response

    r = _parse_scan_response("stream: Eicar-Test-Signature FOUND", Path("x.bin"))
    assert r["infected"] is True
    assert "Eicar" in r["signature"] or "EICAR" in r["signature"].upper() or r["signature"]


def test_malware_parse_ok():
    from app.adapters.detection_malware import _parse_scan_response

    r = _parse_scan_response("stream: OK", Path("x.bin"))
    assert r["infected"] is False


def test_build_fails_closed_without_stub_flag(monkeypatch):
    from app.services.phases.build_phase_svc import run_build_generate

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ZECT_ALLOW_OFFLINE_BUILD_STUB", raising=False)
    result = run_build_generate("hello", file_path="a.py")
    assert result.get("error") == "generation_unavailable"


def test_quarantine_moves_file(tmp_path):
    from app.adapters.detection_malware import quarantine_file

    f = tmp_path / "evil.txt"
    f.write_text("x", encoding="utf-8")
    out = quarantine_file(f, workspace=tmp_path)
    assert out["ok"] is True
    assert not f.exists()
    assert Path(out["to"]).is_file()
    assert ".zect" in out["to"].replace("\\", "/")

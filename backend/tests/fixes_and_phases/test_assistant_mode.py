"""Assistant mode — every other MODE_PIPELINE entry is a fixed stage list;
if a request doesn't match one, nothing happens. This is the fix: a
model-driven tool-calling loop, gated by the same Permission Broker as
Companion, where heavy tools kick off a background MentrixRun and return
immediately instead of blocking.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database import Base
from app.models import MentrixRun
from app.services.forge_loop import orchestrator
from app.services.phases import assistant_phase


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _tool_call(name, args, call_id="call_1"):
    call = Mock()
    call.id = call_id
    call.function = Mock(name=name, arguments=json.dumps(args))
    call.function.name = name  # Mock(name=...) sets the mock's own repr name, not the attribute
    return call


def _completion_with_tool_calls(tool_calls):
    message = Mock(tool_calls=tool_calls, content=None)
    message.model_dump.return_value = {"role": "assistant", "tool_calls": []}
    return Mock(choices=[Mock(message=message)])


def _completion_final(text):
    message = Mock(tool_calls=None, content=text)
    message.model_dump.return_value = {"role": "assistant", "content": text}
    return Mock(choices=[Mock(message=message)])


class TestToCcTool:
    def test_converts_flat_realtime_shape_to_nested_chat_completions_shape(self):
        flat = {"type": "function", "name": "weather_report", "description": "desc", "parameters": {"type": "object", "properties": {}}}
        result = assistant_phase._to_cc_tool(flat)

        assert result == {
            "type": "function",
            "function": {"name": "weather_report", "description": "desc", "parameters": {"type": "object", "properties": {}}},
        }


class TestKickoffBackgroundRun:
    def test_creates_queued_run_and_returns_immediately(self, monkeypatch):
        db = _session()
        monkeypatch.setattr("app.database.SessionLocal", lambda: db)

        started = []
        monkeypatch.setattr(
            assistant_phase.threading,
            "Thread",
            lambda target, daemon, name: Mock(start=lambda: started.append((target, name))),
        )

        result = assistant_phase._kickoff_background_run("upgrade", "Fix the login bug")

        assert result["ok"] is True
        assert result["mode"] == "upgrade"
        assert result["status"] == "queued"
        assert "run_id" in result
        assert started, "expected a background thread to be started"

        row = db.query(MentrixRun).filter(MentrixRun.id == result["run_id"]).first()
        assert row is not None
        assert row.status == "queued"
        assert row.goal == "Fix the login bug"

    def test_worker_marks_run_failed_on_exception(self, monkeypatch):
        db = _session()
        monkeypatch.setattr("app.database.SessionLocal", lambda: db)

        captured_worker = {}
        monkeypatch.setattr(
            assistant_phase.threading,
            "Thread",
            lambda target, daemon, name: Mock(start=lambda: captured_worker.setdefault("fn", target)),
        )
        monkeypatch.setattr(
            "app.services.forge_loop.orchestrator.run_mentrix",
            Mock(side_effect=RuntimeError("boom")),
        )

        result = assistant_phase._kickoff_background_run("bugfix", "goal")
        captured_worker["fn"]()  # run the worker synchronously for the test

        row = db.query(MentrixRun).filter(MentrixRun.id == result["run_id"]).first()
        assert row.status == "failed"


class TestExecuteHeavyTool:
    def test_start_upgrade_run_kicks_off_background(self, monkeypatch):
        monkeypatch.setattr(
            assistant_phase,
            "_kickoff_background_run",
            lambda mode, goal, **kw: {"ok": True, "run_id": 7, "mode": mode, "status": "queued"},
        )

        result = assistant_phase.execute_heavy_tool("start_upgrade_run", {"goal": "upgrade the auth module"})

        assert result == {"ok": True, "run_id": 7, "mode": "upgrade", "status": "queued"}

    def test_request_review_runs_inline(self, monkeypatch):
        monkeypatch.setattr(
            "app.review_service.review_code_snippet",
            lambda code, language, user_id=None: {"quality_score": 85, "summary": "looks fine"},
        )

        result = assistant_phase.execute_heavy_tool("request_review", {"code": "x = 1", "language": "python"})

        assert result == {"ok": True, "score": 85, "summary": "looks fine"}

    def test_request_review_handles_no_api_key(self, monkeypatch):
        monkeypatch.setattr(
            "app.review_service.review_code_snippet",
            Mock(side_effect=ValueError("OpenAI API key not configured.")),
        )

        result = assistant_phase.execute_heavy_tool("request_review", {"code": "x = 1"})

        assert result["ok"] is False

    def test_trigger_deploy_delegates_to_gated_endpoint(self, monkeypatch):
        fake_response = Mock(status="pending_approval", message="needs approval", audit_id=42)
        monkeypatch.setattr(
            "app.routers.deploy_phase.trigger_workflow",
            lambda req, current_user, db: fake_response,
        )

        result = assistant_phase.execute_heavy_tool(
            "trigger_deploy", {"owner": "acme", "repo": "widgets", "workflow_file": "deploy.yml"},
        )

        assert result["ok"] is True
        assert result["status"] == "pending_approval"
        assert result["audit_id"] == 42

    def test_unknown_heavy_tool_returns_error(self):
        result = assistant_phase.execute_heavy_tool("not_a_real_tool", {})
        assert result["ok"] is False

    def test_scan_for_anomalies_runs_inline_against_real_scan(self, monkeypatch):
        db = _session()
        monkeypatch.setattr("app.database.SessionLocal", lambda: db)
        monkeypatch.setattr(
            "app.services.security.threat_detection.run_anomaly_scan",
            lambda db, lookback_hours=24: {"findings": [{"kind": "ip_churn"}], "scanned": {"audit_logs": 3}},
        )

        result = assistant_phase.execute_heavy_tool("scan_for_anomalies", {"lookback_hours": 12})

        assert result["ok"] is True
        assert result["findings"] == [{"kind": "ip_churn"}]
        assert result["scanned"] == {"audit_logs": 3}

    def test_scan_for_anomalies_handles_exception(self, monkeypatch):
        db = _session()
        monkeypatch.setattr("app.database.SessionLocal", lambda: db)
        monkeypatch.setattr(
            "app.services.security.threat_detection.run_anomaly_scan",
            Mock(side_effect=RuntimeError("db exploded")),
        )

        result = assistant_phase.execute_heavy_tool("scan_for_anomalies", {})

        assert result["ok"] is False
        assert "db exploded" in result["error"]

    def test_file_security_ticket_creates_real_issue(self, monkeypatch):
        db = _session()
        monkeypatch.setattr("app.database.SessionLocal", lambda: db)
        monkeypatch.setattr(
            "app.services.mcp.hub.execute_tool",
            lambda db, server_id, tool_name, arguments, user_email="": {
                "status": "success",
                "result": {"key": "SEC-42"},
            },
        )

        result = assistant_phase.execute_heavy_tool(
            "file_security_ticket", {"summary": "IP churn for user 5", "description": "3 distinct IPs in 24h"},
        )

        assert result["ok"] is True
        assert result["ticket_key"] == "SEC-42"

    def test_file_security_ticket_reports_when_jira_not_configured(self, monkeypatch):
        db = _session()
        monkeypatch.setattr("app.database.SessionLocal", lambda: db)
        monkeypatch.setattr(
            "app.services.mcp.hub.execute_tool",
            lambda db, server_id, tool_name, arguments, user_email="": {
                "status": "error",
                "result": {"message": "not configured"},
            },
        )

        result = assistant_phase.execute_heavy_tool("file_security_ticket", {"summary": "test"})

        assert result["ok"] is False


class TestRunAssistantLoop:
    def test_light_tool_executes_inline_via_permission_broker(self, monkeypatch):
        db = _session()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        tool_call = _tool_call("weather_report", {"location": "Austin"})
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            _completion_with_tool_calls([tool_call]),
            _completion_final("It's sunny in Austin."),
        ]
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)
        monkeypatch.setattr(
            "app.services.mentrix.permission_broker.check_tool_permission",
            lambda db, name, user_id=None, user_confirmed=False: {"result": "granted"},
        )
        monkeypatch.setattr(
            "app.services.mentrix.companion._exec_tool",
            lambda db, name, args, project_key="", created_by="": {"ok": True, "weather": "sunny"},
        )

        result = assistant_phase.run_assistant_loop(db, "what's the weather in austin")

        assert result["answer"] == "It's sunny in Austin."
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "weather_report"

    def test_heavy_tool_dispatched_to_execute_heavy_tool(self, monkeypatch):
        db = _session()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        tool_call = _tool_call("start_upgrade_run", {"goal": "upgrade the payments module"})
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            _completion_with_tool_calls([tool_call]),
            _completion_final("Started the upgrade run for you."),
        ]
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)
        monkeypatch.setattr(
            "app.services.mentrix.permission_broker.check_tool_permission",
            lambda db, name, user_id=None, user_confirmed=False: {"result": "granted"},
        )
        monkeypatch.setattr(
            assistant_phase,
            "execute_heavy_tool",
            lambda name, args, **kw: {"ok": True, "run_id": 99, "status": "queued"},
        )

        result = assistant_phase.run_assistant_loop(db, "upgrade the payments module")

        assert result["answer"] == "Started the upgrade run for you."
        assert result["tool_calls"][0]["result"]["run_id"] == 99

    def test_denied_permission_blocks_tool_execution(self, monkeypatch):
        db = _session()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        tool_call = _tool_call("trigger_deploy", {"owner": "acme", "repo": "x", "workflow_file": "d.yml"})
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            _completion_with_tool_calls([tool_call]),
            _completion_final("I can't do that."),
        ]
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)
        monkeypatch.setattr(
            "app.services.mentrix.permission_broker.check_tool_permission",
            lambda db, name, user_id=None, user_confirmed=False: {"result": "denied"},
        )
        heavy_tool_spy = Mock()
        monkeypatch.setattr(assistant_phase, "execute_heavy_tool", heavy_tool_spy)

        result = assistant_phase.run_assistant_loop(db, "deploy to production")

        heavy_tool_spy.assert_not_called()
        assert result["tool_calls"][0]["result"]["ok"] is False
        assert "denied" in result["tool_calls"][0]["result"]["error"].lower()

    def test_pending_approval_does_not_execute_tool(self, monkeypatch):
        db = _session()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        tool_call = _tool_call("slack_send", {"text": "hello"})
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            _completion_with_tool_calls([tool_call]),
            _completion_final("That needs your approval first."),
        ]
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)
        monkeypatch.setattr(
            "app.services.mentrix.permission_broker.check_tool_permission",
            lambda db, name, user_id=None, user_confirmed=False: {"result": "pending_approval"},
        )
        exec_spy = Mock()
        monkeypatch.setattr("app.services.mentrix.companion._exec_tool", exec_spy)

        result = assistant_phase.run_assistant_loop(db, "send a slack message")

        exec_spy.assert_not_called()
        assert result["tool_calls"][0]["result"]["pending_approval"] is True

    def test_no_tool_call_returns_direct_answer(self, monkeypatch):
        db = _session()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = _completion_final("Just chatting, no tool needed.")
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)

        result = assistant_phase.run_assistant_loop(db, "how are you")

        assert result["answer"] == "Just chatting, no tool needed."
        assert result["tool_calls"] == []

    def test_step_cap_prevents_runaway_loop(self, monkeypatch):
        db = _session()
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(assistant_phase, "MAX_ASSISTANT_STEPS", 2)

        tool_call = _tool_call("note_add", {"text": "loop forever"})
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = _completion_with_tool_calls([tool_call])
        monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)
        monkeypatch.setattr(
            "app.services.mentrix.permission_broker.check_tool_permission",
            lambda db, name, user_id=None, user_confirmed=False: {"result": "granted"},
        )
        monkeypatch.setattr(
            "app.services.mentrix.companion._exec_tool",
            lambda db, name, args, project_key="", created_by="": {"ok": True},
        )

        result = assistant_phase.run_assistant_loop(db, "keep adding notes forever")

        assert mock_client.chat.completions.create.call_count == 2
        assert "step limit" in result["answer"].lower()


class TestOrchestratorAssistantMode:
    def test_assistant_pipeline_registered(self):
        assert orchestrator.MODE_PIPELINE["assistant"] == ["assistant_loop"]

    def test_run_mentrix_assistant_mode_calls_the_loop(self, monkeypatch):
        db = _session()
        monkeypatch.setattr(
            "app.services.phases.assistant_phase.run_assistant_loop",
            lambda db, goal, **kw: {"answer": "Done — started an upgrade run.", "tool_calls": [{"tool": "start_upgrade_run"}]},
        )

        run = orchestrator.run_mentrix(db, goal="upgrade the auth module", mode="assistant", project_key="")

        result = json.loads(run.result_json) if getattr(run, "result_json", None) else None
        events = json.loads(run.events_json)
        assert any(e.get("phase") == "assistant_loop" for e in events)

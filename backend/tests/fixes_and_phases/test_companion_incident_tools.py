"""Companion incident tools route to Mentrix MCP hub."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.mentrix.companion import _exec_tool, _parse_intents


def test_parse_intents_jira_get_issue():
    tools = _parse_intents("Load Jira incident INC-42 for triage")
    names = [t["name"] for t in tools]
    assert "jira_get_issue" in names
    t = next(x for x in tools if x["name"] == "jira_get_issue")
    assert t["args"]["issue_key"] == "INC-42"


def test_parse_intents_search_incidents():
    tools = _parse_intents("search incidents in jira")
    assert any(t["name"] == "jira_search_incidents" for t in tools)


def test_exec_jira_get_issue_mocked():
    db = MagicMock()
    hub_out = {
        "status": "success",
        "result": {
            "key": "INC-9",
            "fields": {
                "summary": "API timeout",
                "status": {"name": "Open"},
                "issuetype": {"name": "Incident"},
                "description": "Service X timed out",
            },
        },
    }
    with patch("app.services.mcp.hub.execute_tool", return_value=hub_out) as ex:
        out = _exec_tool(db, "jira_get_issue", {"issue_key": "INC-9"}, created_by="u@test")
    assert out["ok"] is True
    assert out["issue_key"] == "INC-9"
    assert "API timeout" in out["delivery_goal"]
    ex.assert_called()
    assert ex.call_args.kwargs["server_id"] == "jira"
    assert ex.call_args.kwargs["tool_name"] == "get_issue"


def test_exec_datadog_query_mocked():
    db = MagicMock()
    hub_out = {"status": "success", "result": {"data": [{"attributes": {"message": "err"}}]}}
    with patch("app.services.mcp.hub.execute_tool", return_value=hub_out):
        out = _exec_tool(db, "datadog_query_logs", {"query": "status:error"})
    assert out["ok"] is True
    assert out["board"]["type"] == "table"


def test_exec_jira_comment_pr_mocked():
    db = MagicMock()
    hub_out = {"status": "success", "result": {"id": "c1"}}
    with patch("app.services.mcp.hub.execute_tool", return_value=hub_out) as ex:
        out = _exec_tool(
            db,
            "jira_comment_pr",
            {"issue_key": "INC-1", "pr_url": "https://github.com/o/r/pull/1"},
        )
    assert out["ok"] is True
    assert ex.call_args.kwargs["tool_name"] == "add_comment"

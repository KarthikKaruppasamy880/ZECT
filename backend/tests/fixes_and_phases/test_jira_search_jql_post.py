"""Jira MCP adapter uses POST /rest/api/3/search/jql."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.mcp.adapters import jira


def test_search_issues_posts_jql():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"issues": [{"key": "INC-1"}]}

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_resp

    with patch.dict(
        "os.environ",
        {
            "MCP_JIRA_URL": "https://example.atlassian.net",
            "JIRA_EMAIL": "u@example.com",
            "JIRA_API_TOKEN": "tok",
        },
        clear=False,
    ), patch("app.services.mcp.adapters.jira.httpx.Client", return_value=mock_client):
        out = jira.execute(
            "search_issues",
            {"jql": "issuetype = Incident", "max_results": 10},
            config={},
            enabled=True,
        )

    assert out["issues"][0]["key"] == "INC-1"
    mock_client.post.assert_called()
    url = mock_client.post.call_args[0][0]
    assert url.endswith("/rest/api/3/search/jql")
    body = mock_client.post.call_args[1]["json"]
    assert body["jql"] == "issuetype = Incident"
    assert body["maxResults"] == 10


def test_add_comment_sends_adf():
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"id": "1"}

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_resp

    with patch.dict(
        "os.environ",
        {
            "MCP_JIRA_URL": "https://example.atlassian.net",
            "JIRA_EMAIL": "u@example.com",
            "JIRA_API_TOKEN": "tok",
        },
        clear=False,
    ), patch("app.services.mcp.adapters.jira.httpx.Client", return_value=mock_client):
        out = jira.execute(
            "add_comment",
            {"issue_key": "INC-1", "body": "Mentrix PR: https://example.com/pr/1"},
            config={},
            enabled=True,
        )

    assert out["id"] == "1"
    payload = mock_client.post.call_args[1]["json"]
    assert payload["body"]["type"] == "doc"

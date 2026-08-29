"""The GitHub MCP adapter used to return a placeholder {"status": "accepted"}
for create_issue/create_pr/get_file/get_diff/list_branches/create_branch/
search_code/list_issues/list_commits/list_repos instead of calling GitHub.
Verifies each now dispatches to a real github_service call.
"""

from __future__ import annotations

from unittest.mock import patch

from app.adapters import github as github_adapter

CFG = {"token": "gh-test-token"}


class TestGithubAdapterRealDispatch:
    def test_create_issue_calls_github_service(self):
        with patch("app.github_service.create_issue", return_value={"number": 5, "html_url": "https://x", "title": "Bug", "state": "open"}) as mock_call:
            result = github_adapter.execute("create_issue", {"owner": "acme", "repo": "widgets", "title": "Bug", "body": "desc"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", "Bug", "desc")
        assert result["number"] == 5

    def test_create_pr_calls_github_service(self):
        with patch("app.github_service.create_pull_request", return_value={"number": 9, "html_url": "https://x", "title": "t", "state": "open"}) as mock_call:
            result = github_adapter.execute(
                "create_pr",
                {"owner": "acme", "repo": "widgets", "title": "t", "body": "b", "head": "feat", "base": "develop"},
                config=CFG, enabled=True,
            )

        mock_call.assert_called_once_with("acme", "widgets", "t", "b", "feat", "develop")
        assert result["number"] == 9

    def test_get_file_calls_github_service(self):
        with patch("app.github_service.get_file", return_value={"path": "a.py", "content": "x = 1"}) as mock_call:
            result = github_adapter.execute("get_file", {"owner": "acme", "repo": "widgets", "path": "a.py", "ref": "main"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", "a.py", "main")
        assert result["content"] == "x = 1"

    def test_get_diff_calls_github_service(self):
        with patch("app.github_service.get_diff", return_value={"files": []}) as mock_call:
            github_adapter.execute("get_diff", {"owner": "acme", "repo": "widgets", "base": "develop", "head": "feat"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", "develop", "feat")

    def test_list_branches_calls_github_service(self):
        with patch("app.github_service.list_branches", return_value=[{"name": "main"}]) as mock_call:
            result = github_adapter.execute("list_branches", {"owner": "acme", "repo": "widgets"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", limit=50)
        assert result["branches"] == [{"name": "main"}]

    def test_create_branch_calls_github_service(self):
        with patch("app.github_service.create_branch", return_value={"ref": "refs/heads/feat"}) as mock_call:
            github_adapter.execute("create_branch", {"owner": "acme", "repo": "widgets", "branch": "feat", "from_ref": "develop"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", "feat", "develop")

    def test_search_code_calls_github_service(self):
        with patch("app.github_service.search_code", return_value=[{"path": "a.py"}]) as mock_call:
            result = github_adapter.execute("search_code", {"owner": "acme", "repo": "widgets", "query": "TODO"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", "TODO", limit=20)
        assert result["results"] == [{"path": "a.py"}]

    def test_list_issues_calls_github_service(self):
        with patch("app.github_service.list_issues", return_value=[{"number": 1}]) as mock_call:
            result = github_adapter.execute("list_issues", {"owner": "acme", "repo": "widgets"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", state="open", limit=20)
        assert result["issues"] == [{"number": 1}]

    def test_list_commits_calls_github_service(self):
        with patch("app.github_service.list_commits", return_value=[]) as mock_call:
            github_adapter.execute("list_commits", {"owner": "acme", "repo": "widgets"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", "widgets", limit=20)

    def test_list_repos_calls_github_service(self):
        with patch("app.github_service.list_org_repos", return_value=[]) as mock_call:
            github_adapter.execute("list_repos", {"owner": "acme"}, config=CFG, enabled=True)

        mock_call.assert_called_once_with("acme", limit=30)

    def test_unknown_tool_still_falls_through(self):
        result = github_adapter.execute("not_a_real_tool", {"owner": "acme", "repo": "widgets"}, config=CFG, enabled=True)

        assert result["status"] == "unknown_tool"

    def test_disabled_short_circuits_before_any_github_call(self):
        result = github_adapter.execute("create_issue", {"owner": "acme", "repo": "widgets"}, config=CFG, enabled=False)

        assert result["status"] == "disabled"

    def test_no_token_short_circuits(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        result = github_adapter.execute("create_issue", {"owner": "acme", "repo": "widgets"}, config={}, enabled=True)

        assert result["status"] == "not_configured"

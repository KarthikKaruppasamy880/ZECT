"""BrowserTool rewiring (V2 closure §15/16/17).

The Coding Agent's own browser_* tools previously called
app.adapters.playwright_adapter.execute directly, bypassing the
BrowserRuntime/BrowserProvider abstraction the rest of Mentrix (the generic
MCP hub) already goes through -- a second, disconnected browser-automation
call path. Also adds Playwright MCP as an optional provider/interoperability
layer: core logic depends on the BrowserProvider Protocol, never a specific
MCP server, and never silently substitutes native Playwright when the MCP
server is unconfigured/unreachable.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.browser.runtime import (
    BrowserRuntime,
    PlaywrightMCPProvider,
    PlaywrightProvider,
    _origin_allowed,
)


class TestOriginAllowed:
    def test_empty_allowlist_allows_everything(self):
        assert _origin_allowed("https://anything.example/x", []) is True

    def test_exact_and_subdomain_match(self):
        allowed = ["example.com"]
        assert _origin_allowed("https://example.com/path", allowed) is True
        assert _origin_allowed("https://sub.example.com/path", allowed) is True

    def test_non_matching_origin_rejected(self):
        assert _origin_allowed("https://evil.example/x", ["example.com"]) is False


class TestBrowserRuntimeGovernance:
    def test_navigate_to_disallowed_origin_is_blocked_before_reaching_provider(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_BROWSER_ALLOWED_ORIGINS", "example.com")
        provider = MagicMock()
        rt = BrowserRuntime(provider=provider)
        out = rt.navigate("https://evil.example/x")
        assert out["ok"] is False
        assert "origin_not_allowed" in out["error"]
        provider.execute.assert_not_called()

    def test_navigate_to_allowed_origin_reaches_provider(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_BROWSER_ALLOWED_ORIGINS", "example.com")
        provider = MagicMock()
        provider.execute.return_value = {"status": "ok"}
        rt = BrowserRuntime(provider=provider)
        rt.navigate("https://example.com/x")
        provider.execute.assert_called_once()

    def test_no_allowlist_configured_reaches_provider(self, monkeypatch):
        monkeypatch.delenv("MENTRIX_BROWSER_ALLOWED_ORIGINS", raising=False)
        provider = MagicMock()
        provider.execute.return_value = {"status": "ok"}
        rt = BrowserRuntime(provider=provider)
        rt.navigate("https://anything.example/x")
        provider.execute.assert_called_once()


class TestPlaywrightMCPProviderNeverSilentlySubstitutes:
    def test_execute_without_configured_url_is_truthfully_not_configured(self, monkeypatch):
        monkeypatch.delenv("MENTRIX_PLAYWRIGHT_MCP_URL", raising=False)
        provider = PlaywrightMCPProvider()
        out = provider.execute("navigate", {"url": "https://example.com"})
        assert out["status"] == "not_configured"
        assert out["provider"] == "playwright_mcp"

    def test_status_without_configured_url_is_offline(self, monkeypatch):
        monkeypatch.delenv("MENTRIX_PLAYWRIGHT_MCP_URL", raising=False)
        st = PlaywrightMCPProvider().status()
        assert st["online"] is False

    def test_execute_disabled_never_calls_network(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_PLAYWRIGHT_MCP_URL", "http://127.0.0.1:9/mcp")
        provider = PlaywrightMCPProvider()
        with patch("httpx.post") as post:
            out = provider.execute("navigate", {"url": "https://example.com"}, enabled=False)
        assert out["status"] == "disabled"
        post.assert_not_called()

    def test_execute_makes_a_real_jsonrpc_tools_call_request(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_PLAYWRIGHT_MCP_URL", "http://127.0.0.1:9/mcp")
        provider = PlaywrightMCPProvider()
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"status": "ok", "url": "https://example.com/"}}
        with patch("httpx.post", return_value=fake_resp) as post:
            out = provider.execute("navigate", {"url": "https://example.com"})
        assert out["status"] == "ok"
        assert out["provider"] == "playwright_mcp"
        assert out["url"] == "https://example.com/"
        called_kwargs = post.call_args
        assert called_kwargs.args[0] == "http://127.0.0.1:9/mcp"
        body = called_kwargs.kwargs["json"]
        assert body["method"] == "tools/call"
        assert body["params"]["name"] == "navigate"

    def test_jsonrpc_error_response_is_reported_not_swallowed(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_PLAYWRIGHT_MCP_URL", "http://127.0.0.1:9/mcp")
        provider = PlaywrightMCPProvider()
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "boom"}}
        with patch("httpx.post", return_value=fake_resp):
            out = provider.execute("navigate", {"url": "https://example.com"})
        assert out["status"] == "error"
        assert "boom" in out["error"]

    def test_transport_failure_is_reported_not_swallowed(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_PLAYWRIGHT_MCP_URL", "http://127.0.0.1:9/mcp")
        provider = PlaywrightMCPProvider()
        with patch("httpx.post", side_effect=OSError("connection refused")):
            out = provider.execute("navigate", {"url": "https://example.com"})
        assert out["status"] == "error"
        assert "mcp_transport_error" in out["error"]


class TestCodingAgentBrowserToolsRouteThroughBrowserRuntime:
    def test_browser_navigate_dispatches_via_get_browser_runtime_not_playwright_adapter_directly(self, tmp_path):
        from app.services.coding_engine.mentrix_agent_tools import execute_tool

        with patch("app.services.browser.runtime.get_browser_runtime") as get_rt:
            rt = MagicMock()
            rt.run.return_value = {"status": "ok", "url": "https://example.com/", "provider": "playwright"}
            get_rt.return_value = rt
            out = execute_tool("browser_navigate", {"url": "https://example.com"}, workspace=tmp_path)
        assert out["ok"] is True
        rt.run.assert_called_once_with("navigate", {"url": "https://example.com"})

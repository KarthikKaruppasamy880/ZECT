"""Playwright Mentrix MCP adapter — not_configured / mocked navigate."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.adapters import playwright_adapter as pw


def test_playwright_disabled():
    out = pw.execute("navigate", {"url": "https://example.com"}, config={}, enabled=False)
    assert out["status"] == "disabled"


def test_playwright_not_installed():
    with patch.object(pw, "_pw_available", return_value=(False, "Playwright not installed")):
        out = pw.execute("navigate", {"url": "https://example.com"}, config={}, enabled=True)
    assert out["status"] == "not_configured"
    assert "Playwright" in out["message"]


def test_playwright_navigate_mocked():
    page = MagicMock()
    page.url = "https://example.com/"
    page.title.return_value = "Example"
    context = MagicMock()
    context.new_page.return_value = page

    with patch.object(pw, "_pw_available", return_value=(True, "")), patch.object(
        pw, "_get_page", return_value=(context, page)
    ):
        out = pw.execute("navigate", {"url": "https://example.com"}, config={}, enabled=True)

    assert out["status"] == "ok"
    page.goto.assert_called()
    context.close.assert_called()


def test_browser_runtime_dispatches_to_playwright():
    from app.services.browser.runtime import BrowserRuntime, PlaywrightProvider

    page = MagicMock()
    page.url = "https://example.com/"
    page.title.return_value = "Example"
    context = MagicMock()
    context.new_page.return_value = page

    rt = BrowserRuntime(provider=PlaywrightProvider())
    with patch.object(pw, "_pw_available", return_value=(True, "")), patch.object(
        pw, "_get_page", return_value=(context, page)
    ):
        out = rt.navigate("https://example.com")
    assert out["status"] == "ok"
    assert out.get("provider") == "playwright"
    assert out.get("label") == "Browser automation"


def test_mcp_hub_playwright_uses_browser_runtime():
    from app.services.mcp import hub

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []

    with patch("app.services.browser.runtime.get_browser_runtime") as get_rt:
        rt = MagicMock()
        rt.run.return_value = {"status": "ok", "provider": "playwright", "url": "https://x"}
        rt.status.return_value = {"online": True, "provider": "playwright", "label": "Browser automation"}
        get_rt.return_value = rt
        out = hub.execute_tool(
            db,
            server_id="playwright",
            tool_name="navigate",
            arguments={"url": "https://x"},
            user_email="t@example.com",
        )
    assert out["status"] == "success"
    rt.run.assert_called_once()
    assert out["result"]["provider"] == "playwright"


def test_browser_runtime_status_offline_hint():
    from app.services.browser.runtime import BrowserRuntime, PlaywrightProvider

    rt = BrowserRuntime(provider=PlaywrightProvider())
    with patch.object(pw, "_pw_available", return_value=(False, "Playwright not installed. Run: pip install playwright")):
        st = rt.status()
    assert st["online"] is False
    assert "pip install playwright" in st["hint"]

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

"""ZECT Mentrix Playwright MCP adapter — local browser automation (no external IDE)."""

from __future__ import annotations

import os
from typing import Any

# Module-level browser reuse for a single process (optional).
_browser = None
_playwright = None


def _pw_available() -> tuple[bool, str]:
    try:
        import playwright  # noqa: F401
        from playwright.sync_api import sync_playwright  # noqa: F401

        return True, ""
    except ImportError:
        return False, (
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        )


def _get_page():
    global _browser, _playwright
    from playwright.sync_api import sync_playwright

    if _browser is None:
        _playwright = sync_playwright().start()
        headless = os.getenv("MENTRIX_PLAYWRIGHT_HEADLESS", "1") != "0"
        _browser = _playwright.chromium.launch(headless=headless)
    context = _browser.new_context()
    return context, context.new_page()


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    ok, msg = _pw_available()
    if not ok:
        return {
            "status": "not_configured",
            "message": msg,
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }

    if tool_name == "status":
        return {"status": "ready", "engine": "chromium"}

    try:
        context, page = _get_page()
        try:
            if tool_name == "navigate":
                url = arguments.get("url") or arguments.get("path") or ""
                if not url:
                    return {"status": "error", "message": "url required"}
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                return {"status": "ok", "url": page.url, "title": page.title()}
            if tool_name == "snapshot":
                url = arguments.get("url")
                if url:
                    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                text = page.inner_text("body")[:8000]
                return {
                    "status": "ok",
                    "url": page.url,
                    "title": page.title(),
                    "text": text,
                }
            if tool_name == "click":
                selector = arguments.get("selector") or ""
                if not selector:
                    return {"status": "error", "message": "selector required"}
                page.click(selector, timeout=15_000)
                return {"status": "ok", "clicked": selector, "url": page.url}
            if tool_name == "fill":
                selector = arguments.get("selector") or ""
                value = arguments.get("value", "")
                if not selector:
                    return {"status": "error", "message": "selector required"}
                page.fill(selector, str(value), timeout=15_000)
                return {"status": "ok", "filled": selector, "url": page.url}
            return {"status": "unknown_tool", "tool": tool_name}
        finally:
            context.close()
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc), "tool": tool_name}

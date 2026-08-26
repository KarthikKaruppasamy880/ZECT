"""Browser verification tools the Coding Agent needs but didn't have:
select_option, screenshot, wait_for, assert_text/assert_visible, and
console/network evidence attached to every action (not opt-in).

One real end-to-end pass against a local page with a deliberate console
error, a broken image request, and a <select> -- skipped automatically if
this environment has no launchable Chromium (CI portability), plus fast
mocked-page tests for the argument-validation paths matching the existing
test_mcp_playwright_adapter.py convention."""

from __future__ import annotations

import http.server
import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.adapters import playwright_adapter as pw


def teardown_module(_module) -> None:
    # This file launches a real Chromium + Playwright driver -- without an
    # explicit shutdown it stays alive for the rest of the pytest session
    # and can interfere with unrelated tests that run after it.
    pw.shutdown()

_PAGE_HTML = b"""<!doctype html>
<html><body>
<h1 id="title">Hello ZECT</h1>
<select id="lang"><option value="py">Python</option><option value="ts">TypeScript</option></select>
<img src="/does-not-exist.png" />
<script>console.error("boom: deliberate test error");</script>
</body></html>"""


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True
    except Exception:
        return False


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/does-not-exist.png":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(_PAGE_HTML)

    def log_message(self, *_args):
        pass  # keep test output quiet


@pytest.fixture()
def local_page_url():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()


@pytest.mark.skipif(not _chromium_available(), reason="no launchable Chromium in this environment")
class TestRealBrowserVerification:
    def test_navigate_captures_real_console_and_network_evidence(self, local_page_url):
        out = pw.execute("navigate", {"url": local_page_url}, config={}, enabled=True)
        assert out["status"] == "ok"
        assert any("boom" in e["text"] for e in out["console_errors"])
        assert any(f["url"].endswith("does-not-exist.png") for f in out["network_failures"])

    def test_select_option_real(self, local_page_url):
        # Same single-call pattern as fill/click/snapshot: an inline url
        # navigates first, then the action runs on that same fresh page.
        out = pw.execute(
            "select_option", {"url": local_page_url, "selector": "#lang", "value": "ts"}, config={}, enabled=True
        )
        assert out["status"] == "ok"
        assert out["value"] == ["ts"]

    def test_screenshot_and_wait_for_and_assertions_real(self, local_page_url):
        shot = pw.execute("screenshot", {"url": local_page_url}, config={}, enabled=True)
        assert shot["status"] == "ok"
        assert isinstance(shot["png_bytes"], (bytes, bytearray)) and len(shot["png_bytes"]) > 100

        waited = pw.execute(
            "wait_for", {"url": local_page_url, "selector": "#title"}, config={}, enabled=True
        )
        assert waited["status"] == "ok"

        text_ok = pw.execute(
            "assert_text", {"url": local_page_url, "selector": "#title", "expected": "Hello ZECT"},
            config={}, enabled=True,
        )
        assert text_ok["verified"] is True

        text_bad = pw.execute(
            "assert_text", {"url": local_page_url, "selector": "#title", "expected": "Nope"},
            config={}, enabled=True,
        )
        assert text_bad["verified"] is False

        visible = pw.execute(
            "assert_visible", {"url": local_page_url, "selector": "#title"}, config={}, enabled=True
        )
        assert visible["verified"] is True


class TestArgumentValidationWithMockedPage:
    """Matches the existing test_mcp_playwright_adapter.py mocked-page convention."""

    def _mocked(self):
        page = MagicMock()
        page.url = "https://example.com/"
        context = MagicMock()
        context.new_page.return_value = page
        return context, page

    def test_select_option_requires_selector(self):
        context, page = self._mocked()
        with patch.object(pw, "_pw_available", return_value=(True, "")), patch.object(
            pw, "_get_page", return_value=(context, page)
        ):
            out = pw.execute("select_option", {"value": "x"}, config={}, enabled=True)
        assert out["status"] == "error"

    def test_assert_text_requires_expected(self):
        context, page = self._mocked()
        with patch.object(pw, "_pw_available", return_value=(True, "")), patch.object(
            pw, "_get_page", return_value=(context, page)
        ):
            out = pw.execute("assert_text", {"selector": "#x"}, config={}, enabled=True)
        assert out["status"] == "error"

    def test_evidence_tolerates_mocked_page_without_crashing(self):
        """A bare MagicMock page (no real listener-populated lists) must not
        raise -- console_errors/network_failures degrade to empty, not a
        TypeError from trying to iterate a MagicMock attribute."""
        context, page = self._mocked()
        page.title.return_value = "Example"
        with patch.object(pw, "_pw_available", return_value=(True, "")), patch.object(
            pw, "_get_page", return_value=(context, page)
        ):
            out = pw.execute("navigate", {"url": "https://example.com"}, config={}, enabled=True)
        assert out["console_errors"] == []
        assert out["network_failures"] == []

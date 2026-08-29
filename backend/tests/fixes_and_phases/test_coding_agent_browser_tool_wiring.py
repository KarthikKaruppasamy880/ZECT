"""The browser_* Coding Agent tools must be real entries in TOOL_SPECS (the
agent can actually call them) and dispatch to playwright_adapter with the
workspace's evidence directory wired in -- not a second, disconnected
browser-automation implementation."""

from __future__ import annotations

import http.server
import socket
import threading

import pytest

from app.adapters import playwright_adapter as pw
from app.services.coding_engine.mentrix_agent_tools import TOOL_SPECS, execute_tool


def teardown_module(_module) -> None:
    pw.shutdown()

_PAGE_HTML = b"<!doctype html><html><body><h1 id='t'>hi</h1></body></html>"


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
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(_PAGE_HTML)

    def log_message(self, *_args):
        pass


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


def test_all_browser_tools_are_registered():
    names = {spec["function"]["name"] for spec in TOOL_SPECS}
    expected = {
        "browser_navigate",
        "browser_snapshot",
        "browser_click",
        "browser_type",
        "browser_select",
        "browser_screenshot",
        "browser_wait_for",
        "browser_assert_text",
        "browser_assert_visible",
        "browser_console_errors",
        "browser_network_failures",
        "start_app",
        "restart_app",
        "stop_app",
        "health_check",
    }
    missing = expected - names
    assert not missing, f"tools missing from TOOL_SPECS: {missing}"


@pytest.mark.skipif(not _chromium_available(), reason="no launchable Chromium in this environment")
class TestBrowserToolDispatch:
    def test_browser_navigate_reaches_the_real_adapter(self, tmp_path, local_page_url):
        out = execute_tool("browser_navigate", {"url": local_page_url}, workspace=tmp_path)
        assert out["ok"] is True
        assert out["url"] == local_page_url

    def test_browser_assert_text_real(self, tmp_path, local_page_url):
        out = execute_tool(
            "browser_assert_text", {"url": local_page_url, "selector": "#t", "expected": "hi"},
            workspace=tmp_path,
        )
        assert out["ok"] is True

    def test_browser_screenshot_is_saved_under_workspace_evidence_not_inlined(self, tmp_path, local_page_url):
        out = execute_tool("browser_screenshot", {"url": local_page_url}, workspace=tmp_path)
        assert out["ok"] is True
        assert "png_bytes" not in out, "raw bytes must not be inlined into the tool-result payload"
        rel_path = out["screenshot_path"]
        assert rel_path.startswith(".zect/evidence/screenshots/")
        saved = tmp_path / rel_path
        assert saved.is_file()
        assert saved.stat().st_size > 100
        assert out["screenshot_preview_b64"]

    def test_unknown_recipe_id_for_start_app_is_a_clean_error_not_a_crash(self, tmp_path):
        out = execute_tool("start_app", {"recipe_id": "does-not-exist"}, workspace=tmp_path)
        assert out["ok"] is False
        assert "unknown_recipe_id" in out["error"]

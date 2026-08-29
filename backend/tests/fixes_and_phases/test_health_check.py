"""Bounded port/HTTP readiness probe used by the Coding Agent's start_app tool."""

from __future__ import annotations

import http.server
import socket
import threading

from app.services.workspace.health_check import wait_for_port_healthy


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestWaitForPortHealthy:
    def test_reports_healthy_once_a_real_server_is_listening(self):
        port = _free_port()
        server = http.server.HTTPServer(("127.0.0.1", port), http.server.BaseHTTPRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = wait_for_port_healthy("127.0.0.1", port, timeout_s=5)
        finally:
            server.shutdown()
        assert result["ok"] is True
        assert result["status_code"] is not None

    def test_bounded_timeout_when_nothing_is_listening(self):
        port = _free_port()  # guaranteed free, nothing bound here
        result = wait_for_port_healthy("127.0.0.1", port, timeout_s=1.5, poll_interval_s=0.3)
        assert result["ok"] is False
        assert result["elapsed_s"] < 3, "must not block meaningfully longer than timeout_s"
        assert result["error"]

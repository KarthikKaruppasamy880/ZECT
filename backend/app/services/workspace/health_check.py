"""Bounded readiness probe for an App Runner-owned process's port.

Nothing in the codebase answered "is the app I just started actually up"
before this -- the Mentrix Coding Agent's start_app/restart_app tools need
one bounded, synchronous call rather than making the model manually poll
across tool-loop turns.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from typing import Any


def wait_for_port_healthy(
    host: str,
    port: int,
    *,
    path: str = "/",
    timeout_s: float = 20.0,
    poll_interval_s: float = 1.0,
) -> dict[str, Any]:
    """Poll until the port accepts a TCP connection and (if an HTTP path is
    reachable) returns any response, up to ``timeout_s``. Never blocks longer
    than that -- a hung dev server must surface as a bounded failure, not an
    indefinite hang in the agent loop."""
    start = time.monotonic()
    last_error = ""
    while time.monotonic() - start < timeout_s:
        try:
            with socket.create_connection((host, port), timeout=2):
                pass
        except OSError as exc:
            last_error = f"port_closed:{exc}"
            time.sleep(poll_interval_s)
            continue

        status_code: int | None = None
        try:
            req = urllib.request.Request(f"http://{host}:{port}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                status_code = resp.status
        except urllib.error.HTTPError as exc:
            # Any HTTP response -- even an error page -- means the app is up.
            status_code = exc.code
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_error = f"http_unreachable:{exc}"
            time.sleep(poll_interval_s)
            continue

        return {
            "ok": True,
            "host": host,
            "port": port,
            "status_code": status_code,
            "elapsed_s": round(time.monotonic() - start, 2),
        }

    return {
        "ok": False,
        "host": host,
        "port": port,
        "status_code": None,
        "elapsed_s": round(time.monotonic() - start, 2),
        "error": last_error or "timeout",
    }

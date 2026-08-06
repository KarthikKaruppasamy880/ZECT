"""Allowlisted browser URL helpers for Companion → BrowserRuntime."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def browser_allowlist() -> list[str]:
    raw = (os.getenv("MENTRIX_BROWSER_ALLOWLIST") or "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [h.strip().lower() for h in raw.split(",") if h.strip()]


def host_allowed(url: str) -> tuple[bool, str]:
    """Return (ok, reason). Empty allowlist or * permits all http(s) hosts."""
    u = (url or "").strip()
    if not u:
        return False, "url required"
    parsed = urlparse(u if "://" in u else f"https://{u}")
    if parsed.scheme not in ("http", "https"):
        return False, "only http/https allowed"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "host required"
    allow = browser_allowlist()
    if "*" in allow:
        return True, ""
    if host in allow:
        return True, ""
    if any(host == a or host.endswith("." + a) for a in allow):
        return True, ""
    return False, f"host {host} not in MENTRIX_BROWSER_ALLOWLIST"

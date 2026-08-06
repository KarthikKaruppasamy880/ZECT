"""Mentrix BrowserRuntime — Playwright is the primary browser engine."""

from __future__ import annotations

import os
from typing import Any, Protocol

# Reserved for a future reasoning provider (no third-party product names in UI).
DEFAULT_BROWSER_PROVIDER = os.getenv("MENTRIX_BROWSER_PROVIDER", "playwright").strip().lower() or "playwright"


class BrowserProvider(Protocol):
    def status(self) -> dict[str, Any]: ...

    def execute(self, tool_name: str, arguments: dict[str, Any], *, enabled: bool = True) -> dict[str, Any]: ...


class PlaywrightProvider:
    """Wraps the existing Playwright MCP adapter (no duplicate browser lifecycle)."""

    name = "playwright"
    ui_label = "Browser automation"

    def status(self) -> dict[str, Any]:
        from app.adapters.playwright_adapter import _pw_available

        ok, msg = _pw_available()
        if not ok:
            return {
                "online": False,
                "provider": self.name,
                "label": self.ui_label,
                "hint": msg
                or "Install Playwright: pip install playwright && playwright install chromium",
            }
        return {
            "online": True,
            "provider": self.name,
            "label": self.ui_label,
            "hint": "Playwright Chromium ready for Mentrix browser tools.",
        }

    def execute(self, tool_name: str, arguments: dict[str, Any], *, enabled: bool = True) -> dict[str, Any]:
        from app.adapters import playwright_adapter as pw

        out = pw.execute(tool_name, arguments or {}, config={}, enabled=enabled)
        if isinstance(out, dict) and "provider" not in out:
            out = {**out, "provider": self.name, "label": self.ui_label}
        return out


class ReasoningBrowserStub:
    """Placeholder provider — not wired until a Later phase. Never claims ready."""

    name = "reasoning_stub"
    ui_label = "Browser automation (reasoning — not configured)"

    def status(self) -> dict[str, Any]:
        return {
            "online": False,
            "provider": self.name,
            "label": self.ui_label,
            "hint": "Reasoning browser provider is reserved for Later — Playwright remains primary.",
        }

    def execute(self, tool_name: str, arguments: dict[str, Any], *, enabled: bool = True) -> dict[str, Any]:
        return {
            "status": "not_configured",
            "provider": self.name,
            "message": "Reasoning browser provider not enabled — use Playwright primary.",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }


class BrowserRuntime:
    def __init__(self, provider: BrowserProvider | None = None):
        self.provider = provider or self._resolve_provider()

    @staticmethod
    def _resolve_provider() -> BrowserProvider:
        if DEFAULT_BROWSER_PROVIDER in ("reasoning", "reasoning_stub"):
            return ReasoningBrowserStub()
        return PlaywrightProvider()

    def status(self) -> dict[str, Any]:
        st = self.provider.status()
        st.setdefault(
            "primary",
            DEFAULT_BROWSER_PROVIDER == "playwright" or isinstance(self.provider, PlaywrightProvider),
        )
        return st

    def navigate(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return self.run("navigate", {"url": url, **kwargs})

    def snapshot(self, **kwargs: Any) -> dict[str, Any]:
        return self.run("snapshot", kwargs)

    def click(self, selector: str, **kwargs: Any) -> dict[str, Any]:
        return self.run("click", {"selector": selector, **kwargs})

    def fill(self, selector: str, value: str, **kwargs: Any) -> dict[str, Any]:
        return self.run("fill", {"selector": selector, "value": value, **kwargs})

    def run(self, tool_name: str, arguments: dict[str, Any] | None = None, *, enabled: bool = True) -> dict[str, Any]:
        return self.provider.execute(tool_name, arguments or {}, enabled=enabled)


_runtime: BrowserRuntime | None = None


def get_browser_runtime() -> BrowserRuntime:
    global _runtime
    if _runtime is None:
        _runtime = BrowserRuntime()
    return _runtime

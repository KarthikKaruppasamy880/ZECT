"""Mentrix BrowserRuntime — Playwright is the primary browser engine.

Playwright MCP is an optional interoperability layer (V2 closure §16): core
logic (ZECT BrowserTool / this module) depends only on the BrowserProvider
Protocol, never on a specific MCP server. MCP calls still pass through this
module's own governance (allowed-origin check) before reaching the wire, so
switching providers cannot bypass workspace/network policy.
"""

from __future__ import annotations

import os
from typing import Any, Protocol
from urllib.parse import urlparse

# Reserved for a future reasoning provider (no third-party product names in UI).
DEFAULT_BROWSER_PROVIDER = os.getenv("MENTRIX_BROWSER_PROVIDER", "playwright").strip().lower() or "playwright"


def _browser_config_from_env() -> dict[str, Any]:
    """Provider/server, headed/headless, allowed origins, artifact path,
    timeout and trace/video/screenshot policy -- read fresh on every call so
    tests (and operators) can change env vars without restarting."""
    origins = [o.strip() for o in os.getenv("MENTRIX_BROWSER_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    return {
        "provider": DEFAULT_BROWSER_PROVIDER,
        "headless": os.getenv("MENTRIX_PLAYWRIGHT_HEADLESS", "1") != "0",
        "allowed_origins": origins,
        "artifact_dir": os.getenv("MENTRIX_BROWSER_ARTIFACT_DIR", ".zect/evidence/screenshots"),
        "timeout_s": float(os.getenv("MENTRIX_BROWSER_TIMEOUT_S", "30") or 30),
        "trace_policy": os.getenv("MENTRIX_BROWSER_TRACE_POLICY", "off").strip().lower() or "off",
        "mcp_url": os.getenv("MENTRIX_PLAYWRIGHT_MCP_URL", "").strip(),
    }


def _origin_allowed(url: str, allowed_origins: list[str]) -> bool:
    if not allowed_origins or not url:
        return True
    try:
        origin = urlparse(url).netloc.lower()
    except ValueError:
        return False
    return any(origin == o.lower() or origin.endswith(f".{o.lower()}") for o in allowed_origins)


class BrowserProvider(Protocol):
    def status(self) -> dict[str, Any]: ...

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]: ...


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

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        from app.adapters import playwright_adapter as pw

        out = pw.execute(tool_name, arguments or {}, config=config or {}, enabled=enabled)
        if isinstance(out, dict) and "provider" not in out:
            out = {**out, "provider": self.name, "label": self.ui_label}
        return out


class PlaywrightMCPProvider:
    """Optional interoperability layer (V2 closure §16): calls a configured
    Playwright MCP server over JSON-RPC instead of the in-process Playwright
    adapter. Never silently falls back to native Playwright when the server
    is unconfigured/unreachable -- callers get a truthful not_configured/
    error status instead, the same no-silent-substitution discipline used
    for LLM provider routing."""

    name = "playwright_mcp"
    ui_label = "Browser automation (Playwright MCP)"

    def status(self) -> dict[str, Any]:
        url = _browser_config_from_env().get("mcp_url") or ""
        if not url:
            return {
                "online": False,
                "provider": self.name,
                "label": self.ui_label,
                "hint": "Set MENTRIX_PLAYWRIGHT_MCP_URL to point at a Playwright MCP server.",
            }
        try:
            import httpx

            resp = httpx.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, timeout=5.0)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return {
                "online": False,
                "provider": self.name,
                "label": self.ui_label,
                "hint": f"Playwright MCP server unreachable: {exc}",
            }
        return {
            "online": True,
            "provider": self.name,
            "label": self.ui_label,
            "hint": f"Playwright MCP server reachable at {url}.",
        }

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        if not enabled:
            return {"status": "disabled", "provider": self.name}
        cfg = config if config is not None else _browser_config_from_env()
        url = str(cfg.get("mcp_url") or "").strip()
        if not url:
            return {
                "status": "not_configured",
                "provider": self.name,
                "message": "MENTRIX_PLAYWRIGHT_MCP_URL is not set -- not silently substituting native Playwright.",
                "dry_run": {"tool": tool_name, "arguments": arguments},
            }
        timeout_s = float(cfg.get("timeout_s") or 30.0)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments or {}},
        }
        try:
            import httpx

            resp = httpx.post(url, json=payload, timeout=timeout_s)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "provider": self.name, "error": f"mcp_transport_error: {exc}"}
        if isinstance(data, dict) and data.get("error"):
            return {"status": "error", "provider": self.name, "error": str(data["error"])}
        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, dict):
            out = dict(result)
            out.setdefault("status", "ok")
            out["provider"] = self.name
            return out
        return {"status": "ok", "provider": self.name, "result": result}


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

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        config: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
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
        if DEFAULT_BROWSER_PROVIDER in ("playwright_mcp", "mcp"):
            return PlaywrightMCPProvider()
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
        args = arguments or {}
        cfg = _browser_config_from_env()
        url = str(args.get("url") or "")
        if url and not _origin_allowed(url, cfg.get("allowed_origins") or []):
            return {
                "ok": False,
                "status": "blocked",
                "error": f"origin_not_allowed:{url}",
                "provider": getattr(self.provider, "name", ""),
            }
        return self.provider.execute(tool_name, args, config=cfg, enabled=enabled)


_runtime: BrowserRuntime | None = None


def get_browser_runtime() -> BrowserRuntime:
    global _runtime
    if _runtime is None:
        _runtime = BrowserRuntime()
    return _runtime

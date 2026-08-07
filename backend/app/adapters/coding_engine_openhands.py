"""Internal Agent Server adapter (coding-engine remote provider).

Public product names remain mock|remote only. This module specializes the remote
HTTP client for the pinned Agent Server protocol used as ZECT CodingRuntime.
Do not surface third-party product names in routes, UI, DB, or API payloads.
"""

from __future__ import annotations

from typing import Any

from app.adapters.coding_engine_remote import (
    CodingEngineConfigError,
    CodingEngineRequestError,
    RemoteCodingEngine,
)


class AgentServerCodingEngine(RemoteCodingEngine):
    """RemoteCodingEngine with Agent Server conversation + health path preferences.

    Extends remote paths that the independently running coding Agent Server exposes.
    Credentials stay server-side (ZECT_CODING_ENGINE_URL / ZECT_CODING_ENGINE_API_KEY).
    """

    provider_name = "remote"

    def health(self) -> dict[str, Any]:
        """Prefer Agent Server health endpoints, then fall back to remote probes."""
        last_err = "no_response"
        preferred = (
            "api/health",
            "health",
            "alive",
            "ready",
            "server_info",
            "api/server_info",
        )
        for path in preferred:
            try:
                with self._client_factory(timeout=self.timeout) as client:
                    resp = client.get(self._url(path), headers=self._headers())
                if resp.status_code >= 400:
                    last_err = f"http_{resp.status_code}"
                    continue
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": (resp.text or "")[:200]}
                version = None
                if isinstance(body, dict):
                    version = (
                        body.get("version")
                        or body.get("server_version")
                        or body.get("agent_server_version")
                    )
                return {
                    "provider": self.provider_name,
                    "ready": True,
                    "version": version,
                    "detail": f"remote_{path.replace('/', '_')}_ok",
                }
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)[:200]
                continue
        return {
            "provider": self.provider_name,
            "ready": False,
            "version": None,
            "detail": f"remote_unreachable:{last_err}",
        }

    def start_run(self, goal: str, workspace: str = "", **kwargs: Any) -> str:
        """Start an Agent Server conversation; workspace is mounted isolation only."""
        # Strip any accidental third-party branding keys from kwargs before POST
        clean = {
            k: v
            for k, v in kwargs.items()
            if k
            not in (
                "openhands",
                "provider_brand",
                "engine_brand",
            )
        }
        return super().start_run(goal, workspace=workspace, **clean)


def build_agent_server_engine(**kwargs: Any) -> AgentServerCodingEngine:
    """Factory used by get_coding_runtime when ZECT_CODING_ENGINE=remote."""
    try:
        return AgentServerCodingEngine.from_env(**kwargs)
    except CodingEngineConfigError:
        raise


__all__ = [
    "AgentServerCodingEngine",
    "CodingEngineConfigError",
    "CodingEngineRequestError",
    "build_agent_server_engine",
]

"""Remote coding-engine adapter (Stage A stub).

Talks to an independently running Agent Server over HTTP. Credentials stay
server-side. Full conversation/event streaming lands in Stage B — Stage A
only probes health and enforces configuration.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

import httpx

from app.adapters.coding_runtime import RuntimeArtifact, RuntimeEvent


class CodingEngineConfigError(RuntimeError):
    """Remote engine selected but URL/API key missing or unreachable."""


class RemoteCodingEngine:
    """HTTP client for the external coding Agent Server (ZECT-owned interface)."""

    provider_name = "remote"

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout = timeout
        self._runs: dict[str, dict[str, Any]] = {}

    @classmethod
    def from_env(cls) -> "RemoteCodingEngine":
        url = (os.getenv("ZECT_CODING_ENGINE_URL") or "").strip()
        key = (os.getenv("ZECT_CODING_ENGINE_API_KEY") or "").strip()
        if not url or not key:
            raise CodingEngineConfigError(
                "ZECT_CODING_ENGINE=remote requires ZECT_CODING_ENGINE_URL and "
                "ZECT_CODING_ENGINE_API_KEY (server-side only; never expose to the browser)."
            )
        return cls(url, key)

    def _headers(self) -> dict[str, str]:
        return {"X-Session-API-Key": self.api_key, "Accept": "application/json"}

    def health(self) -> dict[str, Any]:
        """Probe remote /health or /ready. Never includes the API key in the payload."""
        last_err = "no_response"
        for path in ("health", "ready", "server_info"):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(urljoin(self.base_url, path), headers=self._headers())
                if resp.status_code >= 400:
                    last_err = f"http_{resp.status_code}"
                    continue
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": (resp.text or "")[:200]}
                version = None
                if isinstance(body, dict):
                    version = body.get("version") or body.get("server_version")
                return {
                    "provider": self.provider_name,
                    "ready": True,
                    "version": version,
                    "detail": f"remote_{path}_ok",
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
        raise CodingEngineConfigError(
            "Remote coding-engine start_run is Stage B — configure health only in Stage A."
        )

    def get_run(self, run_id: str) -> dict[str, Any]:
        raise CodingEngineConfigError("Remote get_run is Stage B")

    def stream_events(self, run_id: str, after: int = 0) -> list[RuntimeEvent]:
        raise CodingEngineConfigError("Remote stream_events is Stage B")

    def submit_message(self, run_id: str, message: str) -> None:
        raise CodingEngineConfigError("Remote submit_message is Stage B")

    def approve_action(self, run_id: str, action_id: str) -> None:
        raise CodingEngineConfigError("Remote approve_action is Stage B")

    def reject_action(self, run_id: str, action_id: str) -> None:
        raise CodingEngineConfigError("Remote reject_action is Stage B")

    def cancel_run(self, run_id: str) -> None:
        raise CodingEngineConfigError("Remote cancel_run is Stage B")

    def get_artifacts(self, run_id: str) -> list[RuntimeArtifact]:
        raise CodingEngineConfigError("Remote get_artifacts is Stage B")

    def dispose_workspace(self, run_id: str) -> None:
        raise CodingEngineConfigError("Remote dispose_workspace is Stage B")

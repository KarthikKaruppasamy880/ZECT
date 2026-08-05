"""Remote coding-engine adapter (Phase 2 Stage B).

HTTP client for an independently running Agent Server. Credentials stay
server-side. Remote event shapes are translated to ZECT RuntimeEvent only.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable
from urllib.parse import urljoin

import httpx

from app.adapters.coding_engine_events import translate_remote_events
from app.adapters.coding_runtime import RuntimeArtifact, RuntimeEvent

HttpFactory = Callable[..., httpx.Client]


class CodingEngineConfigError(RuntimeError):
    """Remote engine selected but URL/API key missing or unreachable."""


class CodingEngineRequestError(RuntimeError):
    """Remote HTTP call failed after retries."""


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class RemoteCodingEngine:
    """HTTP client for the external coding Agent Server (ZECT-owned interface)."""

    provider_name = "remote"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        client_factory: HttpFactory | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout = timeout if timeout is not None else _env_float("ZECT_CODING_ENGINE_TIMEOUT", 30.0)
        self.max_retries = (
            max_retries if max_retries is not None else _env_int("ZECT_CODING_ENGINE_RETRIES", 2)
        )
        self._client_factory: HttpFactory = client_factory or httpx.Client
        # Local mirror of remote conversation state (ZECT run_id → meta)
        self._runs: dict[str, dict[str, Any]] = {}

    @classmethod
    def from_env(cls, **kwargs: Any) -> "RemoteCodingEngine":
        url = (os.getenv("ZECT_CODING_ENGINE_URL") or "").strip()
        key = (os.getenv("ZECT_CODING_ENGINE_API_KEY") or "").strip()
        if not url or not key:
            raise CodingEngineConfigError(
                "ZECT_CODING_ENGINE=remote requires ZECT_CODING_ENGINE_URL and "
                "ZECT_CODING_ENGINE_API_KEY (server-side only; never expose to the browser)."
            )
        return cls(url, key, **kwargs)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Session-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, *parts: str) -> str:
        path = "/".join(p.strip("/") for p in parts if p)
        return urljoin(self.base_url, path)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = self._url(path)
        last_err: Exception | None = None
        attempts = max(1, self.max_retries + 1)
        for attempt in range(attempts):
            try:
                with self._client_factory(timeout=self.timeout) as client:
                    resp = client.request(
                        method,
                        url,
                        headers=self._headers(),
                        json=json_body,
                        params=params,
                    )
                if resp.status_code >= 500 and attempt < attempts - 1:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                if resp.status_code >= 400:
                    raise CodingEngineRequestError(
                        f"remote_{method.lower()}_{resp.status_code}:{(resp.text or '')[:300]}"
                    )
                if not (resp.content or b"").strip():
                    return {}
                try:
                    return resp.json()
                except Exception:
                    return {"raw": (resp.text or "")[:500]}
            except CodingEngineRequestError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                if attempt < attempts - 1:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                raise CodingEngineRequestError(f"remote_unreachable:{exc}") from exc
        raise CodingEngineRequestError(f"remote_unreachable:{last_err}")

    def health(self) -> dict[str, Any]:
        """Probe remote liveness. Never includes the API key in the payload."""
        last_err = "no_response"
        for path in ("health", "alive", "ready", "server_info", "api/health"):
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
                    version = body.get("version") or body.get("server_version")
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
        """Create a remote conversation and seed the goal as the first message."""
        if not (goal or "").strip():
            raise CodingEngineConfigError("goal is required")
        body: dict[str, Any] = {
            "initial_user_message": goal.strip(),
        }
        if workspace:
            body["working_dir"] = workspace
            body["workspace"] = workspace
        # Optional passthrough keys (agent config) — never include secrets from kwargs
        for key in ("repo", "branch", "max_iterations"):
            if key in kwargs and kwargs[key] is not None:
                body[key] = kwargs[key]

        data = self._request("POST", "api/conversations", json_body=body)
        if not isinstance(data, dict):
            data = {}
        remote_id = (
            data.get("id")
            or data.get("conversation_id")
            or data.get("conversationId")
            or (data.get("conversation") or {}).get("id")
        )
        if not remote_id:
            # Some servers return the id as a bare string
            if isinstance(data.get("raw"), str) and data["raw"].strip():
                remote_id = data["raw"].strip().strip('"')
        if not remote_id:
            raise CodingEngineRequestError("remote_start_missing_conversation_id")

        run_id = str(remote_id)
        events = [
            RuntimeEvent(
                1,
                "started",
                f"Remote run started: {goal.strip()[:80]}",
                phase="provisioning",
                data={"workspace": workspace or ""},
            )
        ]
        # If create response embeds events, translate them
        if data.get("events"):
            events.extend(translate_remote_events(data.get("events"), after=1))

        # Best-effort: also POST the goal as an event if create ignored initial message
        try:
            self._request(
                "POST",
                f"api/conversations/{run_id}/events",
                json_body={"type": "message", "content": goal.strip()},
            )
        except CodingEngineRequestError:
            # Create may have already accepted initial_user_message
            pass

        self._runs[run_id] = {
            "id": run_id,
            "goal": goal.strip(),
            "workspace": workspace or "",
            "status": "running",
            "events": events,
            "artifacts": [],
            "remote": {k: v for k, v in data.items() if k not in ("events",) and not _looks_secret(k)},
        }
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self._require_local(run_id)
        if run["status"] not in ("cancelled",):
            try:
                data = self._request("GET", f"api/conversations/{run_id}")
                if isinstance(data, dict):
                    status = _map_remote_status(
                        data.get("status") or data.get("agent_state") or data.get("state")
                    )
                    # Do not resurrect a locally cancelled run from a stale remote FINISHED.
                    if run["status"] != "cancelled":
                        run["status"] = status
                    if data.get("events"):
                        run["events"] = self._merge_events(run["events"], data.get("events"))
            except CodingEngineRequestError:
                pass
        return {
            "id": run["id"],
            "goal": run["goal"],
            "workspace": run["workspace"],
            "status": run["status"],
            "events": [
                {
                    "sequence_id": e.sequence_id,
                    "event": e.event,
                    "message": e.message,
                    "phase": e.phase,
                    "data": e.data,
                }
                for e in run["events"]
            ],
            "provider": self.provider_name,
        }

    def stream_events(self, run_id: str, after: int = 0) -> list[RuntimeEvent]:
        """Fetch events via HTTP (WS live subscribe is optional enhancement).

        Uses GET /api/conversations/{id}/events and returns ZECT RuntimeEvents
        with sequence_id > after for reconnect.
        """
        run = self._require_local(run_id)
        try:
            data = self._request(
                "GET",
                f"api/conversations/{run_id}/events",
                params={"after": after} if after else None,
            )
            run["events"] = self._merge_events(run["events"], data)
        except CodingEngineRequestError:
            pass
        return [e for e in run["events"] if e.sequence_id > after]

    def submit_message(self, run_id: str, message: str) -> None:
        self._require_local(run_id)
        self._request(
            "POST",
            f"api/conversations/{run_id}/events",
            json_body={"type": "message", "content": message},
        )
        seq = self._next_seq(run_id)
        self._runs[run_id]["events"].append(
            RuntimeEvent(seq, "message", message[:2000], phase="running")
        )

    def approve_action(self, run_id: str, action_id: str) -> None:
        self._require_local(run_id)
        self._request(
            "POST",
            f"api/conversations/{run_id}/events",
            json_body={"type": "approve", "action_id": action_id},
        )
        seq = self._next_seq(run_id)
        self._runs[run_id]["events"].append(
            RuntimeEvent(seq, "approved", f"Approved {action_id}", phase="awaiting_approval")
        )

    def reject_action(self, run_id: str, action_id: str) -> None:
        self._require_local(run_id)
        self._request(
            "POST",
            f"api/conversations/{run_id}/events",
            json_body={"type": "reject", "action_id": action_id},
        )
        seq = self._next_seq(run_id)
        self._runs[run_id]["events"].append(
            RuntimeEvent(seq, "rejected", f"Rejected {action_id}", phase="awaiting_approval")
        )

    def cancel_run(self, run_id: str) -> None:
        run = self._require_local(run_id)
        try:
            self._request("DELETE", f"api/conversations/{run_id}")
        except CodingEngineRequestError:
            # Some servers use POST .../stop
            try:
                self._request("POST", f"api/conversations/{run_id}/stop", json_body={})
            except CodingEngineRequestError:
                pass
        run["status"] = "cancelled"
        seq = self._next_seq(run_id)
        run["events"].append(RuntimeEvent(seq, "cancelled", "Run cancelled", phase="cancel"))

    def get_artifacts(self, run_id: str) -> list[RuntimeArtifact]:
        run = self._require_local(run_id)
        arts: list[RuntimeArtifact] = list(run.get("artifacts") or [])
        # Derive file paths from translated file_change events
        for ev in run.get("events") or []:
            if ev.event == "file_change" and ev.data.get("path"):
                path = str(ev.data["path"])
                if not any(a.path == path for a in arts):
                    arts.append(RuntimeArtifact(path=path, kind="file"))
        run["artifacts"] = arts
        return list(arts)

    def dispose_workspace(self, run_id: str) -> None:
        """Drop local mirror; remote conversation delete is best-effort."""
        if run_id in self._runs:
            try:
                self.cancel_run(run_id)
            except Exception:
                pass
            self._runs.pop(run_id, None)

    def _require_local(self, run_id: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if run:
            return run
        # Hydrate from remote if possible
        try:
            data = self._request("GET", f"api/conversations/{run_id}")
        except CodingEngineRequestError as exc:
            raise KeyError(f"Unknown remote run_id={run_id}") from exc
        if not isinstance(data, dict):
            data = {}
        events = translate_remote_events(data.get("events") or [])
        if not events:
            events = [
                RuntimeEvent(1, "status", "Hydrated remote conversation", phase="running")
            ]
        run = {
            "id": run_id,
            "goal": str(data.get("title") or data.get("goal") or ""),
            "workspace": str(data.get("working_dir") or data.get("workspace") or ""),
            "status": _map_remote_status(data.get("status") or data.get("agent_state")),
            "events": events,
            "artifacts": [],
            "remote": {},
        }
        self._runs[run_id] = run
        return run

    def _next_seq(self, run_id: str) -> int:
        events = self._runs[run_id]["events"]
        return (events[-1].sequence_id if events else 0) + 1

    def _merge_events(self, existing: list[RuntimeEvent], raw: Any) -> list[RuntimeEvent]:
        by_seq = {e.sequence_id: e for e in existing}
        after = max(by_seq) if by_seq else 0
        # If remote uses its own ids, translate with after=0 then filter
        translated = translate_remote_events(raw, after=0)
        for ev in translated:
            if ev.sequence_id in by_seq:
                by_seq[ev.sequence_id] = ev
            elif ev.sequence_id > after:
                by_seq[ev.sequence_id] = ev
            else:
                # Assign new seq if remote reused low ids
                new_seq = after + 1
                after = new_seq
                by_seq[new_seq] = RuntimeEvent(
                    new_seq, ev.event, ev.message, phase=ev.phase, data=ev.data
                )
        return [by_seq[k] for k in sorted(by_seq)]


def _map_remote_status(raw: Any) -> str:
    s = str(raw or "running").strip().lower()
    if s in ("finished", "completed", "done", "success"):
        return "completed"
    if s in ("error", "failed", "failure"):
        return "failed"
    if s in ("cancelled", "canceled", "stopped"):
        return "cancelled"
    if s in ("awaiting_user_confirmation", "waiting", "paused", "awaiting_approval"):
        return "awaiting_approval"
    return "running"


def _looks_secret(key: str) -> bool:
    k = key.lower()
    return any(x in k for x in ("key", "token", "secret", "password", "authorization"))

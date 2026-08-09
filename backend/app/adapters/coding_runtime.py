"""Coding-agent runtime adapter interface + MockRuntime + factory (Phase 2 Stage A).

Public provider names: mock | remote | mentrix_native.
Third-party product names must not appear in routes, UI, or public API payloads.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4


@dataclass
class RuntimeArtifact:
    path: str
    kind: str = "file"
    content: str | None = None


@dataclass
class RuntimeEvent:
    sequence_id: int
    event: str
    message: str
    phase: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class CodingAgentRuntime(Protocol):
    def start_run(self, goal: str, workspace: str = "", **kwargs: Any) -> str: ...
    def get_run(self, run_id: str) -> dict[str, Any]: ...
    def stream_events(self, run_id: str, after: int = 0) -> list[RuntimeEvent]: ...
    def submit_message(self, run_id: str, message: str) -> None: ...
    def approve_action(self, run_id: str, action_id: str) -> None: ...
    def reject_action(self, run_id: str, action_id: str) -> None: ...
    def cancel_run(self, run_id: str) -> None: ...
    def get_artifacts(self, run_id: str) -> list[RuntimeArtifact]: ...
    def dispose_workspace(self, run_id: str) -> None: ...


class MockCodingRuntime:
    """Deterministic in-memory runtime for unit tests and offline demos."""

    provider_name = "mock"

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    def start_run(self, goal: str, workspace: str = "", **kwargs: Any) -> str:
        run_id = str(uuid4())
        self._runs[run_id] = {
            "id": run_id,
            "goal": goal,
            "workspace": workspace,
            "status": "running",
            "kwargs": kwargs,
            "events": [
                RuntimeEvent(1, "started", f"Mock run started: {goal[:80]}", phase="provisioning"),
                RuntimeEvent(2, "progress", "Mock builder wrote placeholder", phase="build"),
                RuntimeEvent(3, "completed", "Mock run completed", phase="validating"),
            ],
            "artifacts": [
                RuntimeArtifact(path="mock_output.txt", kind="file", content="ok"),
            ],
            "messages": [],
        }
        self._runs[run_id]["status"] = "completed"
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self._require(run_id)
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
        }

    def stream_events(self, run_id: str, after: int = 0) -> list[RuntimeEvent]:
        run = self._require(run_id)
        return [e for e in run["events"] if e.sequence_id > after]

    def submit_message(self, run_id: str, message: str) -> None:
        run = self._require(run_id)
        run["messages"].append(message)
        seq = len(run["events"]) + 1
        run["events"].append(RuntimeEvent(seq, "message", message, phase="running"))

    def approve_action(self, run_id: str, action_id: str) -> None:
        run = self._require(run_id)
        seq = len(run["events"]) + 1
        run["events"].append(
            RuntimeEvent(seq, "approved", f"Approved {action_id}", phase="awaiting_approval")
        )

    def reject_action(self, run_id: str, action_id: str) -> None:
        run = self._require(run_id)
        seq = len(run["events"]) + 1
        run["events"].append(
            RuntimeEvent(seq, "rejected", f"Rejected {action_id}", phase="awaiting_approval")
        )

    def cancel_run(self, run_id: str) -> None:
        run = self._require(run_id)
        run["status"] = "cancelled"
        seq = len(run["events"]) + 1
        run["events"].append(RuntimeEvent(seq, "cancelled", "Run cancelled", phase="cancel"))

    def get_artifacts(self, run_id: str) -> list[RuntimeArtifact]:
        return list(self._require(run_id)["artifacts"])

    def dispose_workspace(self, run_id: str) -> None:
        self._require(run_id)
        self._runs.pop(run_id, None)

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "ready": True,
            "version": "mock-1",
            "detail": "mock_ok",
        }

    def _require(self, run_id: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Unknown mock run_id={run_id}")
        return run


def selected_coding_engine() -> str:
    """Product default is mentrix_native; CI sets ZECT_CODING_ENGINE=mock explicitly."""
    return (os.getenv("ZECT_CODING_ENGINE") or "mentrix_native").strip().lower() or "mentrix_native"


_runtime_singleton: CodingAgentRuntime | None = None
_runtime_singleton_key: str | None = None
# Sticky Mentrix native instance so coding-agent sessions survive env flips back to mock.
_mentrix_native_singleton: CodingAgentRuntime | None = None


def _runtime_config_key() -> str:
    mode = selected_coding_engine()
    if mode == "remote":
        return (
            f"remote|{(os.getenv('ZECT_CODING_ENGINE_URL') or '').strip()}|"
            f"{bool((os.getenv('ZECT_CODING_ENGINE_API_KEY') or '').strip())}"
        )
    return mode


def reset_coding_runtime_for_tests() -> None:
    """Clear process-local engine singleton (tests only)."""
    global _runtime_singleton, _runtime_singleton_key, _mentrix_native_singleton
    _runtime_singleton = None
    _runtime_singleton_key = None
    _mentrix_native_singleton = None


def get_mentrix_native_runtime() -> CodingAgentRuntime:
    """Always return the Mentrix Coding Agent singleton (for /api/coding-agent)."""
    global _mentrix_native_singleton
    if _mentrix_native_singleton is None:
        from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime

        _mentrix_native_singleton = MentrixNativeCodingRuntime()
    return _mentrix_native_singleton


def get_coding_runtime() -> CodingAgentRuntime:
    """Factory — mock (CI default), mentrix_native, or remote."""
    global _runtime_singleton, _runtime_singleton_key
    key = _runtime_config_key()
    if _runtime_singleton is not None and _runtime_singleton_key == key:
        return _runtime_singleton

    mode = selected_coding_engine()
    if mode == "mock":
        rt: CodingAgentRuntime = MockCodingRuntime()
    elif mode in ("mentrix_native", "native"):
        rt = get_mentrix_native_runtime()
    elif mode == "remote":
        from app.adapters.coding_engine_openhands import (
            CodingEngineConfigError,
            build_agent_server_engine,
        )

        try:
            rt = build_agent_server_engine()
        except CodingEngineConfigError:
            raise
    else:
        raise ValueError(f"Unknown ZECT_CODING_ENGINE={mode!r}; use mock|mentrix_native|remote")

    _runtime_singleton = rt
    _runtime_singleton_key = key
    return rt


def coding_engine_health() -> dict[str, Any]:
    """Public health payload — provider is mock|mentrix_native|remote."""
    mode = selected_coding_engine()
    if mode == "mock":
        return MockCodingRuntime().health()
    if mode in ("mentrix_native", "native"):
        rt = get_mentrix_native_runtime()
        return getattr(rt, "health", lambda: {"provider": "mentrix_native", "ready": True})()
    if mode == "remote":
        from app.adapters.coding_engine_openhands import (
            CodingEngineConfigError,
            build_agent_server_engine,
        )

        try:
            engine = build_agent_server_engine()
        except CodingEngineConfigError as exc:
            return {
                "provider": "remote",
                "ready": False,
                "version": None,
                "detail": str(exc),
            }
        return engine.health()
    return {
        "provider": mode,
        "ready": False,
        "version": None,
        "detail": f"unknown_provider:{mode}",
    }

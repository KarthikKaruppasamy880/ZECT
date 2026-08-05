"""Coding-agent runtime adapter interface + MockRuntime (Phase 1).

OpenHands wiring is Phase 2. Tests and local runs use MockCodingRuntime so
orchestration does not require an external coding engine.
"""

from __future__ import annotations

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

    def _require(self, run_id: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Unknown mock run_id={run_id}")
        return run


def get_coding_runtime() -> CodingAgentRuntime:
    """Factory — Phase 2 will switch on CODING_RUNTIME=openhands."""
    return MockCodingRuntime()

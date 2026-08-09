"""Checkpoint recorder + EXECUTION_STATE helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.work_items.artifact_store import ArtifactStore

CHECKPOINT_TYPES = (
    "op_start",
    "file_change",
    "command_execution",
    "verification",
    "completion",
    "failure",
    "blocking",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_checkpoint(
    store: ArtifactStore,
    *,
    checkpoint_type: str,
    operation_id: str,
    payload: dict[str, Any] | None = None,
    worktree_path: str | None = None,
    base_commit_sha: str | None = None,
    current_commit_sha: str | None = None,
) -> dict[str, Any]:
    if checkpoint_type not in CHECKPOINT_TYPES:
        raise ValueError(f"invalid checkpoint_type: {checkpoint_type}")
    state = store.read_json("EXECUTION_STATE.json", default={})
    if not isinstance(state, dict):
        state = {}
    checkpoints = list(state.get("checkpoints") or [])
    entry = {
        "type": checkpoint_type,
        "operation_id": operation_id,
        "at": _now(),
        "payload": payload or {},
    }
    checkpoints.append(entry)
    state["checkpoints"] = checkpoints
    state["last_checkpoint"] = entry
    state["updated_at"] = _now()
    if worktree_path is not None:
        state["worktree_path"] = worktree_path
    if base_commit_sha is not None:
        state["base_commit_sha"] = base_commit_sha
    if current_commit_sha is not None:
        state["current_commit_sha"] = current_commit_sha
    if operation_id:
        state["resume_operation"] = operation_id
    store.write_json("EXECUTION_STATE.json", state)
    return entry


def load_execution_state(store: ArtifactStore) -> dict[str, Any]:
    state = store.read_json("EXECUTION_STATE.json", default={})
    return state if isinstance(state, dict) else {}

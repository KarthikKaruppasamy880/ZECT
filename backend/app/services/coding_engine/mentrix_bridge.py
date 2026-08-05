"""Mentrix ↔ coding-engine bridge (Phase 2 Stage C).

When ZECT_CODING_ENGINE=remote and a repo workspace is available:
  provision worktree → start remote engine → poll ZECT events into MentrixRun.

Default mock leaves ForgeLoop unchanged (CI-safe).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.coding_runtime import (
    RuntimeEvent,
    get_coding_runtime,
    selected_coding_engine,
)
from app.models import MentrixRun
from app.services.coding_engine.workspace import (
    WorkspaceError,
    dispose_isolated_workspace,
    provision_isolated_workspace,
)


@dataclass
class CodingEngineSlice:
    """Result of an optional coding-engine pre-slice for a Mentrix run."""

    active: bool = False
    engine_provider: str = "mock"
    workspace_id: str | None = None
    engine_run_id: str | None = None
    engine_workspace_path: str | None = None
    branch: str | None = None
    artifact_dir: str | None = None
    repo_path: str | None = None
    isolation: str | None = None
    container_id: str | None = None
    events_appended: int = 0
    files: list[str] = field(default_factory=list)
    error: str | None = None

    def context_patch(self) -> dict[str, Any]:
        if not self.active and not self.error:
            return {}
        return {
            "engine_provider": self.engine_provider,
            "workspace_id": self.workspace_id,
            "engine_run_id": self.engine_run_id,
            "engine_workspace_path": self.engine_workspace_path,
            "engine_branch": self.branch,
            "engine_artifact_dir": self.artifact_dir,
            "engine_isolation": self.isolation,
            "engine_container_id": self.container_id,
            "engine_error": self.error,
        }


def _poll_budget() -> tuple[int, float]:
    attempts = int(os.getenv("ZECT_CODING_ENGINE_POLL_ATTEMPTS", "8") or "8")
    delay = float(os.getenv("ZECT_CODING_ENGINE_POLL_DELAY", "0.25") or "0.25")
    return max(1, attempts), max(0.0, delay)


def _runtime_event_to_mentrix(ev: RuntimeEvent) -> dict[str, Any]:
    return {
        "sequence_id": ev.sequence_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": "coding_engine",
        "phase": ev.phase or "engine",
        "event": ev.event,
        "message": ev.message,
        "data": ev.data or {},
        "next_step": "forge_loop",
    }


def _append_events(run: MentrixRun, new_events: list[dict[str, Any]]) -> int:
    events = json.loads(run.events_json or "[]")
    if not isinstance(events, list):
        events = []
    # Ensure sequence_ids continue
    next_seq = 1
    for e in events:
        if isinstance(e, dict) and isinstance(e.get("sequence_id"), int):
            next_seq = max(next_seq, int(e["sequence_id"]) + 1)
    for ev in new_events:
        if "sequence_id" not in ev:
            ev["sequence_id"] = next_seq
            next_seq += 1
        events.append(ev)
    run.events_json = json.dumps(events)
    return len(new_events)


def _merge_context(run: MentrixRun, patch: dict[str, Any]) -> None:
    result = json.loads(run.result_json or "{}")
    if not isinstance(result, dict):
        result = {}
    ctx = result.get("context") if isinstance(result.get("context"), dict) else {}
    ctx.update({k: v for k, v in patch.items() if v is not None})
    result["context"] = ctx
    if patch.get("engine_workspace_path"):
        result["workspace"] = patch["engine_workspace_path"]
    run.result_json = json.dumps(result)


def prepare_coding_engine_slice(
    db: Session,
    run: MentrixRun,
    *,
    goal: str,
    workspace: str,
    mode: str = "",
) -> CodingEngineSlice:
    """Opt-in remote coding-engine slice. No-op when provider is mock."""
    provider = selected_coding_engine()
    out = CodingEngineSlice(engine_provider=provider)
    if provider != "remote":
        # Record provider on context for observability without changing pipeline.
        if provider == "mock":
            _merge_context(run, {"engine_provider": "mock"})
            db.commit()
        return out

    ws = (workspace or "").strip()
    if not ws:
        out.error = "remote_engine_requires_workspace"
        _merge_context(run, out.context_patch())
        _append_events(
            run,
            [
                {
                    "agent": "coding_engine",
                    "phase": "engine",
                    "event": "skipped",
                    "message": "Remote coding engine skipped — workspace path required",
                }
            ],
        )
        db.commit()
        return out

    try:
        provisioned = provision_isolated_workspace(repo_path=ws, run_id=f"mentrix-{run.id}")
    except (WorkspaceError, ValueError) as exc:
        out.error = f"provision_failed:{exc}"
        _merge_context(run, out.context_patch())
        _append_events(
            run,
            [
                {
                    "agent": "coding_engine",
                    "phase": "engine",
                    "event": "error",
                    "message": f"Workspace provision failed: {exc}",
                }
            ],
        )
        db.commit()
        return out

    out.active = True
    out.workspace_id = provisioned.workspace_id
    out.engine_workspace_path = provisioned.path
    out.branch = provisioned.branch
    out.artifact_dir = provisioned.artifact_dir
    out.repo_path = provisioned.repo_path
    out.isolation = provisioned.isolation
    out.container_id = provisioned.container_id

    try:
        rt = get_coding_runtime()
        engine_run_id = rt.start_run(goal, workspace=provisioned.path, mode=mode or run.mode)
        out.engine_run_id = engine_run_id
        attempts, delay = _poll_budget()
        cursor = 0
        collected: list[RuntimeEvent] = []
        for _ in range(attempts):
            batch = rt.stream_events(engine_run_id, after=cursor)
            for ev in batch:
                collected.append(ev)
                cursor = max(cursor, ev.sequence_id)
            status = (rt.get_run(engine_run_id) or {}).get("status") or "running"
            if status in ("completed", "failed", "cancelled", "awaiting_approval"):
                break
            if delay:
                time.sleep(delay)
        # Final drain
        collected.extend(rt.stream_events(engine_run_id, after=cursor))
        mentrix_evs = [_runtime_event_to_mentrix(ev) for ev in collected]
        # Deduplicate by sequence within this batch
        seen: set[int] = set()
        uniq: list[dict[str, Any]] = []
        for ev in mentrix_evs:
            sid = ev.get("sequence_id")
            if isinstance(sid, int) and sid in seen:
                continue
            if isinstance(sid, int):
                seen.add(sid)
            uniq.append(ev)
        out.events_appended = _append_events(run, uniq)
        arts = rt.get_artifacts(engine_run_id)
        out.files = [a.path for a in arts if a.path]
        result = json.loads(run.result_json or "{}")
        if not isinstance(result, dict):
            result = {}
        result["coding_engine"] = {
            "provider": "remote",
            "run_id": engine_run_id,
            "files": out.files,
            "status": (rt.get_run(engine_run_id) or {}).get("status"),
        }
        run.result_json = json.dumps(result)
    except Exception as exc:  # noqa: BLE001
        out.error = f"engine_failed:{exc}"
        _append_events(
            run,
            [
                {
                    "agent": "coding_engine",
                    "phase": "engine",
                    "event": "error",
                    "message": f"Coding engine failed: {exc}",
                }
            ],
        )

    _merge_context(run, out.context_patch())
    run.current_agent = "coding_engine"
    db.commit()
    return out


def cleanup_coding_engine_slice(slice_result: CodingEngineSlice) -> dict[str, Any] | None:
    """Preserve patch artifacts and remove the worktree/sandbox after Mentrix finishes."""
    if not slice_result.active or not slice_result.workspace_id:
        return None
    try:
        return dispose_isolated_workspace(
            workspace_id=slice_result.workspace_id,
            repo_path=slice_result.repo_path,
            workspace_path=slice_result.engine_workspace_path,
            container_id=slice_result.container_id,
            preserve_artifacts=True,
        )
    except Exception:
        return None

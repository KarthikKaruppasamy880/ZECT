"""Run Mentrix Coding Agent as a ForgeLoop build slice."""

from __future__ import annotations

import os
from typing import Any


def mentrix_native_build_enabled() -> bool:
    mode = (os.getenv("ZECT_CODING_ENGINE") or "mentrix_native").strip().lower()
    return mode in ("mentrix_native", "native")


def run_mentrix_native_build(
    *,
    goal: str,
    workspace: str,
    expected_files: list[str] | None = None,
    timeout_s: float | None = None,
    model: str | None = None,
    project_id: int | None = None,
    skill_id: int | None = None,
    project_key: str | None = None,
) -> dict[str, Any]:
    """Execute Mentrix Coding Agent against workspace; return builder-shaped dict."""
    from app.adapters.coding_runtime import get_mentrix_native_runtime

    if not (workspace or "").strip():
        return {
            "ok": False,
            "error": "workspace_required",
            "files_written": [],
            "engine": "mentrix_native",
        }

    timeout = float(
        timeout_s
        if timeout_s is not None
        else os.getenv("MENTRIX_CODING_AGENT_BUILD_TIMEOUT", "240")
    )
    enriched_goal = goal
    if project_id is not None or project_key:
        enriched_goal = (
            f"{goal}\n\n"
            "Modernize or implement per Blueprint target architecture when provided; "
            "respect Lattice facts in Mentrix context. Prefer grounded edits over invention."
        )
    rt = get_mentrix_native_runtime()
    run_id = rt.start_run(
        enriched_goal,
        workspace=workspace,
        auto_approve_edits=True,
        expected_files=list(expected_files or []),
        model=model,
        max_steps=int(os.getenv("MENTRIX_CODING_AGENT_MAX_STEPS", "24")),
        project_id=project_id,
        skill_id=skill_id,
        project_key=project_key,
    )
    wait = getattr(rt, "wait_until_done", None)
    summary = wait(run_id, timeout_s=timeout) if callable(wait) else rt.get_run(run_id)
    files = list(summary.get("files_written") or [])
    status = summary.get("status")
    return {
        "ok": status == "completed",
        "status": status,
        "run_id": run_id,
        "files_written": files,
        "files_expected": list(expected_files or []),
        "file_path": files[0] if files else "",
        "generated_code": "",
        "engine": "mentrix_native",
        "model": summary.get("model"),
        "events_tail": (summary.get("events") or [])[-8:],
    }

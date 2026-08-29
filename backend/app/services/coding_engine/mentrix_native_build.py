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
    max_steps: int | None = None,
    role: str | None = None,
    allowed_tools: list[str] | None = None,
    mission_id: str | None = None,
    repo_id: str | int | None = None,
    work_item_id: int | None = None,
) -> dict[str, Any]:
    """Execute Mentrix Coding Agent against workspace; return builder-shaped dict."""
    from app.adapters.coding_runtime import get_mentrix_native_runtime, selected_coding_engine

    if not (workspace or "").strip():
        return {
            "ok": False,
            "error": "workspace_required",
            "files_written": [],
            "engine": "mentrix_native",
        }

    # Fail closed: never silently use mock when this native build entrypoint is invoked.
    engine_mode = selected_coding_engine()
    smoke = (os.getenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if engine_mode == "mock" and not smoke:
        return {
            "ok": False,
            "error": "coding_engine_mock_forbidden",
            "files_written": [],
            "engine": "mentrix_native",
            "detail": "ZECT_CODING_ENGINE=mock cannot satisfy mentrix_native build (no silent fallback)",
        }

    # Deterministic smoke: real tools via Mentrix native path (no LLM) — tests only.
    if smoke:
        from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace

        root = resolve_workspace(workspace)
        target = (expected_files or ["mentrix_p0_smoke_marker.py"])[0]
        rel = target.replace("\\", "/").lstrip("./")
        w = execute_tool(
            "write_file",
            {"path": rel, "content": "# mentrix smoke\nprint('smoke-ok')\n"},
            workspace=root,
        )
        r = execute_tool("read_file", {"path": rel}, workspace=root)
        cmd = execute_tool("run_command", {"command": f"python {rel}"}, workspace=root)
        ok = bool(w.get("ok") and r.get("ok"))
        return {
            "ok": ok,
            "status": "completed" if ok else "failed",
            "run_id": "deterministic-smoke",
            "files_written": [rel] if w.get("ok") else [],
            "files_expected": list(expected_files or []),
            "file_path": rel if w.get("ok") else "",
            "generated_code": "",
            "engine": "mentrix_native",
            "model": "deterministic_smoke",
            "events_tail": [
                {"event": "write_file", "ok": w.get("ok"), "file_diff": w.get("file_diff")},
                {"event": "read_file", "ok": r.get("ok")},
                {"event": "run_command", "ok": cmd.get("ok"), "exit_code": cmd.get("exit_code")},
            ],
        }

    timeout = float(
        timeout_s
        if timeout_s is not None
        else os.getenv("MENTRIX_CODING_AGENT_BUILD_TIMEOUT", "240")
    )
    steps = int(
        max_steps
        if max_steps is not None
        else os.getenv("MENTRIX_CODING_AGENT_MISSION_MAX_STEPS")
        or os.getenv("MENTRIX_CODING_AGENT_MAX_STEPS", "48")
    )
    enriched_goal = goal
    if project_id is not None or project_key:
        enriched_goal = (
            f"{goal}\n\n"
            "Modernize or implement per Blueprint target architecture when provided; "
            "respect Lattice facts in Mentrix context. Prefer grounded edits over invention."
        )
    rt = get_mentrix_native_runtime()
    if getattr(rt, "provider_name", "") != "mentrix_native":
        return {
            "ok": False,
            "error": "not_mentrix_native_runtime",
            "files_written": [],
            "engine": "mentrix_native",
            "detail": f"got provider={getattr(rt, 'provider_name', None)}",
        }
    run_id = rt.start_run(
        enriched_goal,
        workspace=workspace,
        auto_approve_edits=True,
        expected_files=list(expected_files or []),
        model=model,
        max_steps=steps,
        project_id=project_id,
        skill_id=skill_id,
        project_key=project_key,
        role=role,
        allowed_tools=allowed_tools,
        mission_id=str(mission_id or ""),
        repo_id=str(repo_id) if repo_id is not None else "",
        work_item_id=work_item_id,
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

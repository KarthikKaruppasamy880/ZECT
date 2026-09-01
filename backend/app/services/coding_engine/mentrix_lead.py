"""Mentrix Lead: role-based tool allowlists for the real Approve & Build
mission loop (coding_engine/lifecycle.py).

This is deliberately NOT the disconnected engineering_agents/roles.py +
engineering_loop.py system (that path is only reachable from the separate
Personal-Agent automation_loops feature and is never invoked by the real
mission flow). Instead this wires role restriction directly into the same
native Mentrix Coding Agent runtime used for edits, tests, and browser
verification (coding_engine_mentrix.py), so a role's tool set is enforced by
the runtime itself -- both by filtering what the model is offered via the
tools-calling API, and by a defense-in-depth check in
MentrixNativeCodingRuntime._run_one_tool that refuses any tool call outside
the allowlist even if the model bypasses that filtering (e.g. via the
JSON-fallback protocol for models without a native tools API).

True parallel worktree-per-agent concurrency is not part of this: each role
still runs sequentially, one native agent run at a time, inside the single
isolated worktree the mission already created for that repo.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROLE_EXPLORE = "explore"
ROLE_CODER = "coder"
ROLE_TESTER = "tester"
ROLE_DEBUGGER = "debugger"
# There is deliberately no ROLE_REVIEWER agent-loop turn here: the real
# review gate is lifecycle.py's review_diff()/run_ultra_review() call, a
# heuristic/LLM pass over the actual diff+evidence, not another native
# agent run. An earlier ROLE_REVIEWER constant + allowlist entry existed
# with no call site anywhere (dead code) -- removed rather than wiring a
# second, redundant review mechanism. (Unrelated: a same-named ROLE_REVIEWER
# in engineering_agents/roles.py belongs to the separate, disconnected
# Personal-Agent automation_loops feature -- see module docstring above.)

_READ_ONLY_TOOLS = [
    "list_dir",
    "read_file",
    "search_code",
    "glob_files",
    "db_schema",
    "git_status",
    "git_diff",
    "git_log",
    "git_branch",
]
_APP_BROWSER_TOOLS = [
    "start_app",
    "restart_app",
    "stop_app",
    "health_check",
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_type",
    "browser_select",
    "browser_screenshot",
    "browser_wait_for",
    "browser_assert_text",
    "browser_assert_visible",
    "browser_console_errors",
    "browser_network_failures",
]

# Bounded, per-role tool allowlists. A role's agent run can only ever be
# offered / execute tools from its own list -- see module docstring.
ROLE_TOOL_ALLOWLISTS: dict[str, list[str]] = {
    ROLE_EXPLORE: list(_READ_ONLY_TOOLS),
    ROLE_CODER: [*_READ_ONLY_TOOLS, "write_file", "apply_patch", "run_command"],
    # Tester's real job here is "verify in a real browser, and if a real
    # problem is found, fix the affected source file(s) and re-verify" (see
    # lifecycle._run_app_and_browser_verification) -- so it needs write
    # access too, not just observation tools.
    ROLE_TESTER: [*_READ_ONLY_TOOLS, "write_file", "apply_patch", "run_command", *_APP_BROWSER_TOOLS],
    ROLE_DEBUGGER: [*_READ_ONLY_TOOLS, "write_file", "apply_patch", "run_command", *_APP_BROWSER_TOOLS],
}


def _last_completed_message(out: dict[str, Any]) -> str:
    for ev in reversed(list(out.get("events_tail") or [])):
        if ev.get("event") == "completed":
            return str(ev.get("message") or "")
    return ""


def run_explore_phase(mission: dict[str, Any], repo: dict[str, Any], wt: Path) -> str:
    """Bounded, read-only reconnaissance pass over the isolated worktree
    before the Coder role makes any edits. Explore has no
    write_file/apply_patch/run_command access -- enforced by
    ROLE_TOOL_ALLOWLISTS[ROLE_EXPLORE], not just instructed in the prompt.
    Returns a findings summary (possibly empty) to fold into the Coder goal.
    """
    from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

    goal = (
        "You are in the Explore role for this mission. Investigate this "
        "repository's structure and the existing code/conventions relevant "
        "to the goal below. You have READ-ONLY tools -- there is no "
        "write_file, apply_patch, or run_command in this phase, and any "
        "attempt to use one will be refused by the runtime. When you are "
        "done, summarize what the Coder role needs to know before making "
        "changes (relevant files, existing patterns, likely edit points).\n\n"
        f"MISSION GOAL:\n{mission.get('goal') or ''}"
    )
    out = run_mentrix_native_build(
        goal=goal,
        workspace=str(wt),
        project_id=mission.get("project_id"),
        role=ROLE_EXPLORE,
        allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_EXPLORE],
        timeout_s=float(os.getenv("MENTRIX_CODING_AGENT_EXPLORE_TIMEOUT", "120")),
        max_steps=int(os.getenv("MENTRIX_CODING_AGENT_EXPLORE_MAX_STEPS", "12")),
        mission_id=mission.get("id"),
        repo_id=repo.get("repository_id"),
        work_item_id=mission.get("work_item_id"),
    )
    return _last_completed_message(out)

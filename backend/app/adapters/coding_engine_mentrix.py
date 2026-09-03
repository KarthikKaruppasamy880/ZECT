"""Mentrix native Coding Agent runtime — in-process tool loop.

Public provider name: mentrix_native. No third-party product branding.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.adapters.coding_runtime import RuntimeArtifact, RuntimeEvent
from app.adapters.llm.agent_model_adapter import (
    AUTO_ROUTED,
    USER_SELECTED,
    ModelProviderError,
    get_agent_model_adapter,
)
from app.adapters.llm.openai_compat import mentrix_llm_chat_model, openai_compat_available
from app.services.coding_engine.mentrix_agent_tools import (
    TOOL_SPECS,
    execute_tool,
    resolve_workspace,
)

_SYSTEM_POLICY = (
    "Do not invent file contents you have not read. "
    "When the goal is done, reply with a short summary and no further tool calls."
)

_PRODUCT_ROLE = (
    "You are Mentrix Coding Agent — ZECT's coding agent for this workspace. "
    "Use tools to inspect and edit the repository. Work in any language the repo uses. "
    "Prefer apply_patch for small edits and write_file for new files. "
    "Run tests/linters with run_command when helpful. "
    "When modernizing legacy code, respect Lattice facts and Blueprint target architecture when provided."
)


def _authorize_agent_write(run: dict[str, Any], workspace: Path, name: str, args: dict[str, Any]) -> "agent_write_policy.WriteDecision | None":
    """CP-07 -- returns None (no opinion, existing behavior unchanged) for
    non-mutating tools and for runs with no work_item_id (never went
    through ASK/PLAN, so there is no FILE_IMPACTS.json to check against --
    the same scope boundary CP-06's approval gate uses). For every other
    write_file/apply_patch call, this is the last checkpoint before
    execute_tool() ever touches disk.
    """
    from app.services.coding_engine import agent_write_policy

    if name not in agent_write_policy.WRITE_MUTATING_TOOLS:
        return None
    work_item_id = run.get("work_item_id")
    if not work_item_id:
        return None
    return agent_write_policy.evaluate_write(
        work_item_id=work_item_id,
        repo_id=run.get("repo_id"),
        tool_name=name,
        path=str(args.get("path") or ""),
        workspace=workspace,
    )


def _load_workspace_rules_safe(workspace: Path) -> str:
    try:
        from app.services.coding_engine.mention_resolver import load_workspace_rules

        return load_workspace_rules(workspace)
    except Exception:  # noqa: BLE001 -- a broken rules file must never break a run
        return ""


def _build_system_content(run: dict[str, Any], role_note: str) -> str:
    """Layered system prompt -- SYSTEM POLICY -> PRODUCT ROLE -> AGENT ROLE ->
    PROJECT INTELLIGENCE -> RULES/SKILLS -- static-to-dynamic so a caching
    provider can reuse the common prefix across steps of the same run (the
    first two sections are identical across every run). Previously one flat
    concatenated paragraph with no section boundaries at all, and RULES/
    SKILLS was reachable only via an explicit @rule mention, never as a
    standing layer -- see ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_
    PLAN.md Phase E.
    """
    sections = [f"## SYSTEM POLICY\n{_SYSTEM_POLICY}", f"## PRODUCT ROLE\n{_PRODUCT_ROLE}"]
    if role_note.strip():
        sections.append(f"## AGENT ROLE\n{role_note.strip()}")
    agent_context = (run.get("agent_context") or "").strip()
    if agent_context:
        sections.append(f"## PROJECT INTELLIGENCE\n{agent_context}")
    rules = _load_workspace_rules_safe(Path(run["workspace"]))
    if rules:
        sections.append(f"## RULES/SKILLS\n{rules}")
    return "\n\n".join(sections)


def _build_user_content(run: dict[str, Any], workspace: Path) -> str:
    """MISSION GOAL -> APPROVED PLAN -> current task, each its own section
    instead of one flat string -- see _build_system_content above. This is
    the SEED user message only; a later follow-up (see _agent_loop) is
    appended as its own new history turn, not folded in here.
    """
    sections = [f"## MISSION GOAL\n{run['goal']}"]
    approved_plan = str(run.get("approved_plan") or "").strip()
    if approved_plan:
        sections.append(f"## APPROVED PLAN\n{approved_plan}")
    task_lines = [f"Workspace: {workspace}"]
    if run.get("expected_files"):
        task_lines.append(f"Expected files (prefer these): {run['expected_files']}")
    sections.append("## CURRENT TASK\n" + "\n".join(task_lines))
    return "\n\n".join(sections)


def _group_into_turns(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group history entries after the seed system+user pair into turns --
    a turn starts with a user or assistant message and absorbs any
    immediately-following tool-role messages. Condensation below only ever
    cuts BETWEEN turns, never inside one, so a tool_calls assistant message
    can never be separated from its tool results (which the chat-completion
    APIs require to stay paired, on pain of a 400)."""
    turns: list[list[dict[str, Any]]] = []
    for msg in messages:
        if msg.get("role") == "tool" and turns:
            turns[-1].append(msg)
        else:
            turns.append([msg])
    return turns


_CONDENSED_SUMMARY_HEADER = (
    "## EARLIER IN THIS RUN (condensed so this conversation stays within "
    "budget; shortened, not fabricated)"
)


def _summarize_turns(turns: list[list[dict[str, Any]]]) -> list[str]:
    lines: list[str] = []
    for turn in turns:
        for msg in turn:
            role = msg.get("role")
            if role == "assistant":
                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
                    lines.append(f"- called {', '.join(names)}")
                elif msg.get("content"):
                    lines.append(f"- assistant: {str(msg['content'])[:160]}")
            elif role == "tool":
                lines.append(f"  -> {str(msg.get('content') or '')[:160]}")
            elif role == "user":
                lines.append(f"- follow-up: {str(msg.get('content') or '')[:200]}")
    return lines


def _condense_history(history: list[dict[str, Any]], max_turns: int) -> list[dict[str, Any]]:
    """Mission Memory: once a run/follow-up conversation grows past
    max_turns REAL (non-summary) turns, fold everything older than the most
    recent max_turns into one deterministic textual digest (tool names +
    truncated outputs/content) instead of silently dropping it -- the gap
    this closes: "history rebuilt fresh each call, dropping prior turns
    rather than condensing" (see
    ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase E).
    Deterministic, not another LLM call, so it can't itself fail or
    hallucinate. The evidence/audit timeline (run["events"]) is a
    completely separate, never-condensed list -- this only ever shrinks
    what the model sees on its next turn.

    Idempotent: an existing summary (detected by its header, always
    immediately after the seed system+user pair) is treated as a fixed
    prefix, not a turn subject to re-condensing -- otherwise calling this
    every loop step would re-wrap the summary inside itself on every call
    once the kept window alone exceeds max_turns.
    """
    if len(history) < 2:
        return history
    system_msg, seed_user_msg = history[0], history[1]
    rest = history[2:]
    existing_summary_body = ""
    if (
        rest
        and rest[0].get("role") == "user"
        and str(rest[0].get("content") or "").startswith(_CONDENSED_SUMMARY_HEADER)
    ):
        existing_summary_body = str(rest[0]["content"])[len(_CONDENSED_SUMMARY_HEADER) :].strip()
        rest = rest[1:]
    turns = _group_into_turns(rest)
    if len(turns) <= max_turns:
        return history
    keep = turns[-max_turns:] if max_turns > 0 else []
    to_fold = turns[: len(turns) - max_turns] if max_turns > 0 else turns
    new_lines = _summarize_turns(to_fold)
    body = "\n".join([existing_summary_body, *new_lines]) if existing_summary_body else "\n".join(new_lines)
    summary_msg = {"role": "user", "content": f"{_CONDENSED_SUMMARY_HEADER}\n{body[:4000]}"}
    flat_keep = [m for turn in keep for m in turn]
    return [system_msg, seed_user_msg, summary_msg, *flat_keep]


class MentrixNativeCodingRuntime:
    """In-process Mentrix Coding Agent (read/search/edit/run/git)."""

    provider_name = "mentrix_native"

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def health(self) -> dict[str, Any]:
        ready = openai_compat_available()
        return {
            "provider": self.provider_name,
            "ready": ready,
            "version": "mentrix-native-1",
            "detail": "mentrix_native_ok" if ready else "llm_not_configured",
            "label": "Mentrix Coding Agent",
        }

    def start_run(self, goal: str, workspace: str = "", **kwargs: Any) -> str:
        run_id = str(uuid4())
        auto_approve = bool(kwargs.get("auto_approve_edits", True))
        explicit_model = (kwargs.get("model") or "").strip()
        model = explicit_model or mentrix_llm_chat_model()
        model_route_mode = str(kwargs.get("model_route_mode") or "").strip() or (
            USER_SELECTED if explicit_model else AUTO_ROUTED
        )
        max_steps = int(kwargs.get("max_steps") or os.getenv("MENTRIX_CODING_AGENT_MAX_STEPS", "24"))
        expected_files = list(kwargs.get("expected_files") or [])
        project_id = kwargs.get("project_id")
        skill_id = kwargs.get("skill_id")
        project_key = (kwargs.get("project_key") or "").strip() or None
        repo_id = str(kwargs.get("repo_id") or "").strip()
        work_item_id = kwargs.get("work_item_id")

        try:
            ws = resolve_workspace(workspace)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(str(exc)) from exc

        # Structured record of what compose_rich_agent_context_pack /
        # compose_context_pack actually assembled -- surfaced on the run so
        # a Mission's "Context Used" can be rendered with the same
        # knowledge/lattice_hits/lattice_indexed/blueprint shape Ask/Plan
        # already use (see ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_
        # PLAN.md Phase D), not just the raw prompt text.
        context_used: dict[str, Any] | None = None
        agent_context = (kwargs.get("agent_context") or "").strip()
        if not agent_context:
            # Same provenance-aware Project Intelligence pipeline Ask/Plan
            # use, when there's enough identity (repo_id/project_id) to look
            # it up -- see agent_context.compose_rich_agent_context_pack.
            # Falls back to the thinner compose_context_pack when there
            # isn't (an ad-hoc workspace not tied to any registered
            # project/repo), so this never blocks a build either way.
            if repo_id or project_id is not None:
                try:
                    from app.services.coding_engine.agent_context import compose_rich_agent_context_pack

                    pack = compose_rich_agent_context_pack(
                        goal=goal,
                        workspace=str(ws),
                        project_id=int(project_id) if project_id is not None else None,
                        project_key=project_key,
                        repository_id=repo_id or None,
                        work_item_id=int(work_item_id) if work_item_id is not None else None,
                        db=kwargs.get("db"),
                    )
                    agent_context = str(pack.get("text") or "")
                    if agent_context:
                        context_used = {k: pack.get(k) for k in ("knowledge", "lattice_hits", "lattice_indexed", "blueprint")}
                except Exception:  # noqa: BLE001
                    agent_context = ""
            if not agent_context:
                try:
                    from app.services.coding_engine.agent_context import compose_context_pack

                    pack = compose_context_pack(
                        goal=goal,
                        project_id=int(project_id) if project_id is not None else None,
                        skill_id=int(skill_id) if skill_id is not None else None,
                        project_key=project_key,
                        db=kwargs.get("db"),
                    )
                    agent_context = str(pack.get("text") or "")
                    if agent_context:
                        context_used = {k: pack.get(k) for k in ("knowledge", "lattice_hits", "lattice_indexed", "blueprint")}
                except Exception:  # noqa: BLE001
                    agent_context = ""

        role = str(kwargs.get("role") or "").strip() or None
        allowed_tools = kwargs.get("allowed_tools")
        allowed_tools = list(allowed_tools) if allowed_tools else None
        mission_id = str(kwargs.get("mission_id") or "").strip()
        approved_plan = str(kwargs.get("approved_plan") or "").strip()

        run: dict[str, Any] = {
            "id": run_id,
            "goal": goal,
            "workspace": str(ws),
            "status": "running",
            "model": model,
            "auto_approve_edits": auto_approve,
            "max_steps": max_steps,
            "expected_files": expected_files,
            "agent_context": agent_context,
            "context_used": context_used,
            "approved_plan": approved_plan,
            "role": role,
            "allowed_tools": allowed_tools,
            "mission_id": mission_id,
            "repo_id": repo_id,
            "work_item_id": work_item_id,
            "model_route_mode": model_route_mode,
            "events": [],
            "artifacts": [],
            "messages": [],
            "pending": {},  # action_id -> {event, args}
            "cancel": False,
            "seq": 0,
            "files_written": [],
            "thread": None,
            "approve_events": {},
        }
        with self._lock:
            self._runs[run_id] = run

        self._emit(run, "started", f"Mentrix Coding Agent: {goal[:120]}", phase="provisioning")
        t = threading.Thread(target=self._agent_loop, args=(run_id,), daemon=True)
        run["thread"] = t
        t.start()
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self._require(run_id)
        return {
            "id": run["id"],
            "goal": run["goal"],
            "workspace": run["workspace"],
            "status": run["status"],
            "model": run.get("model"),
            "context_used": run.get("context_used"),
            "files_written": list(run.get("files_written") or []),
            "pending_approvals": [
                {"action_id": k, **{kk: vv for kk, vv in v.items() if kk != "content"}}
                for k, v in (run.get("pending") or {}).items()
            ],
            "events": [
                {
                    "sequence_id": e.sequence_id,
                    "event": e.event,
                    "message": e.message,
                    "phase": e.phase,
                    "data": e.data,
                    "mission_id": e.mission_id,
                    "agent_id": e.agent_id,
                    "repo_id": e.repo_id,
                    "tool": e.tool,
                    "policy": e.policy,
                    "timestamp": e.timestamp,
                    "status": e.status,
                    "duration_ms": e.duration_ms,
                    "evidence_refs": e.evidence_refs,
                }
                for e in run["events"]
            ],
        }

    def stream_events(self, run_id: str, after: int = 0) -> list[RuntimeEvent]:
        run = self._require(run_id)
        return [e for e in run["events"] if e.sequence_id > after]

    def submit_message(self, run_id: str, message: str) -> None:
        run = self._require(run_id)
        run["messages"].append({"role": "user", "content": message})
        self._emit(run, "message", message[:500], phase="running")
        if run["status"] in ("completed", "failed", "cancelled"):
            # Start a follow-up turn
            run["status"] = "running"
            run["cancel"] = False
            t = threading.Thread(
                target=self._agent_loop,
                args=(run_id,),
                kwargs={"followup": message},
                daemon=True,
            )
            run["thread"] = t
            t.start()

    def approve_action(self, run_id: str, action_id: str) -> None:
        run = self._require(run_id)
        pending = (run.get("pending") or {}).pop(action_id, None)
        self._emit(run, "approved", f"Approved {action_id}", phase="awaiting_approval", data={"action_id": action_id})
        ev = run["approve_events"].get(action_id)
        if ev:
            run.setdefault("_approved_actions", set()).add(action_id)
            if pending:
                run["_approved_payload"] = pending
            ev.set()

    def reject_action(self, run_id: str, action_id: str) -> None:
        run = self._require(run_id)
        (run.get("pending") or {}).pop(action_id, None)
        self._emit(run, "rejected", f"Rejected {action_id}", phase="awaiting_approval", data={"action_id": action_id})
        ev = run["approve_events"].get(action_id)
        if ev:
            run.setdefault("_rejected_actions", set()).add(action_id)
            ev.set()

    def cancel_run(self, run_id: str) -> None:
        run = self._require(run_id)
        run["cancel"] = True
        run["status"] = "cancelled"
        for ev in (run.get("approve_events") or {}).values():
            try:
                ev.set()
            except Exception:  # noqa: BLE001
                pass
        self._emit(run, "cancelled", "Run cancelled", phase="cancel")

    def get_artifacts(self, run_id: str) -> list[RuntimeArtifact]:
        return list(self._require(run_id)["artifacts"])

    def dispose_workspace(self, run_id: str) -> None:
        self.cancel_run(run_id)
        with self._lock:
            self._runs.pop(run_id, None)

    def wait_until_done(self, run_id: str, timeout_s: float = 180.0) -> dict[str, Any]:
        """Block until terminal status (Delivery / tests)."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            run = self._require(run_id)
            if run["status"] in ("completed", "failed", "cancelled"):
                return self.get_run(run_id)
            # Unblock if stuck on approval in auto batch mode — reject wait
            if run.get("pending") and run.get("auto_approve_edits"):
                # Should not happen often; wait for approve events
                pass
            time.sleep(0.25)
        run = self._require(run_id)
        run["status"] = "failed"
        self._emit(run, "failed", "Mentrix Coding Agent timed out", phase="failed")
        return self.get_run(run_id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require(self, run_id: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(f"Unknown Mentrix Coding Agent run_id={run_id}")
        return run

    def _emit(
        self,
        run: dict[str, Any],
        event: str,
        message: str,
        *,
        phase: str = "",
        data: dict[str, Any] | None = None,
        tool: str = "",
        policy: str = "",
        status: str = "",
        duration_ms: int | None = None,
        evidence_refs: list[str] | None = None,
    ) -> RuntimeEvent:
        with self._lock:
            run["seq"] = int(run.get("seq") or 0) + 1
            ev = RuntimeEvent(
                sequence_id=run["seq"],
                event=event,
                message=message,
                phase=phase or run.get("status") or "",
                data=data or {},
                mission_id=str(run.get("mission_id") or ""),
                agent_id=str(run.get("role") or ""),
                repo_id=str(run.get("repo_id") or ""),
                tool=tool,
                policy=policy,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status=status,
                duration_ms=duration_ms,
                evidence_refs=list(evidence_refs or []),
            )
            run["events"].append(ev)
        return ev

    def _agent_loop(self, run_id: str, followup: str | None = None) -> None:
        run = self._require(run_id)
        workspace = Path(run["workspace"])
        model = run["model"]
        max_steps = int(run["max_steps"])
        auto_approve = bool(run["auto_approve_edits"])
        allowed_tools = run.get("allowed_tools")
        role_tools = (
            [t for t in TOOL_SPECS if t["function"]["name"] in allowed_tools] if allowed_tools else TOOL_SPECS
        )

        try:
            adapter, model = get_agent_model_adapter(
                model, mode=str(run.get("model_route_mode") or AUTO_ROUTED)
            )
        except ModelProviderError as exc:
            run["status"] = "failed"
            self._emit(
                run,
                "failed",
                f"blocked_external: model '{model}' unavailable ({exc.reason}) -- "
                "not silently substituting a different provider",
                phase="failed",
            )
            return

        role_note = (
            f"\n\nYou are acting in the '{run['role']}' role for this mission. "
            f"You only have access to these tools: {[t['function']['name'] for t in role_tools]}. "
            "Do not claim to have done something outside that tool set."
            if run.get("role")
            else ""
        )
        # Mission Memory: a follow-up (submit_message resuming a terminal
        # run) reuses and extends the SAME history this run already built,
        # rather than rebuilding a fresh system+user seed and losing every
        # prior tool call/observation -- see _condense_history above.
        history: list[dict[str, Any]] = run.get("history") or [
            {"role": "system", "content": _build_system_content(run, role_note)},
            {"role": "user", "content": _build_user_content(run, workspace)},
        ]
        if followup:
            history.append({"role": "user", "content": f"## FOLLOW-UP\n{followup}"})
        run["history"] = history

        self._emit(
            run,
            "thinking",
            f"Mentrix Coding Agent planning… ({adapter.provider_name}/{model})",
            phase="running",
        )

        max_turns = int(os.getenv("MENTRIX_CODING_AGENT_HISTORY_MAX_TURNS", "40"))
        for step in range(max_steps):
            if run.get("cancel"):
                return
            history = _condense_history(history, max_turns)
            run["history"] = history
            try:
                resp = adapter.create(
                    model=model,
                    messages=history,
                    tools=role_tools,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=2500,
                )
            except Exception:
                # Local models often lack tools API — fall back to JSON protocol
                try:
                    resp = adapter.create(
                        model=model,
                        messages=history
                        + [
                            {
                                "role": "user",
                                "content": (
                                    "Return ONLY JSON: "
                                    '{"action":"tool","name":"<tool>","args":{...}} '
                                    'or {"action":"done","message":"..."} '
                                    f"Tools: {[t['function']['name'] for t in role_tools]}"
                                ),
                            }
                        ],
                        tools=None,
                        tool_choice="none",
                        temperature=0.2,
                        max_tokens=1200,
                    )
                    text = (resp.choices[0].message.content or "").strip()
                    parsed = _parse_json_action(text)
                    if parsed and parsed.get("action") == "done":
                        run["status"] = "completed"
                        self._emit(run, "completed", parsed.get("message") or "Done", phase="validating")
                        return
                    if parsed and parsed.get("action") == "tool":
                        self._run_one_tool(
                            run,
                            workspace,
                            name=str(parsed.get("name") or ""),
                            args=parsed.get("args") or {},
                            auto_approve=auto_approve,
                            history=history,
                            tool_call_id=f"json-{step}",
                        )
                        continue
                    run["status"] = "completed"
                    self._emit(run, "completed", text[:800] or "Done", phase="validating")
                    return
                except Exception as exc2:  # noqa: BLE001
                    run["status"] = "failed"
                    self._emit(run, "failed", f"LLM error: {exc2}", phase="failed")
                    return

            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []
            content = (msg.content or "").strip()

            if tool_calls:
                history.append(
                    {
                        "role": "assistant",
                        "content": content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments or "{}",
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )
                for tc in tool_calls:
                    if run.get("cancel"):
                        return
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    self._run_one_tool(
                        run,
                        workspace,
                        name=tc.function.name,
                        args=args if isinstance(args, dict) else {},
                        auto_approve=auto_approve,
                        history=history,
                        tool_call_id=tc.id,
                    )
                continue

            # No tools — done
            history.append({"role": "assistant", "content": content})
            run["status"] = "completed"
            self._emit(run, "completed", content[:1200] or "Mentrix Coding Agent finished", phase="validating")
            return

        run["status"] = "completed"
        self._emit(run, "completed", "Max steps reached", phase="validating", data={"max_steps": max_steps})

    def _run_one_tool(
        self,
        run: dict[str, Any],
        workspace: Path,
        *,
        name: str,
        args: dict[str, Any],
        auto_approve: bool,
        history: list[dict[str, Any]],
        tool_call_id: str,
    ) -> None:
        safe_args = {k: v for k, v in args.items() if k != "content"}
        if "content" in args:
            safe_args["content_len"] = len(str(args.get("content") or ""))
        self._emit(
            run,
            "tool_start",
            f"{name}",
            phase="running",
            data={"tool": name, "args": safe_args},
            tool=name,
        )
        started_at = time.monotonic()
        allowed_tools = run.get("allowed_tools")
        if allowed_tools and name not in allowed_tools:
            tool_policy = "denied"
            result: dict[str, Any] = {
                "ok": False,
                "error": (
                    f"policy_denied: tool '{name}' is not permitted for the "
                    f"'{run.get('role') or 'current'}' role in this mission"
                ),
            }
        else:
            write_decision = _authorize_agent_write(run, workspace, name, args)
            if write_decision is not None and not write_decision.allowed:
                tool_policy = "denied"
                result = {
                    "ok": False,
                    "error": f"write_blocked: {write_decision.reason}",
                    "reason": write_decision.reason,
                    "detail": write_decision.detail,
                }
            else:
                tool_policy = "allowed"
                result = execute_tool(name, args, workspace=workspace, auto_approve_edits=auto_approve)

        if result.get("needs_approval"):
            tool_policy = "approval_required"
            action_id = str(uuid4())
            payload = {
                "tool": result.get("action") or name,
                "args": result.get("args") or args,
                "summary": result.get("summary") or name,
            }
            run["pending"][action_id] = payload
            ev = threading.Event()
            run["approve_events"][action_id] = ev
            self._emit(
                run,
                "needs_approval",
                payload["summary"],
                phase="awaiting_approval",
                data={"action_id": action_id, **{k: v for k, v in payload.items() if k != "args"}},
            )
            run["status"] = "awaiting_approval"
            # Wait up to 10 minutes for human
            approved = ev.wait(timeout=600)
            run["status"] = "running"
            if run.get("cancel") or action_id in (run.get("_rejected_actions") or set()):
                tool_policy = "denied"
                result = {"ok": False, "error": "rejected_by_user"}
            elif not approved:
                tool_policy = "denied"
                result = {"ok": False, "error": "approval_timeout"}
            else:
                payload_args = dict(payload.get("args") or {})
                payload_args["_approved"] = True
                # A human approving a pending action authorizes the tool
                # call, not an escape from the plan's write contract -- the
                # same check applies here as on the unapproved path.
                write_decision = _authorize_agent_write(run, workspace, payload["tool"], payload_args)
                if write_decision is not None and not write_decision.allowed:
                    tool_policy = "denied"
                    result = {
                        "ok": False,
                        "error": f"write_blocked: {write_decision.reason}",
                        "reason": write_decision.reason,
                        "detail": write_decision.detail,
                    }
                else:
                    tool_policy = "allowed"
                    result = execute_tool(
                        payload["tool"],
                        payload_args,
                        workspace=workspace,
                        auto_approve_edits=True,
                    )

        if result.get("file_diff") and result.get("path"):
            path = result["path"]
            if path not in run["files_written"]:
                run["files_written"].append(path)
            run["artifacts"].append(
                RuntimeArtifact(path=path, kind="file", content=(result.get("diff") or "")[:2000])
            )
            self._emit(
                run,
                "file_diff",
                f"Updated {path}",
                phase="build",
                data={"path": path, "diff": (result.get("diff") or "")[:4000]},
            )

        if result.get("command_output"):
            self._emit(
                run,
                "command_output",
                f"$ {result.get('command')}",
                phase="running",
                data={
                    "exit_code": result.get("exit_code"),
                    "stdout": result.get("stdout"),
                    "stderr": result.get("stderr"),
                },
            )

        duration_ms = int((time.monotonic() - started_at) * 1000)
        evidence_refs = [ref for ref in (result.get("path"), result.get("screenshot_path")) if ref]
        self._emit(
            run,
            "tool_end",
            f"{name}: {'ok' if result.get('ok') else result.get('error') or 'error'}",
            phase="running",
            data={"tool": name, "ok": bool(result.get("ok")), "path": result.get("path")},
            tool=name,
            policy=tool_policy,
            status="ok" if result.get("ok") else "error",
            duration_ms=duration_ms,
            evidence_refs=evidence_refs,
        )

        # Truncate large tool results for the model
        tool_payload = dict(result)
        if "content" in tool_payload and isinstance(tool_payload["content"], str):
            tool_payload["content"] = tool_payload["content"][:8000]
        if "diff" in tool_payload and isinstance(tool_payload["diff"], str):
            tool_payload["diff"] = tool_payload["diff"][:4000]
        history.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(tool_payload, default=str)[:10000],
            }
        )


def _parse_json_action(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None

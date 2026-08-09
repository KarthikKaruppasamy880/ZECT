"""Mentrix native Coding Agent runtime — in-process tool loop.

Public provider name: mentrix_native. No third-party product branding.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.adapters.coding_runtime import RuntimeArtifact, RuntimeEvent
from app.adapters.llm.openai_compat import (
    get_openai_compat_client,
    mentrix_llm_chat_model,
    openai_compat_available,
)
from app.services.coding_engine.mentrix_agent_tools import (
    TOOL_SPECS,
    execute_tool,
    resolve_workspace,
)

_SYSTEM = (
    "You are Mentrix Coding Agent — ZECT's coding agent for this workspace. "
    "Use tools to inspect and edit the repository. Work in any language the repo uses. "
    "Prefer apply_patch for small edits and write_file for new files. "
    "Run tests/linters with run_command when helpful. "
    "Do not invent file contents you have not read. "
    "When modernizing legacy code, respect Lattice facts and Blueprint target architecture when provided. "
    "When the goal is done, reply with a short summary and no further tool calls."
)


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
        model = (kwargs.get("model") or "").strip() or mentrix_llm_chat_model()
        max_steps = int(kwargs.get("max_steps") or os.getenv("MENTRIX_CODING_AGENT_MAX_STEPS", "24"))
        expected_files = list(kwargs.get("expected_files") or [])
        project_id = kwargs.get("project_id")
        skill_id = kwargs.get("skill_id")
        project_key = (kwargs.get("project_key") or "").strip() or None
        agent_context = (kwargs.get("agent_context") or "").strip()
        if not agent_context:
            try:
                from app.services.coding_engine.agent_context import compose_coding_agent_context

                agent_context = compose_coding_agent_context(
                    goal=goal,
                    project_id=int(project_id) if project_id is not None else None,
                    skill_id=int(skill_id) if skill_id is not None else None,
                    project_key=project_key,
                    db=kwargs.get("db"),
                )
            except Exception:  # noqa: BLE001
                agent_context = ""

        try:
            ws = resolve_workspace(workspace)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(str(exc)) from exc

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
    ) -> RuntimeEvent:
        with self._lock:
            run["seq"] = int(run.get("seq") or 0) + 1
            ev = RuntimeEvent(
                sequence_id=run["seq"],
                event=event,
                message=message,
                phase=phase or run.get("status") or "",
                data=data or {},
            )
            run["events"].append(ev)
        return ev

    def _agent_loop(self, run_id: str, followup: str | None = None) -> None:
        run = self._require(run_id)
        workspace = Path(run["workspace"])
        model = run["model"]
        max_steps = int(run["max_steps"])
        auto_approve = bool(run["auto_approve_edits"])

        if not openai_compat_available():
            run["status"] = "failed"
            self._emit(run, "failed", "No Mentrix LLM gateway or OPENAI_API_KEY configured", phase="failed")
            return

        history: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": _SYSTEM
                + (
                    f"\n\nAdditional Mentrix context (skills/memory/Lattice/Blueprint):\n{run['agent_context']}"
                    if (run.get("agent_context") or "").strip()
                    else ""
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Workspace: {workspace}\n"
                    f"Goal: {run['goal']}\n"
                    + (
                        f"Expected files (prefer these): {run['expected_files']}\n"
                        if run.get("expected_files")
                        else ""
                    )
                    + (f"\nFollow-up: {followup}" if followup else "")
                ),
            },
        ]

        try:
            client = get_openai_compat_client(timeout=90.0)
        except Exception as exc:  # noqa: BLE001
            run["status"] = "failed"
            self._emit(run, "failed", f"LLM client error: {exc}", phase="failed")
            return

        self._emit(run, "thinking", "Mentrix Coding Agent planning…", phase="running")

        for step in range(max_steps):
            if run.get("cancel"):
                return
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=history,
                    tools=TOOL_SPECS,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=2500,
                )
            except Exception:
                # Local models often lack tools API — fall back to JSON protocol
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=history
                        + [
                            {
                                "role": "user",
                                "content": (
                                    "Return ONLY JSON: "
                                    '{"action":"tool","name":"<tool>","args":{...}} '
                                    'or {"action":"done","message":"..."} '
                                    f"Tools: {[t['function']['name'] for t in TOOL_SPECS]}"
                                ),
                            }
                        ],
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
        )
        result = execute_tool(name, args, workspace=workspace, auto_approve_edits=auto_approve)

        if result.get("needs_approval"):
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
                result = {"ok": False, "error": "rejected_by_user"}
            elif not approved:
                result = {"ok": False, "error": "approval_timeout"}
            else:
                # Re-run with forced approve
                result = execute_tool(
                    payload["tool"],
                    payload["args"],
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

        self._emit(
            run,
            "tool_end",
            f"{name}: {'ok' if result.get('ok') else result.get('error') or 'error'}",
            phase="running",
            data={"tool": name, "ok": bool(result.get("ok")), "path": result.get("path")},
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

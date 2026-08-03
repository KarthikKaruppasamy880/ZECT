"""Assistant mode — a model-driven tool-calling loop, unlike every other
mode's fixed stage list.

Every other MODE_PIPELINE entry is a pre-scripted sequence of stages; if a
request doesn't match one, nothing happens. This is the fix for that: the
model itself decides which tool to call based on the actual ask, bounded by
a step cap so it can't run away. Every tool call — light or heavy — still
goes through the same Permission Broker gate Companion already uses; this
mode never gets to skip approval for consequential actions just because it's
more autonomous.

Heavy tools (start_upgrade_run, start_bugfix_run, trigger_build) kick off a
background MentrixRun and return immediately with a run id — they do not
block the loop waiting for a multi-minute pipeline to finish.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any

MAX_ASSISTANT_STEPS = int(os.getenv("MENTRIX_ASSISTANT_MAX_STEPS", "6"))

_HEAVY_TOOL_NAMES = {
    "start_upgrade_run",
    "start_bugfix_run",
    "trigger_build",
    "request_review",
    "trigger_deploy",
    "scan_for_anomalies",
    "file_security_ticket",
}


def _heavy_tool_schemas() -> list[dict[str, Any]]:
    """Same flat shape as realtime_tool_schemas() — converted to chat.completions'
    nested {"type":"function","function":{...}} shape by _to_cc_tool below."""
    return [
        {
            "type": "function",
            "name": "start_upgrade_run",
            "description": (
                "Start a full legacy-upgrade run in the background (Lattice scan, "
                "blueprint, plan, build, review, PR gate). Returns immediately with "
                "a run id to check later — does not wait for it to finish."
            ),
            "parameters": {
                "type": "object",
                "properties": {"goal": {"type": "string"}},
                "required": ["goal"],
            },
        },
        {
            "type": "function",
            "name": "start_bugfix_run",
            "description": (
                "Start a bug-fix run in the background (reproduce, trace impacted "
                "components, root-cause, fix, regression test, review, PR gate). "
                "Returns immediately with a run id."
            ),
            "parameters": {
                "type": "object",
                "properties": {"goal": {"type": "string"}},
                "required": ["goal"],
            },
        },
        {
            "type": "function",
            "name": "trigger_build",
            "description": "Start a delivery build run in the background for a specific feature or plan step. Returns immediately with a run id.",
            "parameters": {
                "type": "object",
                "properties": {"goal": {"type": "string"}},
                "required": ["goal"],
            },
        },
        {
            "type": "function",
            "name": "request_review",
            "description": "Run Mentrix Ultra Review on a code snippet and return the result inline — fast enough to not background.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["code"],
            },
        },
        {
            "type": "function",
            "name": "trigger_deploy",
            "description": (
                "Request a GitHub Actions deployment trigger. This ALWAYS requires "
                "human approval before anything actually runs — calling this only "
                "starts that approval flow, it never deploys by itself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "workflow_file": {"type": "string"},
                    "environment": {"type": "string"},
                },
                "required": ["owner", "repo", "workflow_file"],
            },
        },
        {
            "type": "function",
            "name": "scan_for_anomalies",
            "description": (
                "Scan ZECT's own audit trail (PermissionAudit + AuditLog) for signs "
                "someone is probing or misusing access: permission-denial spikes, "
                "logins from multiple IPs, bursts of activity on secrets/users/"
                "permissions, and off-hours access to sensitive resources. Read-only, "
                "fast enough to not background. Only looks at data ZECT already has "
                "— it does not monitor anything outside this app."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_hours": {"type": "integer", "description": "How far back to scan. Defaults to 24."},
                },
                "required": [],
            },
        },
        {
            "type": "function",
            "name": "file_security_ticket",
            "description": (
                "File a real Jira ticket for a security finding (e.g. from "
                "scan_for_anomalies). Requires Jira to be configured "
                "(JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN) — creates an actual issue, "
                "not a placeholder."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "description": {"type": "string"},
                    "project_key": {"type": "string"},
                },
                "required": ["summary"],
            },
        },
    ]


def _to_cc_tool(flat: dict[str, Any]) -> dict[str, Any]:
    """Adapt the Realtime API's flat tool shape to chat.completions' nested
    {"type":"function","function":{name,description,parameters}} shape —
    they are NOT the same wire format despite looking similar."""
    return {
        "type": "function",
        "function": {
            "name": flat["name"],
            "description": flat.get("description", ""),
            "parameters": flat.get("parameters") or {"type": "object", "properties": {}},
        },
    }


def _kickoff_background_run(
    mode: str,
    goal: str,
    *,
    project_key: str = "",
    workspace: str = "",
    repo_id: int | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    from app.database import SessionLocal
    from app.models import MentrixRun

    setup_db = SessionLocal()
    try:
        placeholder = MentrixRun(
            mode=mode,
            goal=goal,
            status="queued",
            current_agent="orchestrator",
            events_json="[]",
            gates_json="{}",
            next_step="",
            created_by=created_by,
        )
        setup_db.add(placeholder)
        setup_db.commit()
        setup_db.refresh(placeholder)
        run_id = placeholder.id
    finally:
        setup_db.close()

    def _worker() -> None:
        from app.services.forge_loop.orchestrator import run_mentrix

        worker_db = SessionLocal()
        try:
            # existing_run must be bound to this thread's own session — a
            # detached object from setup_db can't safely cross sessions.
            row = worker_db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
            if row is None:
                return
            run_mentrix(
                worker_db,
                goal=goal,
                mode=mode,
                project_key=project_key,
                workspace=workspace,
                repo_id=repo_id,
                created_by=created_by,
                existing_run=row,
            )
        except Exception:
            worker_db.rollback()
            row = worker_db.query(MentrixRun).filter(MentrixRun.id == run_id).first()
            if row:
                row.status = "failed"
                worker_db.commit()
        finally:
            worker_db.close()

    threading.Thread(target=_worker, daemon=True, name=f"mentrix-bg-{run_id}").start()
    return {
        "ok": True,
        "run_id": run_id,
        "mode": mode,
        "status": "queued",
        "note": f"Started {mode} run #{run_id} in the background — check /api/mentrix/runs/{run_id} for progress.",
    }


def execute_heavy_tool(
    name: str, args: dict[str, Any], *, created_by: str = "", project_key: str = "", user_id: int | None = None
) -> dict[str, Any]:
    if name == "start_upgrade_run":
        return _kickoff_background_run("upgrade", args.get("goal", ""), project_key=project_key, created_by=created_by)
    if name == "start_bugfix_run":
        return _kickoff_background_run("bugfix", args.get("goal", ""), project_key=project_key, created_by=created_by)
    if name == "trigger_build":
        return _kickoff_background_run("deliver", args.get("goal", ""), project_key=project_key, created_by=created_by)
    if name == "request_review":
        from app.review_service import review_code_snippet

        try:
            result = review_code_snippet(code=args.get("code", ""), language=args.get("language", "unknown"), user_id=user_id)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "score": result.get("quality_score"), "summary": result.get("summary")}
    if name == "trigger_deploy":
        return _trigger_deploy(args, created_by=created_by)
    if name == "scan_for_anomalies":
        return _scan_for_anomalies(args)
    if name == "file_security_ticket":
        return _file_security_ticket(args, created_by=created_by)
    return {"ok": False, "error": f"unknown heavy tool: {name}"}


def _scan_for_anomalies(args: dict[str, Any]) -> dict[str, Any]:
    from app.database import SessionLocal
    from app.services.security.threat_detection import run_anomaly_scan

    lookback_hours = int(args.get("lookback_hours") or 24)
    db = SessionLocal()
    try:
        result = run_anomaly_scan(db, lookback_hours=lookback_hours)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def _file_security_ticket(args: dict[str, Any], *, created_by: str = "") -> dict[str, Any]:
    from app.database import SessionLocal
    from app.services.mcp.hub import execute_tool

    project_key = args.get("project_key") or os.getenv("SECURITY_JIRA_PROJECT_KEY", "SEC")
    summary = args.get("summary", "")[:250]
    description = args.get("description", "")
    db = SessionLocal()
    try:
        outcome = execute_tool(
            db,
            server_id="jira",
            tool_name="create_issue",
            arguments={"project": project_key, "summary": summary, "type": "Bug"},
            user_email=created_by,
        )
        if outcome.get("status") != "success":
            return {"ok": False, "error": outcome.get("result", {}).get("message") or "Jira not configured or unreachable"}
        result = outcome.get("result") or {}
        key = result.get("key")
        return {"ok": bool(key), "ticket_key": key, "description": description}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def _trigger_deploy(args: dict[str, Any], *, created_by: str = "") -> dict[str, Any]:
    """Delegates to the exact same approval-gated endpoint Deploy's own UI
    calls — this tool call cannot bypass that require_approval wall."""
    from app.core.auth.deps import CurrentUser
    from app.database import SessionLocal
    from app.routers.deploy_phase import DeployTriggerRequest, trigger_workflow

    req = DeployTriggerRequest(
        owner=args.get("owner", ""),
        repo=args.get("repo", ""),
        workflow_file=args.get("workflow_file", ""),
        environment=args.get("environment") or "production",
    )
    db = SessionLocal()
    try:
        system_user = CurrentUser(user_id=None, username=created_by or "assistant", email="", auth_mode="system", token="")
        resp = trigger_workflow(req, current_user=system_user, db=db)
        return {"ok": True, "status": resp.status, "message": resp.message, "audit_id": resp.audit_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def run_assistant_loop(
    db: Any,
    goal: str,
    *,
    project_key: str = "",
    created_by: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """The tool-calling loop itself."""
    from openai import OpenAI

    from app.services.mentrix.companion import _exec_tool
    from app.services.mentrix.permission_broker import check_tool_permission
    from app.services.mentrix.realtime import mentrix_instructions, realtime_tool_schemas

    light_tools = realtime_tool_schemas()
    heavy_tools = _heavy_tool_schemas()
    all_tools = [_to_cc_tool(t) for t in light_tools + heavy_tools]
    light_names = {t["name"] for t in light_tools}

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                mentrix_instructions()
                + " You can call tools to actually do things, not just talk about "
                "them. For long-running work (start_upgrade_run/start_bugfix_run/"
                "trigger_build), start it and report back immediately — do not "
                "wait for it to finish."
            ),
        },
        {"role": "user", "content": goal},
    ]

    tool_log: list[dict[str, Any]] = []
    final_text = ""
    for _step in range(MAX_ASSISTANT_STEPS):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=all_tools,
            tool_choice="auto",
            max_tokens=1500,
            temperature=0.2,
        )
        choice = resp.choices[0]
        messages.append(choice.message.model_dump(exclude_none=True))
        tool_calls = choice.message.tool_calls or []
        if not tool_calls:
            final_text = choice.message.content or ""
            break

        for call in tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            perm = check_tool_permission(db, name, user_id=user_id, user_confirmed=False)
            if perm["result"] == "denied":
                tool_result: dict[str, Any] = {"ok": False, "error": "Permission denied for this action"}
            elif perm["result"] == "pending_approval":
                tool_result = {
                    "ok": False,
                    "pending_approval": True,
                    "note": "This action needs Allow confirmation in the Mentrix overlay first.",
                }
            elif name in _HEAVY_TOOL_NAMES:
                tool_result = execute_heavy_tool(name, args, created_by=created_by, project_key=project_key, user_id=user_id)
            elif name in light_names:
                tool_result = _exec_tool(db, name, args, project_key=project_key, created_by=created_by)
            else:
                tool_result = {"ok": False, "error": f"unknown tool: {name}"}

            tool_log.append({"tool": name, "args": args, "result": tool_result})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(tool_result)[:4000],
                }
            )
    else:
        final_text = final_text or "Reached the step limit — some follow-up may still be needed."

    return {"answer": final_text, "tool_calls": tool_log, "model": "gpt-4o-mini"}

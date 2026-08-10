"""First five ZECT Mentrix Automation Loop definitions (L0/L1 default)."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.automation_loops.types import (
    AUTONOMY_L0,
    AUTONOMY_L1,
    LoopBudget,
    LoopPolicy,
    LoopTrigger,
)

DAILY_BRIEF = "daily_brief"
PR_CI_WATCH = "pr_ci_watch"
JIRA_TRIAGE = "jira_triage"
PRESENTATION_PREP = "presentation_prep"
PERSONAL_FOLLOWUP = "personal_followup"

BUILTIN_LOOPS: dict[str, dict[str, Any]] = {
    DAILY_BRIEF: {
        "key": DAILY_BRIEF,
        "name": "Daily Brief Loop",
        "description": "Outlook/Calendar/Slack/Jira/GitHub/WorkItems → PersonalActions via assemble_daily_brief",
        "target": "personal_action",
        "default_autonomy": AUTONOMY_L0,
        "budget": LoopBudget(max_actions=40, max_runtime_seconds=180).as_dict(),
        "policy": LoopPolicy(autonomy_level=AUTONOMY_L0, require_human_gate=True).as_dict(),
        "trigger": LoopTrigger(
            kind="schedule", schedule_task_type="automation_loop:daily_brief", interval_minutes=60
        ).as_dict(),
        "phases": ["observe_connectors", "upsert_personal_actions", "summarize", "gate"],
    },
    PR_CI_WATCH: {
        "key": PR_CI_WATCH,
        "name": "PR/CI Watch Loop",
        "description": "Detect CI/PR failures → analyze → optionally create WorkItem/fix under policy",
        "target": "work_item",
        "default_autonomy": AUTONOMY_L1,
        "budget": LoopBudget(max_actions=15, max_runtime_seconds=240).as_dict(),
        "policy": LoopPolicy(autonomy_level=AUTONOMY_L1, require_human_gate=True, allow_l2=False).as_dict(),
        "trigger": LoopTrigger(
            kind="schedule", schedule_task_type="automation_loop:pr_ci_watch", interval_minutes=30
        ).as_dict(),
        "phases": ["observe_github", "analyze_failures", "recommend_or_create", "gate"],
    },
    JIRA_TRIAGE: {
        "key": JIRA_TRIAGE,
        "name": "Jira Triage Loop",
        "description": "Assigned/blocked/new work → Project Intelligence → recommendation/plan",
        "target": "work_item",
        "default_autonomy": AUTONOMY_L1,
        "budget": LoopBudget(max_actions=20).as_dict(),
        "policy": LoopPolicy(autonomy_level=AUTONOMY_L1, require_human_gate=True).as_dict(),
        "trigger": LoopTrigger(
            kind="schedule", schedule_task_type="automation_loop:jira_triage", interval_minutes=45
        ).as_dict(),
        "phases": ["observe_jira", "project_intelligence", "recommend_plan", "gate"],
    },
    PRESENTATION_PREP: {
        "key": PRESENTATION_PREP,
        "name": "Presentation Preparation Loop",
        "description": "Sources → outline → claim verification → deck → rehearsal → READY_TO_PRESENT",
        "target": "presentation",
        "default_autonomy": AUTONOMY_L1,
        "budget": LoopBudget(max_actions=12, max_runtime_seconds=600).as_dict(),
        "policy": LoopPolicy(autonomy_level=AUTONOMY_L1, require_human_gate=True).as_dict(),
        "trigger": LoopTrigger(kind="manual", schedule_task_type="automation_loop:presentation_prep").as_dict(),
        "phases": ["ingest_sources", "outline", "verify_claims", "prepare_deck", "rehearse", "ready_gate"],
    },
    PERSONAL_FOLLOWUP: {
        "key": PERSONAL_FOLLOWUP,
        "name": "Personal Follow-up Loop",
        "description": "Unanswered mail/Slack/actions → recommend/draft/follow up",
        "target": "personal_action",
        "default_autonomy": AUTONOMY_L1,
        "budget": LoopBudget(max_actions=25).as_dict(),
        "policy": LoopPolicy(autonomy_level=AUTONOMY_L1, require_human_gate=True).as_dict(),
        "trigger": LoopTrigger(
            kind="schedule", schedule_task_type="automation_loop:personal_followup", interval_minutes=120
        ).as_dict(),
        "phases": ["scan_open_actions", "recommend_followups", "draft_optional", "gate"],
    },
}


def list_builtin_definitions() -> list[dict[str, Any]]:
    return [dict(v) for v in BUILTIN_LOOPS.values()]


def get_builtin(key: str) -> dict[str, Any] | None:
    return dict(BUILTIN_LOOPS[key]) if key in BUILTIN_LOOPS else None

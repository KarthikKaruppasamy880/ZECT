"""ZECT Mentrix Automation Loop definitions (personal + engineering; L0/L1 default)."""

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

ENGINEERING_DELIVERY = "engineering_delivery"
BUG_FIX = "bug_fix"
JIRA_DELIVERY = "jira_delivery"
CI_FIX = "ci_fix"
PR_REVIEW_FIX = "pr_review_fix"

ENGINEERING_LOOP_KEYS = frozenset(
    {ENGINEERING_DELIVERY, BUG_FIX, JIRA_DELIVERY, CI_FIX, PR_REVIEW_FIX}
)

_ENG_BUDGET = LoopBudget(
    max_actions=40,
    max_runtime_seconds=900,
    max_tokens=100_000,
    max_cost_usd=25.0,
    max_retries=3,
    max_same_failure=3,
    max_files_changed=200,
    max_coder_test_cycles=3,
    max_coder_review_cycles=3,
    no_progress_threshold=2,
).as_dict()

_ENG_POLICY = LoopPolicy(
    autonomy_level=AUTONOMY_L1,
    require_human_gate=True,
    allow_l2=False,
    allow_l3=False,
).as_dict()

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
    # --- Engineering loops (Planner→Coder↔Test↔Review→Acceptance on MentrixAutomationLoop) ---
    ENGINEERING_DELIVERY: {
        "key": ENGINEERING_DELIVERY,
        "name": "Engineering Delivery Loop",
        "description": "Planner → approval → Coding Agent ↔ Test ↔ Review → AcceptanceVerifier → Evidence → PR",
        "target": "work_item",
        "default_autonomy": AUTONOMY_L1,
        "budget": dict(_ENG_BUDGET),
        "policy": dict(_ENG_POLICY),
        "trigger": LoopTrigger(kind="manual", schedule_task_type="automation_loop:engineering_delivery").as_dict(),
        "phases": [
            "planner",
            "plan_approval",
            "coding_agent",
            "test_agent",
            "review_agent",
            "acceptance_verifier",
            "evidence_verifier",
            "gate",
        ],
    },
    BUG_FIX: {
        "key": BUG_FIX,
        "name": "Bug Fix Loop",
        "description": "Reproduce → plan → code ↔ test ↔ review → acceptance for defect WorkItems",
        "target": "work_item",
        "default_autonomy": AUTONOMY_L1,
        "budget": dict(_ENG_BUDGET),
        "policy": dict(_ENG_POLICY),
        "trigger": LoopTrigger(kind="event", event_name="bug_reported", schedule_task_type="automation_loop:bug_fix").as_dict(),
        "phases": ["planner", "coding_agent", "test_agent", "review_agent", "acceptance_verifier", "gate"],
    },
    JIRA_DELIVERY: {
        "key": JIRA_DELIVERY,
        "name": "Jira Delivery Loop",
        "description": "Jira issue → WorkItem → Project Intelligence → engineering delivery spine",
        "target": "work_item",
        "default_autonomy": AUTONOMY_L1,
        "budget": dict(_ENG_BUDGET),
        "policy": dict(_ENG_POLICY),
        "trigger": LoopTrigger(kind="manual", schedule_task_type="automation_loop:jira_delivery").as_dict(),
        "phases": ["jira_context", "planner", "coding_agent", "test_agent", "review_agent", "acceptance_verifier", "gate"],
    },
    CI_FIX: {
        "key": CI_FIX,
        "name": "CI Fix Loop",
        "description": "CI failure signal → WorkItem → code ↔ test ↔ review → acceptance",
        "target": "work_item",
        "default_autonomy": AUTONOMY_L1,
        "budget": dict(_ENG_BUDGET),
        "policy": dict(_ENG_POLICY),
        "trigger": LoopTrigger(kind="event", event_name="ci_failure", schedule_task_type="automation_loop:ci_fix").as_dict(),
        "phases": ["observe_ci", "planner", "coding_agent", "test_agent", "review_agent", "acceptance_verifier", "gate"],
    },
    PR_REVIEW_FIX: {
        "key": PR_REVIEW_FIX,
        "name": "PR Review Fix Loop",
        "description": "Review findings → verified blockers → coder ↔ test → acceptance",
        "target": "work_item",
        "default_autonomy": AUTONOMY_L1,
        "budget": dict(_ENG_BUDGET),
        "policy": dict(_ENG_POLICY),
        "trigger": LoopTrigger(kind="event", event_name="pr_review_blocking", schedule_task_type="automation_loop:pr_review_fix").as_dict(),
        "phases": ["review_agent", "coding_agent", "test_agent", "acceptance_verifier", "gate"],
    },
}


def list_builtin_definitions() -> list[dict[str, Any]]:
    return [dict(v) for v in BUILTIN_LOOPS.values()]


def get_builtin(key: str) -> dict[str, Any] | None:
    return dict(BUILTIN_LOOPS[key]) if key in BUILTIN_LOOPS else None


def is_engineering_loop(key: str) -> bool:
    return key in ENGINEERING_LOOP_KEYS

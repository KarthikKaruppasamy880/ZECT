"""Engineering delivery loop — Planner→Coder↔Test↔Review→Acceptance→Evidence on MentrixAutomationLoop."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.adapters.coding_runtime import get_mentrix_native_runtime, selected_coding_engine
from app.services.mentrix.automation_loops.types import (
    AUTONOMY_L0,
    AUTONOMY_L1,
    AUTONOMY_L3,
    STATUS_NEEDS_HUMAN,
    CircuitBreaker,
    LoopBudget,
    LoopCheckpoint,
)
from app.services.mentrix.engineering_agents.acceptance_verifier import AcceptanceVerifier
from app.services.mentrix.engineering_agents.planner import MentrixPlanner
from app.services.mentrix.engineering_agents.policy import evaluate_high_risk_action
from app.services.mentrix.engineering_agents.review_agent import MentrixReviewAgent
from app.services.mentrix.engineering_agents.roles import ROLE_CODER
from app.services.mentrix.engineering_agents.test_agent import MentrixTestAgent
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import load_execution_state, record_checkpoint
from app.services.work_items.developer_service import MentrixDeveloperService


class MentrixCodingAgentRole:
    """Thin role wrapper — real mentrix_native only; cannot READY_TO_SHIP."""

    role = ROLE_CODER

    def __init__(self, db: Session) -> None:
        self.db = db
        self.dev = MentrixDeveloperService(db)

    def execute_approved_ops(
        self,
        *,
        work_item_id: int,
        goal: str = "",
        workspace: str = "",
        dry_run: bool = True,
        operation_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        store = ArtifactStore(work_item_id)
        manifest = store.read_json("EXECUTION_MANIFEST.json", default={}) or {}
        ops = list(manifest.get("operations") or [])
        approved_ids = {str(o.get("id")) for o in ops}
        mandatory = list(manifest.get("mandatory_operation_ids") or [])
        requested = list(operation_ids) if operation_ids is not None else list(approved_ids)
        unapproved = [oid for oid in requested if oid not in approved_ids]
        if unapproved:
            return {
                "ok": False,
                "role": self.role,
                "error": "unapproved_operations",
                "unapproved": unapproved,
                "may_ready_to_ship": False,
                "work_item_id": work_item_id,
            }

        engine = selected_coding_engine()
        try:
            _ = get_mentrix_native_runtime()
            native_ok = True
            native_err = ""
        except Exception as exc:  # noqa: BLE001
            native_ok = False
            native_err = str(exc)[:200]

        if dry_run or not workspace:
            for op in ops:
                if op.get("id") in mandatory or op.get("mandatory") or str(op.get("id")) in requested:
                    # Dry-run / empty workspace never claims real completion for EvidenceVerifier
                    op["status"] = "simulated"
            manifest["operations"] = ops
            store.write_json("EXECUTION_MANIFEST.json", manifest)
            record_checkpoint(
                store,
                checkpoint_type="completion",
                operation_id="coding_agent_dry",
                payload={"engine": engine, "ops": requested, "status": "simulated"},
            )
            return {
                "ok": True,
                "role": self.role,
                "dry_run": True,
                "engine": engine,
                "native_ok": native_ok,
                "native_error": native_err,
                "may_ready_to_ship": False,
                "operations_completed": [],
                "operations_simulated": [o["id"] for o in ops if o.get("status") == "simulated"],
                "work_item_id": work_item_id,
            }

        out = self.dev.start_agent(work_item_id=work_item_id, goal=goal, workspace=workspace)
        out["role"] = self.role
        out["may_ready_to_ship"] = False
        out["engine"] = engine
        out["native_ok"] = native_ok
        return out

    def refuse_ready_to_ship(self) -> dict[str, Any]:
        return {"ok": False, "role": self.role, "error": "coder_cannot_ready_to_ship", "may_ready_to_ship": False}


class EngineeringLoopRunner:
    """Run engineering_delivery / bug_fix / jira_delivery / ci_fix / pr_review_fix."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def run(
        self,
        *,
        loop_key: str,
        goal: str,
        work_item_id: int | None = None,
        user_id: int | None = None,
        autonomy: str = AUTONOMY_L1,
        dry_run: bool = True,
        workspace: str = "",
        inject_test: dict[str, Any] | None = None,
        inject_review: list[dict[str, Any]] | None = None,
        auto_approve_plan: bool = False,
        ship: bool = False,
        budget_override: LoopBudget | None = None,
        resume: bool = False,
        force_high_risk: str | None = None,
        data_classification: str = "internal",
        tokens_delta: int = 0,
        cost_delta: float = 0.0,
    ) -> dict[str, Any]:
        budget = budget_override or LoopBudget(
            max_actions=40,
            max_coder_test_cycles=3,
            max_coder_review_cycles=3,
            max_same_failure=3,
            no_progress_threshold=2,
        )
        checkpoint = LoopCheckpoint(phase="start")
        breaker = CircuitBreaker(max_same_failure=budget.max_same_failure)
        phases: list[dict[str, Any]] = []

        # L3 still cannot bypass high-risk policy
        if force_high_risk:
            risk = evaluate_high_risk_action(
                force_high_risk, autonomy=autonomy, data_classification=data_classification
            )
            if risk["denied"] or (risk["needs_confirm"] and autonomy == AUTONOMY_L3 and not ship):
                return {
                    "ok": False,
                    "loop_key": loop_key,
                    "status": STATUS_NEEDS_HUMAN,
                    "error": "permission_or_policy_blocked",
                    "policy": risk,
                    "needs_human": True,
                    "phases": [{"phase": "permission_gate", "ok": False, "policy": risk}],
                }
            phases.append({"phase": "permission_gate", "ok": not risk["denied"], "policy": risk})

        if autonomy == AUTONOMY_L0:
            return {
                "ok": True,
                "loop_key": loop_key,
                "autonomy": AUTONOMY_L0,
                "mode": "observe_only",
                "phases": [{"phase": "observe", "ok": True}],
                "needs_human": True,
            }

        planner = MentrixPlanner(self.db)
        wi_id = work_item_id
        store: ArtifactStore | None = ArtifactStore(wi_id) if wi_id else None

        if resume and wi_id and store:
            state = load_execution_state(store)
            resume_op = state.get("resume_operation") or state.get("phase")
            phases.append({"phase": "resume", "ok": True, "resume_operation": resume_op})
            checkpoint.phase = f"resume:{resume_op}"
            checkpoint.state["resumed_from"] = resume_op
        else:
            plan_out = planner.plan(
                goal=goal,
                work_item_id=work_item_id,
                actor=f"loop:{loop_key}",
                approve=auto_approve_plan,
            )
            wi_id = int(plan_out["work_item_id"])
            store = ArtifactStore(wi_id)
            phases.append({"phase": "planner", "ok": True, "work_item_id": wi_id})
            checkpoint.iteration += 1
            checkpoint.actions_used += 1

            if plan_out.get("needs_approval") and not auto_approve_plan and autonomy in (AUTONOMY_L1, "L2"):
                store.write_json(
                    "EXECUTION_STATE.json",
                    {**(load_execution_state(store)), "phase": "AWAITING_PLAN_APPROVAL", "loop_key": loop_key},
                )
                return {
                    "ok": True,
                    "loop_key": loop_key,
                    "work_item_id": wi_id,
                    "autonomy": autonomy,
                    "status": "AWAITING_PLAN_APPROVAL",
                    "phases": phases,
                    "needs_human": True,
                    "result": plan_out,
                    "checkpoint": checkpoint.as_dict(),
                }

            if plan_out.get("needs_approval") and auto_approve_plan:
                MentrixDeveloperService(self.db).approve_plan(work_item_id=wi_id, actor=f"loop:{loop_key}")
                phases.append({"phase": "plan_approval", "ok": True})

        assert wi_id is not None and store is not None

        # Budget pre-check (tokens/cost/actions)
        checkpoint.tokens_used += int(tokens_delta or 0)
        checkpoint.cost_usd += float(cost_delta or 0)
        if checkpoint.tokens_used > budget.max_tokens:
            return self._escalate(loop_key, wi_id, phases, checkpoint, "budget_tokens_exhausted")
        if checkpoint.cost_usd > budget.max_cost_usd:
            return self._escalate(loop_key, wi_id, phases, checkpoint, "budget_cost_exhausted")
        if checkpoint.actions_used > budget.max_actions:
            return self._escalate(loop_key, wi_id, phases, checkpoint, "budget_actions_exhausted")

        coder = MentrixCodingAgentRole(self.db)
        test_agent = MentrixTestAgent(wi_id)
        review_agent = MentrixReviewAgent(self.db, wi_id)

        coder_test_cycles = 0
        last_progress_sig = ""
        no_progress = 0
        test_inject = inject_test

        while coder_test_cycles < budget.max_coder_test_cycles:
            coder_test_cycles += 1
            checkpoint.actions_used += 1
            if checkpoint.actions_used > budget.max_actions:
                return self._escalate(loop_key, wi_id, phases, checkpoint, "budget_actions_exhausted")

            code_out = coder.execute_approved_ops(
                work_item_id=wi_id, goal=goal, workspace=workspace, dry_run=dry_run
            )
            phases.append({"phase": "coding_agent", "ok": code_out.get("ok"), "cycle": coder_test_cycles})

            # Default: no invented pass — TestAgent soft path is unverified without inject/args
            run_inject = test_inject
            test_out = test_agent.run(inject_result=run_inject)
            phases.append(
                {"phase": "test_agent", "ok": test_out.get("ok"), "route_back": test_out.get("route_back_to_coder")}
            )

            sig = f"test:{test_out.get('ok')}:{test_out.get('failed')}"
            if sig == last_progress_sig and not test_out.get("ok"):
                no_progress += 1
            else:
                no_progress = 0
                last_progress_sig = sig
            if no_progress >= budget.no_progress_threshold:
                return self._escalate(loop_key, wi_id, phases, checkpoint, "no_progress_threshold")

            if not test_out.get("ok"):
                checkpoint, tripped = breaker.record(checkpoint, "test_failure")
                if tripped:
                    return self._escalate(
                        loop_key, wi_id, phases, checkpoint, "circuit_breaker_test_failure", tripped=True
                    )
                # Keep failing inject for circuit/no-progress tests; clear only when caller wants retry success
                continue
            break
        else:
            return self._escalate(loop_key, wi_id, phases, checkpoint, "max_coder_test_cycles")

        coder_review_cycles = 0
        review_inject = inject_review
        while coder_review_cycles < budget.max_coder_review_cycles:
            coder_review_cycles += 1
            checkpoint.actions_used += 1
            review_out = review_agent.review(inject_findings=review_inject)
            phases.append(
                {
                    "phase": "review_agent",
                    "ok": review_out.get("clean"),
                    "blocking": len(review_out.get("blocking") or []),
                    "route_back": review_out.get("route_back_to_coder"),
                }
            )
            if review_out.get("route_back_to_coder"):
                coder.execute_approved_ops(work_item_id=wi_id, goal=goal, workspace=workspace, dry_run=dry_run)
                review_inject = []  # after fix cycle, re-review clean unless reinjected
                checkpoint, tripped = breaker.record(checkpoint, "review_blocking")
                if tripped:
                    return self._escalate(
                        loop_key, wi_id, phases, checkpoint, "circuit_breaker_review", tripped=True
                    )
                # Re-run tester with same inject policy (never invent a pass)
                test_agent.run(inject_result=inject_test if inject_test is not None else None)
                continue
            break
        else:
            return self._escalate(loop_key, wi_id, phases, checkpoint, "max_coder_review_cycles")

        acceptance = AcceptanceVerifier(self.db, wi_id)
        # Do not manufacture completed statuses — AcceptanceVerifier reads real/simulated states
        do_ship = bool(ship and autonomy == AUTONOMY_L3 and not dry_run)
        acc = acceptance.verify(ship=do_ship, actor=f"loop:{loop_key}")
        phases.append(
            {"phase": "acceptance_verifier", "ok": acc.get("ok"), "ready_to_ship": acc.get("ready_to_ship")}
        )

        status = "READY_TO_SHIP" if acc.get("ready_to_ship") else ("NEEDS_EVIDENCE" if not acc.get("ok") else "ACCEPTED")
        if autonomy in (AUTONOMY_L0, AUTONOMY_L1) or (autonomy == "L2" and not do_ship):
            if acc.get("ready_to_ship"):
                status = "READY_FOR_HUMAN_SHIP_GATE"

        state = load_execution_state(store)
        state["phases"] = phases
        state["loop_key"] = loop_key
        state["autonomy"] = autonomy
        state["phase"] = status
        store.write_json("EXECUTION_STATE.json", state)
        checkpoint.phase = status
        checkpoint.last_error = ""
        checkpoint.same_failure_count = 0

        return {
            "ok": bool(acc.get("ok")),
            "loop_key": loop_key,
            "work_item_id": wi_id,
            "user_id": user_id,
            "autonomy": autonomy,
            "status": status,
            "phases": phases,
            "acceptance": acc,
            "checkpoint": checkpoint.as_dict(),
            "budget": budget.as_dict(),
            "needs_human": status
            in ("AWAITING_PLAN_APPROVAL", "READY_FOR_HUMAN_SHIP_GATE", STATUS_NEEDS_HUMAN),
            "native_engine": selected_coding_engine(),
        }

    def _escalate(
        self,
        loop_key: str,
        wi_id: int | None,
        phases: list,
        checkpoint: LoopCheckpoint,
        reason: str,
        *,
        tripped: bool = False,
    ) -> dict[str, Any]:
        checkpoint.phase = STATUS_NEEDS_HUMAN
        if wi_id:
            store = ArtifactStore(wi_id)
            record_checkpoint(
                store, checkpoint_type="blocking", operation_id="engineering_loop", payload={"reason": reason}
            )
            state = load_execution_state(store)
            state["phase"] = STATUS_NEEDS_HUMAN
            state["blocker"] = reason
            state["resume_operation"] = (state.get("last_checkpoint") or {}).get("operation_id") or "engineering_loop"
            store.write_json("EXECUTION_STATE.json", state)
        return {
            "ok": False,
            "loop_key": loop_key,
            "work_item_id": wi_id,
            "status": STATUS_NEEDS_HUMAN,
            "error": reason,
            "circuit_breaker_tripped": tripped,
            "phases": phases,
            "checkpoint": checkpoint.as_dict(),
            "needs_human": True,
        }

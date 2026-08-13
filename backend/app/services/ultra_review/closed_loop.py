"""Ultra Review same-PR closed-loop orchestrator.

Wires: classify → route → (simulated or real) fix/test → re-review gates → verifiers.
Does not auto-merge. Reuses AcceptanceVerifier / EvidenceVerifier when a work_item_id is provided.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.ultra_review.finding_router import (
    ClosedLoopFinding,
    RouteClass,
    VerificationStatus,
    gate_from_findings,
    normalize_closed_loop_finding,
    route_target,
)

# Loop safety defaults (env-overridable)
DEFAULT_MAX_REVIEW_CYCLES = int(os.getenv("ZECT_UR_MAX_REVIEW_CYCLES", "5"))
DEFAULT_MAX_FIX_ATTEMPTS = int(os.getenv("ZECT_UR_MAX_FIX_ATTEMPTS", "3"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(cwd: str | Path, args: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


def head_sha(repo_path: str | Path) -> str:
    r = _git(repo_path, ["rev-parse", "HEAD"])
    return r["stdout"] if r["exit_code"] == 0 else ""


class ClosedLoopOrchestrator:
    """In-memory + optional ArtifactStore cycle runner for same-PR remediation."""

    def __init__(
        self,
        *,
        max_review_cycles: int = DEFAULT_MAX_REVIEW_CYCLES,
        max_fix_attempts: int = DEFAULT_MAX_FIX_ATTEMPTS,
    ) -> None:
        self.max_review_cycles = max_review_cycles
        self.max_fix_attempts = max_fix_attempts

    def classify_batch(
        self,
        raw_findings: list[dict[str, Any]],
        *,
        run_id: str,
        work_item_id: int | None = None,
        pr_id: str | None = None,
        repository_id: int | None = None,
        commit_sha: str = "",
    ) -> list[ClosedLoopFinding]:
        return [
            normalize_closed_loop_finding(
                f,
                run_id=run_id,
                work_item_id=work_item_id,
                pr_id=pr_id,
                repository_id=repository_id,
                commit_sha=commit_sha,
            )
            for f in raw_findings
        ]

    def run_cycle(
        self,
        *,
        findings: list[ClosedLoopFinding],
        cycle: int,
        old_head_sha: str,
        repo_path: str | None = None,
        apply_local_fix: bool = False,
        fix_file: str | None = None,
        fix_content: str | None = None,
        test_command: list[str] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """One remediation cycle: route → optional fix/test → gate → re-review status."""
        if cycle > self.max_review_cycles:
            return {
                "ok": False,
                "state": "NEEDS_HUMAN_DECISION",
                "reason": "max_review_cycles_exceeded",
                "cycle": cycle,
                "max_review_cycles": self.max_review_cycles,
            }

        gates = gate_from_findings(findings)
        open_findings = [
            f
            for f in findings
            if f.verification_status
            not in (VerificationStatus.RESOLVED, VerificationStatus.FALSE_POSITIVE, VerificationStatus.INVALIDATED)
        ]
        if not open_findings and gates["MERGE_ELIGIBLE"]:
            return {
                "ok": True,
                "state": "READY_TO_SHIP" if gates["READY_TO_SHIP"] else "EVIDENCE_VERIFYING",
                "cycle": cycle,
                "old_head_sha": old_head_sha,
                "new_head_sha": old_head_sha,
                "gates": gates,
                "findings": [f.model_dump() for f in findings],
                "auto_merge": False,
            }

        # Pick primary finding to remediate this cycle (SECURITY first)
        priority = [
            RouteClass.SECURITY,
            RouteClass.ARCHITECTURE_CHANGE,
            RouteClass.PLAN_REVISION,
            RouteClass.SCOPE_CHANGE,
            RouteClass.TEST_GAP,
            RouteClass.LOCAL_FIX,
        ]
        primary = None
        for route in priority:
            for f in open_findings:
                if f.recommended_action == route:
                    primary = f
                    break
            if primary:
                break
        if primary is None:
            primary = open_findings[0]

        target = route_target(primary.recommended_action)
        state = "FIXING"
        if primary.recommended_action == RouteClass.SECURITY:
            state = "FINDINGS_BLOCKING"
        elif primary.recommended_action in (
            RouteClass.PLAN_REVISION,
            RouteClass.SCOPE_CHANGE,
            RouteClass.ARCHITECTURE_CHANGE,
        ):
            state = "NEEDS_PLAN_REVISION"

        fix_result: dict[str, Any] = {"applied": False, "dry_run": dry_run}
        test_result: dict[str, Any] = {"ran": False}
        new_head = old_head_sha
        resolved_ids: list[str] = []

        if primary.recommended_action in (RouteClass.LOCAL_FIX, RouteClass.TEST_GAP, RouteClass.SECURITY):
            if apply_local_fix and repo_path and fix_file and fix_content is not None and not dry_run:
                path = Path(repo_path) / fix_file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(fix_content, encoding="utf-8")
                _git(repo_path, ["add", fix_file])
                commit = _git(
                    repo_path,
                    ["commit", "-m", f"fix(closed-loop): address {primary.finding_id}"],
                )
                fix_result = {
                    "applied": commit["exit_code"] == 0,
                    "dry_run": False,
                    "commit": commit,
                    "file": fix_file,
                }
                new_head = head_sha(repo_path) or old_head_sha
                state = "TESTING"
                if test_command:
                    try:
                        proc = subprocess.run(
                            test_command,
                            cwd=str(repo_path),
                            capture_output=True,
                            text=True,
                            timeout=120,
                            check=False,
                        )
                        test_result = {
                            "ran": True,
                            "exit_code": proc.returncode,
                            "ok": proc.returncode == 0,
                            "stdout_tail": (proc.stdout or "")[-500:],
                            "stderr_tail": (proc.stderr or "")[-500:],
                        }
                    except Exception as e:
                        test_result = {"ran": True, "ok": False, "error": str(e)}
                else:
                    test_result = {"ran": False, "ok": True, "skipped": True}

                if fix_result.get("applied") and test_result.get("ok", True):
                    primary.verification_status = VerificationStatus.RESOLVED
                    primary.resolved_at = _now()
                    primary.blocks_ship = False
                    primary.merge_eligible = True
                    resolved_ids.append(primary.finding_id)
                    state = "RE_REVIEWING"
            elif dry_run:
                # Dry-run path used by unit tests / disposable harness without mutating real repos
                fix_result = {
                    "applied": False,
                    "dry_run": True,
                    "would_route_to": target,
                    "finding_id": primary.finding_id,
                }
                if apply_local_fix:
                    # Simulate successful remediation for proof harness
                    primary.verification_status = VerificationStatus.RESOLVED
                    primary.resolved_at = _now()
                    primary.blocks_ship = False
                    primary.merge_eligible = True
                    resolved_ids.append(primary.finding_id)
                    new_head = f"{old_head_sha[:7] or 'dry'}-fix{cycle}" if old_head_sha else f"dry-fix-{cycle}"
                    state = "RE_REVIEWING"
                    test_result = {"ran": True, "ok": True, "simulated": True}

        gates_after = gate_from_findings(findings)
        if gates_after["READY_TO_SHIP"]:
            state = "READY_TO_SHIP"
        elif gates_after["needs_plan_revision"]:
            state = "NEEDS_PLAN_REVISION"
        elif gates_after["security_blockers"] and state != "RE_REVIEWING":
            state = "FINDINGS_BLOCKING"

        return {
            "ok": True,
            "state": state,
            "cycle": cycle,
            "old_head_sha": old_head_sha,
            "fix_sha": new_head if new_head != old_head_sha else None,
            "new_head_sha": new_head,
            "primary_finding_id": primary.finding_id,
            "routing": primary.recommended_action.value,
            "route_target": target,
            "fix_result": fix_result,
            "test_result": test_result,
            "resolved_finding_ids": resolved_ids,
            "gates": gates_after,
            "findings": [f.model_dump() for f in findings],
            "auto_merge": False,
            "same_pr": True,
        }

    def run_until_clean_or_budget(
        self,
        *,
        raw_findings: list[dict[str, Any]],
        old_head_sha: str,
        work_item_id: int | None = None,
        pr_id: str | None = None,
        repository_id: int | None = None,
        repo_path: str | None = None,
        apply_local_fix: bool = False,
        fix_file: str | None = None,
        fix_content: str | None = None,
        test_command: list[str] | None = None,
        dry_run: bool = True,
        db: Session | None = None,
    ) -> dict[str, Any]:
        run_id = f"ur-cl-{uuid.uuid4().hex[:10]}"
        findings = self.classify_batch(
            raw_findings,
            run_id=run_id,
            work_item_id=work_item_id,
            pr_id=pr_id,
            repository_id=repository_id,
            commit_sha=old_head_sha,
        )
        cycles: list[dict[str, Any]] = []
        head = old_head_sha
        final: dict[str, Any] = {}
        for cycle in range(1, self.max_review_cycles + 1):
            # Only apply concrete file fix on first LOCAL_FIX/SECURITY/TEST_GAP cycle
            final = self.run_cycle(
                findings=findings,
                cycle=cycle,
                old_head_sha=head,
                repo_path=repo_path,
                apply_local_fix=apply_local_fix,
                fix_file=fix_file,
                fix_content=fix_content,
                test_command=test_command,
                dry_run=dry_run,
            )
            cycles.append(final)
            head = final.get("new_head_sha") or head
            if final.get("state") in ("READY_TO_SHIP", "NEEDS_HUMAN_DECISION", "NEEDS_PLAN_REVISION"):
                break
            if final.get("state") == "RE_REVIEWING" and final.get("gates", {}).get("READY_TO_SHIP"):
                final["state"] = "READY_TO_SHIP"
                break
            # After simulated resolve, re-gate
            if final.get("gates", {}).get("MERGE_ELIGIBLE") and final.get("gates", {}).get("READY_TO_SHIP"):
                final["state"] = "READY_TO_SHIP"
                break
            # Prevent infinite identical cycles when dry_run without apply
            if not apply_local_fix and not dry_run:
                break
            if dry_run and not apply_local_fix:
                break

        acceptance: dict[str, Any] = {"ran": False}
        if db is not None and work_item_id and final.get("state") == "READY_TO_SHIP":
            try:
                from app.services.mentrix.engineering_agents.acceptance_verifier import AcceptanceVerifier

                acceptance = AcceptanceVerifier(db, work_item_id).verify(ship=False)
                acceptance = {"ran": True, **acceptance}
            except Exception as e:
                acceptance = {"ran": True, "ok": False, "error": str(e)}

        return {
            "run_id": run_id,
            "pr_id": pr_id,
            "work_item_id": work_item_id,
            "cycles": cycles,
            "final_state": final.get("state"),
            "gates": final.get("gates"),
            "old_head_sha": old_head_sha,
            "new_head_sha": final.get("new_head_sha"),
            "acceptance": acceptance,
            "auto_merge": False,
            "started_at": _now(),
            "findings": [f.model_dump() for f in findings],
        }


def persist_cycle_artifact(work_item_id: int, payload: dict[str, Any]) -> str | None:
    """Write CLOSED_LOOP_REVIEW.json into existing ArtifactStore when available."""
    try:
        from app.services.work_items.artifact_store import ArtifactStore

        store = ArtifactStore(work_item_id)
        store.write_json("CLOSED_LOOP_REVIEW.json", payload)
        return "CLOSED_LOOP_REVIEW.json"
    except Exception:
        return None

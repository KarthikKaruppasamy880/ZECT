"""Mentrix Review Agent — Ultra Review worker over git diff + artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domains.pr_review.finding_schema import ReviewFindingSpec, ValidationStatus
from app.services.mentrix.engineering_agents.roles import ROLE_REVIEWER
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import record_checkpoint


class MentrixReviewAgent:
    """Independent review; verified blocking findings route back to coder."""

    role = ROLE_REVIEWER

    def __init__(self, db: Session, work_item_id: int) -> None:
        self.db = db
        self.work_item_id = work_item_id
        self.store = ArtifactStore(work_item_id)

    def review(
        self,
        *,
        diff_text: str = "",
        findings: list[dict[str, Any]] | None = None,
        inject_findings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        record_checkpoint(self.store, checkpoint_type="op_start", operation_id="review_agent")
        plan = self.store.read_plan()
        tests = self.store.read_json("TEST_RESULTS.json", default={}) or {}
        raw = inject_findings if inject_findings is not None else (findings or [])

        # Optional Ultra Review context (best-effort)
        try:
            from app.services.work_items.ultra_review_context import build_ultrareview_work_item_context

            ctx = build_ultrareview_work_item_context(self.db, work_item_id=self.work_item_id, query="review")
        except Exception:  # noqa: BLE001
            ctx = {}

        normalized: list[dict[str, Any]] = []
        for f in raw:
            if isinstance(f, ReviewFindingSpec):
                row = f.model_dump()
            else:
                row = dict(f)
                row.setdefault("id", uuid4().hex[:12])
                row.setdefault("severity", "info")
                row.setdefault("category", "correctness")
                row.setdefault(
                    "verification_status",
                    row.get("validation_status") or ValidationStatus.unvalidated.value,
                )
            # Normalize verification_status field name
            vs = str(row.get("verification_status") or row.get("validation_status") or "unverified").lower()
            row["verification_status"] = vs
            row["validation_status"] = vs
            normalized.append(row)

        verified_statuses = {
            "verified",
            "validated",
            str(ValidationStatus.validated),
        }
        non_actionable_statuses = {
            "unverified",
            "unvalidated",
            "false-positive",
            "false_positive",
            str(ValidationStatus.false_positive),
            "likely",
            "waived",
            str(ValidationStatus.invalidated),
            str(ValidationStatus.unvalidated),
        }
        blocking = [
            f
            for f in normalized
            if str(f.get("severity", "")).lower() in ("critical", "high", "blocking", "error")
            and str(f.get("verification_status")).lower() in verified_statuses
        ]
        # Unverified / false-positive must not trigger coder edits
        non_actionable = [
            f for f in normalized if str(f.get("verification_status")).lower() in non_actionable_statuses
        ]

        clean = len(blocking) == 0
        result = {
            "role": self.role,
            "ok": clean,
            "clean": clean,
            "findings": normalized,
            "blocking": blocking,
            "non_actionable": non_actionable,
            "route_back_to_coder": bool(blocking),
            "may_edit_from_unverified": False,
            "may_ready_to_ship": False,
            "plan_chars": len(plan or ""),
            "tests_ok": bool(tests.get("ok")) if tests else None,
            "diff_chars": len(diff_text or ""),
            "ultra_context_keys": list(ctx.keys()) if isinstance(ctx, dict) else [],
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self.store.write_json("REVIEW.json", result)
        record_checkpoint(
            self.store,
            checkpoint_type="verification" if clean else "blocking",
            operation_id="review_agent",
            payload={"blocking": len(blocking), "findings": len(normalized)},
        )
        return result

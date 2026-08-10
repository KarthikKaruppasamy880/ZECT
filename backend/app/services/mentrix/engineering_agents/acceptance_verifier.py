"""AcceptanceVerifier — deterministic gate wrapping EvidenceVerifier (+ tests/review blockers)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domains.work_items.service import transition_status
from app.domains.work_items.status import STATUS_READY_TO_SHIP
from app.services.mentrix.engineering_agents.roles import ROLE_ACCEPTANCE, role_may_declare_ready_to_ship
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import record_checkpoint
from app.services.work_items.evidence_verifier import EvidenceItem, EvidenceVerifier


class AcceptanceVerifier:
    """Only verified success may transition to READY_TO_SHIP. LLM text alone never passes."""

    role = ROLE_ACCEPTANCE

    def __init__(self, db: Session, work_item_id: int) -> None:
        self.db = db
        self.work_item_id = work_item_id
        self.store = ArtifactStore(work_item_id)
        self.verifier = EvidenceVerifier()

    def verify(
        self,
        *,
        evidence: list[dict[str, Any]] | list[EvidenceItem] | None = None,
        ship: bool = False,
        actor: str = "acceptance_verifier",
    ) -> dict[str, Any]:
        assert role_may_declare_ready_to_ship(self.role)

        manifest = self.store.read_json("EXECUTION_MANIFEST.json", default={}) or {}
        tests = self.store.read_json("TEST_RESULTS.json", default={}) or {}
        review = self.store.read_json("REVIEW.json", default={}) or {}

        mandatory = list(manifest.get("mandatory_operation_ids") or [])
        reqs = list(manifest.get("requirement_ids") or [])
        acs = list(manifest.get("acceptance_ids") or [])

        ev_list: list[Any] = list(evidence or self.store.read_json("EVIDENCE.json", default=[]) or [])

        # Only claim req/AC coverage for completed ops that declare those links (no blanket pass)
        ops = list(manifest.get("operations") or [])
        linked_reqs: list[str] = []
        linked_acs: list[str] = []
        completed_op_ids: list[str] = []
        for op in ops:
            st = str(op.get("status") or "").lower()
            if st in ("done", "completed", "verified"):
                completed_op_ids.append(str(op.get("id") or ""))
                linked_reqs.extend(str(x) for x in (op.get("requirement_ids") or []))
                linked_acs.extend(str(x) for x in (op.get("acceptance_ids") or []))
        # Deduplicate while preserving order
        linked_reqs = list(dict.fromkeys(linked_reqs))
        linked_acs = list(dict.fromkeys(linked_acs))

        # Auto-attach typed evidence from tests/review when present
        if tests.get("ok") is True:
            for oid in completed_op_ids or ([mandatory[0]] if mandatory else [""]):
                ev_list.append(
                    {
                        "id": f"test-pass:{oid}",
                        "type": "TEST_RESULT",
                        "operation_id": oid,
                        "requirement_ids": [r for r in linked_reqs if r in reqs],
                        "acceptance_ids": [a for a in linked_acs if a in acs],
                        "payload": {"ok": True},
                        "llm_claim": False,
                    }
                )
        if review.get("clean") is True:
            oid = completed_op_ids[0] if completed_op_ids else (mandatory[0] if mandatory else "")
            ev_list.append(
                {
                    "id": "review-clean",
                    "type": "REVIEW_FINDING",
                    "operation_id": oid,
                    "requirement_ids": [r for r in linked_reqs if r in reqs],
                    "acceptance_ids": [a for a in linked_acs if a in acs],
                    "payload": {"clean": True},
                    "llm_claim": False,
                }
            )

        result = self.verifier.verify(
            mandatory_operation_ids=mandatory,
            requirement_ids=reqs,
            acceptance_ids=acs,
            evidence=ev_list,
        )
        errors = list(result.errors)
        if tests and tests.get("ok") is False:
            errors.append("tests_failed_block_ready_to_ship")
            result.ok = False
            result.ready_to_ship = False
        if review and review.get("blocking"):
            errors.append("blocking_review_findings")
            result.ok = False
            result.ready_to_ship = False
        # 100-op manifest cannot finish at 99/100
        if ops:
            done = [o for o in ops if str(o.get("status") or "").lower() in ("done", "completed", "verified")]
            if len(done) < len(ops):
                # Only enforce if operations declared status tracking
                pending_mandatory = [
                    o["id"]
                    for o in ops
                    if o.get("mandatory") and str(o.get("status") or "pending").lower() not in ("done", "completed", "verified")
                ]
                if pending_mandatory:
                    for oid in pending_mandatory:
                        if oid not in result.missing_operations:
                            result.missing_operations.append(oid)
                    result.ok = False
                    result.ready_to_ship = False
                    errors.append("incomplete_manifest_operations")

        out = result.to_dict()
        out["errors"] = errors
        out["role"] = self.role
        out["work_item_id"] = self.work_item_id
        self.store.write_json("EVIDENCE.json", ev_list if isinstance(ev_list, list) else [])
        record_checkpoint(
            self.store,
            checkpoint_type="verification" if result.ok else "blocking",
            operation_id="acceptance_verifier",
            payload=out,
        )

        shipped = False
        if ship and result.ready_to_ship and result.ok and not errors:
            transition_status(
                self.db,
                self.work_item_id,
                STATUS_READY_TO_SHIP,
                actor=actor,
                allow_gate=True,
                reason="AcceptanceVerifier+EvidenceVerifier",
            )
            shipped = True
        out["shipped"] = shipped
        out["ready_to_ship"] = bool(result.ready_to_ship and result.ok and not errors)
        return out

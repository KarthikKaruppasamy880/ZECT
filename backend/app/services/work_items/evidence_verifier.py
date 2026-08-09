"""EvidenceVerifier — operation/requirement/acceptance coverage + typed evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EVIDENCE_TYPES = (
    "FILE_EXISTS",
    "FILE_CHANGED",
    "COMMAND_EXIT",
    "TEST_RESULT",
    "BUILD_RESULT",
    "LINT_RESULT",
    "TYPECHECK_RESULT",
    "API_RESULT",
    "UI_RESULT",
    "SECURITY_RESULT",
    "REVIEW_FINDING",
    "HUMAN_APPROVAL",
)


@dataclass
class EvidenceItem:
    id: str
    type: str
    operation_id: str = ""
    requirement_ids: list[str] = field(default_factory=list)
    acceptance_ids: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    llm_claim: bool = False


@dataclass
class VerificationResult:
    ok: bool
    ready_to_ship: bool
    missing_operations: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)
    missing_acceptance: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "ready_to_ship": self.ready_to_ship,
            "missing_operations": self.missing_operations,
            "missing_requirements": self.missing_requirements,
            "missing_acceptance": self.missing_acceptance,
            "errors": self.errors,
        }


class EvidenceVerifier:
    """LLM text alone cannot COMPLETE / READY_TO_SHIP."""

    def verify(
        self,
        *,
        mandatory_operation_ids: list[str],
        requirement_ids: list[str],
        acceptance_ids: list[str],
        evidence: list[EvidenceItem] | list[dict[str, Any]],
    ) -> VerificationResult:
        items: list[EvidenceItem] = []
        for e in evidence:
            if isinstance(e, EvidenceItem):
                items.append(e)
            else:
                items.append(
                    EvidenceItem(
                        id=str(e.get("id") or ""),
                        type=str(e.get("type") or ""),
                        operation_id=str(e.get("operation_id") or ""),
                        requirement_ids=list(e.get("requirement_ids") or []),
                        acceptance_ids=list(e.get("acceptance_ids") or []),
                        payload=dict(e.get("payload") or {}),
                        llm_claim=bool(e.get("llm_claim")),
                    )
                )

        errors: list[str] = []
        typed = [i for i in items if i.type in EVIDENCE_TYPES and not i.llm_claim]
        llm_only = [i for i in items if i.llm_claim or i.type not in EVIDENCE_TYPES]
        if items and not typed and llm_only:
            errors.append("llm_text_alone_cannot_complete")

        covered_ops = {i.operation_id for i in typed if i.operation_id}
        covered_reqs: set[str] = set()
        covered_acs: set[str] = set()
        for i in typed:
            covered_reqs.update(i.requirement_ids)
            covered_acs.update(i.acceptance_ids)

        missing_ops = [o for o in mandatory_operation_ids if o not in covered_ops]
        missing_reqs = [r for r in requirement_ids if r not in covered_reqs]
        missing_acs = [a for a in acceptance_ids if a not in covered_acs]

        ok = not missing_ops and not missing_reqs and not missing_acs and not errors
        return VerificationResult(
            ok=ok,
            ready_to_ship=ok,
            missing_operations=missing_ops,
            missing_requirements=missing_reqs,
            missing_acceptance=missing_acs,
            errors=errors,
        )

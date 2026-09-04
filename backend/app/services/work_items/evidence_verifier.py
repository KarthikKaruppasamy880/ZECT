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

# Evidence types whose own payload records a pass/fail outcome. A recorded
# item of one of these types only proves a check of that kind was RUN --
# _evidence_outcome_failed() below checks whether it actually PASSED, so a
# failing TEST_RESULT/BUILD_RESULT/etc can never satisfy coverage just by
# existing (the gap this class previously had: any typed, non-llm_claim
# evidence counted regardless of what its payload said happened).
_OUTCOME_EVIDENCE_TYPES = frozenset(
    {
        "COMMAND_EXIT",
        "TEST_RESULT",
        "BUILD_RESULT",
        "LINT_RESULT",
        "TYPECHECK_RESULT",
        "API_RESULT",
        "UI_RESULT",
        "SECURITY_RESULT",
    }
)


def _evidence_outcome_failed(payload: dict[str, Any]) -> bool:
    if "ok" in payload:
        return not bool(payload.get("ok"))
    status = str(payload.get("status") or "").strip().lower()
    if status in {"fail", "failed", "error"}:
        return True
    exit_code = payload.get("exit_code")
    if exit_code is not None:
        try:
            return int(exit_code) != 0
        except (TypeError, ValueError):
            return False
    return False


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
        current_heads: dict[str, str] | None = None,
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
        typed_all = [i for i in items if i.type in EVIDENCE_TYPES and not i.llm_claim]
        llm_only = [i for i in items if i.llm_claim or i.type not in EVIDENCE_TYPES]
        if items and not typed_all and llm_only:
            errors.append("llm_text_alone_cannot_complete")

        typed: list[EvidenceItem] = []
        for i in typed_all:
            if i.type in _OUTCOME_EVIDENCE_TYPES and _evidence_outcome_failed(i.payload or {}):
                errors.append(f"failing_evidence:{i.type}:{i.operation_id or i.id}")
            else:
                typed.append(i)

        covered_ops = {i.operation_id for i in typed if i.operation_id}
        covered_reqs: set[str] = set()
        covered_acs: set[str] = set()
        for i in typed:
            covered_reqs.update(i.requirement_ids)
            covered_acs.update(i.acceptance_ids)

        missing_ops = [o for o in mandatory_operation_ids if o not in covered_ops]
        missing_reqs = [r for r in requirement_ids if r not in covered_reqs]
        missing_acs = [a for a in acceptance_ids if a not in covered_acs]

        if current_heads:
            errors.extend(self.stale_head_errors(typed, current_heads))

        ok = not missing_ops and not missing_reqs and not missing_acs and not errors
        return VerificationResult(
            ok=ok,
            ready_to_ship=ok,
            missing_operations=missing_ops,
            missing_requirements=missing_reqs,
            missing_acceptance=missing_acs,
            errors=errors,
        )

    @staticmethod
    def stale_head_errors(
        items: list[EvidenceItem],
        current_heads: dict[str, str],
    ) -> list[str]:
        """Recorded evidence head_sha must match current PR/worktree HEAD."""
        errors: list[str] = []
        heads = {str(k): str(v) for k, v in (current_heads or {}).items() if v}
        if not heads:
            return errors
        seen: set[str] = set()
        for item in items:
            recorded = str((item.payload or {}).get("head_sha") or "")
            if not recorded:
                continue
            rid = str((item.payload or {}).get("repository_id") or "")
            keys = [k for k in (rid, item.operation_id, item.id) if k]
            current = next((heads[k] for k in keys if k in heads), "")
            if not current:
                continue
            if recorded != current:
                tag = f"stale_evidence:{rid or item.operation_id or item.id}"
                if tag not in seen:
                    seen.add(tag)
                    errors.append(tag)
        return errors

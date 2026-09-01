"""EvidenceVerifier must check evidence OUTCOME, not just evidence TYPE.

Previously any typed, non-llm_claim evidence item satisfied operation/
requirement/acceptance coverage regardless of what its own payload said
happened -- a TEST_RESULT, BUILD_RESULT, or UI_RESULT item with
payload={"ok": False} (or status="fail", or a non-zero exit_code) still
counted as "this operation has a TEST_RESULT", so a broken build or a
failing UI check could satisfy coverage and reach ready_to_ship=True.
See Phase D of ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md:
"EvidenceVerifier currently trusts recorded TEST_RESULT/BUILD_RESULT/
UI_RESULT payloads rather than independently re-executing."
"""

from __future__ import annotations

from app.services.work_items.evidence_verifier import EvidenceItem, EvidenceVerifier


def _verify(evidence):
    return EvidenceVerifier().verify(
        mandatory_operation_ids=["op-1"],
        requirement_ids=["req-1"],
        acceptance_ids=["ac-1"],
        evidence=evidence,
    )


class TestOutcomeMustBePassing:
    def test_passing_test_result_satisfies_coverage(self):
        result = _verify(
            [
                EvidenceItem(
                    id="e1",
                    type="TEST_RESULT",
                    operation_id="op-1",
                    requirement_ids=["req-1"],
                    acceptance_ids=["ac-1"],
                    payload={"ok": True},
                )
            ]
        )
        assert result.ok is True
        assert result.missing_operations == []

    def test_failing_test_result_does_not_satisfy_coverage(self):
        result = _verify(
            [
                EvidenceItem(
                    id="e1",
                    type="TEST_RESULT",
                    operation_id="op-1",
                    requirement_ids=["req-1"],
                    acceptance_ids=["ac-1"],
                    payload={"ok": False},
                )
            ]
        )
        assert result.ok is False
        assert "op-1" in result.missing_operations
        assert "failing_evidence:TEST_RESULT:op-1" in result.errors

    def test_failing_build_result_blocks_even_when_a_test_result_passes(self):
        """A passing test must not paper over a broken build -- both are
        typed evidence for the same operation, and BUILD_RESULT's own
        payload says it failed."""
        result = _verify(
            [
                EvidenceItem(id="e1", type="TEST_RESULT", operation_id="op-1", payload={"ok": True}),
                EvidenceItem(id="e2", type="BUILD_RESULT", operation_id="op-1", payload={"ok": False}),
            ]
        )
        assert result.ok is False
        assert "failing_evidence:BUILD_RESULT:op-1" in result.errors

    def test_failing_ui_result_via_status_field_blocks(self):
        result = _verify(
            [EvidenceItem(id="e1", type="UI_RESULT", operation_id="op-1", payload={"status": "fail"})]
        )
        assert result.ok is False
        assert any(e.startswith("failing_evidence:UI_RESULT:") for e in result.errors)

    def test_failing_command_exit_via_nonzero_exit_code_blocks(self):
        result = _verify(
            [EvidenceItem(id="e1", type="COMMAND_EXIT", operation_id="op-1", payload={"exit_code": 1})]
        )
        assert result.ok is False
        assert any(e.startswith("failing_evidence:COMMAND_EXIT:") for e in result.errors)

    def test_zero_exit_code_passes(self):
        result = _verify(
            [
                EvidenceItem(
                    id="e1",
                    type="COMMAND_EXIT",
                    operation_id="op-1",
                    requirement_ids=["req-1"],
                    acceptance_ids=["ac-1"],
                    payload={"exit_code": 0},
                )
            ]
        )
        assert result.ok is True

    def test_outcome_check_only_applies_to_outcome_bearing_types(self):
        """REVIEW_FINDING and FILE_EXISTS have no pass/fail payload
        convention -- their mere presence (as typed, non-llm_claim evidence)
        still satisfies coverage, unchanged from before."""
        result = _verify(
            [
                EvidenceItem(
                    id="e1",
                    type="FILE_EXISTS",
                    operation_id="op-1",
                    requirement_ids=["req-1"],
                    acceptance_ids=["ac-1"],
                    payload={"path": "app.py"},
                )
            ]
        )
        assert result.ok is True
        assert result.errors == []

    def test_missing_ok_and_status_and_exit_code_is_not_treated_as_failing(self):
        """A payload that simply doesn't record an outcome (no ok/status/
        exit_code key) is not proof of failure -- only an explicit failing
        signal should block coverage."""
        result = _verify(
            [
                EvidenceItem(
                    id="e1",
                    type="LINT_RESULT",
                    operation_id="op-1",
                    requirement_ids=["req-1"],
                    acceptance_ids=["ac-1"],
                    payload={"warnings": 0},
                )
            ]
        )
        assert result.ok is True

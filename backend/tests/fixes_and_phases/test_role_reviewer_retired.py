"""Phase D: mentrix_lead.ROLE_REVIEWER was dead code -- defined with a tool
allowlist entry but no call site anywhere ever invoked a Reviewer-role agent
run. The real review gate is lifecycle.py's review_diff()/run_ultra_review(),
already exercised by other tests. This just guards against the dead constant
silently reappearing (e.g. via a careless merge) without anyone wiring it up
for real -- see ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase D.
"""

from __future__ import annotations

from app.services.coding_engine import mentrix_lead


def test_role_reviewer_constant_does_not_exist():
    assert not hasattr(mentrix_lead, "ROLE_REVIEWER")


def test_role_tool_allowlists_only_has_the_four_real_roles():
    assert set(mentrix_lead.ROLE_TOOL_ALLOWLISTS.keys()) == {
        mentrix_lead.ROLE_EXPLORE,
        mentrix_lead.ROLE_CODER,
        mentrix_lead.ROLE_TESTER,
        mentrix_lead.ROLE_DEBUGGER,
    }

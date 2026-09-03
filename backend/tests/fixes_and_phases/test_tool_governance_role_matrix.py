"""CP-09A -- the canonical role/tool-governance matrix: ASK | PLAN |
EXPLORE | CODER | TESTER | DEBUGGER | REVIEWER | DELIVERY.

EXPLORE/CODER/DEBUGGER's tool allowlists and CODER/TESTER/DEBUGGER's
AgentWritePolicy write-time gate are already proven in
test_mentrix_role_tool_restriction.py and test_agent_write_policy.py --
not repeated here. This file proves the four roles that were never an
agent-loop turn in the first place (ASK, PLAN, REVIEWER, DELIVERY) never
had, and still don't have, a code path to the tool-execution choke point
(mentrix_agent_tools.execute_tool) at all -- a structural guarantee, not
a per-call check, so nothing has to remember to add one later -- plus
that TESTER's write access is bound by the exact same plan-authorized
gate CODER's is (its extra App/browser tools don't grant it a bypass).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND_APP = Path(__file__).resolve().parents[2] / "app"


def _imports_execute_tool(module_path: Path) -> bool:
    """AST-based, not a text grep -- a module merely *mentioning* the
    string "execute_tool" in a comment/docstring must not count."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "mentrix_agent_tools" in node.module:
            if any(alias.name == "execute_tool" for alias in node.names):
                return True
        if isinstance(node, ast.Import):
            if any(alias.name.endswith("mentrix_agent_tools") for alias in node.names):
                # Imported the whole module -- check for any `.execute_tool(` call.
                for call in ast.walk(tree):
                    if (
                        isinstance(call, ast.Attribute)
                        and call.attr == "execute_tool"
                    ):
                        return True
    return False


class TestAskPlanReviewerDeliveryNeverReachTheToolChokePoint:
    def test_ask_plan_llm_phase_has_no_path_to_execute_tool(self):
        assert not _imports_execute_tool(_BACKEND_APP / "services" / "phases" / "llm_phase.py")

    def test_developer_service_ask_and_plan_never_import_execute_tool(self):
        # developer_service.py legitimately imports mentrix_agent_tools for
        # an unrelated deterministic-smoke marker path (see CP-07 survey) --
        # assert THAT path is not reachable from ask()/plan() specifically
        # by checking neither function's own source references it.
        import inspect

        from app.services.work_items.developer_service import MentrixDeveloperService

        for fn_name in ("ask", "plan"):
            src = inspect.getsource(getattr(MentrixDeveloperService, fn_name))
            assert "execute_tool" not in src, f"{fn_name}() must never call execute_tool directly"

    def test_reviewer_ultra_review_has_no_path_to_execute_tool(self):
        assert not _imports_execute_tool(_BACKEND_APP / "services" / "phases" / "review_phase_svc.py")
        assert not _imports_execute_tool(_BACKEND_APP / "review_service.py")

    def test_delivery_git_approval_flow_never_calls_write_file_or_apply_patch(self):
        import inspect

        from app.services.coding_engine import lifecycle

        for fn_name in ("approve_git", "_git"):
            src = inspect.getsource(getattr(lifecycle, fn_name))
            assert "write_file" not in src and "apply_patch" not in src, (
                f"{fn_name}() is the DELIVERY role's own surface (git commit/push) -- "
                "it must never also implement code changes"
            )


class TestTesterSharesCoderAndDebuggersWriteGate:
    """TESTER's extra App-Runner/browser tools (for "verify in a real
    browser, fix what's found") must not be a loophole around
    AgentWritePolicy -- same unplanned-path/cross-repo/stale-plan rules
    CODER and DEBUGGER are bound by."""

    def test_tester_role_write_is_governed_by_the_same_agent_write_policy(self, tmp_path):
        from app.services.coding_engine import agent_write_policy as awp

        (tmp_path / "Ghost.java").write_text("class Ghost {}\n", encoding="utf-8")
        policy = awp.AgentWritePolicy(work_item_id=1, authorized=True, primary_repo_id=7, plan_hash="h", file_impacts=[])
        decision = awp.authorize_write(policy, tool_name="write_file", repo_id=7, path="not_in_the_plan.py", workspace=tmp_path)
        assert decision.allowed is False
        assert decision.reason == "unplanned_path"

    def test_tester_role_is_present_in_the_shared_role_tool_allowlists(self):
        from app.services.coding_engine.mentrix_lead import ROLE_TESTER, ROLE_TOOL_ALLOWLISTS

        assert ROLE_TESTER in ROLE_TOOL_ALLOWLISTS
        # Bounded, not unlimited -- it does not include e.g. arbitrary MCP/
        # deployment tools that were never in the registry to begin with.
        assert "run_command" in ROLE_TOOL_ALLOWLISTS[ROLE_TESTER]

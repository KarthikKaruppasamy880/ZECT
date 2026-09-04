"""CP-09B -- the canonical Skills Router: Mission phase/role -> intent ->
Skill Router -> selected skill -> instructions/context/checks. Proves the
deterministic role/signal -> intent mapping, that it reuses the existing
DB-backed Skills Engine (skills_engine.py) rather than a second store, that
a skill contributes instructions/context only (never tool permissions --
proven structurally, same AST style as test_tool_governance_role_matrix.py),
and that lifecycle.py's three role invocations actually select and emit a
skill (durable Mission event, survives replay) rather than this module
existing unused.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.infrastructure.database import SessionLocal
from app.services.coding_engine import skill_router as sr


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestDeterministicIntentBuilding:
    def test_build_intent_is_pure_and_deterministic(self):
        assert sr.build_intent(sr.ROLE_ASK) == sr.build_intent(sr.ROLE_ASK)

    def test_additive_signals_extend_but_never_replace_the_base_role_intent(self):
        """test_failed/browser_acceptance genuinely extend their role's own
        base intent -- unlike the specialized-review signals (ui_diff,
        security_sensitive, db_schema_diff, bpmn_diff, prompt_diff), which
        must override it outright so they win ties against same-role
        skills (see TestSelectSkillReusesTheExistingSkillsEngineNotANewStore)."""
        base = sr.build_intent(sr.ROLE_CODER)
        extended = sr.build_intent(sr.ROLE_CODER, signals={"test_failed": True})
        assert base in extended
        assert extended != base

    def test_override_signals_replace_rather_than_extend_the_base_role_intent(self):
        base = sr.build_intent(sr.ROLE_CODER)
        overridden = sr.build_intent(sr.ROLE_CODER, signals={"security_sensitive": True})
        assert base not in overridden

    def test_unset_signal_keys_are_no_ops(self):
        assert sr.build_intent(sr.ROLE_PLAN, signals={"ui_diff": False}) == sr.build_intent(sr.ROLE_PLAN)


class TestSelectSkillReusesTheExistingSkillsEngineNotANewStore:
    """The mandate explicitly forbids a second skill store -- this proves
    the router's selection is backed by the same SkillDefinition rows
    /api/skills-engine/match already serves, seeded by the same
    _seed_if_empty it already calls."""

    def test_ask_role_selects_zect_reconcile(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_ASK)
        assert selection.skill_name == "zect-reconcile"
        assert selection.skill_id is not None

    def test_plan_role_selects_zect_plan(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_PLAN)
        assert selection.skill_name == "zect-plan"

    def test_coder_role_selects_zect_build(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_CODER)
        assert selection.skill_name == "zect-build"

    def test_debugger_role_with_test_failed_signal_reuses_zinnia_debug(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_DEBUGGER, signals={"test_failed": True})
        assert selection.skill_name == "zinnia-debug"

    def test_tester_role_with_browser_acceptance_signal_selects_zect_browser_test(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_TESTER, signals={"browser_acceptance": True})
        assert selection.skill_name == "zect-browser-test"

    def test_reviewer_role_reuses_zinnia_code_review(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_REVIEWER)
        assert selection.skill_name == "zinnia-code-review"

    def test_delivery_role_selects_zect_pr_ready(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_DELIVERY)
        assert selection.skill_name == "zect-pr-ready"

    @pytest.mark.parametrize(
        "signal,expected_skill",
        [
            ("ui_diff", "zect-ui-review"),
            ("security_sensitive", "zect-security-review"),
            ("db_schema_diff", "zect-db-review"),
            ("bpmn_diff", "zect-bpmn-review"),
            ("prompt_diff", "prompt-engineer"),
        ],
    )
    def test_specialized_signals_select_their_named_skill(self, db, signal, expected_skill):
        selection = sr.select_skill_with_db(db, sr.ROLE_CODER, signals={signal: True})
        assert selection.skill_name == expected_skill

    def test_unrecognized_role_matches_no_skill_rather_than_a_wrong_one(self, db):
        selection = sr.select_skill_with_db(db, "totally_unmodeled_role_xyz")
        assert selection.skill_name is None
        assert selection.reason == "no_skill_matched_intent"
        assert selection.goal_prefix() == ""

    def test_only_the_single_best_match_is_returned_not_every_skill(self, db):
        """'Load only the relevant Skill... never inject all skills into
        every model call' -- select_skill_with_db must return one winner,
        not the whole match list skills_engine.match_skills() would."""
        selection = sr.select_skill_with_db(db, sr.ROLE_ASK)
        assert isinstance(selection.skill_name, str)
        assert not isinstance(selection.skill_name, list)


class TestSkillsCannotExpandToolPermissions:
    """Structural guarantee, not a per-call check -- mirrors
    test_tool_governance_role_matrix.py's AST approach. A skill may
    contribute instructions/context/checks; it must have no code path to
    the tool-execution choke point or a role's allowlist at all."""

    def test_skill_router_module_never_imports_the_tool_choke_point(self):
        tree = ast.parse(Path(sr.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "mentrix_agent_tools" not in node.module
                assert "agent_write_policy" not in node.module

    def test_skill_selection_has_no_allowed_tools_or_role_override_field(self):
        fields = set(sr.SkillSelection.__dataclass_fields__)
        assert "allowed_tools" not in fields
        assert "role_override" not in fields
        assert "tool_permissions" not in fields

    def test_goal_prefix_is_plain_text_not_a_tool_grant(self, db):
        selection = sr.select_skill_with_db(db, sr.ROLE_CODER)
        prefix = selection.goal_prefix()
        assert isinstance(prefix, str)
        assert "execute_tool" not in prefix


class TestLifecycleRoleInvocationsActuallySelectAndEmitASkill:
    """Wiring proof: the 3 native-build role invocations must select a
    skill and record it as a durable Mission event (so it survives replay
    after tab switch/refresh/restart, same mechanism CP-09's other typed
    events use) -- not just have skill_router.py sitting unused."""

    def _stub_native_build(self, monkeypatch, module_path: str):
        def _fake(**kwargs):
            return {"run_id": "", "ok": True, "status": "completed", "files_written": [], "summary": "done"}

        monkeypatch.setattr(f"{module_path}.run_mentrix_native_build", _fake)

    def test_coder_invocation_emits_skill_selected_event(self, tmp_path, monkeypatch):
        from app.services.coding_engine import lifecycle

        self._stub_native_build(monkeypatch, "app.services.coding_engine.mentrix_native_build")
        mission = lifecycle.start_mission(goal="add a function", roots=[{"id": 1, "label": "x", "path": str(tmp_path)}], plan="# plan\n")
        for repo in mission["repos"]:
            repo["worktree_path"] = str(tmp_path)
        lifecycle._run_native_implementer(mission)
        selected = [e for e in mission["events"] if e["event"] == "skill_selected"]
        assert selected, mission["events"]
        assert selected[-1]["data"].get("skill_name") == "zect-build"
        assert selected[-1]["data"].get("role") == "coder"

    def test_debugger_invocation_emits_skill_selected_event(self, tmp_path, monkeypatch):
        from app.services.coding_engine import lifecycle

        self._stub_native_build(monkeypatch, "app.services.coding_engine.mentrix_native_build")
        mission = lifecycle.start_mission(goal="fix bug", roots=[{"id": 1, "label": "x", "path": str(tmp_path)}], plan="# plan\n")
        repo = mission["repos"][0]
        repo["worktree_path"] = str(tmp_path)
        lifecycle._diagnose_and_repair_repo(mission, repo, tmp_path, {"ok": False, "kind": "test", "stdout": "boom", "stderr": ""})
        selected = [e for e in mission["events"] if e["event"] == "skill_selected"]
        assert selected, mission["events"]
        assert selected[-1]["data"].get("skill_name") == "zinnia-debug"

    def test_tester_invocation_emits_skill_selected_event_when_app_is_runnable(self, tmp_path, monkeypatch):
        from app.services.coding_engine import lifecycle

        self._stub_native_build(monkeypatch, "app.services.coding_engine.mentrix_native_build")
        monkeypatch.setattr(
            "app.services.workspace.runtime_discovery.discover_runtime_recipes",
            lambda _wt: {"recipes": [{"id": "r1"}]},
        )
        mission = lifecycle.start_mission(goal="verify", roots=[{"id": 1, "label": "x", "path": str(tmp_path)}], plan="# plan\n")
        repo = mission["repos"][0]
        repo["worktree_path"] = str(tmp_path)
        lifecycle._run_app_and_browser_verification(mission, repo, tmp_path)
        selected = [e for e in mission["events"] if e["event"] == "skill_selected"]
        assert selected, mission["events"]
        assert selected[-1]["data"].get("skill_name") == "zect-browser-test"

    def test_skill_selected_event_uses_the_same_emit_save_mission_path_as_other_typed_events(self, tmp_path, monkeypatch):
        """CP-09 already proved _emit()/_save_mission() survive a
        reconnect for every other typed Mission event -- this only needs
        to prove skill_selected goes through that exact same function
        (not a second, parallel side channel), which the other tests in
        this class already do by asserting on mission['events'] (append_
        in-place, same object _emit()/_save_mission() write through)."""
        from app.services.coding_engine import lifecycle

        self._stub_native_build(monkeypatch, "app.services.coding_engine.mentrix_native_build")
        mission = lifecycle.start_mission(goal="add a function", roots=[{"id": 1, "label": "x", "path": str(tmp_path)}], plan="# plan\n")
        for repo in mission["repos"]:
            repo["worktree_path"] = str(tmp_path)
        lifecycle._run_native_implementer(mission)
        selected = [e for e in mission["events"] if e["event"] == "skill_selected"]
        assert selected and all("seq" in e for e in selected), mission["events"]


class TestDeveloperServiceAskAndPlanNeverGainAToolPath:
    """A skill is loaded via select_skill_with_db (LLM-free, deterministic)
    -- ask()/plan() must still never reach execute_tool, exactly the
    guarantee test_tool_governance_role_matrix.py already proves; re-check
    here so a future edit to the skill-wiring lines can't quietly add one."""

    def test_ask_and_plan_source_has_no_execute_tool_reference(self):
        from app.services.work_items.developer_service import MentrixDeveloperService

        for fn_name in ("ask", "plan"):
            src = inspect.getsource(getattr(MentrixDeveloperService, fn_name))
            assert "execute_tool" not in src

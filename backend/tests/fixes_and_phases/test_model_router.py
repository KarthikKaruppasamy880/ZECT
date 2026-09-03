"""CP-08 -- task-aware model routing for ASK/PLAN/AGENT.

Before this module, ASK, PLAN, and every AGENT role (Coder, Debugger,
Tester) resolved a model through the exact same call --
mentrix_llm_chat_model(), one global env-var-driven default -- so a
one-line classification question and a large multi-file Java PLAN got the
identical model, purely because that happened to be the UI's configured
default. This suite proves the missing axis: task type + complexity +
context size + vision/tool-calling requirement + privacy requirement now
actually changes which model gets picked, with every rejected candidate
recorded (no silent fallback), and a privacy requirement that can't be
satisfied BLOCKS rather than silently downgrading to a reachable model.
"""

from __future__ import annotations

import pytest

from app.services.work_items import model_router as mr


@pytest.fixture(autouse=True)
def _clean_provider_env(monkeypatch):
    """Every test starts from a known-empty provider/policy env so a
    developer's real .env (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.) never
    leaks into a routing decision this suite is asserting on."""
    for var in (
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ZECT_LLM_BASE_URL", "ZECT_AGENT_MODEL_PIN",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ZECT_MODEL_FALLBACK_POLICY", "automatic")


class TestTaskProfile:
    def test_unknown_task_type_rejected(self):
        with pytest.raises(ValueError):
            mr.TaskProfile(task_type="not_a_real_task")

    def test_vision_browser_auto_sets_needs_vision(self):
        t = mr.TaskProfile(task_type=mr.TASK_VISION_BROWSER)
        assert t.needs_vision is True

    def test_coding_tasks_auto_set_needs_tool_calling(self):
        for task_type in (mr.TASK_MULTI_FILE_CODING, mr.TASK_DEBUGGING, mr.TASK_VISION_BROWSER):
            assert mr.TaskProfile(task_type=task_type).needs_tool_calling is True


class TestRoutingByTaskAndComplexity:
    def test_lightweight_ask_prefers_cheap_fast_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK))
        assert decision.ok
        cap = mr.MODEL_CAPABILITIES[decision.selected_model]
        assert cap.cost_tier <= 2
        assert cap.reasoning_tier <= 2

    def test_large_java_multi_file_coding_routes_to_strongest_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        decision = mr.route_model(
            mr.TaskProfile(
                task_type=mr.TASK_MULTI_FILE_CODING, complexity=mr.COMPLEXITY_COMPLEX,
                repo_language="java", repo_size_files=400, needs_tool_calling=True,
            )
        )
        assert decision.ok
        assert decision.selected_model == "claude-opus-5"
        assert mr.MODEL_CAPABILITIES[decision.selected_model].reasoning_tier == 5

    def test_large_java_multi_file_coding_and_trivial_ask_route_differently(self, monkeypatch):
        """The exact CP-08 acceptance scenario: a large Java multi-file
        AGENT implementation must NOT land on the same model as a trivial
        classification-style ASK merely because both would otherwise fall
        back to the same UI default."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        big_java = mr.route_model(
            mr.TaskProfile(
                task_type=mr.TASK_MULTI_FILE_CODING, complexity=mr.COMPLEXITY_COMPLEX,
                repo_language="java", repo_size_files=400, needs_tool_calling=True,
            )
        )
        trivial_ask = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK, complexity=mr.COMPLEXITY_TRIVIAL))
        assert big_java.selected_model != trivial_ask.selected_model
        assert mr.MODEL_CAPABILITIES[big_java.selected_model].reasoning_tier > mr.MODEL_CAPABILITIES[trivial_ask.selected_model].reasoning_tier

    def test_complex_plan_eligible_for_strongest_model_not_ui_default(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("ZECT_LLM_CHAT_MODEL", "gpt-4o-mini")  # the "UI default" this must NOT collapse to
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_PLAN, complexity=mr.COMPLEXITY_COMPLEX, repo_size_files=500))
        assert decision.ok
        assert decision.selected_model != "gpt-4o-mini"
        assert mr.MODEL_CAPABILITIES[decision.selected_model].reasoning_tier >= 4

    def test_debugging_and_vision_tasks_pick_capable_models(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        debug = mr.route_model(mr.TaskProfile(task_type=mr.TASK_DEBUGGING, complexity=mr.COMPLEXITY_COMPLEX))
        assert debug.ok and mr.MODEL_CAPABILITIES[debug.selected_model].supports_tool_calling

        vision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_VISION_BROWSER))
        assert vision.ok and mr.MODEL_CAPABILITIES[vision.selected_model].supports_vision

    def test_context_window_insufficient_candidates_are_skipped(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        # Every real candidate has >=128k context; an absurd requirement
        # proves the rejection path is reachable and recorded, not that a
        # production task would realistically hit it.
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK, context_tokens_estimate=10_000_000))
        assert decision.blocked
        assert all(s.reason == "context_window_insufficient" for s in decision.chain)


class TestNoSilentFallback:
    def test_missing_provider_records_rejection_chain_before_falling_through(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")  # anthropic NOT configured
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_MULTI_FILE_CODING, complexity=mr.COMPLEXITY_COMPLEX))
        assert decision.ok
        assert decision.selected_model != "claude-opus-5"  # not configured, must not silently appear as selected
        rejected = [s for s in decision.chain if not s.accepted]
        assert rejected and all(s.model != decision.selected_model for s in rejected)
        accepted = [s for s in decision.chain if s.accepted]
        assert len(accepted) == 1 and accepted[0].model == decision.selected_model

    def test_privacy_local_only_blocks_rather_than_downgrades_to_cloud(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        # Cloud is fully configured and would happily serve this -- but the
        # task demands local_only, and no local gateway is configured.
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK, privacy_requirement=mr.PRIVACY_LOCAL_ONLY))
        assert decision.blocked
        assert decision.policy_decision == "blocked"
        assert decision.selected_model == ""
        # Non-local candidates rejected for being non-local; the local
        # candidates rejected for not actually being configured (no
        # ZECT_LLM_BASE_URL in this test) -- either way, nothing accepted.
        assert not any(s.accepted for s in decision.chain)
        assert all(s.reason in ("privacy_requires_local_only", "mentrix_local_not_configured") for s in decision.chain)

    def test_privacy_local_only_succeeds_when_local_gateway_configured(self, monkeypatch):
        monkeypatch.setenv("ZECT_LLM_BASE_URL", "http://localhost:11434")
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK, privacy_requirement=mr.PRIVACY_LOCAL_ONLY))
        assert decision.ok
        assert mr.MODEL_CAPABILITIES[decision.selected_model].local_only is True

    def test_privacy_local_only_blocks_tool_calling_task_even_with_gateway_configured(self, monkeypatch):
        """Honest fail-closed default: the seeded local models are marked
        supports_tool_calling=False (unverified for this deployment), so an
        AGENT task requiring tools must BLOCK rather than pretend a local
        model can serve it."""
        monkeypatch.setenv("ZECT_LLM_BASE_URL", "http://localhost:11434")
        decision = mr.route_model(
            mr.TaskProfile(task_type=mr.TASK_MULTI_FILE_CODING, privacy_requirement=mr.PRIVACY_LOCAL_ONLY, needs_tool_calling=True)
        )
        assert decision.blocked

    def test_fully_exhausted_chain_blocks_with_no_configured_provider(self):
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK))
        assert decision.blocked
        assert decision.policy_decision == "blocked"
        assert decision.chain  # every candidate tried and rejected, not silently skipped

    def test_decision_to_dict_exposes_requested_fallback_reason_policy_chain(self, monkeypatch):
        """The exact audit shape the mandate requires: requested model ->
        fallback candidate -> reason -> policy decision, all inspectable
        from one serialized object."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        decision = mr.route_model(
            mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK), mode=mr.USER_SELECTED, requested_model="claude-opus-5"
        )
        d = decision.to_dict()
        assert d["requested_model"] == "claude-opus-5"
        assert d["selected_model"] and d["selected_model"] != "claude-opus-5"
        assert d["policy_decision"] in ("allowed", "blocked")
        assert d["chain"][0]["model"] == "claude-opus-5"
        assert d["chain"][0]["accepted"] is False
        assert d["chain"][0]["reason"]


class TestPolicyPinnedAndUserSelected:
    def test_policy_pinned_wins_outright(self, monkeypatch):
        monkeypatch.setenv("ZECT_AGENT_MODEL_PIN", "gpt-4o")
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK), mode=mr.POLICY_PINNED)
        assert decision.selected_model == "gpt-4o"
        assert decision.routing_reason == "policy_pinned_override"

    def test_user_selected_model_tried_first_then_falls_through_task_order(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")  # anthropic not configured
        decision = mr.route_model(
            mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK), mode=mr.USER_SELECTED, requested_model="claude-sonnet-5"
        )
        assert decision.ok
        assert decision.chain[0].model == "claude-sonnet-5"
        assert decision.chain[0].accepted is False
        assert decision.selected_model != "claude-sonnet-5"


class TestTelemetryFields:
    def test_to_telemetry_fields_contains_the_mandated_field_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        decision = mr.route_model(mr.TaskProfile(task_type=mr.TASK_LIGHTWEIGHT_ASK, phase="ask"))
        fields = mr.to_telemetry_fields(decision, phase="ask", role="", input_tokens=120, output_tokens=45, latency_ms=850)
        for key in (
            "phase", "role", "provider", "model", "routing_reason", "context_budget",
            "input_tokens", "output_tokens", "cached_tokens", "estimated_cost", "latency_ms",
        ):
            assert key in fields
        assert fields["input_tokens"] == 120
        assert fields["output_tokens"] == 45

    def test_estimate_cost_usd_uses_known_rate_card_not_a_wrong_default(self):
        cost = mr.estimate_cost_usd("gpt-4o-mini", input_tokens=1000, output_tokens=1000)
        assert cost > 0
        assert mr.estimate_cost_usd("totally-unknown-model-id", input_tokens=1000, output_tokens=1000) == 0.0


class TestRuntimeEventCarriesRoutingFields:
    def test_runtime_event_has_cp08_fields_with_safe_defaults(self):
        from app.adapters.coding_runtime import RuntimeEvent

        ev = RuntimeEvent(sequence_id=1, event="tool_start", message="x")
        assert ev.provider == ""
        assert ev.model == ""
        assert ev.input_tokens == 0
        assert ev.estimated_cost == 0.0

    def test_runtime_event_accepts_routing_fields(self):
        from app.adapters.coding_runtime import RuntimeEvent

        ev = RuntimeEvent(
            sequence_id=1, event="model_call", message="x", role="coder", provider="anthropic",
            model="claude-opus-5", routing_reason="best_fit_for_multi_file_coding_complexity_complex",
            context_budget=200_000, input_tokens=500, output_tokens=200, cached_tokens=0, estimated_cost=0.01,
        )
        assert ev.model == "claude-opus-5"
        assert ev.estimated_cost == 0.01


class TestNativeRuntimeRoutesPerRole:
    """End-to-end through MentrixNativeCodingRuntime.start_run() -- proves
    the wiring, not just the pure route_model() function: a Coder-role run
    against a large Java repo lands on a different model than a Debugger/
    Tester-role run against a tiny one, with zero explicit model= passed
    by the caller (exactly how lifecycle.py's Coder/Debugger/Tester calls
    invoke it today)."""

    def test_coder_role_large_java_repo_routes_to_strongest_model(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        for i in range(200):
            (tmp_path / f"File{i}.java").write_text("class X {}\n", encoding="utf-8")

        from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime

        rt = MentrixNativeCodingRuntime()
        run_id = rt.start_run("Implement a large feature", workspace=str(tmp_path), role="coder", auto_approve_edits=True)
        run = rt._require(run_id)
        assert run["model"] == "claude-opus-5"
        assert run["routing_decision"]["task_type"] == "multi_file_coding"
        assert run["routing_decision"]["policy_decision"] == "allowed"

    def test_trivial_role_small_repo_does_not_get_the_strongest_model(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")

        from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime

        rt = MentrixNativeCodingRuntime()
        run_id = rt.start_run("Fix a typo", workspace=str(tmp_path), role="coder", auto_approve_edits=True)
        run = rt._require(run_id)
        assert run["model"] != "claude-opus-5"

    def test_explicit_model_bypasses_routing_and_is_marked_user_selected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime
        from app.adapters.llm.agent_model_adapter import USER_SELECTED

        rt = MentrixNativeCodingRuntime()
        run_id = rt.start_run("Do X", workspace=str(tmp_path), role="coder", model="gpt-4o-mini", auto_approve_edits=True)
        run = rt._require(run_id)
        assert run["model"] == "gpt-4o-mini"
        assert run["model_route_mode"] == USER_SELECTED
        assert run["routing_decision"] is None

    def test_routing_blocked_fails_the_run_instead_of_silently_using_the_global_default(self, tmp_path, monkeypatch):
        # No provider configured at all -- routing must BLOCK, and the run
        # must fail closed rather than falling back to mentrix_llm_chat_model().
        from app.adapters.coding_engine_mentrix import MentrixNativeCodingRuntime

        rt = MentrixNativeCodingRuntime()
        run_id = rt.start_run("Do X", workspace=str(tmp_path), role="coder", auto_approve_edits=True)
        run = rt._require(run_id)
        assert run["routing_decision"]["blocked"] is True
        assert run["model"] == ""
        rt._agent_loop(run_id)
        run = rt._require(run_id)
        assert run["status"] == "failed"
        assert any(e.event == "failed" and "blocked_external" in e.message for e in run["events"])

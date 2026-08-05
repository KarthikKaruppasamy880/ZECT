"""GPT-5.4 added as a selectable model (matching the model minionbot's
qa-workbench config uses for code generation) — registered in the
multi-provider model registry and priced in the token tracker so usage
isn't silently mis-costed at gpt-4o-mini's rate.
"""

from __future__ import annotations

from app.domains.agent_run.model_selection import MODELS, _find_model
from app.token_tracker import PRICING, _estimate_cost


class TestGpt54Registered:
    def test_gpt54_is_in_the_models_registry(self):
        ids = [m["id"] for m in MODELS]
        assert "gpt-5.4" in ids

    def test_gpt54_resolves_to_openai_provider(self):
        model = _find_model("gpt-5.4")
        assert model["id"] == "gpt-5.4"
        assert model["provider"] == "openai"

    def test_gpt54_has_positive_cost_metadata(self):
        model = _find_model("gpt-5.4")
        assert model["cost_per_1k_input"] > 0
        assert model["cost_per_1k_output"] > 0


class TestGpt54Priced:
    def test_gpt54_has_a_pricing_entry(self):
        assert "gpt-5.4" in PRICING
        assert PRICING["gpt-5.4"]["input"] > 0
        assert PRICING["gpt-5.4"]["output"] > 0

    def test_gpt54_not_mis_costed_at_gpt4o_mini_rate(self):
        gpt54_cost = _estimate_cost("gpt-5.4", 1_000_000, 1_000_000)
        mini_cost = _estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
        assert gpt54_cost != mini_cost

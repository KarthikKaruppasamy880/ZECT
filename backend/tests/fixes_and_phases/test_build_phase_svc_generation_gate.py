"""run_build_generate's offline-stub gate checked only OPENAI_API_KEY, even
though _generate_core (used whenever the gate passes) already branches
between Anthropic and OpenAI via resolve_generation_model(). An
Anthropic-only deployment (ANTHROPIC_API_KEY set, no OPENAI_API_KEY) would
silently hit the offline placeholder on every build step instead of
calling Claude, despite the app's own documented Anthropic-preferred
generation behavior.
"""

from __future__ import annotations

from app.services.phases.build_phase_svc import _generation_ready


class TestGenerationReadyGate:
    def test_ready_with_only_openai_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        assert _generation_ready() is True

    def test_ready_with_only_anthropic_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        assert _generation_ready() is True

    def test_not_ready_with_neither_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        assert _generation_ready() is False

    def test_product_fails_closed_without_provider(self, monkeypatch):
        from app.services.phases.build_phase_svc import run_build_generate

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ZECT_ALLOW_OFFLINE_BUILD_STUB", raising=False)

        result = run_build_generate("Add a health endpoint", file_path="app/health.py")

        assert result.get("error") == "generation_unavailable"
        assert result.get("offline") is False
        assert result.get("generated_code") == ""

    def test_offline_stub_only_when_flag_set(self, monkeypatch):
        from app.services.phases.build_phase_svc import run_build_generate

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ZECT_ALLOW_OFFLINE_BUILD_STUB", "1")

        result = run_build_generate("Add a health endpoint", file_path="app/health.py")

        assert result["offline"] is True

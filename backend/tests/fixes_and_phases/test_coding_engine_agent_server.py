"""Agent Server coding-engine adapter uses public provider name remote only."""

from __future__ import annotations

from app.adapters.coding_engine_openhands import AgentServerCodingEngine
from app.adapters.coding_runtime import reset_coding_runtime_for_tests, selected_coding_engine


def test_agent_server_provider_name_is_remote():
    assert AgentServerCodingEngine.provider_name == "remote"


def test_factory_remote_uses_agent_server(monkeypatch):
    reset_coding_runtime_for_tests()
    monkeypatch.setenv("ZECT_CODING_ENGINE", "remote")
    monkeypatch.setenv("ZECT_CODING_ENGINE_URL", "http://engine.test")
    monkeypatch.setenv("ZECT_CODING_ENGINE_API_KEY", "secret-key")
    from app.adapters.coding_runtime import get_coding_runtime

    rt = get_coding_runtime()
    assert rt.provider_name == "remote"
    assert isinstance(rt, AgentServerCodingEngine)
    assert selected_coding_engine() == "remote"

"""Phase B — HLD generator: run_blueprint()/build_deep_prompt() only template
structural data into a prompt string; neither calls an LLM. run_hld_generate()
reuses _run_scout()+run_blueprint() for data gathering and adds the one new
step — an actual LLM call that synthesizes a design document — routed through
Anthropic when configured, same as build_phase_svc.py's existing pattern."""

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.services.phases.hld_phase import run_hld_generate

FAKE_SCOUT = {
    "structural_blueprint": {
        "tech_stack": ["fastapi", "react"],
        "stats": {"files_indexed": 42, "api_endpoints": 5, "functions": 30, "classes": 4},
        "api_endpoints": [{"name": "get_health", "path": "/api/health"}],
        "dependency_graph": {"app.main": ["app.routers.health"]},
        "god_nodes": [{"kind": "function", "name": "run_forge_loop", "path": "orchestrator.py", "degree": 40}],
        "functions": [{"name": "run_forge_loop", "path": "orchestrator.py"}],
    },
    "explain_notes": [],
    "graph_hits": [],
    "graph_summary": {},
}

FAKE_HLD_MARKDOWN = (
    "## Component Breakdown\n- orchestrator: runs the FSM\n\n"
    "## Data Flow\nGoal -> scout -> blueprint -> LLM\n\n"
    "## Architecture Diagram\n```mermaid\ngraph TD; A-->B\n```\n\n"
    "## Risks & Technical Debt\n- run_forge_loop is a god node (degree=40)\n\n"
    "## Recommendations\n- Split orchestrator into smaller stages"
)


def _patch_scout(monkeypatch, scout=FAKE_SCOUT):
    monkeypatch.setattr(
        "app.services.forge_loop.orchestrator._run_scout",
        lambda db, goal, project_key, events: scout,
    )


def _patch_completion(monkeypatch, content=FAKE_HLD_MARKDOWN, capture=None):
    def fake_complete(client, *, messages, model, max_tokens, temperature, language_hint, create_fn=None):
        if capture is not None:
            capture["messages"] = messages
            capture["model"] = model
            capture["create_fn"] = create_fn
            capture["client"] = client
        return {
            "content": content,
            "tokens_used": 500,
            "prompt_tokens": 400,
            "completion_tokens": 100,
        }

    monkeypatch.setattr("app.services.quality.truncation.complete_with_continuations", fake_complete)


class TestRunHldGenerate:
    def test_reuses_scout_and_blueprint_for_prompt(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        _patch_scout(monkeypatch)
        captured = {}
        _patch_completion(monkeypatch, capture=captured)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = run_hld_generate(Mock(spec=Session), "proj-1", goal="Upgrade this repo")

        user_msg = captured["messages"][1]["content"]
        assert "api_endpoints" in user_msg or "/api/health" in user_msg
        assert "run_forge_loop" in user_msg
        assert result["hld_document"] == FAKE_HLD_MARKDOWN
        assert result["project_key"] == "proj-1"

    def test_uses_openai_by_default(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        _patch_scout(monkeypatch)
        captured = {}
        _patch_completion(monkeypatch, capture=captured)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = run_hld_generate(Mock(spec=Session), "proj-1")

        assert result["model"] == "gpt-4o-mini"
        assert captured["create_fn"] is None
        assert captured["client"] is not None

    def test_routes_to_anthropic_when_configured(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        _patch_scout(monkeypatch)
        captured = {}
        _patch_completion(monkeypatch, capture=captured)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        result = run_hld_generate(Mock(spec=Session), "proj-1")

        assert result["model"] == "claude-sonnet-5"
        assert captured["create_fn"] is not None
        assert captured["client"] is None

    def test_logs_tokens_with_user_id(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        _patch_scout(monkeypatch)
        _patch_completion(monkeypatch)
        logged = {}
        monkeypatch.setattr(
            "app.token_tracker.log_tokens",
            lambda **kw: logged.update(kw),
        )

        run_hld_generate(Mock(spec=Session), "proj-1", user_id=9)

        assert logged["user_id"] == 9
        assert logged["total_tokens"] == 500
        assert logged["feature"] == "hld"

    def test_raises_valueerror_on_api_error(self, monkeypatch):
        from openai import APIError

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        _patch_scout(monkeypatch)

        def boom(*a, **kw):
            raise APIError("boom", request=Mock(), body=None)

        monkeypatch.setattr("app.services.quality.truncation.complete_with_continuations", boom)

        with pytest.raises(ValueError):
            run_hld_generate(Mock(spec=Session), "proj-1")


class TestHldRouterEndpoint:
    def test_endpoint_returns_hld_document(self, monkeypatch):
        from app.routers.lattice import HldRequest, hld_generate_api

        monkeypatch.setattr(
            "app.services.phases.hld_phase.run_hld_generate",
            lambda db, project_key, goal="", user_id=None: {
                "hld_document": FAKE_HLD_MARKDOWN,
                "project_key": project_key,
                "model": "gpt-4o-mini",
                "tokens_used": 500,
                "structural_summary_used": "...",
            },
        )

        req = HldRequest(project_key="proj-1")
        result = hld_generate_api(req, db=Mock(spec=Session), current_user=Mock(user_id=3))

        assert result["hld_document"] == FAKE_HLD_MARKDOWN
        assert result["project_key"] == "proj-1"

    def test_endpoint_raises_503_on_value_error(self, monkeypatch):
        from fastapi import HTTPException

        from app.routers.lattice import HldRequest, hld_generate_api

        def boom(db, project_key, goal="", user_id=None):
            raise ValueError("OpenAI API error: no key")

        monkeypatch.setattr("app.services.phases.hld_phase.run_hld_generate", boom)

        req = HldRequest(project_key="proj-1")
        with pytest.raises(HTTPException) as exc:
            hld_generate_api(req, db=Mock(spec=Session), current_user=Mock(user_id=3))
        assert exc.value.status_code == 503

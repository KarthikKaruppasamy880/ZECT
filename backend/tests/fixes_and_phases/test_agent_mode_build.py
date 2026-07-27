"""Agent Mode must map build stages to Mentrix upgrade (real codegen)."""

from __future__ import annotations

from app.routers.agent_mode import AgentRunRequest, _resolve_mode


class TestResolveMode:
    def test_default_stages_with_build_use_upgrade(self):
        req = AgentRunRequest(task="add healthcheck", stages=["ask", "plan", "build", "review"])
        assert _resolve_mode(req) == "upgrade"

    def test_ask_only_is_chat(self):
        req = AgentRunRequest(task="explain auth", stages=["ask"])
        assert _resolve_mode(req) == "chat"

    def test_review_only(self):
        req = AgentRunRequest(task="review", stages=["review"])
        assert _resolve_mode(req) == "review_only"

    def test_explicit_mode_override(self):
        req = AgentRunRequest(task="fix bug", stages=["build"], mode="bugfix")
        assert _resolve_mode(req) == "bugfix"

    def test_deploy_implies_upgrade(self):
        req = AgentRunRequest(task="ship", stages=["deploy"])
        assert _resolve_mode(req) == "upgrade"


class TestAppRunnerWindowsPopen:
    def test_popen_kwargs_no_setsid_on_windows(self, monkeypatch):
        import app.routers.app_runner as ar

        monkeypatch.setattr(ar, "_IS_WINDOWS", True)
        kwargs = ar._popen_kwargs()
        assert "preexec_fn" not in kwargs
        assert "creationflags" in kwargs

    def test_popen_kwargs_setsid_on_unix(self, monkeypatch):
        import app.routers.app_runner as ar
        import os

        monkeypatch.setattr(ar, "_IS_WINDOWS", False)
        monkeypatch.setattr(os, "setsid", lambda: None, raising=False)
        kwargs = ar._popen_kwargs()
        assert "preexec_fn" in kwargs

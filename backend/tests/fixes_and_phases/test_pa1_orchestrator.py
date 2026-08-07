"""PA-1 MentrixOrchestrator + no-delete + browser allowlist defaults."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.browser.allowlist import host_allowed
from app.services.mentrix.no_delete_policy import refuse_delete
from app.services.mentrix.orchestrator import MentrixOrchestrator, pa1_orchestrator_enabled


def test_pa1_flag_default_on(monkeypatch):
    monkeypatch.delenv("MENTRIX_PA1_ORCHESTRATOR", raising=False)
    assert pa1_orchestrator_enabled() is True
    monkeypatch.setenv("MENTRIX_PA1_ORCHESTRATOR", "0")
    assert pa1_orchestrator_enabled() is False


def test_browser_default_blocks_unknown(monkeypatch):
    monkeypatch.delenv("MENTRIX_BROWSER_ALLOWLIST", raising=False)
    ok, _ = host_allowed("https://github.com/org/repo")
    assert ok is True
    bad, reason = host_allowed("https://evil-phishing.example")
    assert bad is False
    assert "allowlist" in reason.lower() or "not in" in reason.lower()


def test_browser_star_still_opt_in(monkeypatch):
    monkeypatch.setenv("MENTRIX_BROWSER_ALLOWLIST", "*")
    ok, _ = host_allowed("https://anywhere.example")
    assert ok is True


def test_refuse_delete():
    out = refuse_delete(intent="desktop_delete")
    assert out["ok"] is False
    assert out["error"] == "delete_never_allowed"


def test_orchestrator_denies_delete(monkeypatch):
    monkeypatch.setenv("MENTRIX_PA1_ORCHESTRATOR", "1")
    db = MagicMock()
    orch = MentrixOrchestrator()
    called = {"n": 0}

    def exec_tool(*_a, **_k):
        called["n"] += 1
        return {"ok": True}

    out = orch.execute_tool(
        db,
        "desktop_delete",
        {"path": "C:/tmp/x"},
        user_confirmed=True,
        exec_tool=exec_tool,
    )
    assert out.status == "denied"
    assert out.result["error"] == "delete_never_allowed"
    assert called["n"] == 0


def test_orchestrator_executes_when_allowed(monkeypatch):
    monkeypatch.setenv("MENTRIX_PA1_ORCHESTRATOR", "1")
    db = MagicMock()

    with patch(
        "app.services.mentrix.policy_services.check_tool_permission",
        return_value={
            "result": "granted",
            "needs_confirm": False,
            "action": "companion_navigate",
            "audit_id": 1,
        },
    ):
        orch = MentrixOrchestrator()

        def exec_tool(*_a, **_k):
            return {"ok": True, "navigate": "/mentrix"}

        out = orch.execute_tool(
            db,
            "navigate",
            {"path": "/mentrix"},
            user_confirmed=True,
            exec_tool=exec_tool,
        )
    assert out.status == "executed"
    assert out.result["ok"] is True
    assert out.command.verification.get("kind")


def test_orchestrator_pending_confirm(monkeypatch):
    monkeypatch.setenv("MENTRIX_PA1_ORCHESTRATOR", "1")
    db = MagicMock()
    with patch(
        "app.services.mentrix.policy_services.check_tool_permission",
        return_value={
            "result": "pending_approval",
            "needs_confirm": True,
            "action": "companion_delivery_start",
            "audit_id": 9,
        },
    ):
        orch = MentrixOrchestrator()
        out = orch.execute_tool(
            db,
            "start_delivery",
            {"goal": "x"},
            user_confirmed=False,
            exec_tool=lambda *a, **k: {"ok": True},
        )
    assert out.status == "pending_confirm"
    assert out.pending is not None

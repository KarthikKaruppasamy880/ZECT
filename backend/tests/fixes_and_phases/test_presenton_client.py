"""Presenton client readiness helpers (no live Presenton required)."""

from app.services.presenton_client import generate_presentation, presenton_configured


def test_presenton_not_configured(monkeypatch):
    monkeypatch.delenv("PRESENTON_BASE_URL", raising=False)
    assert presenton_configured() is False
    out = generate_presentation("hello deck")
    assert out["ok"] is False
    assert out["error"] == "presenton_not_configured"


def test_presenton_empty_content(monkeypatch):
    monkeypatch.setenv("PRESENTON_BASE_URL", "http://127.0.0.1:5000")
    out = generate_presentation("   ")
    assert out["ok"] is False
    assert out["error"] == "empty_content"

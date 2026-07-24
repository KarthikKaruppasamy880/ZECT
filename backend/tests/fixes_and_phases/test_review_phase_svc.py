"""Phase E — Mentrix Ultra Review's orchestrator-facing wrapper used to run a
4th standalone OpenAI call (same 5-severity JSON schema as the three routers
consolidated in Phase A), and its runs were never persisted. This verifies it
now delegates to the canonical review_code_snippet() and adapts the response
back to its existing score/passed/critical_findings contract."""

from unittest.mock import Mock

from app.services.phases.review_phase_svc import run_ultra_review

SAMPLE_RESULT = {
    "summary": "Mostly fine.",
    "quality_score": 80,
    "findings": [{
        "severity": "high",
        "category": "vulnerabilities",
        "title": "Hardcoded secret",
        "description": "API key hardcoded.",
        "line": 5,
        "suggestion": "Use env var.",
    }],
    "tokens_used": 40,
    "model": "gpt-4o-mini",
    "review_session_id": 7,
}


class TestRunUltraReviewDelegates:
    def test_delegates_to_canonical_engine_and_adapts_response(self, monkeypatch):
        captured = {}

        def fake_review_code_snippet(code, language, user_id=None, db=None):
            captured["code"] = code
            captured["language"] = language
            captured["user_id"] = user_id
            captured["db"] = db
            return SAMPLE_RESULT

        monkeypatch.setattr("app.review_service.review_code_snippet", fake_review_code_snippet)

        db = Mock()
        result = run_ultra_review("x = 1", language="python", goal="test", db=db, user_id=3)

        assert captured["user_id"] == 3
        assert captured["db"] is db
        assert result["score"] == 80
        assert result["quality_score"] == 80
        assert result["passed"] is True  # score 80 >= 70, no critical findings
        assert result["critical_findings"] == 0
        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "high"
        assert "Hardcoded secret" in result["findings"][0]["message"]
        assert result["review_session_id"] == 7
        assert result["offline"] is False

    def test_severity_threshold_filters_findings(self, monkeypatch):
        two_findings = {
            **SAMPLE_RESULT,
            "findings": [
                {**SAMPLE_RESULT["findings"][0], "severity": "critical"},
                {**SAMPLE_RESULT["findings"][0], "severity": "info", "title": "Style nit"},
            ],
        }
        monkeypatch.setattr(
            "app.review_service.review_code_snippet",
            lambda code, language, user_id=None, db=None: two_findings,
        )

        result = run_ultra_review("x = 1", severity_threshold="high")

        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "critical"
        assert result["critical_findings"] == 1
        assert result["passed"] is False  # critical finding present

    def test_falls_back_to_offline_heuristics_when_no_api_key(self, monkeypatch):
        def raise_no_key(code, language, user_id=None, db=None):
            raise ValueError("OpenAI API key not configured.")

        monkeypatch.setattr("app.review_service.review_code_snippet", raise_no_key)

        result = run_ultra_review("API_KEY = 'sk-hardcoded'", goal="upgrade")

        assert result["offline"] is True
        assert result["model"] == "offline"
        assert result["critical_findings"] == 1
        assert result["passed"] is False

    def test_context_is_prepended_not_dropped(self, monkeypatch):
        captured = {}

        def fake(code, language, user_id=None, db=None):
            captured["code"] = code
            return SAMPLE_RESULT

        monkeypatch.setattr("app.review_service.review_code_snippet", fake)

        run_ultra_review("x = 1", context="upgrade rules context")

        assert "upgrade rules context" in captured["code"]
        assert "x = 1" in captured["code"]

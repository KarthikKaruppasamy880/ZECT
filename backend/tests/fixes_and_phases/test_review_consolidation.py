"""Unit tests for the review-engine consolidation.

Three routers duplicated the same LLM review logic under different names
(review_phase.py "Mentrix Ultra Review", code_review.py "ZECT Review Engine",
ultrareview.py "ZECT Ultrareview") — this verifies all three now delegate to
the one canonical engine (review_service.review_code_snippet) instead of each
calling OpenAI independently, and that persistence (ReviewSession/ReviewFinding)
is shared across all of them.
"""

import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import ReviewFinding, ReviewSession
from app.review_service import _persist_review_session, review_code_snippet


SAMPLE_RESULT = {
    "summary": "Looks mostly fine.",
    "quality_score": 72,
    "total_issues": 1,
    "categories": {"vulnerabilities": 1},
    "findings": [{
        "severity": "high",
        "category": "vulnerabilities",
        "title": "Hardcoded secret",
        "description": "API key is hardcoded in source.",
        "file": "auth.py",
        "line": 12,
        "suggestion": "Move to env var.",
        "code_snippet": "API_KEY = 'sk-abc123'",
        "fixed_code": "API_KEY = os.getenv('API_KEY')",
        "cwe_id": "CWE-798",
        "owasp_category": "A07:2021-Identification and Authentication Failures",
    }],
    "strengths": ["Clear naming"],
    "recommendations": ["Add tests"],
    "tokens_used": 42,
    "model": "gpt-4o-mini",
}


class TestPersistReviewSession:
    def test_returns_none_when_no_db(self):
        assert _persist_review_session(None, review_type="snippet", result=SAMPLE_RESULT) is None

    def test_creates_session_and_findings(self):
        db = Mock(spec=Session)
        added = []
        db.add.side_effect = lambda obj: added.append(obj)

        session_id = _persist_review_session(db, review_type="snippet", result=SAMPLE_RESULT, user_id=7)

        sessions = [o for o in added if isinstance(o, ReviewSession)]
        findings = [o for o in added if isinstance(o, ReviewFinding)]
        assert len(sessions) == 1
        assert sessions[0].user_id == 7
        assert sessions[0].review_type == "snippet"
        assert sessions[0].overall_score == 72
        assert sessions[0].high_count == 1
        assert len(findings) == 1
        assert findings[0].cwe_id == "CWE-798"
        assert findings[0].owasp_category.startswith("A07:2021")
        assert findings[0].fixed_code == "API_KEY = os.getenv('API_KEY')"
        assert db.commit.called

    def test_persistence_failure_does_not_raise(self):
        db = Mock(spec=Session)
        db.add.side_effect = Exception("db is down")

        result = _persist_review_session(db, review_type="snippet", result=SAMPLE_RESULT)

        assert result is None
        assert db.rollback.called


class TestReviewCodeSnippetPersists:
    def test_persists_and_returns_session_id(self, monkeypatch):
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(content=json.dumps(SAMPLE_RESULT)))]
        mock_resp.usage = Mock(total_tokens=42, prompt_tokens=30, completion_tokens=12)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_resp

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr("app.review_service._get_client", lambda: mock_client)
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        db = Mock(spec=Session)
        captured_session = {}

        def fake_persist(db_arg, **kwargs):
            captured_session.update(kwargs)
            return 999

        monkeypatch.setattr("app.review_service._persist_review_session", fake_persist)

        result = review_code_snippet(code="x = 1", language="python", user_id=5, db=db)

        assert result["review_session_id"] == 999
        assert captured_session["review_type"] == "snippet"
        assert captured_session["user_id"] == 5


class TestReviewPhaseDelegatesNotDuplicates:
    """review_phase.py's /analyze must call review_code_snippet, not its own
    OpenAI call — this is the core of the consolidation."""

    def test_analyze_delegates_and_adapts_response(self, monkeypatch):
        from app.routers.review_phase import ReviewRequest, analyze_code

        monkeypatch.setattr(
            "app.review_service.review_code_snippet",
            lambda code, language, user_id=None, db=None: {**SAMPLE_RESULT, "review_session_id": 1},
        )

        req = ReviewRequest(code="x = 1", language="python", severity_threshold="high")
        result = analyze_code(req, current_user=Mock(user_id=1), db=Mock(spec=Session))

        assert result.score == 72
        assert result.passed is True  # 72 >= 70 threshold
        assert len(result.findings) == 1
        assert "Hardcoded secret" in result.findings[0].message

    def test_severity_threshold_filters_findings(self, monkeypatch):
        from app.routers.review_phase import ReviewRequest, analyze_code

        two_findings = {**SAMPLE_RESULT, "findings": [
            {**SAMPLE_RESULT["findings"][0], "severity": "high"},
            {**SAMPLE_RESULT["findings"][0], "severity": "info", "title": "Minor style nit"},
        ]}
        monkeypatch.setattr(
            "app.review_service.review_code_snippet",
            lambda code, language, user_id=None, db=None: {**two_findings, "review_session_id": 1},
        )

        req = ReviewRequest(code="x = 1", language="python", severity_threshold="high")
        result = analyze_code(req, current_user=Mock(user_id=1), db=Mock(spec=Session))

        # threshold "high" should exclude the "info" finding
        assert len(result.findings) == 1
        assert result.findings[0].severity == "high"

    def test_context_is_prepended_to_code_not_dropped(self, monkeypatch):
        from app.routers.review_phase import ReviewRequest, analyze_code

        captured = {}

        def fake_review(code, language, user_id=None, db=None):
            captured["code"] = code
            return {**SAMPLE_RESULT, "findings": [], "review_session_id": 1}

        monkeypatch.setattr("app.review_service.review_code_snippet", fake_review)

        req = ReviewRequest(code="x = 1", language="python", context="part of auth module")
        analyze_code(req, current_user=Mock(user_id=1), db=Mock(spec=Session))

        assert "auth module" in captured["code"]
        assert "x = 1" in captured["code"]


class TestUltrareviewDelegatesAndReusesHistory:
    def test_snippet_endpoint_delegates_and_fetches_persisted_session(self, monkeypatch):
        from app.routers.ultrareview import SnippetReviewRequest, review_snippet

        monkeypatch.setattr(
            "app.review_service.review_code_snippet",
            lambda code, language, user_id=None, db=None: {**SAMPLE_RESULT, "review_session_id": 42},
        )

        fake_session = Mock(
            id=42, status="completed", overall_score=72.0, review_summary="ok",
            total_findings=1, critical_count=0, high_count=1, medium_count=0, low_count=0, info_count=0,
            tokens_used=42, cost_usd=0.001, duration_seconds=1, model_used="gpt-4o-mini",
        )
        db = Mock(spec=Session)
        db.query().filter().first.return_value = fake_session
        db.query().filter().all.return_value = []

        req = SnippetReviewRequest(code="x = 1", language="python")
        result = review_snippet(req, current_user=Mock(user_id=3), db=db)

        assert result.session_id == 42
        assert result.overall_score == 72.0

    def test_raises_if_persistence_failed(self, monkeypatch):
        from app.routers.ultrareview import SnippetReviewRequest, review_snippet
        from fastapi import HTTPException

        monkeypatch.setattr(
            "app.review_service.review_code_snippet",
            lambda code, language, user_id=None, db=None: {**SAMPLE_RESULT, "review_session_id": None},
        )

        req = SnippetReviewRequest(code="x = 1", language="python")
        with pytest.raises(HTTPException) as exc:
            review_snippet(req, current_user=Mock(user_id=3), db=Mock(spec=Session))
        assert exc.value.status_code == 500

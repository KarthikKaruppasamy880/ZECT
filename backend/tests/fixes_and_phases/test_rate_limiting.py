"""Unit tests for per-user rate limiting and token budget enforcement."""

import pytest
from unittest.mock import Mock
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.middleware.rate_limiter import RateLimiter, _rate_limit_key, _is_expensive
from app.infrastructure.budget import check_budget, BudgetExceeded, _get_budget
from app.models import TokenBudget, TokenLog


class TestRateLimiterBucketing:
    """Test the token-bucket algorithm itself."""

    def test_allows_within_burst(self):
        limiter = RateLimiter(requests_per_minute=60, burst=5)
        for _ in range(5):
            allowed, _ = limiter.allow("user:1")
            assert allowed is True

    def test_denies_after_burst_exhausted(self):
        limiter = RateLimiter(requests_per_minute=60, burst=3)
        for _ in range(3):
            limiter.allow("user:1")
        allowed, headers = limiter.allow("user:1")
        assert allowed is False
        assert "Retry-After" in headers

    def test_buckets_are_isolated_per_key(self):
        limiter = RateLimiter(requests_per_minute=60, burst=2)
        limiter.allow("user:1")
        limiter.allow("user:1")
        # user:1 exhausted, user:2 should be unaffected
        allowed_1, _ = limiter.allow("user:1")
        allowed_2, _ = limiter.allow("user:2")
        assert allowed_1 is False
        assert allowed_2 is True


class TestRateLimitKeying:
    """Test that requests are keyed by authenticated user, not just IP."""

    def test_keys_by_user_id_when_authenticated(self):
        request = Mock()
        request.state.user_id = 42
        key, authenticated = _rate_limit_key(request)
        assert key == "user:42"
        assert authenticated is True

    def test_falls_back_to_ip_when_unauthenticated(self):
        request = Mock(spec=["state", "client"])
        request.state = Mock(spec=[])  # no user_id attribute
        request.client.host = "10.0.0.5"
        key, authenticated = _rate_limit_key(request)
        assert key == "ip:10.0.0.5"
        assert authenticated is False

    def test_different_users_get_different_keys(self):
        req_a = Mock()
        req_a.state.user_id = 1
        req_b = Mock()
        req_b.state.user_id = 2
        key_a, _ = _rate_limit_key(req_a)
        key_b, _ = _rate_limit_key(req_b)
        assert key_a != key_b


class TestExpensivePathDetection:
    """Test that LLM-cost paths get flagged for the stricter tier."""

    @pytest.mark.parametrize("path", [
        "/api/llm/ask",
        "/api/llm/plan",
        "/api/code-review",
        "/api/analysis/blueprint",
        "/api/build/generate",
        "/api/review/pr",
        "/api/deploy/run",
        "/api/dream-engine/cycle",
        "/api/agent/run",
        "/api/mentrix/companion/stream",
    ])
    def test_flags_expensive_paths(self, path):
        assert _is_expensive(path) is True

    @pytest.mark.parametrize("path", [
        "/api/projects",
        "/api/settings",
        "/api/audit",
        "/api/secrets",
        "/healthz",
    ])
    def test_does_not_flag_cheap_paths(self, path):
        assert _is_expensive(path) is False


class TestBudgetEnforcement:
    """Test the check_budget() function used by the enforce_token_budget dependency."""

    @pytest.fixture
    def db_mock(self):
        return Mock(spec=Session)

    def test_no_budget_row_allows_request(self, db_mock):
        db_mock.query().filter().first.return_value = None
        # Should not raise
        check_budget(db_mock, user_id=1)

    def test_enforce_limits_false_allows_request(self, db_mock):
        budget = Mock(spec=TokenBudget, enforce_limits=False)
        db_mock.query().filter().first.return_value = budget
        check_budget(db_mock, user_id=1)

    @staticmethod
    def _filtered_logs_mock(logs):
        """A Mock that supports both direct iteration and .all() — check_budget
        does `for log in query.filter(...)` for daily and `.filter(...).all()` for monthly."""
        m = Mock()
        m.__iter__ = Mock(return_value=iter(logs))
        m.all.return_value = logs
        return m

    def test_daily_limit_exceeded_raises(self, db_mock):
        budget = Mock(
            spec=TokenBudget,
            enforce_limits=True,
            daily_token_limit=1000,
            monthly_token_limit=0,
            monthly_cost_limit_usd=0.0,
        )
        log = Mock(spec=TokenLog, total_tokens=1500, estimated_cost_usd=0.1)

        def query_side_effect(model):
            q = Mock()
            if model is TokenBudget:
                q.filter.return_value.first.return_value = budget
            else:
                q.filter.return_value = self._filtered_logs_mock([log])
            return q

        db_mock.query.side_effect = query_side_effect

        with pytest.raises(BudgetExceeded) as exc_info:
            check_budget(db_mock, user_id=1)
        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["limit_type"] == "daily_tokens"

    def test_within_limits_does_not_raise(self, db_mock):
        budget = Mock(
            spec=TokenBudget,
            enforce_limits=True,
            daily_token_limit=100_000,
            monthly_token_limit=1_000_000,
            monthly_cost_limit_usd=100.0,
        )
        log = Mock(spec=TokenLog, total_tokens=10, estimated_cost_usd=0.001)

        def query_side_effect(model):
            q = Mock()
            if model is TokenBudget:
                q.filter.return_value.first.return_value = budget
            else:
                q.filter.return_value = self._filtered_logs_mock([log])
            return q

        db_mock.query.side_effect = query_side_effect

        check_budget(db_mock, user_id=1)  # should not raise


class TestBudgetExceededException:
    """Test the BudgetExceeded exception shape."""

    def test_has_429_status(self):
        exc = BudgetExceeded("Daily limit reached", "daily_tokens")
        assert exc.status_code == 429

    def test_detail_includes_limit_type(self):
        exc = BudgetExceeded("Monthly cost limit reached", "monthly_cost")
        assert exc.detail["limit_type"] == "monthly_cost"
        assert "Monthly cost limit reached" in exc.detail["message"]


class TestLogTokensUserId:
    """Test that log_tokens persists the user_id (previously always None)."""

    def test_log_tokens_accepts_user_id(self, monkeypatch):
        from app import token_tracker

        captured = {}

        class FakeSession:
            def add(self, entry):
                captured["entry"] = entry

            def commit(self):
                pass

            def rollback(self):
                pass

            def close(self):
                pass

        monkeypatch.setattr(token_tracker, "SessionLocal", lambda: FakeSession())

        token_tracker.log_tokens(
            action="ask_question",
            feature="ask_mode",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            user_id=99,
        )

        assert captured["entry"].user_id == 99

    def test_log_tokens_user_id_defaults_to_none(self, monkeypatch):
        from app import token_tracker

        captured = {}

        class FakeSession:
            def add(self, entry):
                captured["entry"] = entry

            def commit(self):
                pass

            def rollback(self):
                pass

            def close(self):
                pass

        monkeypatch.setattr(token_tracker, "SessionLocal", lambda: FakeSession())

        token_tracker.log_tokens(action="ask_question", feature="ask_mode", total_tokens=5)

        assert captured["entry"].user_id is None

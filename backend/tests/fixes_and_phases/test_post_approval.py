"""Phase 4 Stage D — post approval gate unit tests."""
import pytest

from app.domains.pr_review.post_approval import (
    approve_post,
    build_fix_goal_from_findings,
    clear_approval,
    get_approval,
    require_approval,
)


def test_approve_and_require():
    clear_approval(42)
    with pytest.raises(PermissionError):
        require_approval(42)
    rec = approve_post(42, [1, 2, 2], approved_by="u@zect.dev", owner="o", repo="r", pr_number=7)
    assert rec["finding_ids"] == [1, 2]
    assert get_approval(42)["approved_by"] == "u@zect.dev"
    assert require_approval(42)["pr_number"] == 7
    clear_approval(42)


def test_approve_requires_ids():
    with pytest.raises(ValueError):
        approve_post(1, [])


def test_build_fix_goal():
    class F:
        title = "Leak"
        severity = "critical"
        file_path = "a.py"
        line_start = 3
        description = "secret"
        suggestion = "use env"

    goal = build_fix_goal_from_findings([F()], repo="acme/zect", pr_number=9)
    assert "Leak" in goal
    assert "a.py" in goal
    assert "#9" in goal or "9" in goal

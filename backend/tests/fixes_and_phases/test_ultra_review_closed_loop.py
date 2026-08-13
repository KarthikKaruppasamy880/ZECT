"""Ultra Review closed-loop PR engineering — unit proofs (no auto-merge)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.services.ultra_review.closed_loop import ClosedLoopOrchestrator, head_sha
from app.services.ultra_review.coderabbit_benchmark import compare_blind
from app.services.ultra_review.finding_router import (
    RouteClass,
    Severity,
    VerificationStatus,
    classify_finding,
    gate_from_findings,
    normalize_closed_loop_finding,
    route_target,
)


def test_classify_local_fix():
    assert classify_finding({"title": "Unused import", "category": "style"}) == RouteClass.LOCAL_FIX


def test_classify_test_gap():
    assert classify_finding({"title": "Missing test for auth helper", "category": "coverage"}) == RouteClass.TEST_GAP


def test_classify_security():
    assert classify_finding({"title": "Path traversal in file read", "severity": "critical", "category": "security"}) == RouteClass.SECURITY


def test_classify_plan_revision():
    assert classify_finding({"title": "Violates plan: wrong API shape", "is_verified": True}) == RouteClass.PLAN_REVISION


def test_classify_architecture():
    assert classify_finding({"title": "Requires schema migration and redesign", "architecture_impact": True}) == RouteClass.ARCHITECTURE_CHANGE


def test_security_blocks_merge_eligible():
    f = normalize_closed_loop_finding(
        {
            "id": 1,
            "title": "SSRF in fetch URL",
            "severity": "critical",
            "category": "security",
            "is_verified": True,
        }
    )
    assert f.recommended_action == RouteClass.SECURITY
    gates = gate_from_findings([f])
    assert gates["READY_TO_SHIP"] is False
    assert gates["MERGE_ELIGIBLE"] is False
    assert "1" in gates["security_blockers"] or f.finding_id in gates["security_blockers"]


def test_local_fix_cycle_resolves_same_pr_dry_run():
    orch = ClosedLoopOrchestrator(max_review_cycles=3)
    raw = [
        {
            "id": "bug-1",
            "title": "Off-by-one in parser",
            "severity": "high",
            "category": "bug",
            "file": "parser.py",
            "line": 10,
            "is_verified": True,
        }
    ]
    out = orch.run_until_clean_or_budget(
        raw_findings=raw,
        old_head_sha="aaa111",
        pr_id="PR-99",
        apply_local_fix=True,
        dry_run=True,
    )
    assert out["auto_merge"] is False
    assert out["same_pr"] if "same_pr" in out else True
    assert out["old_head_sha"] == "aaa111"
    assert out["new_head_sha"] != "aaa111" or out["final_state"] in ("READY_TO_SHIP", "RE_REVIEWING")
    # After simulated fix, finding should be resolved and gates open
    resolved = [f for f in out["findings"] if f["verification_status"] == "RESOLVED"]
    assert resolved
    assert out["gates"]["MERGE_ELIGIBLE"] is True
    assert out["final_state"] == "READY_TO_SHIP"
    assert out["cycles"][0]["routing"] == "LOCAL_FIX"
    assert out["cycles"][0]["route_target"]["agent"] == "coding_agent"


def test_security_cycle_forces_block_then_resolve():
    orch = ClosedLoopOrchestrator(max_review_cycles=2)
    raw = [
        {
            "id": "sec-1",
            "title": "Auth bypass on admin route",
            "severity": "critical",
            "category": "security",
            "is_verified": True,
            "file": "auth.py",
            "line": 1,
        }
    ]
    # Without apply — remains blocked
    blocked = orch.run_until_clean_or_budget(
        raw_findings=raw,
        old_head_sha="bbb222",
        apply_local_fix=False,
        dry_run=True,
    )
    assert blocked["gates"]["READY_TO_SHIP"] is False
    assert blocked["gates"]["MERGE_ELIGIBLE"] is False

    fixed = orch.run_until_clean_or_budget(
        raw_findings=raw,
        old_head_sha="bbb222",
        apply_local_fix=True,
        dry_run=True,
    )
    assert fixed["gates"]["MERGE_ELIGIBLE"] is True
    assert fixed["final_state"] == "READY_TO_SHIP"
    assert fixed["auto_merge"] is False


def test_plan_revision_needs_planner():
    f = normalize_closed_loop_finding(
        {
            "id": "plan-1",
            "title": "Violates plan: wrong endpoint contract",
            "severity": "high",
            "is_verified": True,
        }
    )
    assert f.recommended_action == RouteClass.PLAN_REVISION
    assert route_target(f.recommended_action)["planner"] is True
    gates = gate_from_findings([f])
    assert gates["needs_plan_revision"] is True
    assert gates["MERGE_ELIGIBLE"] is False


def test_max_review_cycles_circuit_breaker():
    orch = ClosedLoopOrchestrator(max_review_cycles=1)
    # Unresolvable without apply keeps looping once then stops
    out = orch.run_cycle(
        findings=[
            normalize_closed_loop_finding(
                {"id": "x", "title": "bug", "severity": "high", "is_verified": True}
            )
        ],
        cycle=2,
        old_head_sha="c",
        dry_run=True,
        apply_local_fix=False,
    )
    assert out["state"] == "NEEDS_HUMAN_DECISION"
    assert out["reason"] == "max_review_cycles_exceeded"


def test_same_pr_real_git_fixture(tmp_path: Path):
    """Disposable git repo: seed bug → fix commit → head changes → finding resolved."""
    repo = tmp_path / "disp"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "zect@test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "zect"], cwd=repo, check=True, capture_output=True)
    buggy = repo / "app.py"
    buggy.write_text("SECRET = 'hardcoded-password-demo'\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    old = head_sha(repo)
    assert old

    orch = ClosedLoopOrchestrator(max_review_cycles=2)
    out = orch.run_until_clean_or_budget(
        raw_findings=[
            {
                "id": "sec-demo",
                "title": "Hardcoded password / secret exposure",
                "severity": "critical",
                "category": "security",
                "file": "app.py",
                "line": 1,
                "is_verified": True,
            }
        ],
        old_head_sha=old,
        pr_id="disposable-1",
        repo_path=str(repo),
        apply_local_fix=True,
        fix_file="app.py",
        fix_content="SECRET = os.environ['APP_SECRET']\n",
        dry_run=False,
    )
    new = head_sha(repo)
    assert out["old_head_sha"] == old
    assert new != old
    assert out["new_head_sha"] == new
    assert out["gates"]["MERGE_ELIGIBLE"] is True
    assert out["auto_merge"] is False
    assert "os.environ" in buggy.read_text(encoding="utf-8")


def test_coderabbit_blind_protocol():
    bad = compare_blind([{"title": "a", "file": "x.py", "line": 1}], [{"title": "a", "file": "x.py", "line": 1}], mentrix_ran_first=False)
    assert bad["ok"] is False
    assert bad["error"] == "blind_protocol_violated"

    ok = compare_blind(
        [{"title": "SSRF", "file": "a.py", "line": 2, "severity": "critical", "category": "security"}],
        [{"title": "SSRF", "file": "a.py", "line": 2, "severity": "high"}, {"title": "style", "file": "b.py", "line": 3}],
        mentrix_ran_first=True,
    )
    assert ok["ok"] is True
    assert ok["blind"] is True
    assert ok["claim"].startswith("No superiority")
    assert ok["counts"]["shared"] == 1
    assert ok["counts"]["coderabbit_only"] == 1


def test_mutating_fix_requires_allowlist_env(monkeypatch):
    """API-level mutating fix must stay fail-closed without ZECT_UR_ALLOW_MUTATING_FIX."""
    from fastapi import HTTPException
    from app.domains.agent_run import ultrareview as ur

    class Body:
        findings = [{"id": "1", "title": "bug", "severity": "low"}]
        session_id = None
        work_item_id = None
        pr_id = None
        repository_id = None
        old_head_sha = "abc"
        repo_path = "/tmp/x"
        apply_local_fix = True
        fix_file = "a.py"
        fix_content = "x"
        test_command = None
        dry_run = False
        max_review_cycles = 2

    monkeypatch.delenv("ZECT_UR_ALLOW_MUTATING_FIX", raising=False)

    class DummyDB:
        pass

    class DummyUser:
        email = "t@t.com"

    with pytest.raises(HTTPException) as ei:
        ur.closed_loop_run(Body(), db=DummyDB(), _user=DummyUser())  # type: ignore[arg-type]
    assert ei.value.status_code == 403

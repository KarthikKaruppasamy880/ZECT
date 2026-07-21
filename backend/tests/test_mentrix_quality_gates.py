"""Unit tests for Mentrix anti-hallucination quality gates (no full app import required for helpers)."""

from app.services.quality.acceptance import verify_acceptance_criteria, verify_design_contract
from app.services.quality.error_classifier import classify_error
from app.services.quality.eval_harness import run_golden_suite, score_fixture
from app.services.quality.grounding import validate_grounding
from app.services.quality.truncation import brace_balance_ok, stitch_continuation, structural_ok


def test_brace_balance_and_structure():
    assert brace_balance_ok("def x():\n    return (1 + 2)\n")
    assert not brace_balance_ok("def x(:\n    return 1\n")
    assert structural_ok("def x():\n    return 1\n", "python")["ok"]
    assert not structural_ok("def x(:\n", "python")["ok"]


def test_stitch_continuation_avoids_repeat():
    base = "def hello():\n    print('hi"
    cont = "hi')\n    return 1\n"
    out = stitch_continuation(base, cont)
    assert "print('hi')" in out or "hi')" in out
    assert out.count("def hello") <= 1


def test_grounding_flags_invented_api():
    code = "class C:\n    def run(self):\n        return self.getUserByEmail('x')\n"
    res = validate_grounding(
        code,
        language="python",
        scout={"graph_hits": [{"name": "findByEmail"}]},
        blueprint={"prompt": "use findByEmail"},
    )
    assert res["ok"] is False
    assert "getUserByEmail" in res["invented"]


def test_grounding_allows_defined_methods():
    code = (
        "def mentrix_upgrade_placeholder():\n"
        "    return True\n"
        "def main():\n"
        "    return mentrix_upgrade_placeholder()\n"
    )
    res = validate_grounding(code, language="python", blueprint={"prompt": "Mentrix"})
    assert res["ok"] is True


def test_design_contract_and_acceptance():
    contract = {
        "required_files": ["a.py"],
        "required_mentions": ["Mentrix"],
        "acceptance_criteria": ["Mentrix upgrade placeholder present"],
    }
    code = "# Mentrix offline\ndef mentrix_upgrade_placeholder():\n    return True\n"
    assert verify_design_contract(contract=contract, files_written=["a.py"], generated_code=code)["ok"]
    assert verify_acceptance_criteria(criteria=contract["acceptance_criteria"], generated_code=code)["ok"]
    bad = verify_design_contract(contract=contract, files_written=[], generated_code="x")
    assert bad["ok"] is False


def test_error_classifier_categories():
    assert classify_error("brace imbalance truncated", gate="incomplete")["category"] == "SYNTAX"
    assert classify_error("invented_api getUserByEmail", gate="grounding")["category"] == "VALIDATION"
    sec = classify_error(
        "",
        findings=[{"severity": "critical", "category": "security", "message": "hardcoded secret"}],
    )
    assert sec["category"] == "SECURITY"
    assert sec["auto_waive"] is False
    assert sec["next_step"] == "await_human"


def test_eval_harness_golden_suite():
    suite = run_golden_suite()
    assert suite["fixtures"] >= 2
    assert suite["blocking"] is False
    ids = {r["id"]: r for r in suite["results"]}
    assert ids["upgrade_stub_ok"]["ok"] is True
    assert ids["invented_api_fail"]["ok"] is False


def test_gates_allow_approve_hard_rules():
    from app.services.quality.gates_policy import gates_allow_approve, gates_allow_create_pr

    gates = {
        "lint_ok": True,
        "sandbox_ready": False,
        "review_ok": False,
        "incomplete_ok": False,
        "api_eval_ok": True,
        "grounding_ok": True,
        "contract_ok": True,
        "acceptance_ok": True,
        "security_critical": False,
        "rejected_files": [],
    }
    ok, blockers = gates_allow_approve(gates, acknowledge=True)
    assert ok is False
    assert any("incomplete" in b for b in blockers)

    gates2 = {**gates, "incomplete_ok": True, "sandbox_ready": True, "review_ok": True}
    assert gates_allow_approve(gates2, acknowledge=False)[0] is True

    sec = {**gates2, "security_critical": True}
    assert gates_allow_approve(sec, acknowledge=True)[0] is False
    assert gates_allow_create_pr(sec)[0] is False

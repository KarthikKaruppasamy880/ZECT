"""Mentrix golden eval harness — non-blocking observability seed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.quality.acceptance import verify_acceptance_criteria, verify_design_contract
from app.services.quality.grounding import validate_grounding
from app.services.quality.incomplete_files import check_incomplete_files


def default_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "mentrix_golden"


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    code = fixture.get("generated_code") or ""
    files_written = fixture.get("files_written") or []
    contract = fixture.get("design_contract") or {}
    incomplete = check_incomplete_files(
        files_expected=fixture.get("files_expected") or files_written,
        files_written=files_written,
        generated_code=code,
    )
    grounding = validate_grounding(
        code,
        language=fixture.get("language") or "python",
        blueprint={"design_contract": contract, "prompt": fixture.get("blueprint_prompt") or ""},
        scout=fixture.get("scout") or {},
    )
    contract_ok = verify_design_contract(
        contract=contract,
        files_written=files_written,
        generated_code=code,
    )
    acceptance = verify_acceptance_criteria(
        criteria=contract.get("acceptance_criteria") or fixture.get("acceptance_criteria"),
        generated_code=code,
        plan_text=fixture.get("plan_text") or "",
    )
    checks = {
        "incomplete": incomplete.get("ok"),
        "grounding": grounding.get("ok"),
        "contract": contract_ok.get("ok"),
        "acceptance": acceptance.get("ok"),
    }
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "id": fixture.get("id") or "unnamed",
        "ok": passed == total,
        "score": int(100 * passed / total) if total else 0,
        "checks": checks,
        "details": {
            "incomplete": incomplete,
            "grounding": grounding,
            "contract": contract_ok,
            "acceptance": acceptance,
        },
        "blocking": False,
        "note": "Observability only — promote to merge gate after signal is trusted",
    }


def run_golden_suite(fixtures_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(fixtures_dir) if fixtures_dir else default_fixtures_dir()
    results = []
    if root.is_dir():
        for path in sorted(root.glob("*.json")):
            results.append(score_fixture(load_fixture(path)))
    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "fixtures": len(results),
        "passed": ok_count,
        "failed": len(results) - ok_count,
        "pass_rate": round(ok_count / len(results), 2) if results else None,
        "results": results,
        "blocking": False,
    }

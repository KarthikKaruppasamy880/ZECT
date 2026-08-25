"""Ultra Review for Present product READY closure diff."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
load_dotenv(BACKEND / ".env", override=True)
sys.path.insert(0, str(BACKEND))

from app.services.phases.review_phase_svc import run_ultra_review  # noqa: E402

FILES = [
    "backend/app/services/pptx_parse.py",
    "backend/scripts/present_product_fidelity_proof.py",
    "backend/scripts/present_cold_restart_gate.py",
    "backend/tests/fixes_and_phases/test_pptx_parse.py",
    "frontend/e2e/present-product-ready-acceptance.spec.ts",
    "frontend/e2e/present-product-ready-electron.spec.ts",
    "frontend/e2e/present-product-ready-gates.spec.ts",
    "frontend/e2e/fixtures/make_zinnia_rail_deck.py",
    "ZECT_PRESENT_PRODUCT_FINAL_ACCEPTANCE.md",
]


def main() -> int:
    diff = subprocess.check_output(["git", "diff", "origin/develop...HEAD", "--", *FILES], cwd=str(REPO))
    blob = diff.decode("utf-8", errors="replace")[:80000]
    out = run_ultra_review(
        blob or "# no diff",
        language="python",
        goal=(
            "Present product READY closure: pptx media parse limit, acceptance harness only, "
            "no architecture changes, no secrets, flag Critical/High only."
        ),
    )
    findings = [
        {"severity": row.get("severity"), "message": str(row.get("message") or "")[:300]}
        for row in list(out.get("findings") or [])
        if isinstance(row, dict)
    ]
    critical = [f for f in findings if str(f.get("severity") or "").lower() in {"critical", "high"}]
    payload = {
        "passed": out.get("passed"),
        "score": out.get("score") or out.get("quality_score"),
        "critical_high_count": len(critical),
        "findings": findings[:25],
    }
    dest = REPO / "test-results" / "present-product-ready" / "ultra-review.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("passed") and not critical else 1


if __name__ == "__main__":
    raise SystemExit(main())

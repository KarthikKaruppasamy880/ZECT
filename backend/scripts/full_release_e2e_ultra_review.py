"""Mentrix Ultra Review of Tranche H full-release E2E diff."""

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
    "frontend/e2e/full-release-e2e-production.spec.ts",
    "frontend/e2e/full-release-e2e-electron.spec.ts",
    "frontend/e2e/helpers/releaseJourney.ts",
    "frontend/package.json",
    "backend/tests/test_full_release_e2e_inventory.py",
    "ZECT_FULL_RELEASE_E2E_ACCEPTANCE.md",
    "ZECT_PRODUCTION_GRADE_IMPLEMENTATION_MATRIX.md",
    "ZECT_PRODUCTION_GRADE_FINAL_ACCEPTANCE.md",
]

MAX_DIFF = 240_000


def main() -> int:
    diff = subprocess.check_output(
        ["git", "diff", "origin/develop...HEAD", "--", *FILES],
        cwd=str(REPO),
    )
    blob = diff.decode("utf-8", errors="replace")
    if not blob.strip():
        diff = subprocess.check_output(["git", "diff", "HEAD", "--", *FILES], cwd=str(REPO))
        blob = diff.decode("utf-8", errors="replace")
    if not blob.strip():
        print(json.dumps({"passed": False, "error": "empty_diff"}))
        return 1
    if len(blob) > MAX_DIFF:
        print(json.dumps({"passed": False, "error": "diff_truncated", "bytes": len(blob)}))
        return 1
    out = run_ultra_review(
        blob,
        language="typescript",
        goal=(
            "Tranche H full-release E2E: one coherent browser journey and one Electron "
            "journey (shell load is not PASS). skip ≠ PASS for Electron/externals. "
            "No auto-merge. Do not start Tranche I / S8C / Graphify."
        ),
    )
    payload = {
        "passed": out.get("passed"),
        "offline": out.get("offline"),
        "score": out.get("score") or out.get("quality_score"),
        "critical_findings": out.get("critical_findings"),
        "model": out.get("model"),
        "summary": str(out.get("summary") or "")[:800],
    }
    print(
        json.dumps(
            {
                "passed": payload["passed"],
                "score": payload["score"],
                "critical": payload["critical_findings"],
                "model": payload["model"],
            }
        )
    )
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

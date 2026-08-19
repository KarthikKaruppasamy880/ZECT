"""Mentrix Ultra Review of next-phases integration diff."""

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
    "scripts/zect_stack.py",
    "backend/tests/test_zect_stack_control.py",
    "backend/tests/test_next_phases_integrated_spine.py",
    "backend/scripts/next_phases_live_proof.py",
    "frontend/e2e/mentrix-companion.spec.ts",
    "ZECT_CANONICAL_ARCHITECTURE.md",
    "ZECT_NEXT_PHASES_INTEGRATED_ACCEPTANCE.md",
    "ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md",
    "ZECT_RELEASE_PROFILE_ACCEPTANCE.md",
    "ZECT_PRODUCTION_GRADE_IMPLEMENTATION_MATRIX.md",
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
        language="markdown",
        goal=(
            "Next-phases integration after #170-#172. Graphify must remain the Lattice "
            "GraphifySnapshot adapter — no second RAG. zect.ps1 must resolve npm on Windows, "
            "load backend .env without logging values, and set Vite to :8020 not CI :8000. "
            "Presenton/Voicebox/PowerPoint/NSIS/GitHub/Jira/Camunda must stay BLOCKED_EXTERNAL "
            "or OPTIONAL_UNAVAILABLE when absent. Connect Voice e2e must not click a disabled "
            "button. No auto-merge. Do not award live Presenton Generate PASS."
        ),
    )
    print(
        json.dumps(
            {
                "passed": out.get("passed"),
                "score": out.get("score") or out.get("quality_score"),
                "critical": out.get("critical_findings"),
                "model": out.get("model"),
            }
        )
    )
    return 0 if out.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

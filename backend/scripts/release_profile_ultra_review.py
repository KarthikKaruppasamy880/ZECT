"""Mentrix Ultra Review of release-profile reconciliation diff."""

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
    ".github/workflows/ci.yml",
    "frontend/package.json",
    "frontend/e2e/full-release-e2e-electron.spec.ts",
    "backend/tests/test_release_profile_inventory.py",
    "backend/tests/test_final_release_audit_inventory.py",
    "ZECT_PRODUCTION_GRADE_FINAL_ACCEPTANCE.md",
    "ZECT_PRODUCTION_GRADE_IMPLEMENTATION_MATRIX.md",
    "ZECT_PRODUCTION_GRADE_BLOCKER_REGISTER.md",
    "ZECT_RELEASE_PROFILE_ACCEPTANCE.md",
    "ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md",
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
        language="yaml",
        goal=(
            "Release-profile reconciliation only. ZECT_CORE must not be blocked by optional "
            "GitHub/Jira/Camunda/Presenton/Voicebox. PostgreSQL is mandatory only for "
            "server_postgres; desktop_sqlite is Core. Windows CI Electron job must fail if "
            "electron.exe is missing (skip ≠ PASS). No Graphify, no zect.ps1, no auto-merge."
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

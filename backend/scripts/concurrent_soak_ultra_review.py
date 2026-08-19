"""Mentrix Ultra Review of concurrent soak/isolation/native Quality diff."""

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
    "backend/app/infrastructure/perf_thresholds.py",
    "backend/app/services/coding_engine/lifecycle.py",
    "backend/app/services/coding_engine/mentrix_agent_tools.py",
    "backend/tests/test_concurrent_soak_isolation_production.py",
    "backend/tests/test_performance_reliability_production.py",
    "frontend/e2e/concurrent-isolation-production.spec.ts",
    "frontend/package.json",
    "backend/scripts/concurrent_soak_ultra_review.py",
    "ZECT_CONCURRENT_SOAK_ISOLATION_ACCEPTANCE.md",
    "ZECT_PERFORMANCE_RELIABILITY_ACCEPTANCE.md",
    "ZECT_CANONICAL_ARCHITECTURE.md",
    "ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md",
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
        untracked = []
        for rel in FILES:
            p = REPO / rel
            tracked = subprocess.call(
                ["git", "ls-files", "--error-unmatch", rel],
                cwd=str(REPO),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if p.is_file() and tracked != 0:
                untracked.append(
                    f"--- a/{rel}\n+++ b/{rel}\n" + p.read_text(encoding="utf-8", errors="replace")[:8000]
                )
        blob = diff.decode("utf-8", errors="replace") + "\n".join(untracked)
    if not blob.strip():
        print(json.dumps({"passed": False, "error": "empty_diff"}))
        return 1
    if len(blob) > MAX_DIFF:
        print(json.dumps({"passed": False, "error": "diff_truncated", "bytes": len(blob)}))
        return 1
    out = run_ultra_review(
        blob,
        language="python",
        goal=(
            "Overlapping-thread isolation, Companion concurrent soak, native Present Quality "
            "generate (not Presenton), runner terminal isolation and cleanup, resource return "
            "to baseline. Thresholds declared first. skip ≠ PASS for unset externals. No auto-merge."
        ),
    )
    payload = {
        "passed": out.get("passed"),
        "offline": out.get("offline"),
        "score": out.get("score") or out.get("quality_score"),
        "critical_findings": out.get("critical_findings"),
        "model": out.get("model"),
        "summary": str(out.get("summary") or "")[:800],
        "findings": [
            {"severity": row.get("severity"), "message": str(row.get("message") or "")[:300]}
            for row in list(out.get("findings") or [])
            if isinstance(row, dict)
        ][:20],
    }
    dest = REPO / "test-results" / "concurrent-soak-isolation" / "ultra-review.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
    return 0 if payload.get("passed") and not payload.get("critical_findings") else 1


if __name__ == "__main__":
    raise SystemExit(main())

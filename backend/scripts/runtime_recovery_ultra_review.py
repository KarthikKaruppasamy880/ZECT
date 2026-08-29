"""Mentrix Ultra Review of runtime recovery diff. Does not print secrets."""

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
    "backend/app/services/coding_engine/lifecycle.py",
    "backend/app/domains/workspace/coding_agent.py",
    "backend/tests/test_runtime_recovery_production.py",
    "electron/service-lifecycle.js",
    "frontend/e2e/runtime-recovery-production.spec.ts",
    "frontend/e2e/runtime-recovery-electron.spec.ts",
]


def main() -> int:
    diff = subprocess.check_output(["git", "diff", "--", *FILES], cwd=str(REPO))
    blob = diff.decode("utf-8", errors="replace")[:60000]
    out = run_ultra_review(
        blob or "# no staged diff",
        language="python",
        goal=(
            "Runtime recovery: coding-agent missions must survive process restart via durable JSON, "
            "mission ids cannot traverse, corrupt files fail closed, sidecar must not start when API "
            "already listens, no secrets, no auto-merge, NSIS clean-machine remains BLOCKED_EXTERNAL."
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
            {
                "severity": row.get("severity"),
                "message": str(row.get("message") or "")[:300],
            }
            for row in list(out.get("findings") or [])
            if isinstance(row, dict)
        ][:20],
    }
    dest = REPO / "test-results" / "runtime-recovery-production" / "ultra-review.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": payload["passed"],
                "offline": payload["offline"],
                "critical_findings": payload["critical_findings"],
                "score": payload["score"],
                "model": payload["model"],
                "finding_count": len(payload["findings"]),
            }
        )
    )
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

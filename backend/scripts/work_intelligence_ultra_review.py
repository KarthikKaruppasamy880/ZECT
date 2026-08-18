"""Mentrix Ultra Review of Work intelligence production diff. Does not print secrets."""

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
    "backend/app/domains/work_items/router.py",
    "backend/app/services/mentrix/companion_scope.py",
    "backend/app/services/lattice/indexer.py",
    "backend/app/domains/agent_run/mentrix.py",
    "backend/tests/test_work_intelligence_production.py",
    "frontend/src/pages/WorkItems.tsx",
    "frontend/src/components/WorkItemDetailPanel.tsx",
    "frontend/src/pages/MentrixFabric.tsx",
    "frontend/e2e/work-intelligence-production.spec.ts",
]


def main() -> int:
    diff = subprocess.check_output(["git", "diff", "--", *FILES], cwd=str(REPO))
    blob = diff.decode("utf-8", errors="replace")[:60000]
    out = run_ultra_review(
        blob or "# no staged diff",
        language="python",
        goal=(
            "WorkItems/Processes/Lattice production: fixture isolation, EvidenceVerifier gate, "
            "honest BLOCKED_EXTERNAL for unset Jira/Camunda, per-root Lattice no leakage, "
            "no auto-merge, no Graphify, no secrets."
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
    dest = REPO / "test-results" / "work-intelligence-production" / "ultra-review.json"
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

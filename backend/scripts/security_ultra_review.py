"""Mentrix Ultra Review of Security production diff. Does not print secrets."""

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
    "backend/app/infrastructure/allowed_paths.py",
    "backend/app/services/mentrix/permission_broker.py",
    "backend/tests/test_security_production.py",
    "backend/tests/fixes_and_phases/test_allowed_paths.py",
    "frontend/src/pages/Permissions.tsx",
    "frontend/src/pages/SecurityIncidents.tsx",
    "frontend/e2e/security-production.spec.ts",
    "frontend/e2e/security-electron.spec.ts",
]


def main() -> int:
    diff = subprocess.check_output(["git", "diff", "--", *FILES], cwd=str(REPO))
    blob = diff.decode("utf-8", errors="replace")[:60000]
    out = run_ultra_review(
        blob or "# no staged diff",
        language="python",
        goal=(
            "Security campaign: path jail must not use string prefix; git write always-confirm; "
            "cross-user isolation; SSRF fail-closed; secrets redacted; unauthorized push BLOCKED_EXTERNAL; "
            "no auto-merge; no exploit PoCs; honest OAuth/Voicebox BLOCKED_EXTERNAL."
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
    dest = REPO / "test-results" / "security-production" / "ultra-review.json"
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

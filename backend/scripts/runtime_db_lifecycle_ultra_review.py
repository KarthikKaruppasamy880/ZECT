"""Mentrix Ultra Review of runtime/database lifecycle diff. Does not print secrets."""

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
    "backend/app/infrastructure/database.py",
    "backend/app/infrastructure/db_url.py",
    "backend/alembic/env.py",
    "backend/alembic/versions/f1a6c7d8e9b0_orm_catchup_create_all.py",
    "backend/app/main.py",
    "backend/app/services/system_health.py",
    "backend/app/services/desktop_readiness.py",
    "backend/tests/test_runtime_db_lifecycle_production.py",
    "electron/resources/backend/zect_api_entry.py",
    "electron/resources/backend/run-api.ps1",
    "frontend/src/pages/SystemHealth.tsx",
    "frontend/e2e/runtime-recovery-production.spec.ts",
]

MAX_DIFF = 120_000


def main() -> int:
    diff = subprocess.check_output(
        ["git", "diff", "origin/develop...HEAD", "--", *FILES],
        cwd=str(REPO),
    )
    blob = diff.decode("utf-8", errors="replace")
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
            "Runtime DB lifecycle: desktop_sqlite is the supported packaged store via create_all; "
            "server_postgres must use Alembic upgrade heads, fail closed with no SQLite fallback, "
            "no secrets in healthz, no auto-merge. Do not treat sqlite as defective because Postgres exists."
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
    dest = REPO / "test-results" / "runtime-db-lifecycle" / "ultra-review.json"
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

"""Mentrix Ultra Review of S7.5/S7.6 production diff. Does not print secrets."""

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
    "backend/app/domains/agent_run/mentrix.py",
    "backend/app/services/mentrix/presentation/blocks.py",
    "backend/app/services/mentrix/presentation/native_provider.py",
    "backend/app/services/mentrix/presentation/plan.py",
    "backend/app/services/mentrix/presentation/planner.py",
    "backend/app/services/mentrix/presentation/provider.py",
    "backend/app/services/mentrix/presentation/renderer.py",
    "backend/app/services/mentrix/presentation/visual.py",
    "backend/app/services/mentrix/presentation/visual_planner.py",
    "backend/app/services/phases/llm_phase.py",
    "frontend/src/components/PresentDeckPanel.tsx",
    "frontend/src/lib/api.ts",
]


def main() -> int:
    diff = subprocess.check_output(
        ["git", "diff", "--", *FILES],
        cwd=str(REPO),
    )
    extra = []
    vp = REPO / "backend/app/services/mentrix/presentation/visual_planner.py"
    if vp.is_file():
        extra.append("\n# NEW FILE visual_planner.py\n" + vp.read_text(encoding="utf-8")[:12000])
    blob = diff.decode("utf-8", errors="replace") + "\n".join(extra)
    blob = blob[:60000]
    out = run_ultra_review(
        blob,
        language="python",
        goal=(
            "S7.5/S7.6 native presentation quality: Model Gateway planner, VisualPlanner, "
            "Fast-Basic labeling, Presenton remains default, no Presenton calls on native success, "
            "untrusted context wrapping. Flag Critical/Major security or default-switch regressions."
        ),
    )
    findings = []
    for row in list(out.get("findings") or []):
        if not isinstance(row, dict):
            continue
        findings.append(
            {
                "severity": row.get("severity"),
                "category": row.get("category"),
                "message": str(row.get("message") or "")[:400],
                "suggestion": str(row.get("suggestion") or "")[:200],
            }
        )
    payload = {
        "brand": out.get("brand"),
        "passed": out.get("passed"),
        "score": out.get("score") or out.get("quality_score"),
        "critical_findings": out.get("critical_findings"),
        "offline": out.get("offline"),
        "model": out.get("model"),
        "summary": str(out.get("summary") or "")[:800],
        "findings": findings[:40],
    }
    dest = REPO / "test-results" / "s7-parity" / "ultra-review-s76.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": payload["passed"],
                "offline": payload["offline"],
                "critical_findings": payload["critical_findings"],
                "finding_count": len(findings),
                "score": payload["score"],
            }
        )
    )
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

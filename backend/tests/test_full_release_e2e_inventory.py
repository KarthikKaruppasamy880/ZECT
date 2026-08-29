"""Frozen product-suite inventory for Tranche H full-release E2E.

CI `npm run test:e2e:core` is the headed run. This test only proves the frozen
files still exist so a suite cannot disappear silently. Skip ≠ PASS.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

FROZEN_CORE_SPECS = [
    "frontend/e2e/mentrix-smoke.spec.ts",
    "frontend/e2e/labs-productivity-spine.spec.ts",
    "frontend/e2e/mentrix-companion.spec.ts",
    "frontend/e2e/mentrix-incident.spec.ts",
    "frontend/e2e/agent-workspace-shell.spec.ts",
    "frontend/e2e/phase-completion-smoke.spec.ts",
    "frontend/e2e/core-ux-hygiene.spec.ts",
    "frontend/e2e/workspace-multi-root.spec.ts",
    "frontend/e2e/companion-production-missions.spec.ts",
    "frontend/e2e/coding-agent-production.spec.ts",
    "frontend/e2e/present-voice-production.spec.ts",
    "frontend/e2e/work-intelligence-production.spec.ts",
    "frontend/e2e/security-production.spec.ts",
    "frontend/e2e/runtime-recovery-production.spec.ts",
    "frontend/e2e/concurrent-isolation-production.spec.ts",
    "frontend/e2e/ux-accessibility-production.spec.ts",
    "frontend/e2e/full-release-e2e-production.spec.ts",
]

ELECTRON_SPECS_SKIP_NEQ_PASS = [
    "frontend/e2e/full-release-e2e-electron.spec.ts",
    "frontend/e2e/ux-accessibility-electron.spec.ts",
    "frontend/e2e/workspace-electron-restore.spec.ts",
    "frontend/e2e/coding-agent-electron.spec.ts",
    "frontend/e2e/present-voice-electron.spec.ts",
    "frontend/e2e/companion-electron-missions.spec.ts",
    "frontend/e2e/runtime-recovery-electron.spec.ts",
]


def test_frozen_core_specs_exist() -> None:
    missing = [rel for rel in FROZEN_CORE_SPECS if not (REPO / rel).is_file()]
    assert missing == [], missing


def test_electron_release_specs_exist() -> None:
    missing = [rel for rel in ELECTRON_SPECS_SKIP_NEQ_PASS if not (REPO / rel).is_file()]
    assert missing == [], missing

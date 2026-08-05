# Phase 4 Execution Plan — PR Review Platform

Companion to `Upgrade.md` Phase 4. Staged PRs to `develop`. **Phase 9 remains ON HOLD.**

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Canonical `ReviewFinding` schema + fingerprint + normalize | **Done** (#95) |
| B | Diff-line validation + dedupe by fingerprint + rank | **Done** (#95) |
| C | Deterministic checks → findings (`source=deterministic`): secrets/TODO + rules | **This PR** |
| D | Approval gate before GitHub post + coding-engine fix-run hook for accepted findings | Pending |

## Stage C files

- `backend/app/domains/pr_review/deterministic_checks.py` — secrets/TODO/rules collectors
- `backend/app/review_service.py` — merge deterministic findings in PR + snippet review
- `backend/app/services/phases/review_phase_svc.py` — shared credential regex
- `backend/tests/fixes_and_phases/test_deterministic_checks.py`

## Deferred

- Structured lint (eslint/ruff) issue parsing — `run_lint` returns stderr only today.

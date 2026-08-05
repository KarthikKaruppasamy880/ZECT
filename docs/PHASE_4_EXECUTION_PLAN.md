# Phase 4 Execution Plan — PR Review Platform

Companion to `Upgrade.md` Phase 4. Staged PRs to `develop`. **Phase 9 remains ON HOLD.**

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Canonical `ReviewFinding` schema (Upgrade.md fields) + fingerprint + normalize LLM/DB/rules; ultrareview GET returns spec shape | **This PR** |
| B | Diff-line validation + dedupe by fingerprint + rank by severity/confidence | Pending |
| C | Deterministic checks → findings (`source=deterministic`): lint/secrets/rules | Pending |
| D | Approval gate before GitHub post + coding-engine fix-run hook for accepted findings | Pending |

## Stage A files

- `backend/app/domains/pr_review/finding_schema.py` — canonical Upgrade.md shape + fingerprint/normalizers
- `backend/app/review_service.py` — persist via normalizer (line_end filled)
- `backend/app/domains/agent_run/ultrareview.py` — `FindingOut = ReviewFindingSpec`
- `backend/tests/fixes_and_phases/test_review_finding_schema.py`
- `docs/PHASE_4_EXECUTION_PLAN.md`, `docs/ROADMAP.md`

## Guardrails

- Do not auto-post speculative findings to GitHub.
- Do not invent DB migrations that break existing SQLite installs in Stage A (fingerprint computed at read time).

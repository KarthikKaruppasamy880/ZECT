# Phase 4 Execution Plan — PR Review Platform

Companion to `Upgrade.md` Phase 4. Staged PRs to `develop`. **Phase 9 remains ON HOLD.**

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Canonical `ReviewFinding` schema (Upgrade.md fields) + fingerprint + normalize LLM/DB/rules; ultrareview GET returns spec shape | **Done** (re-landed on develop via Stage B PR — #94 had merged only into the Stage E branch) |
| B | Diff-line validation + dedupe by fingerprint + rank by severity/confidence | **This PR** |
| C | Deterministic checks → findings (`source=deterministic`): lint/secrets/rules | Pending |
| D | Approval gate before GitHub post + coding-engine fix-run hook for accepted findings | Pending |

## Stage B files

- `backend/app/domains/pr_review/finding_pipeline.py` — validate / dedupe / rank / `finalize_pr_findings`
- `backend/app/review_service.py` — PR reviews run `finalize_pr_findings` before persist
- `backend/tests/fixes_and_phases/test_finding_pipeline.py`
- Also includes Stage A cherry-pick onto `develop` (`finding_schema.py`, ultrareview wiring)

## Guardrails

- Do not auto-post speculative findings to GitHub.
- Invalidated findings (file/line not in diff) are kept but ranked last — not silently dropped.

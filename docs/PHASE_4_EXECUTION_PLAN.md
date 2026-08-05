# Phase 4 Execution Plan — PR Review Platform

Companion to `Upgrade.md` Phase 4. Staged PRs to `develop`. **Phase 9 remains ON HOLD.**

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Canonical `ReviewFinding` schema + fingerprint + normalize | **Done** (#95) |
| B | Diff-line validation + dedupe by fingerprint + rank | **Done** (#95) |
| C | Deterministic checks → findings (`source=deterministic`): secrets/TODO + rules | **Done** (#96) |
| D | Approval gate before GitHub post + Mentrix/coding-engine fix-run for accepted findings | **Done** (this PR) |

## Stage D files

- `backend/app/domains/pr_review/post_approval.py` — in-memory approve store, fix goal builder, GitHub post helper (reuses `github_service`)
- `backend/app/domains/agent_run/ultrareview.py` — `approve-post` / `approval` / `post-github` / `start-fix-run`
- `backend/app/domains/pr_review/code_review.py` — `auto_comment` default false; `/pr/inline` and auto-fix-loop reject `auto_comment=true` with 403
- `frontend/src/pages/CodeReview.tsx` — review → select → Approve → Post / Start Fix Run
- `backend/tests/fixes_and_phases/test_post_approval.py`

## Notes

- Approvals are in-memory (cleared on process restart); human must re-approve before post/fix.
- Single manual comment via `/api/review/pr/comment` remains ungated.
- Webhook configs with `auto_comment=True` in DB can still post on webhook events.

## Deferred

- Structured lint (eslint/ruff) issue parsing — `run_lint` returns stderr only today.

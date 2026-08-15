# ZECT Data Hygiene Acceptance

**Date:** 2026-08-14  
**Gate:** provenance isolation is implemented; this operator DB was cleaned with keep-cleanup (`keep_ids=[7]` ZOAS Eval). 62 leftover E2E/onboarding rows deleted. `GET /api/projects?exclude_fixtures=0` and `exclude_fixtures=1` both return only ZOAS Eval. Audit: 0 proven_test, 0 name_candidates, 1 authorized.

## Defect

Normal Projects UI listed Phase6 / E2E / onboarding / demo names because isolation was **name regex only**. That is not a security rule and must not be used to delete data.

## Permanent model

| Entity | Fields | Meaning |
|--------|--------|---------|
| `Project` | `provenance` (`user` \| `test`), `test_run_id` | Test rows require both `test` and a non-empty `test_run_id` |
| `WorkItem` | `is_test_fixture`, `test_run_id` | Do **not** overload `source` (user\|jira\|camunda\|github) |

Schema is added via `_add_missing_columns()` (no Alembic required).

## List behavior

- Frontend `getProjects()` sends `exclude_fixtures=1`.
- Hidden when `exclude_fixtures=1`:
  - **proven test:** `provenance=test` **and** `test_run_id` set;
  - **name candidates** (default): Phase6 / `zect-r36-` / demo names, **display filter only**.
- `exclude_name_candidates=0` proves a user-provenance project named `Phase6 Onboard` is **visible**. Name is not a security rule.
- WorkItems default list excludes `is_test_fixture=true`. `include_fixtures=true` for debug.

## APIs (not delete-by-name)

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/api/projects/fixtures/audit` | `proven_test`, `name_candidates`, `authorized` |
| POST | `/api/projects/fixtures/tag` | Tag **by id** with `test_run_id` |
| POST | `/api/projects/fixtures/cleanup` | Default `dry_run=true`. Live delete **only** proven test projects (+ their WorkItems) |

Creating `provenance=test` without `test_run_id` outside pytest is 403.

## Keep-cleanup (operator, explicit ids)

| Method | Path | Behavior |
|--------|------|----------|
| POST | `/api/projects/fixtures/keep-cleanup` | Body `{ keep_ids, dry_run }`. Refuses empty `keep_ids`. Dry-run returns `would_keep` / `would_delete` / `count`. Live delete removes WorkItems then Projects (repos cascade); nullable `project_id` FKs are nulled first. **Never delete-by-name.** |

This operator machine: keep only the audited **ZOAS Eval** id. All other project rows (hidden E2E leftovers included) are deleted via keep-cleanup after a dry-run confirmation. E2E `POST /api/projects` now sends `provenance=test` + `test_run_id` so leftover user rows do not return.

## Cleanup procedure (human)

1. `GET /api/projects/fixtures/audit`  
2. Confirm candidate ids (owner, repos, timestamps).  
3. `POST /api/projects/fixtures/tag` with those ids.  
4. `POST /api/projects/fixtures/cleanup` with `dry_run=true`.  
5. Repeat with `dry_run=false` only after review.

Desired normal account: authorized projects only (ZECT/ZOAS **if** audit confirms). Never hardcode those names as an allowlist.

## Tests

`backend/tests/fixes_and_phases/test_fixture_isolation.py` and `test_p0_present_quality.py` keep-cleanup cases:

- name matcher is candidate-only;
- proven test hidden from `exclude_fixtures=1`;
- user project visible;
- cleanup does not delete `provenance=user`;
- keep-cleanup never deletes `keep_ids`; empty `keep_ids` is 400;
- fixture WorkItems hidden unless `include_fixtures=true`.

## UI

Projects page banner when audit still has name-candidates. Copy tells operators to review audit, not to wildcard-delete.

# P0 Post-Build Regression Audit

**Date:** 2026-08-09 (updated after whitespace fix)
**Branch:** `develop` @ `77ec26f`
**Scope:** Mentrix P0 Consolidation
**P1:** Not started

## Verdict

| Overall | Status |
|---------|--------|
| **Acceptance recommendation** | **ACCEPTABLE WITH KNOWN PRE-EXISTING TEST INFRASTRUCTURE ISSUES** |
| Fully repository-green | **No** â€” auth fixture + Vitest/Playwright overlap remain |
| P0 functional regression (modified modules) | **PASS** |
| Clean repo whitespace (`git diff --check`) | **PASS** (fixed) |
| Broad authed HTTP suites | **BLOCKED** by pre-existing auth fixture mismatch (not a P0 regression) |

P0 product work is acceptable to proceed toward commit/review **without** claiming full CI green. Explicit backlog items (Â§7) are deferred to P1 / test-infrastructure â€” **P1 not started**.

---

## Note on â€œ74 changed filesâ€

Git dirty working tree for this audit is **~42 porcelain paths**, not 74.

The earlier session figure **74** referred to **FastAPI registered routes** after `register_routers()`, not a 74-file P0 diff.

---

## 1. Categorized changed-file summary

### Summary counts (git porcelain)

| Category | Count | Notes |
|----------|------:|-------|
| Modified tracked | 5 | P0 production backend |
| New backend production | 15 | `domains/work_items` + `services/work_items` |
| New tests | 1 | `test_mentrix_p0_consolidation.py` |
| Architecture / plan docs | 15+ | 8 `docs/architecture/ZECT_*.md` + `.zect/plans/...` (+ audit) |
| Frontend production | 0 | No FE changes in P0 |
| Configuration | 0 | No package/CI/env config in P0 set |
| Deleted | 0 | â€” |
| Unrelated / hygiene risk | 6 | Must **not** be committed with P0 |
| Generated `__pycache__` | ignored | Covered by `.gitignore` |

### Modified files (tracked)

| Path | Role |
|------|------|
| `backend/app/api/register.py` | Register WorkItem + Mentrix Developer routers |
| `backend/app/models.py` | `WorkItem` + `WorkItemEvent` |
| `backend/app/services/coding_engine/mentrix_native_build.py` | Fail-closed mock ban + deterministic smoke (**EOF whitespace fixed**) |
| `backend/app/services/mentrix/companion.py` | Developer Ask/Plan/Agent tools |
| `backend/app/services/phases/llm_phase.py` | `openai_compat` + fallback policy |

### Unrelated / do **not** include in P0 commit

| Path | Why |
|------|-----|
| `backend/data/desktop_bridge_queue.json` | Runtime queue data |
| `backend/data/mentrix-brain/.gitkeep` | Runtime scaffolding |
| `companion-voice-online.png` | Unrelated screenshot |
| `.cursor/mcp.json.example` | Cursor tooling |
| `prompts/ZECT_CURSOR_MASTER_ARCHITECTURE_PROMPT.md.md` | Plan input (optional docs) |
| `prompts/ZECT_P0_PLAN_REVISION_REQUIREMENTS.md` | Plan input (optional docs) |

---

## 2. Verification gates (post whitespace fix)

| Gate | Result | Evidence |
|------|--------|----------|
| G1 Changed-file inventory | **PASS** | Categorized above |
| G2 Unrelated isolation | **PASS** | Runtime/png/cursor/prompts flagged |
| G3 Secrets / `.env` / caches | **PASS** | No secrets in P0 porcelain; `__pycache__` ignored |
| G4 `git status` inspect | **PASS** | On `develop` |
| G5 `git diff --check` | **PASS** | exit 0 after EOF blank-line removal |
| G6 P0 consolidation suite | **PASS** | **18 passed** (re-run) |
| G7 Product-spine / Fabric / Coding Agent | **PASS** | **35 passed** (spine+fabric+coding+cost_tree) |
| G8 Broad non-auth `fixes_and_phases` | **PASS** | **580 passed** (`--ignore=test_phase10_stage_b.py`) |
| G9 Broad authed HTTP suites | **BLOCKED** | Pre-existing `auth_token` / `.env override=True` (backlog Â§7) |
| G10 Frontend `tsc` / `build` | **PASS** | Prior audit; no FE P0 changes since |
| G11 Frontend Vitest unit | **PASS** | Prior: 57 passed with `--exclude e2e` |
| G12 Default `npm test` | **FAIL** (pre-existing) | Vitest/Playwright overlap (backlog Â§7) |
| G13 No new P0 regression after whitespace fix | **PASS** | G6â€“G8 all green |
| G14 P1 not started | **PASS** | Backlog only |

---

## 3. Re-verification run (2026-08-09 whitespace fix)

| Suite | Result |
|-------|--------|
| `git diff --check HEAD` | **PASS** (exit 0) |
| `test_mentrix_p0_consolidation.py` | **18 passed** |
| `test_product_spine` + `test_fabric_camunda` + `test_mentrix_coding_agent` + `test_cost_tree_wins` | **35 passed** |
| `tests/fixes_and_phases/` ignore `test_phase10_stage_b.py` | **580 passed** |

Logs: `artifacts/p0_reverify_p0_suite.txt`, `artifacts/p0_reverify_spine.txt`, `artifacts/p0_reverify_fixes.txt`.

**Change made:** remove trailing blank line at EOF in `mentrix_native_build.py` only. No functional edits.

---

## 4. Pre-existing failures vs P0 regressions

### Pre-existing (explicit backlog â€” not fixed in this step)

1. **Auth fixture / env override** â€” `conftest` sets `ZECT_USERNAME`/`ZECT_PASSWORD`; `main.py` `load_dotenv(..., override=True)` wins â†’ `auth_token` setup `401 Invalid credentials`. Affects authed HTTP tests (`test_mentrix_platform`, `test_phase10_stage_b`, some coding-engine HTTP tests).
2. **Frontend Vitest collecting Playwright e2e** â€” default `npm test` fails on `e2e/*.spec.ts` `test.describe()`; unit path works with `--exclude "**/e2e/**"`.

### P0-introduced (resolved)

1. ~~`git diff --check` EOF blank line~~ â†’ **fixed**.

### P0 regressions after fix

**None observed** in G6â€“G8.

---

## 5. Final gate rollup

| Gate group | Status |
|------------|--------|
| Inventory + unrelated isolation | **PASS** |
| Secrets / runtime exclusion | **PASS** |
| Whitespace (`diff --check`) | **PASS** |
| P0 + product-spine / Fabric / Coding Agent | **PASS** |
| Broad non-auth `fixes_and_phases` | **PASS** |
| Broad authed regression green | **BLOCKED** (pre-existing infra) |
| Frontend build/typecheck/unit | **PASS** |
| Default `npm test` | **FAIL** (pre-existing infra) |
| **P0 acceptance** | **ACCEPTABLE WITH KNOWN PRE-EXISTING TEST INFRASTRUCTURE ISSUES** |
| Fully repository-green | **No** |

---

## 6. Commit hygiene (still required before commit)

- [ ] Do **not** add unrelated runtime/png/cursor files listed in Â§1
- [ ] Optional: version `prompts/*` only if intentional
- [ ] Confirm no `.env` / secrets staged

---

## 7. Explicit P1 / test-infrastructure backlog (do not start P1 yet)

| ID | Item | Priority |
|----|------|----------|
| TI-001 | Fix pytest auth fixture vs `load_dotenv(override=True)` so `auth_token` works with local `.env` | P1 / test-infra |
| TI-002 | Stop Vitest from collecting Playwright `e2e/**` (exclude in vitest config or `npm test` script) | P1 / test-infra |

These are **not** P0 product gaps and must not block the P0 â€œacceptable with known issuesâ€ status above.

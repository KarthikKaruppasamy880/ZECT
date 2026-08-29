# Phase 2: Diff-Based Apply — IMPLEMENTATION COMPLETE

**Status:** ✅ **DONE**
**Date Completed:** July 24, 2026
**Files Created:** 2
**Files Modified:** 5
**Tests Added:** 7
**Scope:** Second of four phases toward best-in-class code generation. See `PHASE_1_BUILD_INTELLIGENCE_COMPLETION.md` for Phase 1.

---

## What Was Fixed

Build's `write_to_repo` path (used by `agent_mode.py`'s automated orchestrator) overwrote the target file's *entire* content from scratch with zero review — no diff, no read of what was already there. Confirmed as-designed via `target.write_text(code, encoding="utf-8")` with no prior read.

### Design decision: purely additive, zero regression

Rather than changing `write_to_repo`'s existing immediate-write behavior (which `agent_mode.py`'s fully-automated Ask→Plan→Build→Review→Deploy loop depends on), this phase adds a **parallel, opt-in review path**:

- Every generation call now computes a diff against the existing file (if one exists) — pure information added to the response, `write_to_repo`'s behavior is byte-for-byte unchanged.
- A new `POST /api/build/apply` endpoint is the only way code reaches disk when `write_to_repo` wasn't set — generate, review the diff, then explicitly apply.

Confirmed via test (`test_write_to_repo_still_writes_regardless_of_diff`) that `write_to_repo=True` still writes immediately exactly as before, with the diff now also present in the response as a bonus, not a gate.

---

## Files Created

- `backend/tests/test_build_diff_apply.py` — 7 tests.
- `docs/PHASE_2_DIFF_BASED_APPLY_COMPLETION.md` (this file).

## Files Modified

- `backend/app/services/phases/build_phase_svc.py` — `_generate_core()` reads the existing file (if any) and computes a diff via the existing `diff_viewer._compute_diff()`, attached to the result as `file_existed`/`diff`. `write_to_repo`'s write itself is unchanged.
- `backend/app/routers/build_phase.py` — same diff computation in the actual `/build/generate` HTTP endpoint (the one the page hits — confirmed in Phase 1 this is a separate code path from the service wrapper, so both needed the change again). New `POST /api/build/apply` endpoint: writes to disk only after review, path-traversal guarded (resolves the target against the repo root and rejects anything that escapes it), audit-logged via the existing `log_audit` from Fix #3.
- `frontend/src/lib/api.ts` — `buildGenerate()` gained an optional `repo_id` param; new `buildApply()`.
- `frontend/src/pages/BuildPhase.tsx` — added a "Repo ID" input; when the response includes a diff, renders the **existing** `DiffViewer.tsx` component (zero new UI component built) with Apply/Reject actions. Apply calls the new endpoint; Reject just clears the result.

---

## Why This Reused Everything It Could

- **`diff_viewer.py`'s `_compute_diff()`** — already computes unified + side-by-side diffs + stats via `difflib`. Its output shape (`unified`, `side_by_side`, `stats`) maps directly onto `DiffViewer.tsx`'s props (just a casing difference, `side_by_side` → `sideBySide`) — confirmed by reading both before writing any code, so no adapter layer was needed.
- **`DiffViewer.tsx`** — already renders side-by-side/unified toggle, stats, everything Build needed. Zero new frontend component.
- **`log_audit` (Fix #3's RBAC module)** — reused for the new write action instead of inventing a separate audit path.

Net new code was small: the diff-computation wiring in two backend files, one new endpoint, one new API client function, and UI wiring in the existing page.

---

## Security Note

`POST /api/build/apply` accepts a `file_path` from the client and writes to `{repo.local_path}/{file_path}` — path traversal (`../../etc/passwd`) is blocked by resolving the target path and rejecting anything outside the repo root, tested explicitly (`test_rejects_path_traversal`).

---

## Tests

```bash
cd backend
python -m pytest tests/test_build_diff_apply.py -v
# 7 tests: diff computed when file exists / absent when new, write_to_repo
# behavior unchanged (no regression), apply endpoint writes + audits correctly,
# path-traversal rejected, uncloned-repo rejected, legitimate nested paths allowed.
```

Full regression: **165 passed**, zero new failures (fixed two Phase 1 tests whose mock `db` needed an explicit `None` return for the new unconditional repo lookup Phase 2 added — a test-fixture staleness issue from the control-flow change, not a production bug; production code already guards with `if repo and repo.local_path`).

---

## What's Next (Phases 3-4, not started)

3. Multi-file coordinated planning — extend `run_build_from_plan`'s step parsing to carry a file-set per step, generate coordinated changes across files in one call instead of independent per-file calls with no awareness of each other.
4. Iterate-and-verify loop with checkpointing — reuse `sandbox.py`'s real test execution, `rules_engine.py`'s real rule evaluation, and `git_ops.py`'s real commit/PR integration for revertible checkpoints after apply.

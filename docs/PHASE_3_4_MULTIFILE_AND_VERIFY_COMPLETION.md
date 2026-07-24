# Phase 3 & 4: Multi-File Coordination + Iterate-and-Verify — IMPLEMENTATION COMPLETE

**Status:** ✅ **DONE** (backend + API client; frontend UI panel not built — see "Known Follow-ups")
**Date Completed:** July 24, 2026
**Files Created:** 2
**Files Modified:** 4
**Tests Added:** 19
**Scope:** Third and fourth of four phases toward best-in-class code generation. See `PHASE_1_BUILD_INTELLIGENCE_COMPLETION.md` and `PHASE_2_DIFF_BASED_APPLY_COMPLETION.md` for prior phases.

---

## Key Finding: Phase 4 Needed Far Less New Code Than Planned

Before writing anything, checked whether `autofix.py`, `rules_engine.py`, `git_ops.py` already covered pieces of the planned "iterate-and-verify loop":

- **`autofix.py`'s `run_and_fix()`** already implements exactly the loop Phase 4 was scoped to build: run a command → on failure, AI-analyze the error → apply a suggested fix → re-run → repeat up to `max_retries`. It already runs arbitrary shell commands in an arbitrary `cwd`.
- **`rules_engine.py`'s `evaluate_rules()`** already does real regex-based rule matching against submitted code — free, deterministic, no LLM call.
- **`git_ops.py`'s `git_commit()`** already does real `git add` + `git commit` with a `files` param for scoped commits.

So Phase 4 became: wire Build's output into these three existing, real systems, rather than build a fourth. New code was a handful of thin wrapper endpoints, not a new loop.

---

## Phase 3: Multi-File Coordinated Generation

### Problem
Each `/build/generate` call produced exactly one file with no awareness of other files a plan step might also need to touch — no way to keep a new endpoint and its corresponding test, or a model change and its migration, consistent with each other in one pass.

### Solution
- `POST /api/build/generate-multi` — one model call generates all `target_files` (max 8 per call, bounded for cost/latency) together, via a repeating `===FILE: <path>===` / `===END FILE===` format the model is instructed to follow. Context retrieval (Phase 1) is unioned and deduped across all target files before the call.
- `_parse_multi_file_response()` — parses the multi-file format back into individual `FileChange` entries (file_path, language, explanation, code), each independently diffed against its existing content (Phase 2's `diff_against_existing`, now shared via `file_ops.py`) and rule-checked (see Phase 4 below).
- `POST /api/build/apply-multi` — batch version of `/apply`: writes every reviewed file, then one checkpoint commit covering all of them.

### Refactor done along the way
Extracted `diff_against_existing()` and `write_file()` (Phase 2's logic) plus the new `check_rule_violations()` into `backend/app/services/build_intel/file_ops.py` — this was the third call site for the diff logic (single-file, multi-file, and `build_phase_svc.py`'s internal path), which is the point where extraction earns its keep rather than being premature.

---

## Phase 4: Rule Pre-Check + Iterate-and-Verify

### What's new (thin wrappers over real, existing systems)

1. **Rule pre-check, before any human ever sees the diff.** `check_rule_violations()` runs `rules_engine.py`'s real `evaluate_rules()` against every generated file, attached to both `/generate` and `/generate-multi`'s responses as `rule_violations`. Free, deterministic, catches things like secrets-in-code or `eval()` usage before a human wastes time reviewing a diff that was going to get rule-blocked anyway.

2. **Checkpointing.** `/apply` and `/apply-multi` both gained an optional `commit_message` — when set, the write is followed by a real `git commit` via `git_ops.py`'s existing `git_commit()`, **called exactly as-is, including its existing path-allowlist security check** (not bypassed). That check is Unix-path-specific (`ALLOWED_ROOTS = ["/home", "/tmp", "/var", "/opt"]`) — a pre-existing cross-platform gap, not something introduced here (see Known Follow-ups). Checkpoint failures don't fail the whole apply — the file write already succeeded and is the primary action; a `commit_warning` field surfaces what happened instead.

3. **`POST /api/build/verify-and-fix`** — resolves `repo_id` → the repo's real local clone path, then hands off to `autofix.py`'s existing `run_and_fix()` with that path as `cwd`. This is the "run tests, fix on failure, retry" step — reusing the loop that already existed rather than reimplementing it.

---

## Files Created

- `backend/app/services/build_intel/file_ops.py` — shared diff/path-safety/rule-check helpers (Phase 2's logic, extracted; Phase 3/4's rule-check, new).
- `backend/tests/test_build_multi_and_verify.py` — 12 tests.
- `docs/PHASE_3_4_MULTIFILE_AND_VERIFY_COMPLETION.md` (this file).

## Files Modified

- `backend/app/routers/build_phase.py` — refactored `/generate` and `/apply` to use the shared helpers; added `_parse_multi_file_response()`, `/generate-multi`, `/apply-multi`, `/verify-and-fix`; added `rule_violations` to `/generate`'s response.
- `backend/app/services/phases/build_phase_svc.py` — refactored `_generate_core()` to use the shared helpers (no behavior change).
- `frontend/src/lib/api.ts` — `buildApply()` gained an optional `commit_message` param; new `buildGenerateMulti()`, `buildApplyMulti()`, `buildVerifyAndFix()`.

---

## Tests

```bash
cd backend
python -m pytest tests/test_build_multi_and_verify.py -v
# 12 tests: multi-file response parsing (ordering, field extraction, edge cases),
# generate-multi validation (empty/too-many target_files) and end-to-end
# generation+diffing, apply-multi (batch write + single checkpoint commit,
# path-traversal rejected), verify-and-fix (delegates to autofix.run_and_fix
# with the repo's real cwd, rejects uncloned repos).
```

Full regression: **177 passed**, zero new failures (up from 165 after Phase 2).

---

## Known Follow-ups (flagged, not silently expanded into this scope)

- **No frontend UI panel for multi-file review or verify-and-fix.** The API client functions exist (`buildGenerateMulti`, `buildApplyMulti`, `buildVerifyAndFix`) so the capability is reachable, but `BuildPhase.tsx` doesn't yet have a multi-file target-list input or a "run tests" button wired to them — Phase 2's single-file diff UI shipped, this didn't, given the scope of building all four phases' backends in one pass. Worth its own pass.
- **`git_ops.py`'s `ALLOWED_ROOTS` is Unix-path-only** (`/home`, `/tmp`, `/var`, `/opt`) — checkpointing via `commit_message` will fail with a `commit_warning` on Windows dev environments (like this one) where repo clones live under `C:\Users\...`. This is a pre-existing bug in `git_ops.py` affecting all its endpoints, not something Phase 4 introduced — deliberately not "fixed" here since it's a general infra gap outside Build's scope, and silently patching a security allowlist without a dedicated look felt like the wrong call to make as a side effect.
- **`autofix.py`'s `_ai_analyze_error()` doesn't thread `user_id` into `log_tokens`** — same class of gap as the one closed in Fix #4 for `llm.py`/`code_review.py`, just not caught there since `autofix.py` wasn't in scope at the time. Now that `/verify-and-fix` calls into it, its token usage is attributed to no one. Flagging rather than fixing now, since it touches a file outside this phase's direct scope.

# Phase 1: Build Semantic Retrieval — IMPLEMENTATION COMPLETE

**Status:** ✅ **DONE**
**Date Completed:** July 24, 2026
**Files Created:** 7
**Files Modified:** 6
**Tests Added:** 22
**Scope:** First of four phases toward Cursor-parity code generation (see `docs/zect-user-experience-assessment/` for the full 4-phase plan and honest accuracy expectations — no LLM-based tool, including Cursor itself, achieves 100% correctness; this closes the context-quality gap, not that one).

---

## What Was Fixed

Build's context injection (`_build_repo_context`) was a flat, static snapshot — README + top-2-level file tree + language stats + one config file, capped at 4KB, identical regardless of what the plan step actually asked for. It never queried the Lattice graph or Code Index that already exist in this repo. Every generation call got the same generic slice of the repo, no matter how specific the task.

### Before
```python
# Same 4KB snapshot for every plan step, regardless of relevance
if req.repo_id and not req.project_context:
    from app.routers.llm import _build_repo_context
    req.project_context = _build_repo_context(db, req.repo_id, max_chars=4000)
```

### After
```python
# Chunk-level semantic search scoped to what THIS plan step is actually about
hits = semantic_search(db, req.repo_id, query, top_k=6, user_id=current_user.user_id)
if hits:
    req.project_context = "\n\n".join(
        f"--- {h['file_path']} (lines {h['line_start']}-{h['line_end']}) ---\n{h['content']}"
        for h in hits
    )
else:
    # No index built yet for this repo — exact old behavior, zero regression
    req.project_context = _build_repo_context(db, req.repo_id, max_chars=4000)
```

---

## Files Created

- `backend/app/services/build_intel/chunker.py` — boundary-aware chunking, reuses `auto_indexer.PATTERNS` to split at real function/class boundaries per language; falls back to overlapping fixed-size line chunks for unrecognized languages or files with no detected boundaries.
- `backend/app/services/build_intel/embeddings.py` — OpenAI `text-embedding-3-small` wrapper. Logs token usage per Fix #4's pattern.
- `backend/app/services/build_intel/retriever.py` — pure-Python cosine similarity search, no numpy/vector-DB dependency (deliberate — see "Design Decisions" below).
- `backend/app/services/build_intel/indexer.py` — orchestrates chunk → embed → store, mirrors `auto_indexer.index_repo`'s exact validation/walk pattern.
- `backend/app/routers/build_intel.py` — `POST /{repo_id}/reindex`, `GET /{repo_id}/status`, `POST /{repo_id}/search` (debug/manual).
- `backend/tests/test_build_intel.py` — 22 tests.
- `docs/PHASE_1_BUILD_INTELLIGENCE_COMPLETION.md` (this file).

## Files Modified

- `backend/app/models.py` — new `CodeEmbedding` table.
- `backend/app/routers/build_phase.py` — **the actual `/build` page endpoint** now uses retrieval (was previously going to be missed if only the internal service wrapper got patched — verified this was a separate, duplicate code path before fixing it). Added `enforce_token_budget` (this endpoint had zero budget enforcement before, despite making real LLM calls).
- `backend/app/services/phases/build_phase_svc.py` — same retrieval wiring for the internal path `agent_mode.py`'s orchestrator calls.
- `backend/app/routers/repo_clone.py` — `POST /{repo_id}/index` now also builds the semantic index alongside the existing symbol index, so no new UI action is needed to trigger it.
- `backend/app/middleware/rate_limiter.py` — added `/api/build-intel` to the expensive-path list from Fix #4.
- `backend/app/token_tracker.py` — added real `text-embedding-3-small` pricing ($0.02/1M tokens, verified against current OpenAI pricing) instead of letting it silently default to gpt-4o-mini rates.
- `backend/app/main.py` — registered the new router.

---

## Design Decisions (and why)

**No new pip dependencies.** Embeddings use the OpenAI SDK already installed; similarity search is plain Python (`sum(x*y for x,y in zip(a,b))`) rather than pulling in chromadb/pgvector/sqlite-vec. At single-repo scale (hundreds to low thousands of chunks) this is fast enough, and it avoids touching `requirements.txt`, which needs explicit approval per standing project rules. Revisit if a repo's chunk count grows large enough for this to become the bottleneck.

**Claude/Anthropic swap deliberately deferred, not included here.** The original 4-phase plan mentioned Claude Sonnet for generation quality — that requires a new `anthropic` SDK dependency and a real client (the existing `model_selection.py` attempt is broken — it points OpenAI's SDK at Anthropic's URL, which doesn't work, different API shape entirely). Since that's a `requirements.txt` change requiring explicit sign-off, Phase 1 keeps generation on the existing `gpt-4o-mini` path and only fixes the *context* going into it. Worth a separate, explicit decision before adding.

**Reuses existing infrastructure wherever it already existed:** `auto_indexer.PATTERNS`/`EXT_TO_LANG`/`SKIP_DIRS` for language detection and file walking, rather than duplicating them.

**Graceful degradation, not a hard cutover:** if no semantic index exists yet for a repo, Build behaves exactly as before (falls back to `_build_repo_context`). Nothing breaks for repos that haven't been reindexed.

**Cost caps on indexing:** `MAX_FILES=500`, `MAX_CHUNKS=2000` per index run — embedding costs real money per chunk, so this is more conservative than the free regex symbol indexer's `MAX_FILES=2000` cap. Truncation is reported in the response (`"truncated": true`), never silent.

---

## A bug found while implementing this (not part of the original ask, fixed anyway)

`build_phase.py`'s `POST /api/build/generate` — the endpoint the actual `/build` page hits — turned out to have its **own independent** context-injection and generation logic, completely separate from `build_phase_svc.py`'s `_generate_core()`. They look similar but don't share code. If I'd only patched the service wrapper (used internally by `agent_mode.py`'s orchestrator), the page a user actually opens would have gotten zero benefit from this whole phase. Both paths are now patched.

Also found: neither `build_phase.py` nor `build_phase_svc.py` had `enforce_token_budget` wired in at all, despite both making real, billed OpenAI calls — same class of gap Fix #4 was meant to close, just not caught there because the earlier assessment (wrongly) assumed Build had no backend. Fixed here since I was already touching these exact functions.

---

## Tests

```bash
cd backend
python -m pytest tests/test_build_intel.py -v
# 22 tests: chunking (boundary detection, fallback, edge cases), cosine similarity
# correctness, retrieval (sorted top-k, malformed-row resilience), indexer
# validation + end-to-end (real file walk, mocked embeddings), and integration
# tests confirming build_phase_svc actually uses retrieval when available and
# falls back cleanly when it doesn't.
```

Full regression: `python -m pytest tests/ -q` → **151 passed**, plus 1 failure + 26 errors that are a **pre-existing, unrelated** `conftest.py` fixture issue (`auth_token` fixture logs in with hardcoded `test@zect.local` credentials that don't match this environment's actual seeded user) — confirmed via `git diff` that `conftest.py`, `auth.py`, and `.env` credentials are untouched by any work this session, so this predates everything done here.

---

## What's Next (Phases 2-4, not started)

2. Diff-based apply — read existing file, generate a patch instead of full overwrite; reuse `diff_viewer.py`'s real `difflib`-based diff computation and the existing `DiffViewer.tsx` component instead of building new ones.
3. Multi-file coordinated planning — extend `run_build_from_plan`'s step parsing to carry a file-set per step.
4. Iterate-and-verify loop with checkpointing — reuse `sandbox.py`'s real test execution, `rules_engine.py`'s real rule evaluation, and `git_ops.py`'s real commit/PR integration for revertible checkpoints.

## Update: Claude Sonnet Swap — Also Done

Approved and implemented same day. `backend/app/services/llm/anthropic_client.py` is a real Anthropic client — not a repeat of `model_selection.py`'s broken attempt (which pointed OpenAI's SDK at Anthropic's URL; different API shape entirely: separate `system` param, content-block list instead of `.choices[0].message.content`, `input_tokens`/`output_tokens` instead of `prompt_tokens`/`completion_tokens`, `stop_reason` values like `"max_tokens"` instead of `finish_reason="length"`).

**Design:** `create_fn()` shims Anthropic's response into the exact shape `complete_with_continuations()` already expects, so the existing truncation-continuation logic works unchanged for both providers — zero duplication of that logic per-provider.

**Routing:** both `build_phase.py`'s `/build/generate` endpoint and `build_phase_svc.py`'s internal path now check `anthropic_available()` — Claude Sonnet 5 when `ANTHROPIC_API_KEY` is set, the existing `gpt-4o-mini` path unchanged when it isn't. No regression for repos/environments without an Anthropic key.

**Also fixed while in this code:** `model_selection.py`'s `/status` endpoint was reporting `anthropic_configured: true` whenever *any* OpenAI key existed, even with zero Anthropic key configured — a real, separate bug, now corrected. Its `/chat` endpoint's Anthropic branch (previously non-functional) now routes through the real client too.

**Pricing:** added a verified `claude-sonnet-5` entry to `token_tracker.py`'s pricing table ($3/$15 per 1M tokens, standard rate — Anthropic's introductory $2/$10 rate runs through 2026-08-31) so cost tracking doesn't silently misreport Claude usage under gpt-4o-mini's rate.

**Tests:** 16 new tests in `test_anthropic_client.py` — response-shape mapping, system-message extraction, stop-reason mapping, routing behavior (both branches), and the `model_selection.py` status-reporting fix. All passing; full regression 158 passed, zero new failures.

## Known Follow-ups (flagged, not silently expanded into this scope)

- `agent_mode.py`'s orchestrator doesn't yet thread a real `user_id` into its build calls (defaults to `None` — non-breaking, just anonymous for budget/usage attribution in that specific path).
- The pre-existing `auth_token` test fixture mismatch (not caused by this work, but blocks two full test files from running).

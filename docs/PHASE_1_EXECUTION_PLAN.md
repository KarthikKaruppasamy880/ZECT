# Phase 1 Execution Plan — Backend Domain/Adapter Split + Frontend AgentWorkspace

Companion to `ROADMAP.md` / `TARGET_ARCHITECTURE.md`. This is the file-by-file
plan those docs say must exist before any Phase 1 code changes. Written for
execution in Cursor (or any tool), one stage at a time — each stage below is
sized to be its own PR, independently mergeable, independently revertible.

**Do not skip the verification checkpoint at the end of a stage.** Import-path
breakage across ~58 routers and ~35 services is the primary risk of this
refactor — moving a file is easy, missing one of its importers is how a
production endpoint 500s silently.

## Target layout (from TARGET_ARCHITECTURE.md — not re-decided here)

```
backend/app/
  api/              # thin FastAPI routers, no business logic
  domains/          # one module per domain
  adapters/         # provider adapters (already exists as services/mcp/adapters/*
                     # and services/llm/* — mostly a move, not new code)
  infrastructure/   # db, auth, config, vault (mostly app/core/* + database.py)
  workers/          # background job execution (new — currently one inline
                     # function in routers/mentrix.py)
```

## Stage 0 — Prep (no moves yet)

- Resolve the roadmap's flagged duplicate-concept check *before* assigning
  domain boundaries, so we don't carve a permanent domain slot for something
  that's about to be deleted:
  - Skill Library vs. Skills Engine — **already resolved**, merged in
    `refactor/merge-skill-library-into-skills-engine`.
  - Memory System (`memory.py`) vs. Mentrix Notes (`services/mentrix/notes.py`)
    — not yet checked. 30 min task: read both, decide keep-one-or-both, before
    Stage 4.
  - Knowledge Base (`knowledge_base.py`) vs. Lattice Graph (`lattice.py`) vs.
    Docs Center — not yet checked. Same treatment, before Stage 2.
- Confirm test baseline: `cd backend && python -m pytest -q` should show the
  same pass count as today (516 passed / 1 pre-existing unrelated failure —
  `test_mentrix_upgrade_pipeline_phases`, missing Lattice-index test fixture,
  tracked separately) before Stage 1 starts, so any new failure after a move
  is attributable to that move.

## Stage 1 — `infrastructure/` (lowest risk, do first)

Move, updating imports at every call site:

| Current | Target |
|---|---|
| `app/database.py` | `app/infrastructure/database.py` |
| `app/core/auth/*` (`rbac.py`, `deps.py`, `oidc.py`, `session_store.py`) | `app/infrastructure/auth/*` |
| `app/core/allowed_paths.py` | `app/infrastructure/allowed_paths.py` |
| `app/core/budget.py` | `app/infrastructure/budget.py` |

These are imported by nearly every router (`from app.database import get_db`
appears ~50+ times) — highest import-count, but mechanically simple (pure
path rename, no logic change). Good first stage precisely because a broken
import here is immediately obvious (app fails to start) rather than a subtle
runtime gap.

**Verification:** `python -m pytest -q` full pass count unchanged; app boots
(`uvicorn app.main:app` starts without ImportError).

## Stage 2 — `adapters/` (second-lowest risk)

Already-adapter-shaped code, mostly a directory move:

| Current | Target |
|---|---|
| `app/services/mcp/adapters/*` (github, jira, slack, confluence, datadog, email_adapter, filesystem, playwright_adapter) | `app/adapters/*` |
| `app/services/llm/anthropic_client.py`, `openai_tts.py`, `chatterbox_client.py`, `response_cache.py` | `app/adapters/llm/*` |
| `app/services/llm/elevenlabs_client.py`, `voicebox_client.py` | **Delete**, not move — already flagged dead in the Phase 0 backlog (voicebox_client.py already removed in the merged fix; elevenlabs_client.py still needs removal) |

**Verification:** `python -m pytest -q` unchanged; `services/mcp/hub.py`'s
`execute_tool()` dispatch still resolves every adapter (its own test file
covers this — run it explicitly).

## Stage 3 — `workers/` (new directory, small diff, real behavior extraction)

- Extract `_run_mentrix_in_background()` out of `app/routers/mentrix.py`
  (added in the background-task fix, currently merged to `develop`) into
  `app/workers/mentrix_worker.py`. Router keeps only the `BackgroundTasks.add_task(...)`
  call site.
- This is the concrete seed of the `workers/` directory the audit flagged as
  "missing entirely" — one file, not a redesign.

**Verification:** the three Mentrix deliver/upgrade/recovery tests in
`test_mentrix_platform.py` still pass with the same pre-existing exception
(Lattice fixture gap).

## Stage 4 — `domains/` (largest stage — do last, and possibly split further)

Proposed router → domain mapping (first pass; refine while moving, per the
roadmap's own "inspect → plan → implement" rule — treat this table as a
starting point, not a contract):

| Domain | Routers |
|---|---|
| Project | `projects.py`, `analytics.py`, `export_share.py`, `token_controls.py`, `generated_outputs.py` |
| Repository | `repo_analysis.py`, `repo_browser.py`, `repo_clone.py`, `file_explorer.py`, `file_watcher.py`, `git_ops.py`, `code_index.py`, `lattice.py`, `knowledge_base.py`, `build_intel.py` |
| Agent Run | `mentrix.py`, `orchestration.py`, `agent_mode.py`, `build_phase.py`, `review_phase.py`, `deploy_phase.py`, `ultrareview.py`, `context_management.py`, `model_selection.py`, `llm.py` |
| Workspace | `diff_viewer.py`, `autofix.py`, `rules_engine.py`, `app_runner.py`, `sandbox.py` |
| PR Review | `code_review.py`, `github.py` |
| Integration | `jira_integration.py`, `slack_integration.py`, `confluence_integration.py`, `datadog_integration.py`, `email_integration.py`, `mcp.py`, `ci_monitor.py`, `ci_remediation.py` |
| Personal Agent | `memory.py`, `skills_engine.py`, `playbooks.py`, `scheduler.py`, `transfer.py`, `data_flywheel.py`, `data_layer.py`, `dream_engine.py`, `conversations.py`, `session_insights.py`, `persistent_sessions.py`, `user_sessions.py` |
| Voice | `voice_clone.py`, `realtime.py` |
| Permissions | `permissions.py`, `secrets_manager.py`, `auth.py` |
| Audit | `audit_trail.py` |
| Security Incident | none currently — **on hold**, don't create the directory yet |

`settings.py` doesn't map cleanly to one domain (touches project + global
config) — decide at move time, don't block the stage on it.

Given the size (58 routers), **split Stage 4 into one PR per domain**, not
one PR for all ten. Suggested order: Audit (1 file, trivial) → Voice (2
files) → PR Review (2 files) → Permissions (3 files) → Workspace (5 files) →
Repository (10 files) → Integration (8 files) → Personal Agent (12 files,
resolve Stage 0's Memory/Notes question first) → Agent Run (10 files, most
behaviorally sensitive — do last with the most test coverage already proven
stable from the smaller stages).

**Verification per domain PR:** full backend suite, plus a manual hit on
that domain's endpoints if any lack test coverage (check before moving —
some of these 58 routers may have thin/no dedicated test files; note the gap
rather than silently assuming coverage exists).

## Frontend — Unified AgentWorkspace

Current: 7 separate pages/routes for what the target architecture treats as
one Agent Run domain UI — `AskMode.tsx`, `PlanMode.tsx`, `BuildPhase.tsx`,
`ReviewPhase.tsx`, `DeployPhase.tsx`, `AgentMode.tsx`, `Mentrix.tsx` — each
with its own route in `App.tsx`, its own nav entry, and likely duplicated
polling/status/error-display logic against the same underlying `MentrixRun`.

**This is not a mechanical file move like the backend stages** — before any
code, decide the actual UX: single page with tabs per phase? A left-rail
step indicator with one content pane? Keep separate URLs (`/agent/:runId/build`)
or collapse to one (`/agent/:runId` with in-page phase switching)? That's a
product decision, not something to infer from existing file boundaries.

Recommended approach:
1. Inventory what's duplicated vs. genuinely phase-specific across the 7
   pages (e.g. is the polling loop copy-pasted 7 times, or already shared via
   a hook?) — a few hours of reading, produces the actual consolidation list.
2. Sketch the target single-workspace layout (wireframe-level, doesn't need
   to be pixel-perfect) and get sign-off on *that* before writing any
   component code — this is the step most likely to get redone if skipped.
3. Build the unified shell, migrate one phase's UI into it at a time behind
   the existing routes (so `/build` still works mid-migration), verify with
   the existing 32 frontend tests plus manual click-through per phase, then
   remove the old page + route only once its content lives in the new shell.
4. Update `Sidebar.tsx` nav last, once the unified route is the only one left.

Not scoped further here — step 1-2 above should happen as their own short
pass (research + a plan/mockup) before this doc's frontend section gets a
file list the way the backend stages already have one.

## What this doc deliberately does not cover

- Phase 2 (Coding-engine provider / sandboxed execution) — a different
  phase, not part of this restructure.
- The Agent Run state-machine reconciliation (`queued`/`provisioning`/
  `validating` states) noted in TARGET_ARCHITECTURE.md — real work, but
  additive behavior change, not a file-location change; scope separately.
- Resolving the Memory/Notes and Knowledge Base/Lattice duplicate-concept
  questions — flagged in Stage 0 as a prerequisite, not solved here.

# ZECT Product Acceptance

**Verdict: RELEASE_READY** (pending CI green + merge of PR #128 — update after merge)

Generated: 2026-08-09

## RELEASE_READY / BLOCKED

| Field | Value |
|-------|-------|
| Verdict | **RELEASE_READY** (core product acceptance met with executable evidence; malware/desktop deferred by design) |
| Gate | PR [#128](https://github.com/KarthikKaruppasamy880/ZECT/pull/128) → `develop` |

## Core flows

| Flow | Result | Evidence |
|------|--------|----------|
| WorkItem → PLAN → approve → Agent → verify → READY_TO_SHIP | **PASS** | `test_e2e_work_item_to_ready_to_ship` |
| Incomplete / LLM-only cannot READY_TO_SHIP | **PASS** | `test_evidence_verifier_rejects_llm_only`, `test_gate_statuses_require_evidence_allow_gate` (403 without `allow_gate`) |
| Resume / checkpoint fields | **PASS** | `test_checkpoint_types_and_resume_fields` + resume assert in E2E spine |
| Project Intelligence dual-read (Lattice/Blueprint/KB/Memory/Skills/Playbooks) | **PASS** | P1 suite `test_mentrix_p1_project_intelligence.py` |
| Context Used panel | **PASS** | mentrix-smoke Playwright + unit `contextUsed.test.ts` |
| Ultra Review 3-lane (no second LLM) | **PASS** | `test_ultrareview_three_lanes` |
| Fallback never silent cloud | **PASS** | `test_fallback_policies_never_ask_automatic`; default policy `never` |
| Fabric / close-loop dry_run | **PASS** | P1 `test_evidence_ready_to_ship_triggers_close_loop_dry_run` |

## Tests

| Suite | Result |
|-------|--------|
| Backend P0+P1+P2/P3+matrix | **40 passed** (`pytest` closeout set) |
| Spine/gates subset | **5 passed** (READY_TO_SHIP, evidence reject, fallback, gate 403, skills bi-sync) |
| Frontend unit (Vitest) | **60 passed** |
| Core Playwright (`npm run test:e2e:core`) | **33 passed** local |
| `git diff --check` | **clean** |
| Full Playwright (historical) | Not DoD; CI now runs **core** suite + `ZECT_PYTEST=1` |

## Local-model matrix

`claim_fully_local: false` (do not claim fully local)

| Surface | Status | Notes |
|---------|--------|-------|
| Ask | PARTIAL | openai_compat + fallback_policy; no live local gateway in this env |
| Plan | PARTIAL | same |
| Companion | PARTIAL | gateway path; no `resolve_model_route` enforcement |
| Agent/Coding | PARTIAL | deterministic smoke VERIFIED in pytest; live LLM needs gateway |
| ForgeLoop | PARTIAL | Ask/Plan local-capable; Build often cloud unless mentrix_native |
| Ultra Review | CLOUD_ONLY | LLM path; lane merge offline |
| Blueprint | PARTIAL | openai_compat + policy |
| Embeddings | CLOUD_ONLY | OpenAI embeddings only |

Env probe (dotenv): local_gateway=false, cloud_openai=true, fallback_policy=never.

## Skills sync

| Direction | Status |
|-----------|--------|
| FS → DB | **PASS** (`sync_filesystem_skills_to_db`) |
| DB → FS | **PASS** (`sync_db_skills_to_filesystem`) |
| Bidirectional | **PASS** (`POST /api/system/skills-fs/sync` default `bidirectional`; conflict: local DB wins) |
| Execution SoT | SkillDefinition DB |

## Remaining blockers

- None for core Mentrix consolidation release.
- Live local LLM gateway not configured in acceptance env → surfaces marked PARTIAL (not BLOCKED on product architecture).
- Full historical Playwright suite outside `test:e2e:core` may still flake (out of core DoD).

## Explicitly deferred product epics

1. **ZECT-native malware engine** (deep scanner / daemon rewrite) — SecurityScanner reads Security Agent findings only.
2. **Advanced Computer Mode / desktop automation** — readiness surface only; no rewrite.

## PR / merge status

| Item | Status |
|------|--------|
| Branch | `feat/mentrix-p3-deferred-closeout` |
| PR | https://github.com/KarthikKaruppasamy880/ZECT/pull/128 |
| Commits | P3 closeout + skills bi-sync + core e2e CI + nav/e2e fixes |
| Merge | Pending CI green on latest push — merge to `develop` when backend/frontend/e2e pass |

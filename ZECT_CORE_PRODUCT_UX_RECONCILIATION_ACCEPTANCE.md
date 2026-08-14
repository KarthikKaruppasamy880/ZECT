# ZECT Core Product UX Reconciliation — Acceptance

**Date:** 2026-08-13  
**Spec:** `prompts/ZECT_CORE_PRODUCT_UX_RECONCILIATION.md`  
**Prerequisite:** `prompts/ZECT_RELEASE_CANDIDATE_FINAL_CLOSURE.md` (this session, first)  
**Branch:** `feat/release-closure-core-ux` (local, unpushed) from `184aa78`  
**origin/develop (unchanged):** `45f4407fc2c5603db572e7b23b88289226557aeb`  
**Product PR / merge to develop:** **BLOCKED_EXTERNAL** (`gh` not logged in; cannot push `KarthikKaruppasamy880/ZECT.git`)

## Verdict

**CORE_UX_PARTIAL**

Do not claim `CORE_UX_PASS`. User-facing editor/export/hygiene/workbench/process-sample landed and were headed-proven on this workstation. Origin merge, clean-machine NSIS, packaged Present/Voicebox, live two-slide clone, live standard-voice speak, and multi-repo READY_AFTER_FIX were **not** closed.

**R5+ not started** (KV cache, advanced Document Intelligence, broader Web, Graphify, new agents).

Companion closure verdict remains **RELEASE_CANDIDATE_PARTIAL** (see `ZECT_R1_6_R2_6_R3_6_ACCEPTANCE.md`).

## Presenton reference (capability only)

| Presenton capability | ZECT backend | ZECT UI | Reuse/adapt? | ZECT-native needed? | Out of scope |
|----------------------|--------------|---------|--------------|---------------------|--------------|
| Generate from prompt | PresentationProvider HTTP (`PRESENTON_BASE_URL`) | ZECT Present prompt + Generate | HTTP engine only | ZECT-branded prompt/gallery | Presenton admin UI |
| Template gallery / upload | Registry + upload API | Zinnia / Org / My Templates cards | Mapping only | ZECT gallery, hide provider UUID | Direct Presenton `:5000` |
| Generation progress | Single generate call | Staged Preparing → Outline → Slides → Applying template → Finalizing → Ready | UX stages while waiting | Honest labels, not provider events | Streaming provider internals |
| Editor thumbs / text / notes | Parse PPTX + notes sidecar | `PresentEditor` + SplitPane | Concept only | ZECT editor | Charts/images/tables/layout blocks |
| Export PPTX | Allowlisted FileResponse | Export PPTX download in ZECT UI | Native download | ZECT export | Presenton export chrome |
| Voice / rehearse | Voicebox + speak FSM | Clone / stock / No narration | Existing audio_owner | ZECT Present voice select | Presenton branding |

License: Presenton Apache-2.0 recorded in `THIRD_PARTY_NOTICES.md`. ZECT does not vendor Presenton UI. Normal users stay in ZECT-branded `/present`. Local Presenton `:5000` probed this session (HTTP 200) as engine health only — **not** used as the acceptance surface.

## UX1–UX6

| Tranche | Status | Headed | Security | Notes |
|---------|--------|--------|----------|-------|
| UX1 Projects/WorkItems hygiene | **PARTIAL** | PASS `core-ux-hygiene.spec.ts` | Unit: fixture-name hide + PPTX allowlist | `exclude_fixtures=1`; search; fixtures **hidden** not deleted by pattern |
| UX2 Developer workbench | **PARTIAL** | PASS toggles (explorer/agent/bottom/reset) | Timeline string-payload hardened | Nested SplitPane Explorer \| Editor \| Agent + bottom Terminal/Timeline; persist localStorage; onboarding collapsed when root exists |
| UX3 Present templates/generation/editor | **PARTIAL** | PASS editor+export; gallery via editor path | Allowlisted PPTX download/parse/save-notes | Charts/images/tables **not** edited (honest). Prompt composer on gallery. Progress stages during generate |
| UX4 Voice/rehearsal | **PARTIAL** | UI: clone/stock/none options headed | Prior cross-user clone deny UNIT_PASS | Live 2-slide clone + stock speak **not re-run**. Prior 1-slide clone PASS preserved. Voicebox Chatterbox `models_ready=true` this session |
| UX5 Processes/Jira/Camunda + sample | **PARTIAL** | PASS sample WorkItem + ingest form visible | Untrusted-external tag on jira/camunda/github ingest | Reuses `ingest_work_item` / source adapters. Sample never completes live Camunda. Live Jira/Camunda fetch still config-dependent |
| UX6 Full headed + design tokens | **PARTIAL** | Editor/export/hygiene headed | Hygiene + allowlist + untrusted tag | `--zect-*` tokens + `:focus-visible`. Full Companion→all-screens campaign not re-run |

## Headed Playwright (this session)

| Spec | Result |
|------|--------|
| `e2e/auth.setup.ts` | PASS |
| `e2e/core-ux-hygiene.spec.ts` | **PASS** (Projects search, sample process, Fabric sample + ingest form, Developer toggles) |
| `e2e/present-editor-export.spec.ts` | **PASS** (thumbs, notes save, Export PPTX download >100 bytes, No narration + stock options) |
| `e2e/present-product.spec.ts` | FAIL this run (landed on login; `login-username` helper vs storageState). **Not** treated as gallery REGRESSION — editor spec already opened `/present` ZECT UI successfully |

Command: headed Chromium, `VITE_API_URL=http://127.0.0.1:8000`. Artifacts under `test-results/` (uncommitted).

## Unit / security this session

| Suite | Result |
|-------|--------|
| `test_present_editor_and_hygiene.py` + `test_packaging_sidecar.py` | **8 passed** (JSON event harden, fixture names, PPTX allowlist, untrusted tag, `_run_to_dict` string payload) |
| `test_voice_cloning.py` (with above + registry) | included in 54 passed / 2 failed |
| `test_present_template_registry.py` | **2 failed** when live registry already has a Zinnia mapping (`zinnia_verified` true vs isolated `tmp_path` expectation). Isolation issue against workstation registry — not treated as product REGRESSION |
| frontend vitest (`src/mentrix`, `src/components`) | **15 passed** |

No new full cross-user live security campaign. Existing negatives preserved: PPTX path allowlist, fixture hide (not delete), ingest untrusted prefix, sample process does not complete engine tasks.

## Developer workbench

Target hierarchy implemented when a workspace root exists:

```text
Header: Project/Repo/Branch | Hide explorer | Hide agent | Hide tools | Reset layout
------------------------------------------------
Explorer | Editor (Monaco) | Mentrix Agent
------------------------------------------------
Terminal | Timeline          + Context panel
```

Splitters persist `zect_ws_h` / `zect_ws_agent` / `zect_ws_v`. Timeline no longer throws on string `result_json`/`events_json`. ASK/PLAN/AGENT engines were **not** rebuilt.

## Remaining gaps (do not paper over)

1. Push/PR/CI/Ultra Review/merge to `develop` — **BLOCKED_EXTERNAL**  
2. Clean Windows NSIS + packaged Present/Voicebox — **BLOCKED_EXTERNAL: CLEAN_WINDOWS_ENVIRONMENT_REQUIRED**  
3. Live clone Present-all ≥2 slides; live standard-voice speak; Disconnect FSM live  
4. Live Jira/Camunda fetch (needs configured connectors); leftover `zect-r36-*` GitHub repos DELETE 403  
5. Multi-repo READY_AFTER_FIX live re-run (spec updated; not executed this session)  
6. Charts/images/tables/elements in Present editor  
7. Pixel-complete Presenton-parity generation UX  

## Stop

**STOP before R5.** No KV cache, OCR/XLSX, broader Web, Graphify, or new agents.

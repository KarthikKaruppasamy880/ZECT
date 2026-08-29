# ZECT Core Product UX Reconciliation — Acceptance

**Date:** 2026-08-14  
**Spec:** `prompts/ZECT_CORE_PRODUCT_UX_RECONCILIATION.md`  
**Closeout:** `prompts/ZECT_CURRENT_BRANCH_CLOSEOUT_BEFORE_SOVEREIGNTY.md`  
**Branch:** `develop`  
**local HEAD:** `98e19e64045543ea306d7e1ff003e9df9992d9ef`  
**origin/develop:** `98e19e64045543ea306d7e1ff003e9df9992d9ef`  
**match:** **YES**  
**PR:** [#150](https://github.com/KarthikKaruppasamy880/ZECT/pull/150) **MERGED** (`Merge pull request #150 from KarthikKaruppasamy880/feat/release-closure-core-ux`)  
**PR head that merged:** `717f009ae3dcdc389989c27286c70ed81fd8b8f3`  
**Sovereignty plan:** **NOT STARTED**

## Verdict

**CORE_UX_PARTIAL** (merged and post-merge smoke healthy)

Do not claim `CORE_UX_PASS`. User-facing editor/export/hygiene/workbench/process-sample/voice **selectors** are on `develop` and were headed-proven after the merge. Clean-machine NSIS, packaged Present/Voicebox, live two-slide clone, live standard-voice speak, Disconnect live, and multi-repo READY_AFTER_FIX remain **PARTIAL / BLOCKED_EXTERNAL**.

Companion closure verdict remains **RELEASE_CANDIDATE_PARTIAL** (see `ZECT_R1_6_R2_6_R3_6_ACCEPTANCE.md`).

Post-merge sovereignty gate: **READY_FOR_SOVEREIGNTY_AUDIT** — `branch=develop`, `local==origin/develop`, Core UX PR merged, post-merge smoke green, no unresolved branch-introduced Critical/Major. **R5+ not started.**

## Presenton reference (capability only)

| Presenton capability | ZECT backend | ZECT UI | Reuse/adapt? | ZECT-native needed? | Out of scope |
|----------------------|--------------|---------|--------------|---------------------|--------------|
| Generate from prompt | PresentationProvider HTTP (`PRESENTON_BASE_URL`) | ZECT Present prompt + Generate | HTTP engine only | ZECT-branded prompt/gallery | Presenton admin UI |
| Template gallery / upload | Registry + upload API | Zinnia / Org / My Templates cards | Mapping only | ZECT gallery, hide provider UUID | Direct Presenton `:5000` |
| Generation progress | Single generate call | Staged Preparing → Outline → Slides → Applying template → Finalizing → Ready | UX stages while waiting | Honest labels, not provider events | Streaming provider internals |
| Editor thumbs / text / notes | Parse PPTX + notes sidecar | `PresentEditor` + SplitPane | Concept only | ZECT editor | Charts/images/tables/layout blocks |
| Export PPTX | Allowlisted FileResponse | Export PPTX download in ZECT UI | Native download | ZECT export | Presenton export chrome |
| Voice / rehearse | Voicebox + speak FSM | Clone / stock / No narration | Existing audio_owner | ZECT Present voice select | Presenton branding |

License: Presenton Apache-2.0 recorded in `THIRD_PARTY_NOTICES.md`. ZECT does not vendor Presenton UI. Normal users stay in ZECT-branded `/present`.

## UX1–UX6

| Tranche | Status | Headed (post-merge @ `98e19e6`) | Security | Notes |
|---------|--------|--------------------------------|----------|-------|
| UX1 Projects/WorkItems hygiene | **PARTIAL** | PASS `core-ux-hygiene.spec.ts` | Unit: fixture-name hide + PPTX allowlist | `exclude_fixtures=1`; search; fixtures **hidden** not deleted by pattern |
| UX2 Developer workbench | **PARTIAL** | PASS toggles (explorer/agent/bottom/reset) | Timeline string-payload hardened | Nested SplitPane Explorer \| Editor \| Agent + bottom Terminal/Timeline; persist localStorage |
| UX3 Present templates/generation/editor | **PARTIAL** | PASS editor+export (retry; first post-merge run flake) | Allowlisted PPTX download/parse/save-notes | Charts/images/tables **not** edited (honest) |
| UX4 Voice/rehearsal | **PARTIAL** | UI: clone/stock/none options headed (selectors in editor spec) | Prior cross-user clone deny UNIT_PASS | Live 2-slide clone + stock speak **not re-run**. Prior 1-slide clone PASS preserved |
| UX5 Processes/Jira/Camunda + sample | **PARTIAL** | PASS sample WorkItem + ingest form visible | Untrusted-external tag on jira/camunda/github ingest | Sample never completes live Camunda. Live Jira/Camunda fetch still config-dependent |
| UX6 Full headed + design tokens | **PARTIAL** | Editor/export/hygiene headed post-merge | Hygiene + allowlist + untrusted tag | Full Companion→all-screens campaign not re-run |

## Headed Playwright (post-merge, 2026-08-14)

Command: headed Chromium, `VITE_API_URL=http://127.0.0.1:8000`, `PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173`. Artifacts under `test-results/` (uncommitted).

| Spec | Result |
|------|--------|
| `e2e/auth.setup.ts` | PASS |
| `e2e/core-ux-hygiene.spec.ts` | **PASS** (20.7s) — Projects search, sample process, Fabric sample + ingest form, Developer layout toggles |
| `e2e/present-editor-export.spec.ts` | First run **FAIL** (`zect-present-page` not visible in 20s — login/storageState flake, same class as prior `present-product.spec.ts`). Immediate retry **PASS** (9.7s): thumbs, notes save, Export PPTX download >100 bytes, `option[value="none"]` + `stock:` voice selectors. **Not** treated as product REGRESSION |

## Frozen regression (post-merge @ `98e19e6`)

| Suite | Result |
|-------|--------|
| GitHub CI push `98e19e6` | **PASS** — backend + frontend + e2e ([run 31769567309](https://github.com/KarthikKaruppasamy880/ZECT/actions/runs/31769567309)) |
| Local pytest subset (`test_packaging_sidecar`, `test_present_template_registry`, `test_multi_repo_developer`, `test_voice_cloning`, `test_present_editor_and_hygiene`) | **67 passed, 2 failed, 1 skipped** |
| Local registry isolation fails | `test_fallback_provider_ids_cannot_register_as_zinnia_master`, `test_provider_lifecycle_states` — live workstation registry `zinnia_verified` / `READY` vs isolated `tmp_path`. **Not** product REGRESSION (CI isolated pytest **PASS**) |
| frontend vitest (`src/mentrix`, `src/components`) | **15 passed** |

No new full cross-user live security campaign. Existing negatives preserved: PPTX path allowlist, fixture hide (not delete), ingest untrusted prefix, sample process does not complete engine tasks.

## Branch-introduced Critical/Major (PR #150)

Valid C/M on the PR were fixed on head `717f009` before merge (JSON payload harden, notes-sidecar symlink/`O_NOFOLLOW`, GitHub token via git config env, `get_github()` lock, sample-process IntegrityError reuse, SplitPane pointer capture + keyboard, e2e Python helper). Remaining Ultra Review / CodeRabbit hits on fake test tokens, layout-reset reload, localStorage, e2e races, over-broad redaction, docs/NSIS/live-voice/READY_AFTER_FIX, and docstring coverage were triaged **FALSE_POSITIVE / OUT_OF_SCOPE**. **No unresolved branch-introduced Critical/Major.** No new product code in this post-merge session.

## Remaining gaps (do not paper over)

1. Clean Windows NSIS + packaged Present/Voicebox — **BLOCKED_EXTERNAL: CLEAN_WINDOWS_ENVIRONMENT_REQUIRED**  
2. Live clone Present-all ≥2 slides; live standard-voice speak; Disconnect FSM live — **PARTIAL** (selectors / UNIT_PASS only where noted)  
3. Live Jira/Camunda fetch (needs configured connectors); leftover `zect-r36-*` GitHub repos DELETE 403  
4. Multi-repo READY_AFTER_FIX live re-run — **PARTIAL / BLOCKED_EXTERNAL** (spec exists; live re-run not done)  
5. Charts/images/tables/elements in Present editor  
6. Pixel-complete Presenton-parity generation UX  

## Stop

**STOP before R5.** No KV cache, OCR/XLSX, broader Web, Graphify, or new agents. Do not start `prompts/ZECT_OSS_SOVEREIGNTY_NATIVE_ENGINES_PLAN.md` from this file — sovereignty is a separate explicit start.

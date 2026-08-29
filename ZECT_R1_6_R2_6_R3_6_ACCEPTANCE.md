# ZECT R1.6 / R2.6 / R3.6 — Final release proof

**Date:** 2026-08-13 (closure + core UX addendum)  
**Specs:** `prompts/ZECT_R1_6_R2_6_R3_6_FINAL_RELEASE_PROOF.md` then `prompts/ZECT_RELEASE_CANDIDATE_FINAL_CLOSURE.md` then `prompts/ZECT_CORE_PRODUCT_UX_RECONCILIATION.md`  
**Feature branch (prior):** `feat/r16-r26-r36-final-proof` @ `92e206e30b06b64bcdf576fe37e3147d27fca136` / docs `184aa78`  
**This session branch:** `feat/release-closure-core-ux` (local; production+UX uncommitted)  
**origin/develop (unchanged):** `45f4407fc2c5603db572e7b23b88289226557aeb`  
**Product PR to develop:** **not pushed** (`gh` not logged in)

## Verdict

**RELEASE_CANDIDATE_PARTIAL**

Do not claim `RELEASE_CANDIDATE_PASS`. R1.6 clean-machine NSIS is unproven. Origin merge is **BLOCKED_EXTERNAL**. Closure headed-proved Present **EDITOR** and **EXPORT** in the ZECT UI. Live two-slide clone, standard-voice speak, Disconnect live, packaged runtime, and multi-repo READY_AFTER_FIX remain open. **R5+ not started.** Core UX: `ZECT_CORE_PRODUCT_UX_RECONCILIATION_ACCEPTANCE.md` → **CORE_UX_PARTIAL**.

## Gate report (closure §11)

| Gate | Status | Notes |
|------|--------|-------|
| WINDOWS_CLEAN_INSTALL | **BLOCKED_EXTERNAL** | No clean VM; system Python on PATH; no NSIS in `electron/dist` |
| PACKAGED_BACKEND | **BLOCKED_EXTERNAL** | Same as clean install |
| PRESENT_PPTX_GENERATION | **PASS** (API, prior) / PARTIAL (UI first click 502 prior) | Presenton `:5000` HTTP 200 this session; generate not re-run |
| ZINNIA_VERIFIED | **PASS** (prior) | Registry mapping; UUID not copied here |
| TEMPLATE_GALLERY | **PASS** | ZECT `/present`, not Presenton UI |
| PRESENT_EDITOR | **PASS** (headed this session) | Thumbs, notes save, executive rewrite control. Charts/images/tables not edited |
| PRESENT_EXPORT | **PASS** (headed this session) | ZECT UI Export PPTX download >100 bytes |
| CLONED_VOICE | **PASS** (prior, 1 slide) | 2-slide Present-all not re-proven this session |
| STANDARD_VOICE | **PARTIAL** | Stock + No narration options headed-visible; live stock speak not run |
| NO_OVERLAP | **PASS** (prior, one playback) | Unchanged |
| DISCONNECT_FSM_LIVE | **UNIT_PASS** | Headed Connect/Disconnect not live |
| PACKAGED_PRESENT | **BLOCKED_EXTERNAL** | Managed external Presenton; not bundled |
| PACKAGED_VOICEBOX | **BLOCKED_EXTERNAL** | Docker Voicebox `chatterbox-mtl` `models_ready=true` this workstation; not NSIS-bundled |
| MULTI_REPO_REAL_PRS | **PASS** (prior) | Two real `github.com` PRs |
| MULTI_REPO_BLOCKED_GATE | **PASS** (prior) | `ready_to_ship: false` |
| MULTI_REPO_READY_AFTER_FIX | **NOT RUN** | Spec remediates then re-AGENT; DELETE 403 leftovers |
| FULL_HEADED_E2E | **PARTIAL** | Hygiene + editor/export PASS; full surface campaign not re-run |
| SECURITY | **PARTIAL** | PPTX allowlist, fixture hide, untrusted ingest tag |
| FROZEN_REGRESSION | **PARTIAL** | Hygiene/sidecar passed; 2 registry tests failed against live workstation registry |
| PPTX_GENERATION | **PASS** (API) / PARTIAL (UI first click) | Preserved prior: HTTP 200, PPTX ~624,433 bytes; first UI click 502 then API retry |
| EDITOR | **PASS** | Supersedes prior PARTIAL — headed this session |
| EXPORT | **PASS** | Supersedes prior PARTIAL — headed this session |
| PACKAGED_RUNTIME | **BLOCKED_EXTERNAL** | Unchanged |

## R1.6 Clean Windows

**BLOCKED_EXTERNAL.** No NSIS installer proof on a machine without system Python / source checkout. Sidecar from #146 remains PARTIAL.

## R2.6 ZECT Present + Zinnia + cloned voice

Live engines: backend `:8000` UP; Presenton Docker `:5000` UP; Voicebox Docker `:17493` `synth=chatterbox-mtl`, `models_ready=true` (not stub). Surface: **ZECT Present UI**, not Presenton standalone.

| Item | Result |
|------|--------|
| Template gallery / Zinnia / user PPTX register | PASS |
| Generate in ZECT UI | First click 502; API retry 200 + disk PPTX |
| Cloned Narrate | PASS (headed Playwright `ZECT_LIVE_R26=1`) |
| Present-all two-slide clone | NOT PROVEN |
| Cross-user clone deny | UNIT_PASS (`test_speak_rejects_another_users_voice_id`) |
| Speak timeout | Production default `VITE_MENTRIX_SPEAK_TIMEOUT_MS` 45000 → 180000 (CPU Chatterbox ~70s) |
| Presenton status clobber | Fixed: do not clear `presentonReady` on `reachable: false` template-list; retry status |

Opt-in spec: `frontend/e2e/present-zinnia-clone-live.spec.ts` (skipped unless `ZECT_LIVE_R26=1`). Live evidence JSON stays uncommitted (`test-results/`).

## R3.6 Live multi-repo GitHub PR

**GitHub PR create: PASS.** `local_branch_only` was not treated as PASS.

Headed Playwright `ZECT_LIVE_R36=1`: **2 passed** (auth setup + agent). Evidence `test-results/multi-repo-r36/evidence.json` (uncommitted):

| Field | Value |
|-------|--------|
| `github_pr` | `CREATED` |
| `created_pr_count` | 2 |
| PR A | `https://github.com/KarthikKaruppasamy880/zect-r36-mss82cce-a/pull/1` (`pr_status: created`, branch `zect-wi-107-repo-112`) |
| PR B | `https://github.com/KarthikKaruppasamy880/zect-r36-mss82cce-b/pull/1` (`pr_status: created`, branch `zect-wi-107-repo-113`) |
| `work_item_id` | 107 |
| `repository_ids` | 112, 113 |
| `ready_to_ship` | `false` |
| `aggregate_status` | `failed` (negative: failing `tests/test_block.py` on repo-b) |
| repo DELETE cleanup | HTTP **403** (OAuth token lacks `delete_repo`) — disposable private repos may still exist |

Not proven: remediate failing test → re-run AGENT → `READY_TO_SHIP`. Production push uses `http.extraHeader` (token not stored in origin URL). GitHub client refreshes if `GITHUB_TOKEN` changes.

Opt-in spec: `frontend/e2e/multi-repo-github-live.spec.ts` now **fails** unless ≥2 `github.com` PRs with `pr_status: created`.

## Frozen tests (this campaign, pre-merge)

- pytest (`test_packaging_sidecar`, `test_present_template_registry`, `test_multi_repo_developer`, `test_voice_cloning`, `--noconftest`, py 3.12): **62 passed**
- vitest (`voiceHoldOff` + speak + PresentDeckCloneGate): **17 passed**

CI on a GitHub PR was **not** recorded (branch not on origin).

## Merge discipline

Local commit `92e206e` is on `feat/r16-r26-r36-final-proof` only. **Do not force-merge.** Push/PR/merge to `develop` when GitHub credentials for `KarthikKaruppasamy880/ZECT` are available (`gh auth login` or a PAT that can push this repo). After merge: sync SHA into the four canonical docs.

Do not commit `test-results/`, `.zect/live-endurance/`, or `backend/.env`.

## Stop

**STOP before R5** (KV cache, OCR/XLSX, broader web, Graphify, new agents).

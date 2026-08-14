# ZECT R1.6 / R2.6 / R3.6 — Final release proof

**Date:** 2026-08-13  
**Spec:** `prompts/ZECT_R1_6_R2_6_R3_6_FINAL_RELEASE_PROOF.md`  
**Feature branch:** `feat/r16-r26-r36-final-proof` @ `92e206e30b06b64bcdf576fe37e3147d27fca136`  
**origin/develop (unchanged):** `45f4407fc2c5603db572e7b23b88289226557aeb`  
**Product PR to develop:** **not pushed** (`gh` not logged in; HTTPS push to `ZECT.git` returned invalid credentials)

## Verdict

**RELEASE_CANDIDATE_PARTIAL**

Do not claim `RELEASE_CANDIDATE_PASS`. R1.6 clean-machine NSIS is unproven. R2.6 cloned Narrate and Zinnia PPTX (via ZECT API) passed live; Present-all / export / Disconnect live / packaged Present remain PARTIAL. R3.6 created two real `github.com` PRs (not `local_branch_only`); remediate→`READY_TO_SHIP` was not re-run. **R5+ not started.**

## Gate report

| Gate | Status | Notes |
|------|--------|-------|
| PPTX_GENERATION | **PASS** (API) / PARTIAL (UI first click) | ZECT `POST /api/mentrix/presenton/generate` HTTP 200, lifecycle READY, PPTX ~624,433 bytes. First ZECT Present UI click returned HTTP 502 / `GENERATION_FAILED`; same API retry succeeded. |
| ZINNIA_VERIFIED | **PASS** | `zinnia_verified: true`, `mapping_source: registry`, `template_sent` is a 36-char provider UUID (not `modern/general/standard/swift`). UUID not copied here. |
| TEMPLATE_GALLERY | **PASS** | ZECT Present gallery + Zinnia executive card + user PPTX template register in ZECT UI (not Presenton `:5000`). |
| EDITOR | **PARTIAL** | Inspect/edit/rewrite not fully re-proven this campaign. |
| CLONED_VOICE | **PASS** | ZECT Present **Narrate** → `/speak` through ZECT APIs → Voicebox `chatterbox-mtl` `models_ready: true`. Evidence: 1 speak call, 145004 bytes, `engine: zect_voicebox`, HTTP 200, `stock_engine_calls: 0`. Status: Narrating with saved voice “R26 Live Clone”. |
| NO_OVERLAP | **PASS** | `audio_play_count: 1`, `max_concurrent_playback: 1`. Present-all prefetch / two sequential clone speaks **not** fully proven. |
| DISCONNECT_FSM | **UNIT_PASS** | `voiceHoldOff` vitest. Headed Realtime Connect/Disconnect not live this run. |
| EXPORT | **PARTIAL** | Editable PPTX export not fully re-proven. |
| PACKAGED_RUNTIME | **BLOCKED_EXTERNAL** | This workstation is not a clean Windows VM (system Python 3.12/3.14 on PATH, source checkout, no NSIS artifacts in `electron/dist`). Source-run tests were not substituted as packaging PASS. |

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

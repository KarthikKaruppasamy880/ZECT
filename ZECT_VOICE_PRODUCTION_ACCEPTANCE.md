# ZECT Voice Production Acceptance

**Date:** 2026-08-18  
**Canonical develop at branch point:** `76f5a58b53f973fc748359db5a9858cb884a5b38` (PR **#158**).  
**This PR branch:** `feat/present-voice-production`  
**No auto-merge.**

## Verdict

Companion clone UI, Present narration selectors, ownership isolation, and cancel/no-overlap unit behavior are on this SHA. Live Voicebox clone speak and live OpenAI stock speak are **not** default PASS.

| Gate | Result | Evidence |
|------|--------|----------|
| Companion clone panel | **PASS** (headed + Electron skip) | `/mentrix-home?voice=1` `clone-voice-panel` |
| Clone ownership / cross-user | **PASS** | HTTP list omits victim `voice_id`; speak/delete **404** (`test_voice_cross_user_http_denied`); existing `TestCrossUserCloneDenied` |
| Stock / none selectors | **PASS** (UI) | `present-deck-voice-select` has `none` and `stock:*` |
| Stock speak live | **BLOCKED_EXTERNAL** without OpenAI key; opt-in `ZECT_LIVE_VOICE_STOCK=1` | `test_stock_voice_invalid_and_unconfigured` |
| Engine status honest | **PASS** | `/api/mentrix/voice/engine-status` `online` bool; offline hint names Voicebox |
| ≥2 slides / one audio owner / cancel | **PASS** (unit) | `frontend/src/mentrix/speak.test.ts` (serial playback, `cancelMentrixSpeech`) |
| Live ≥2-slide clone narration | **BLOCKED_EXTERNAL** if Voicebox down | never faked |
| Fallback / outage | **PARTIAL** | 503 when Voicebox/OpenAI unavailable; reconnect not re-soaked this SHA |
| Browser | **PASS** (selectors + engine chip) | `present-voice-production.spec.ts` |
| Electron | **PASS** if binary present; else **skip ≠ PASS** | `present-voice-electron.spec.ts` |

Unavailable Voicebox: **BLOCKED_EXTERNAL**, never fake PASS.

Headed evidence on this SHA: Voicebox offline at local engine URL; clone Test speak disabled. Stock/none selectors **PASS**. Cross-user HTTP **PASS**.

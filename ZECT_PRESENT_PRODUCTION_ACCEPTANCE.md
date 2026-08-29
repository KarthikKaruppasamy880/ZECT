# ZECT Present Production Acceptance

**Date:** 2026-08-18  
**Canonical develop at branch point:** `76f5a58b53f973fc748359db5a9858cb884a5b38` (PR **#158** Coding Agent human-merged).  
**This PR branch:** `feat/present-voice-production`  
**No auto-merge.** WorkItems / Processes / Lattice (tranche C) is **not started**.  
**Provider default:** Presenton (`:8000`). Native remains opt-in `ZECT_PRESENTATION_PROVIDER=zect_native`. This PR does **not** flip the default and does **not** create a new blinded A/B (output path unchanged).

## Verdict

**READY_TO_MERGE_PRESENT_VOICE** after human merge of this focused PR and CI green.  
This tranche does **not** make overall ZECT production-ready. Valid OOXML alone is not Present Quality PASS.

| Gate | Result | Evidence |
|------|--------|----------|
| Dashboard Create AI / Blank / Import / Recent / Zinnia templates | **PASS** (HTTP + headed) | `test_blank_import_notes_idempotent_quality`; `present-voice-production.spec.ts` |
| User template upload isolated from Zinnia ids | **PASS** (HTTP) | `test_zinnia_and_user_templates_http` |
| Quality + Fast controls + lifecycle chip | **PASS** (UI) | Create workspace buttons; generate stays disabled when provider not READY |
| Live Quality/Fast Generate → finished deck | **BLOCKED_EXTERNAL** unless Presenton READY **and** `ZECT_LIVE_PRESENT=1` / `ZECT_LIVE_P0=1` | Default pytest/e2e do not click a 10+ min generate; `test_presenton_status_honest` |
| Progress (`present-generation-progress`) | **PARTIAL** | Testid exists on generate; not observed without a live run |
| Review / notes save / reopen / export idempotence | **PASS** | save-notes twice; PPTX download byte-stable when not hard-blocked |
| Critic on executive/roadmap/architecture/metrics prompts | **PASS** (unit) | `test_critic_case_prompts_do_not_crash` |
| Native visual PPTX (image/chart/table) inspector | **PASS** (native renderer, not Presenton) | `test_native_visual_render_inspector_not_presenton` |
| Inspector uses actual PPTX slide size (4:3 blank ≠ 16:9 false clip) | **PASS** | `final_pptx_inspector.inspect_pptx_bytes`; blank export no longer 409 |
| FinalPptxInspector + non-overridable Critical 409 | **PASS** | `test_critical_quality_409_not_overridable`; headed hard-block UI |
| Import garbage PPTX fail-closed | **PASS** | `import_pptx_bytes` + HTTP 400 |
| Browser headed | **PASS** | `frontend/e2e/present-voice-production.spec.ts` in `test:e2e:core` |
| Electron | **PASS** | `present-voice-electron.spec.ts` (binary present this machine; skip ≠ core PASS) |
| Real Microsoft PowerPoint COM | **BLOCKED_EXTERNAL** | `test_powerpoint_com_opt_in_or_blocked_external` (opt-in `ZECT_LIVE_PPT_COM=1`) |
| Mentrix Ultra Review | **PASS** (0 critical) | score 85, `gpt-4o-mini`; CodeRabbit **SKIPPED** ≠ PASS |

## Lifecycle proved

`Dashboard → Create AI (Zinnia template) → Quality/Fast controls → Blank → Review/Edit notes → Export gate → Import → Rehearse`

Live Presenton Generate and live PowerPoint COM are recorded as **BLOCKED_EXTERNAL**, never as PASS.

## Stop

`READY_TO_MERGE_PRESENT_VOICE` — human merge only. Do not start tranche C.

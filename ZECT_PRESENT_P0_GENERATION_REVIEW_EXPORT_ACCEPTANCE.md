# ZECT Present P0 Generation → Review → Export Acceptance

**Date:** 2026-08-15  
**Canonical develop:** `1b1cf40` (PR **#153** human-merged).  
**Branch:** `feat/developer-workspace-ux`  
**Presenton default:** unchanged (`:8000`). Native opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native` on `:8010`).  
**S8C / S8D / Graphify / KV / OCR:** not started.

## Gate

**READY_TO_MERGE** (human merge only) after CI on the PR.

| Proof | Result |
|-------|--------|
| Headed Quality Dashboard → Create → Zinnia → Generate → Review → Export | **PASS** (`mentrix-deck-10.pptx`, 11:14 AM) |
| Headed Fast (Advanced, controlled `<details>` + DOM `.click()`) | **PASS** (`mentrix-deck-12.pptx`, 11:16 AM) |
| Critical findings non-overridable | Colliding `mentrix-deck-8.pptx` + `accept_warnings=true` → **409** `export_blocked_critical_quality` / `text_shape_collision`. Clean Quality deck → **200** |
| PowerPoint COM | **Quality deck-10: 0 findings. Fast deck-12: 0 findings.** Opened in desktop PowerPoint via COM — not inferred from OOXML. Pre-repair decks 8/9 had title TextBox stacked on the Zinnia OBJECT placeholder |
| Electron Quality then Fast | **PASS** (28.7s). Artifacts `test-results/present-p0-electron/quality.pptx` and `fast.pptx`. Unique `--user-data-dir` (did not `taskkill electron.exe`) |
| Projects after generate | No E2E/onboarding rows. `proven_test=0` |

## Defects closed this session

| Defect | Repair |
|--------|--------|
| Fast Generate never fired (Advanced `<details>` closed; React wiped `el.open`) | Controlled `advancedOpen`; headed/Electron use `HTMLButtonElement.click()` |
| Zinnia OBJECT placeholder (title slot) filled with bullets while a title TextBox sat on the same box | Prefer TITLE/BODY types; leftover OBJECT: top → title, next → body; never both |
| Example KPI `n/a` overlapped body | Skip painting metrics whose value is n/a |
| Export gate missed COM-visible collisions (placeholder xfrms on layout) | Inspector fills missing geom from python-pptx resolved positions |
| Electron `page.waitForEvent("download")` never fired | Main-process `will-download` + `setSavePath` |
| Repeated 401/404 | Token guards; catalog-gated identity/branches; presence WS cap; Context Used stable deps |

## PowerPoint evidence (manual COM)

Recorded in `test-results/present-p0-headed/powerpoint-com-evidence.json` and `test-results/present-p0-electron/powerpoint-com-evidence.json` (not committed). Copies: `2026-08-15-quality-zinnia.pptx`, `2026-08-15-fast-zinnia.pptx`.

Checked: duplicate text, title/body collisions, clipping, broken pictures/charts, placeholder name duplication, template corruption.

## What this is not

- Not S8C/S8D  
- Not Presenton branding / Template Studio  
- Not switching the product default off Presenton  

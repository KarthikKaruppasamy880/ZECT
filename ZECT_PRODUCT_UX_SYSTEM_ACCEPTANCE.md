# ZECT Product UX / Accessibility System Acceptance

**Date:** 2026-08-18  
**Canonical develop (pre-PR):** `69816ea0435024a3cf1a441eea71db3fc157d1e2` (PR **#165** human-merged)  
**Branch:** `feat/ux-accessibility-release-sweep`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md` — Tranche G only  
**Stop label:** `READY_TO_MERGE_UX_ACCESSIBILITY` — human merge only, no auto-merge.  
**Do not start** Tranche H, S8C/S8D, Graphify, KV-cache, OCR/XLSX, broader Web, new agents.

Leftover untracked markdown from 2026-08-14 is **not** evidence. This file is the tranche G record.

## Verdict

Local headed browser sweep **PASS**. Local Electron Companion/Present/Developer/Knowledge **PASS** (`electron.exe` present). Live Presenton / Voicebox / Jira / Camunda / GitHub were not clicked and remain **BLOCKED_EXTERNAL**.

Overall ZECT remains **ZECT_PRODUCTION_PARTIAL**. Tranche H–I are not in this PR. CI on the focused PR is required before human merge.

## Fixes (code, not docs-only)

- Session verify: 8s abort so operators are not trapped on unbounded **Loading…**; `auth-checking` status; skip link focuses `#zect-main`
- Named collapsed sidebar links (`aria-label`, `aria-current`); collapse controls `aria-expanded`; section headings; Ctrl+B / Escape
- Project/repo/branch dropdowns: Escape, `aria-expanded` / `aria-haspopup`, `zect-dropdown`
- SplitPane Home/End/Escape + `aria-valuetext`
- Companion Chat/Incident/Voice tabs: arrows/Home/End, roving focus, `tabpanel`
- Knowledge / Skills / Playbooks / PI / Learning / Login: labels, `role=alert` / `role=status`, empty/loading, wrap at 1280
- WorkItems filters `aria-pressed`; Processes refresh/surface names; Present decks loading/empty; Developer pane `aria-pressed`; Mentrix dock expand/send names

## Surfaces

| Surface | Route | Headed proof |
|---------|-------|----------------|
| Companion | `/mentrix-home` | `mentrix-companion-page` + tab keyboard |
| Present | `/present` | `zect-present-page` + named nav |
| Developer | `/workspace` | `developer-workspace` + split handle when visible |
| Agent Workspace | `/ask` | `agent-workspace` |
| Projects | `/projects` | `projects-page` + skip/collapse/dropdown |
| WorkItems | `/work-items` | `work-items-page` |
| Processes | `/fabric` | `mentrix-fabric-page` + `process-sample-card` (live Jira/Camunda unset = **BLOCKED_EXTERNAL**) |
| PI | `/project-intelligence` | `project-intelligence-page` |
| Lattice | `/lattice` | `lattice-page` (Graphify not started) |
| Knowledge | `/knowledge-base` | `knowledge-base-page` |
| Learning | `/learning` | `zect-learning-page` |
| Skills | `/skills-engine` | `skills-engine-page` |
| Playbooks | `/playbooks` | `playbooks-page` |

Viewports: **1280×720** and **1920×1080**. Horizontal overflow allowance ≤ 24px.

## Tests

```powershell
cd frontend
npx playwright test e2e/ux-accessibility-production.spec.ts
npx playwright test e2e/ux-accessibility-electron.spec.ts
```

Local (2026-08-18): production spec **4 passed**; Electron spec **passed** (not skipped). Electron skip without `electron/node_modules/electron/dist/electron.exe` ≠ PASS.

Security regression: `tests/test_security_production.py` — **29 passed, 1 skipped**.

Mentrix Ultra Review: **passed**, score 85, **0 critical** (`gpt-4o-mini`). One medium (verify abort vs unmount) already uses a `cancelled` flag.

## Stop

Human-merge this PR after CI. Next focused tranche after merge: **H** full-release E2E. Do not start S8C.

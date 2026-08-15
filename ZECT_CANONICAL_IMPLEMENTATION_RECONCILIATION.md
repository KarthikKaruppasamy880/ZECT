# ZECT Canonical Implementation Reconciliation

**Date:** 2026-08-15  
**Canonical develop:** `origin/develop` = `1b1cf40d05d6b9ed94d5ec27da524676b377379a` (PR **#153** `feat/present-s75-quality-closure`, human-merged).  
**Working branch:** `feat/developer-workspace-ux` (local; **not on develop** until human merge).  
**No auto-merge.** Presenton remains product default (`:8000`). Native is opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native` on `:8010`).

## Rule

Never assume prior Cursor work is on `develop`. Production truth is `origin/develop` only.

## Post-merge #153 proof (this session)

| Gate | Result |
|------|--------|
| Frozen pytest on develop | 1000 passed after local `croniter` install; not a #153 regression |
| Headed P0 Quality + Fast from `/present` vs native `:8010` | **PASS** (Quality ~20s, Fast ~10s) |
| Critical export | Colliding `mentrix-deck-8.pptx` → `GET .../pptx?accept_warnings=true` **409** `export_blocked_critical_quality`. Clean Quality `mentrix-deck-10.pptx` → **200** |
| PowerPoint COM (not OOXML inference) | Pre-repair decks 8/9: placeholder vs title TextBox collisions. Post-repair **deck-10 Quality** and **deck-12 Fast**: **0 findings**. Electron `quality.pptx` / `fast.pptx` also COM-inspected |
| Projects fixture isolation | `e2e_like=[]`, `proven_test=0`. Authorized: ZOAS Eval + ZECT Sample Processes (sample, not E2E/onboarding) |
| Developer Workspace chrome | Resizable explorer/editor/agent/bottom, persistence, maximize/hide, Lattice SHA→STALE, stale repo 401/404 hygiene |
| Electron Present | Dashboard → Create → Quality then Fast → Review → Export **PASS** (28.7s) with unique `--user-data-dir` |

## Capability matrix (delta vs #153 develop)

| Capability | On develop `1b1cf40`? | This branch | Live proven? | Status |
|------------|----------------------|-------------|--------------|--------|
| Present Dashboard → Generate → Review → Export | yes (#153) | Fast `<details>` controlled; Zinnia OBJECT title XOR | Headed + Electron | **THIS PR** |
| Native quality / inspector | yes (#153) | Layout-resolved placeholder geom; skip n/a metrics | PowerPoint COM + 409 gate | **THIS PR** |
| Presenton default | **yes** | unchanged | `:8000` `PROVIDER_UNAVAILABLE` (Docker off) | **ON DEVELOP** |
| Developer Workspace chrome | shell yes | persistence/maximize/tabs | headed hygiene + P0 workspace | **THIS PR** |
| Lattice STALE on commit move | partial | SHA compare | unit + header chip | **THIS PR** |
| S8C / S8D / Graphify / KV / OCR / new agents | no | **not started** | n/a | **OUT OF SCOPE** |

## Recommended merge

One PR to `develop`: Developer Workspace UX + Present Fast/Electron/PowerPoint closure. Human merge only.

## Official S8C

**Not started.** `NOT_READY_FOR_S8C`.

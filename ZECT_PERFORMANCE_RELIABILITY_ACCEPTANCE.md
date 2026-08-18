# ZECT Performance / Reliability / Observability Acceptance

**Date:** 2026-08-18  
**Canonical develop (pre-PR):** `962bb6b58e1108b2a3d697419a82351723baa317` (PR **#163** human-merged)  
**Branch:** `feat/performance-reliability-architecture`  
**Prompt:** `prompts/ZECT_PERFORMANCE_RELIABILITY_OBSERVABILITY_AND_ARCHITECTURE_CLOSURE.md`  
**Stop label:** `READY_TO_MERGE_PERFORMANCE_RELIABILITY_ARCHITECTURE` — human merge only, no auto-merge.  
**Do not start** S8C/S8D, Graphify, KV-cache, OCR/XLSX, broader Web, new agents, or tranche G a11y until this PR is human-merged.

Thresholds were declared in `backend/app/infrastructure/perf_thresholds.py` **before** interpreting results. They were not raised after a failing run.

## Verdict

**PERFORMANCE_RELIABILITY_PARTIAL** internally (Companion concurrent-load, multi-terminal soak, live Voice, live Present Quality generate, Electron, clean-machine NSIS, live Postgres are not PASS).  
The PR is still offered for human merge of proven observability, architecture, isolation, bounded soak, and cancel/diagnose gates.

Overall ZECT remains **ZECT_PRODUCTION_PARTIAL**.

## Thresholds (frozen)

| Metric | Threshold | Fixture |
|--------|-----------|---------|
| Lattice ingest | ≤ 25_000 ms | 120 small `.py` files (`LATTICE_INGEST_FILES`) |
| 3-root workspace search | ≤ 8_000 ms | alpha/beta/gamma git roots |
| Coding isolate 2 missions | ≤ 20_000 ms | two disposable repos |
| Present RESTRICTED fail-closed | ≤ 3_000 ms | Presenton path, no engine call |
| Present Fast plan | ≤ 8_000 ms | `fast_basic` heuristic |
| Soak | 8 iterations × 16 files; RSS growth ≤ 96 MiB; DB checked-out ≤ 8; handle growth ≤ 200 if measured |
| Cancel index / present / mission | ≤ 8s / 3s / 5s | cooperative cancel |
| Isolation leaks | 0 | 3 WorkItems + 2 coding missions |

## Gates

| Gate | Result |
|------|--------|
| Thresholds declared before results | **PASS** |
| Large-repo Lattice ingest (120 files) | **PASS** (`test_lattice_ingest_large_repo_under_threshold`) |
| ≥3-root workspace search | **PASS** |
| Concurrent WorkItem artifact isolation | **PASS** |
| Concurrent Coding Agent missions / worktrees | **PASS** |
| Bounded soak RSS + DB checked-out | **PASS** |
| File handles | **PASS** when `GetProcessHandleCount` returns; otherwise recorded unmeasured in soak extra — not silently treated as PASS if RSS failed |
| Cancel Lattice ingest | **PASS** |
| Cancel Present generate | **PASS** |
| Cancel Coding Agent | **PASS** |
| Diagnose failed Coding Agent from telemetry | **PASS** (eval review block → `failure_class=blocked`) |
| Diagnose failed Present from telemetry | **PASS** (`restricted_external_provider`) |
| Correlation ID echo (`X-Correlation-Id`) | **PASS** (pytest + headed e2e) |
| Secrets not in telemetry / MCP args | **PASS** |
| Architecture + storage audit | **PASS** (code-backed; no pgvector claim) |
| Companion concurrent load/soak | **PARTIAL** — existing `test_companion_production.py` isolation reused; no concurrent-session soak in this PR |
| Concurrent terminals | **PARTIAL** — coding-agent sibling tests exercise parallel pytest; dedicated multi-terminal soak not added |
| Present Quality full generate latency | **PARTIAL** — Fast plan timed; live Quality PPTX generate is environment-dependent |
| Voice under load | **BLOCKED_EXTERNAL** (`ZECT_VOICEBOX_BASE_URL` / Chatterbox unset) skip ≠ PASS |
| Live PostgreSQL soak | **BLOCKED_EXTERNAL** (`ZECT_TEST_POSTGRES_URL` unset) skip ≠ PASS |
| Live Presenton | **BLOCKED_EXTERNAL** when unset — RESTRICTED fail-closed proven without calling it |
| Electron System Health | **SKIPPED** if `electron.exe` missing ≠ PASS |
| Clean-machine Windows NSIS | **BLOCKED_EXTERNAL** |
| Live GitHub / Jira / Camunda | **BLOCKED_EXTERNAL** when unset — does not block ZECT-native perf tests |
| Mentrix Ultra Review | **PASS** (score 85, 0 critical; medium telemetry fail-soft applied) |
| CodeRabbit | **SKIPPED** until triggered; skip ≠ PASS |
| GitHub Actions backend (PR #164 `dad338f`) | **FAIL** — `test_mission_f_sibling_failure_blocks_then_repair` on Linux/pytest 9.1.1 (repo 11 tests still fail after repair). Follow-up commit isolates nested pytest + hardens patch lookup. skip ≠ PASS until that SHA is green |

## Observability (implemented)

- `X-Correlation-Id` middleware + CORS expose
- Ring-buffer events: correlation/run, WorkItem/project, stage, duration, retries, failure_class, model/tool route
- `GET /api/system/telemetry` (auth)
- `POST /api/system/operations/cancel`, `/api/lattice/ingest/cancel`, `/api/mentrix/presenton/generate/cancel`
- Privileged audit: present generate, coding cancel, git approve
- MCP `arguments_json` / `result_json` redacted
- No presentation bodies or raw patches in telemetry

## Tests

```powershell
cd backend
python -m pytest tests/test_performance_reliability_production.py -q
```

Plus post-#163 smoke: `test_runtime_db_lifecycle_production.py`, `test_runtime_recovery_production.py`.

## Stop

Human-merge this PR. Do **not** start a11y (tranche G) or soak-expansion roadmap work until `origin/develop` contains this merge.

# ZECT — Roadmap (Phase 0 Audit Baseline)

Status as of this audit. Work proceeds one phase at a time per the execution rules: inspect → plan → list files → state risks → wait for approval → implement → verify → report. **Phase 9 is on hold — do not implement Wazuh, osquery, Velociraptor, automatic containment, or endpoint-response workflows until explicitly unblocked.**

Branding rule applies to every phase below: third-party projects may be used internally behind ZECT-owned adapter interfaces; never surfaced in UI, routes, DB models, public APIs, or branding; legally required attribution always preserved in `THIRD_PARTY_NOTICES.md`/dependency metadata. See TARGET_ARCHITECTURE.md for how this is encoded per-phase.

| # | Phase | Completion | Evidence |
|---|---|---|---|
| 0 | Repo audit + doc set | **Done** (this pass) | CURRENT_ARCHITECTURE.md, TARGET_ARCHITECTURE.md, FEATURE_INVENTORY.md, THREAT_MODEL.md, this file. |
| 1 | Core platform, shared AgentRun | **Done (spine)** | `api/` + `domains/` + `adapters/` + `infrastructure/` + `workers/`; Mentrix shared run + cancel/retry/files/artifacts/terminal/gates; event `sequence_id` + SSE reconnect; MockCodingRuntime; audit on Mentrix state changes; Agent Workspace shell with Ask/Plan/Build/Review/Deploy modes. Residual: fat domain routers (not fully thin services), embedded Monaco diff still via App Runner, OpenHands = Phase 2. |
| 2 | Coding-engine provider | **Done (A–D)** | Worktree isolation + optional Docker sandbox (falls back when Docker unavailable); remote HTTP adapter; Mentrix opt-in engine slice; health/version/isolation reporting. See `PHASE_2_EXECUTION_PLAN.md`. |
| 3 | Cursor-like workspace | **Done (A–E)** | `/workspace` tree+Monaco+git+terminal+Mentrix timeline+diff/hunks+inline Ask+symbols/worktrees. See `PHASE_3_EXECUTION_PLAN.md`. |
| 4 | PR review platform | **Done (A–D)** | Schema + validate/dedupe/rank; deterministic secrets/TODO/rules; approve-before-post + Mentrix bugfix hook. See `PHASE_4_EXECUTION_PLAN.md`. |
| 5 | Permissions/secrets/audit | **In progress (Stage B)** | A done (#98). Stage B: temporary `CapabilityGrant` + Upgrade capability aliases wired into `/check` and Mentrix broker. Remaining: secret refs + diagnostics, emergency-stop. See `PHASE_5_EXECUTION_PLAN.md`. |
| 6 | Realtime voice | **~75% — most complete phase** | Persistent session, per-sentence streaming speech, true cross-sentence prefetch, barge-in cancellation, 8 named latency checkpoints, short-timeout no-silent-retry — all shipped this session. Built on the OpenAI Realtime API directly (already brand-clean); no LiveKit dependency needed unless a future provider swap is wanted. |
| 7 | Browser/desktop access | ~15% — and inverted priority order | "Computer Mode" is OS-level simulated input (SendKeys/window activation) — the tier the target architecture says should be *last resort*, currently the *only* method. No DOM/accessibility-tree automation. File-organization workflow (hash+rollback) not built. |
| 8 | Email/Slack/Calendar/Jira | ~40% | Real Jira/Slack/Confluence/Datadog MCP adapters work today. Admin-configured credentials, not per-user OAuth; no draft-before-send gate; no Calendar adapter. |
| 9 | Security monitoring/incident response | **ON HOLD** | Existing custom audit-log anomaly detector → Jira ticket flow is a real, separate, ZECT-native capability — kept as-is, not extended toward Wazuh/osquery/Velociraptor until unblocked. |
| 10 | Memory/skills/automation | ~35% | Mentrix Notes + a Skills concept exist. Scheduled/condition-based automation with retry/idempotency not verified as built to spec. Sidebar has both "Skill Library" and "Skills Engine," and both "Memory System" and "Mentrix Notes" — check for real duplication before building more here (see FEATURE_INVENTORY.md). |
| 11 | Packaging/licensing/release | ~0% | No dependency/license audit, signed builds, or update mechanism found. |

## Phase 0 exit backlog (small, concrete items surfaced by this audit — not yet actioned)

Carry into whichever phase naturally owns each:

- **Security (→ Phase 5):** ~~`app_runner.py`~~, ~~`sandbox.py`~~, ~~webhook signature~~, ~~auth `.env` override~~, ~~CORS on 500s~~, ~~diff_viewer path allowlist~~ — all **fixed in code** (see `THREAT_MODEL.md`). Remaining Phase 5 product gaps: temporary capability grants, secret references, diagnostics UI, global emergency-stop (`PHASE_5_EXECUTION_PLAN.md`).
- **Dead code (→ Phase 1 or 11 cleanup):** `services/llm/voicebox_client.py`, `services/llm/elevenlabs_client.py` (legacy, test-only references); `frontend/src/pages/StagePage.tsx` / `/stages/:stage` route (no nav link, no in-app navigation to it).
- **Correctness (→ Phase 1):** `build_phase_svc.py`'s offline-stub gate checks only `OPENAI_API_KEY`, not `ANTHROPIC_API_KEY` — an Anthropic-only deployment would silently hit the placeholder instead of calling Claude.
- **Duplicate-concept check (→ Phase 1/10):** Skill Library vs. Skills Engine; Memory System vs. Mentrix Notes; Knowledge Base vs. Lattice Graph vs. Docs Center. Naming similarity only, not yet confirmed as real duplication — needs a hands-on look before deciding to merge/remove anything.
- **Test environment (→ before any Phase 1 CI setup):** fix `auth.py`'s unconditional `.env` reload so the test suite's injected credentials survive a login call (the previously-noted missing `pytest-asyncio` was a stale finding from a different/broken Python install, not a real gap — corrected in CURRENT_ARCHITECTURE.md).
- **Windows portability (→ Phase 1):** `allowed_paths.py`'s default roots are POSIX-only; a fresh Windows install with no `ZECT_WORKSPACE_ROOT` set would have File Explorer/Git Ops silently unable to match any path.

## Next decision point

**Phase 5 Stage B** is the current deliverable (temporary capability grants). Phase 9 remains ON HOLD.

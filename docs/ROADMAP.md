# ZECT — Roadmap (Phase 0 Audit Baseline)

Status as of this audit. Work proceeds one phase at a time per the execution rules: inspect → plan → list files → state risks → wait for approval → implement → verify → report. Phase 9 security spine is delivered; automatic containment remains disabled.

Branding rule applies to every phase below: third-party projects may be used internally behind ZECT-owned adapter interfaces; never surfaced in UI, routes, DB models, public APIs, or branding; legally required attribution always preserved in `THIRD_PARTY_NOTICES.md`/dependency metadata. See TARGET_ARCHITECTURE.md for how this is encoded per-phase.

| # | Phase | Completion | Evidence |
|---|---|---|---|
| 0 | Repo audit + doc set | **Done** (this pass) | CURRENT_ARCHITECTURE.md, TARGET_ARCHITECTURE.md, FEATURE_INVENTORY.md, THREAT_MODEL.md, this file. |
| 1 | Core platform, shared AgentRun | **Done (spine)** | `api/` + `domains/` + `adapters/` + `infrastructure/` + `workers/`; Mentrix shared run + cancel/retry/files/artifacts/terminal/gates; event `sequence_id` + SSE reconnect; MockCodingRuntime; audit on Mentrix state changes; Agent Workspace shell with Ask/Plan/Build/Review/Deploy modes. Residual: fat domain routers (not fully thin services), embedded Monaco diff still via App Runner, OpenHands = Phase 2. |
| 2 | Coding-engine provider | **Done (A–D)** | Worktree isolation + optional Docker sandbox (falls back when Docker unavailable); remote HTTP adapter; Mentrix opt-in engine slice; health/version/isolation reporting. See `PHASE_2_EXECUTION_PLAN.md`. |
| 3 | Cursor-like workspace | **Done (A–E)** | `/workspace` tree+Monaco+git+terminal+Mentrix timeline+diff/hunks+inline Ask+symbols/worktrees. See `PHASE_3_EXECUTION_PLAN.md`. |
| 4 | PR review platform | **Done (A–D)** | Schema + validate/dedupe/rank; deterministic secrets/TODO/rules; approve-before-post + Mentrix bugfix hook. See `PHASE_4_EXECUTION_PLAN.md`. |
| 5 | Permissions/secrets/audit | **Done (A–D)** | Audit unify; grants; secret refs + redaction + diagnostics; global emergency-stop + audit hash chain. See `PHASE_5_EXECUTION_PLAN.md`. |
| 6 | Realtime voice | **Done (Stage A)** | Voice telemetry HUD (mode + latency marks). See `PHASES_6_11_STAGE_A.md`. |
| 7 | Browser/desktop access | **Done (Stage A)** | Browser fill verify + artifacts; file-organize dry-run/approve/hash/rollback. |
| 8 | Email/Slack/Calendar/Jira | **Done (Stage A)** | Slack/email draft-before-send via `OutboundDraft`. Calendar/OAuth deferred. |
| 9 | Security monitoring/incident response | **Done (A–D spine)** | Detection Provider + findings/incidents; draft→approve→Jira/Slack; signed ingest; containment stubs disabled. |
| 10 | Memory/skills/automation | **Done (A–B)** | Typed memory + retention/export/secret-on-write; skill approval gates; watches + due-run + max_attempts. See `PHASE_10_EXECUTION_PLAN.md`. |
| 11 | Packaging/licensing/release | **Done (A–B)** | Notices, RELEASE, support bundle, EULA/PRIVACY/BACKUP, CSP, architecture + tool comparison. Signing deferred Stage C. |

## Next decision point

**Upgrade spine Stages A–B complete through Phase 11.** Remaining optional Stage C: Electron code signing / auto-update. Architecture: `docs/ARCHITECTURE_AND_WORKFLOWS.md`.

## Phase 0 exit backlog (small, concrete items surfaced by this audit — not yet actioned)

Carry into whichever phase naturally owns each:

- **Security (→ Phase 5):** ~~`app_runner.py`~~, ~~`sandbox.py`~~, ~~webhook signature~~, ~~auth `.env` override~~, ~~CORS on 500s~~, ~~diff_viewer path allowlist~~ — all **fixed in code** (see `THREAT_MODEL.md`). Remaining Phase 5 product gaps: temporary capability grants, secret references, diagnostics UI, global emergency-stop (`PHASE_5_EXECUTION_PLAN.md`).
- **Dead code (→ Phase 1 or 11 cleanup):** `services/llm/voicebox_client.py`, `services/llm/elevenlabs_client.py` (legacy, test-only references); `frontend/src/pages/StagePage.tsx` / `/stages/:stage` route (no nav link, no in-app navigation to it).
- **Correctness (→ Phase 1):** ~~`build_phase_svc.py`'s offline-stub gate checks only `OPENAI_API_KEY`~~ — **fixed**: `_generation_ready()` accepts OpenAI **or** Anthropic (`anthropic_available()`); covered by `test_build_phase_svc_generation_gate.py`.
- **Duplicate-concept check (→ Phase 1/10):** Skill Library vs. Skills Engine; Memory System vs. Mentrix Notes; Knowledge Base vs. Lattice Graph vs. Docs Center. Naming similarity only, not yet confirmed as real duplication — needs a hands-on look before deciding to merge/remove anything.
- **Test environment (→ before any Phase 1 CI setup):** fix `auth.py`'s unconditional `.env` reload so the test suite's injected credentials survive a login call (the previously-noted missing `pytest-asyncio` was a stale finding from a different/broken Python install, not a real gap — corrected in CURRENT_ARCHITECTURE.md).
- **Windows portability (→ Phase 1):** `allowed_paths.py`'s default roots are POSIX-only; a fresh Windows install with no `ZECT_WORKSPACE_ROOT` set would have File Explorer/Git Ops silently unable to match any path.

## Next decision point

**Phase 9 Stage A–D spine** is the current deliverable (security incidents). Automatic containment remains disabled.

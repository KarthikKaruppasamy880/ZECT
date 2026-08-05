# ZECT — Roadmap (Phase 0 Audit Baseline)

Status as of this audit. Work proceeds one phase at a time per the execution rules: inspect → plan → list files → state risks → wait for approval → implement → verify → report. **Phase 9 is on hold — do not implement Wazuh, osquery, Velociraptor, automatic containment, or endpoint-response workflows until explicitly unblocked.**

Branding rule applies to every phase below: third-party projects may be used internally behind ZECT-owned adapter interfaces; never surfaced in UI, routes, DB models, public APIs, or branding; legally required attribution always preserved in `THIRD_PARTY_NOTICES.md`/dependency metadata. See TARGET_ARCHITECTURE.md for how this is encoded per-phase.

| # | Phase | Completion | Evidence |
|---|---|---|---|
| 0 | Repo audit + doc set | **Done** (this pass) | CURRENT_ARCHITECTURE.md, TARGET_ARCHITECTURE.md, FEATURE_INVENTORY.md, THREAT_MODEL.md, this file. |
| 1 | Core platform, shared AgentRun | ~35% | Real `MentrixRun` state machine + persisted events + SSE streaming exist. No `api/domains/adapters/infrastructure/workers` split; Ask/Plan/Build/Review are separate pages, not one workspace; no background-worker process (audit finding — everything runs in-request); no MockRuntime. |
| 2 | Coding-engine provider | ~5% | Build calls Anthropic/OpenAI directly in-process. No isolated per-run workspace, no sandboxing, no separate engine-server process. Furthest from target. |
| 3 | Cursor-like workspace | ~20% | Build has file-attach + diff viewer + generated-files list. No Monaco, file tree, terminal, inline code actions, or symbol search. |
| 4 | PR review platform | ~60% | Ultra Review consolidated (verified — no duplicate implementations remain), gated human-approve-then-create-PR is real. `ReviewFinding` schema fields (fingerprint, confidence, validation_status) not verified against spec. |
| 5 | Permissions/secrets/audit | ~55% | RBAC + Fernet secrets + pervasive audit log + permission broker exist. Missing granular capability grants w/ expiry, permission-diagnostics page, emergency stop. **Inherits THREAT_MODEL.md findings 1-6 as backlog**, especially the two Critical items (app_runner.py, sandbox.py). |
| 6 | Realtime voice | **~75% — most complete phase** | Persistent session, per-sentence streaming speech, true cross-sentence prefetch, barge-in cancellation, 8 named latency checkpoints, short-timeout no-silent-retry — all shipped this session. Built on the OpenAI Realtime API directly (already brand-clean); no LiveKit dependency needed unless a future provider swap is wanted. |
| 7 | Browser/desktop access | ~15% — and inverted priority order | "Computer Mode" is OS-level simulated input (SendKeys/window activation) — the tier the target architecture says should be *last resort*, currently the *only* method. No DOM/accessibility-tree automation. File-organization workflow (hash+rollback) not built. |
| 8 | Email/Slack/Calendar/Jira | ~40% | Real Jira/Slack/Confluence/Datadog MCP adapters work today. Admin-configured credentials, not per-user OAuth; no draft-before-send gate; no Calendar adapter. |
| 9 | Security monitoring/incident response | **ON HOLD** | Existing custom audit-log anomaly detector → Jira ticket flow is a real, separate, ZECT-native capability — kept as-is, not extended toward Wazuh/osquery/Velociraptor until unblocked. |
| 10 | Memory/skills/automation | ~35% | Mentrix Notes + a Skills concept exist. Scheduled/condition-based automation with retry/idempotency not verified as built to spec. Sidebar has both "Skill Library" and "Skills Engine," and both "Memory System" and "Mentrix Notes" — check for real duplication before building more here (see FEATURE_INVENTORY.md). |
| 11 | Packaging/licensing/release | ~0% | No dependency/license audit, signed builds, or update mechanism found. |

## Phase 0 exit backlog (small, concrete items surfaced by this audit — not yet actioned)

Carry into whichever phase naturally owns each:

- **Security (→ Phase 5):** ~~`app_runner.py` arbitrary shell exec with no RBAC/path-allowlist~~ and ~~`sandbox.py` silent host-fallback + command injection in its Docker path~~ — both Critical findings **fixed** (`fix/app-runner-sandbox-rbac-and-injection`). Remaining: GitHub webhook signature check is opt-in not mandatory (High); `auth.py` reloads `.env` with `override=True` on every login, breaking test isolation and creating a live-credential-swap side effect (High, confirmed reproducible); CORS allowlist bypass on unhandled 500s (Medium); `diff_viewer.py`'s `repo_path` not confirmed path-allowlisted (Medium, needs closer read).
- **Dead code (→ Phase 1 or 11 cleanup):** `services/llm/voicebox_client.py`, `services/llm/elevenlabs_client.py` (legacy, test-only references); `frontend/src/pages/StagePage.tsx` / `/stages/:stage` route (no nav link, no in-app navigation to it).
- **Correctness (→ Phase 1):** `build_phase_svc.py`'s offline-stub gate checks only `OPENAI_API_KEY`, not `ANTHROPIC_API_KEY` — an Anthropic-only deployment would silently hit the placeholder instead of calling Claude.
- **Duplicate-concept check (→ Phase 1/10):** Skill Library vs. Skills Engine; Memory System vs. Mentrix Notes; Knowledge Base vs. Lattice Graph vs. Docs Center. Naming similarity only, not yet confirmed as real duplication — needs a hands-on look before deciding to merge/remove anything.
- **Test environment (→ before any Phase 1 CI setup):** fix `auth.py`'s unconditional `.env` reload so the test suite's injected credentials survive a login call (the previously-noted missing `pytest-asyncio` was a stale finding from a different/broken Python install, not a real gap — corrected in CURRENT_ARCHITECTURE.md).
- **Windows portability (→ Phase 1):** `allowed_paths.py`'s default roots are POSIX-only; a fresh Windows install with no `ZECT_WORKSPACE_ROOT` set would have File Explorer/Git Ops silently unable to match any path.

## Next decision point

Per the execution rules, Phase 1 needs its own file-by-file plan before any code changes — that's the next thing to produce and get your sign-off on, once you tell me whether to fold in any of the exit-backlog items above (especially the two Critical security ones) as part of Phase 1, or handle them as an immediate, separate out-of-band patch first.

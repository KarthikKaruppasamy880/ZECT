# ZECT — Target Architecture

Adapted from the 11-phase roadmap, with one binding rule applied throughout: **third-party projects are implementation detail behind ZECT-owned interfaces — never named in UI, routes, DB models, public APIs, or branding.** Where the original roadmap named a specific third-party framework as "the" implementation, this doc renames the *interface* to ZECT terminology and treats the third-party project as one replaceable provider behind it, per your branding clarification.

## Diagram

```
ZECT Desktop — Electron and React
|
+-- Workspace UI
|   +-- project explorer
|   +-- repository explorer
|   +-- code editor
|   +-- diff viewer
|   +-- terminal
|   +-- agent timeline
|   +-- approval center
|
+-- ZECT FastAPI Control Plane
    |
    +-- Project Domain
    +-- Repository Domain
    +-- Agent Run Domain
    +-- Workspace Domain
    +-- PR Review Domain
    +-- Integration Domain
    +-- Personal Agent Domain
    +-- Security Incident Domain        (ON HOLD — see ROADMAP.md Phase 9)
    +-- Voice Domain
    +-- Permissions Domain
    +-- Audit Domain
    |
    +-- ZECT Provider Adapters           <- renamed from "Runtime Adapters"
        +-- Coding Engine Provider       <- was "OpenHands coding runtime"
        +-- Voice Engine Provider        <- currently the OpenAI Realtime API directly;
        |                                   LiveKit Agents is one *candidate* provider
        |                                   behind this interface, not a requirement
        +-- Browser Automation Provider  <- was "Playwright / Browser Use"
        +-- Desktop Automation Provider  <- current: OS-level SendKeys-style
        +-- Source Control Provider      (GitHub today)
        +-- Issue Tracker Provider       (Jira today)
        +-- Team Chat Provider           (Slack today)
        +-- Email Provider
        +-- Detection Provider           (ON HOLD — was Wazuh/osquery/Velociraptor)
```

## The rule this encodes

For every "Provider" box above:
1. ZECT defines the interface (method names, request/response shapes) in ZECT's own terms.
2. A concrete implementation lives in one adapter module and may use a third-party library/SDK/self-hosted service internally.
3. Nothing outside that adapter module — no route name, no DB column, no UI string, no log line shown to you in the app — names the underlying third-party project.
4. Swapping providers means writing a new adapter against the same interface; callers don't change.
5. Where a license requires attribution, it lives in `THIRD_PARTY_NOTICES.md` / dependency metadata — never removed, never hidden, just not surfaced in the product's own UI/branding.

This is exactly the pattern already used today for MCP adapters (`services/mcp/adapters/{github,jira,slack,confluence,datadog}.py` behind one `execute_tool(server_id, tool_name, ...)` interface) and for TTS (`chatterbox_client.py` / `openai_tts.py` behind the `/api/mentrix/voice/speak` contract) — the target architecture generalizes a pattern that's already proven in this codebase, not a new idea.

## Interface naming for the two highest-risk-of-leaking-a-brand-name phases

- **Phase 2 (coding engine):** interface is `CodingAgentRuntime` in the original roadmap. Rename to **`ZectCodingEngine`** (or similar ZECT-prefixed name) for anything that surfaces in logs/UI/DB (e.g. an `engine_provider` column value should read `"zect_native"` or `"sandboxed_v1"`, never `"openhands"`). Internal adapter module `adapters/coding_engine_openhands.py` (or similar) is fine — that's implementation-detail file naming, not a public contract.
- **Phase 6 (voice):** already clean today — ZECT talks to OpenAI's Realtime API directly, with no separate "LiveKit" branding anywhere. If a future provider swap (e.g. to LiveKit) happens, it goes behind the existing `startMentrixRealtime`/voice-session interface, which is already ZECT-named.

## Backend layout change (Phase 1)

Current (`services/` organized by feature — see CURRENT_ARCHITECTURE.md) moves toward:

```
backend/app/
  api/              # thin FastAPI routers, no business logic
  domains/          # one module per domain in the diagram above
  adapters/         # provider adapters (per the rule above)
  infrastructure/   # db, auth, config, vault
  workers/          # background job execution (currently missing entirely)
```

This is a real refactor, not a rename — scope it as its own Phase 1 plan with a file-by-file move list before touching anything, per the roadmap's own execution rules.

## Agent Run state machine (target)

```
created -> queued -> provisioning -> running -> awaiting_approval -> running -> validating -> completed
Terminal: failed | cancelled | timed_out
```

Current `MentrixRun.status` (`running, completed, awaiting_approval, needs_human, approved, pr_created, failed, cancelled`) is a real but non-identical state machine — missing explicit `queued`/`provisioning` pre-run states and a distinct `validating` state (currently folded into the lint/sandbox/review gates). Reconciling these is Phase 1 work.

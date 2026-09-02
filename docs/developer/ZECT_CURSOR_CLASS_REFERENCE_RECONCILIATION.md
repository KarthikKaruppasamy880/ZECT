# ZECT Developer — Cursor-Class Reference Reconciliation

Companion to `ZECT_CURSOR_CLASS_ASK_PLAN_AGENT_REBUILD_MASTER_V1.md`. This document is the required
"study before code" deliverable: it records what Roo Code and OpenHands actually do (with upstream
SHA/license), what ZECT actually does today (with exact file:line evidence, gathered by direct code
inspection — not assumption), and classifies every capability so the CP-01..CP-10 PR sequence has a
concrete, cited basis. No runtime code is changed by this document.

No source, filenames, or branding from either reference project is reused. Only architectural
concepts are adopted, each tagged with its origin below.

---

## 1. Upstream references studied

### Roo Code
- Repo: `github.com/RooCodeInc/Roo-Code`
- Commit observed: `b867ec9145750d0ae1ff7f02d35406e9bf2a0b16` (`main`)
- License: Apache License 2.0

### OpenHands
- Repo: `github.com/OpenHands/OpenHands` (org renamed from `All-Hands-AI`; old slug still resolves as history)
- Commit observed: `a4aca995912b5041ed5c9f8dd4389b06fc283cab` (`main`)
- License: MIT
- Companion SDK repo: `github.com/OpenHands/software-agent-sdk`
- Commit observed: `e26683288ab4dd69518810016b74682de2a8c4e4` (`main`)
- License: MIT

Both observed 2026-09-02.

---

## 2. Roo Code patterns worth adopting

| # | Pattern | Where in Roo Code | Concept to adapt into ZECT |
|---|---|---|---|
| 1 | Mode → tool-group allowlist enforced **in code twice** (tool-list construction *and* execution-time) | `packages/types/src/mode.ts` (`DEFAULT_MODES`), `src/core/tools/validateToolUse.ts` (`isToolAllowedForMode`), `src/core/prompts/tools/filter-tools-for-mode.ts` | ASK/PLAN/AGENT must have a real tool allowlist checked before sending the tool list to the model *and* again before executing any tool call — not prompt text alone. |
| 2 | Edit-scope restriction per mode via `fileRegex` (e.g. Architect can only touch `.md`) | `mode.ts`, `FileRestrictionError` | PLAN mode should be code-enforced to only write `.plan.md`-family paths, not merely instructed to. |
| 3 | Two distinct handoff primitives: cheap same-task mode swap vs. structured new delegated task | `SwitchModeTool.ts`, `Task.startSubtask()` (`new_task`) | ASK→PLAN should be a "mode swap" (same WorkItem, same history) not a new object; a future Orchestrator-style delegation (e.g. spinning off a Debugger) should be the structured-seed-message primitive instead. |
| 4 | @mentions resolve to typed structured content blocks with truncation metadata | `src/core/mentions/index.ts`, `src/shared/context-mentions.ts` | ZECT's context items already use `ProvenanceItem`-like shapes in some places (`agent_context.py`) — this should become the *only* way any context enters a prompt, including attachments and grep hits, with explicit truncation metadata surfaced to the UI. |
| 5 | Expensive context tools (semantic search) gated behind explicit feature/config checks; model pulls context on demand via tool call | `filterNativeToolsForMode`, `codebase_search` tool | Ties directly into ZECT's Lattice `READY`/`NOT_INDEXED` states — when not ready, ASK should either fall back explicitly and *say so*, or not offer repo-grounded claims at all, rather than silently grep-fallback and still speak confidently. |
| 6 | Project-level MCP config (`.roo/mcp.json`) merges over global, watched for changes; MCP tools mode-gated identically to native tools | `McpHub.ts` | ZECT's MCP `hub.py` has no mode-awareness at all (confirmed below) — should gain the same mode gate as native tools once one exists. |
| 7 | Terminal streams via discrete events (`line`, `shell_execution_complete`) | `ExecaTerminalProcess.ts` | Directly reusable concept for ZECT's PTY/App Runner output surfacing to the Mission event log. |
| 8 | One shared, validated schema for built-in and custom modes — enforcement code never branches on "is this custom" | `CustomModesManager.ts`, `modeConfigSchema` | If ZECT ever exposes custom modes, this avoids a second enforcement path. |
| 9 | Checkpoints and conversation persistence are two separate subsystems (shadow-git file snapshots vs. task-message persistence) | `ShadowCheckpointService.ts`, `task-persistence/` | ZECT already separates Mission JSON-file state from WorkItem DB rows (see §4) — this validates keeping them separate rather than merging, but argues for making the *linkage* explicit and bidirectional (see Finding W2 below). |

## 3. OpenHands patterns worth adopting

| # | Pattern | Where in OpenHands | Concept to adapt into ZECT |
|---|---|---|---|
| 1 | Discriminated typed event union (`ActionEvent`, `ObservationEvent`, `AgentErrorEvent`, ...) with a dedicated renderer per type | `src/types/agent-server/core`, `event-message.tsx` | ZECT Mission events are currently untyped string literals appended to a list (see Finding M2) — should become a real discriminated union so the UI can render diff/terminal/browser/error events distinctly instead of one generic log line. |
| 2 | Hard REST+WS "Agent Server" boundary — UI never directly touches the execution sandbox | `openhands-agent-server` README, routers | ZECT already has this shape in principle (frontend → FastAPI → coding_engine) — the gap is that Missions have **no** streaming boundary at all (polling only, Finding M3), unlike OpenHands' explicit WS. |
| 3 | `RemoteWorkspace` abstraction — sandbox is "any HTTP-reachable execution surface"; Docker is just one backend | `openhands-workspace` | Not urgent for ZECT today (git-worktree isolation already works, Finding A4), but worth keeping in mind if ZECT ever needs remote/hosted execution. |
| 4 | Single append-only per-conversation event log that every tool (terminal/browser/file) writes into | `openhands-sdk/conversation/` | Directly addresses ZECT's Context Manager duplication (Finding C1) — one canonical event/context log per Mission, not three independent builders. |
| 5 | Event schema separates **visible curated `thought`** from raw provider reasoning/CoT; UI collapses raw CoT by default | `event/llm_convertible/action.py`, `CollapsibleThinking` | Both golden-test mandates already require "do not expose hidden chain-of-thought" — this is the concrete mechanism: a schema-level split, not a UI filter bolted on after the fact. |
| 6 | Explicit allowlist of what crosses the host↔sandbox boundary in *both* directions (env vars in, telemetry out) | `agent_server/README.md`, `forward_env` defaults | Directly applicable to a regulated insurance environment — ZECT should have the same explicit, auditable allowlist for what an Agent Mission's worktree/process can see from the host and what evidence/telemetry can leave it. |

---

## 4. Current ZECT — verified findings (file:line cited)

### A. ASK

- `POST /api/mentrix/developer/ask` → `backend/app/domains/work_items/router.py:275` (`developer_ask`) → `MentrixDeveloperService.ask()`, `backend/app/services/work_items/developer_service.py:353`.
- `AskIn` (`router.py:239`) has **no `model` field**. `ModelSelector.tsx`'s value is never sent for ASK (`MentrixCodingAgentPanel.tsx:929-936`, `api.ts:169-178`) — cosmetic only for this mode. (It *is* wired for AGENT mission sessions via `codingAgentCreateSession`, so the gap is ASK-specific, not app-wide.)
- Repo resolution: `resolve_authorized_repository_ids()` (`multi_repo_context.py:14`) → `_build_pack()`/`_build_multi_repo()` (`developer_service.py:118`/`313`).
- Grounding: `_workspace_file_items()` (`developer_service.py:229`) does filename/keyword grep over `Repo.local_path`, capped at 12 items, runs regardless of Lattice state. Feeds `MentrixContextEngine.build()` (`context_engine.py:86`), token-budgeted ~8000, per-source truncation 1500-4000 chars.
- LLM call: `llm_phase.run_ask()` (`llm_phase.py:171`). **System prompt has no instruction to say "not found" when grounding is weak, and no post-hoc check that named entities in the answer actually appear in retrieved content.**
- `EvidenceVerifier` exists (`developer_service.py:72`) but is **never invoked inside `ask()`** — only used later, in mission-acceptance verification (line 858).

**Finding A1 (= task_800f64a7): ASK hallucination.** No anti-hallucination gate exists at all — confirmed root cause, not just symptom.

- Wrong-repo bug: `multi_repo_context.py::merge_context_packs` (line 84) — `primary = packs[0] if packs else ContextPack()` (line 93), and lines 94-100 copy `primary.repository_id/repository_ref/base_commit_sha` into the merged pack unconditionally. `packs[0]` reflects `repository_ids[0]`, which the frontend builds from fetched-repo order (`workspaceRoots.ts:65-73`, a plain filter), **not** the user's active-repo selection (`ActiveProjectContext.activeRepoId` is never consulted here).

**Finding A2 (= task_003a5c12): wrong Context Used repo.** Exact fix point: `merge_context_packs` must pick the pack whose `repository_id` matches the caller's active repo, not `packs[0]`.

### B. PLAN

- `POST /api/mentrix/developer/plan` → `router.py:315` → `developer_service.py::plan()` (line 509). `POST /api/mentrix/developer/approve-plan` → `router.py:336` → `approve_plan()` (line 632).
- Artifact convention: `backend/app/services/work_items/artifact_store.py`, `ArtifactStore` — writes **`PLAN.md`** (not `.plan.md`) under `<artifact_root>/<work_item_id>/PLAN.md`; hash = SHA-256 of newline-normalized content (`plan_hash_bytes`, lines 42-44). *(A separate, also-real path, `POST /api/coding-agent/plans`, writes the human-facing `.zect/plans/<id>-coding.plan.md` copy inside the actual target repo — this is the one Explorer/Monaco shows, and it is correctly workspace-scoped; confirmed live during the CMS benchmark.)*
- Hash/approval persistence: DB columns on `WorkItem` (`models.py:1605-1607`), written by `developer_service.py:574-580`/`632-646`.

**Finding B1 (= task_fd3b43f0), root cause pinned exactly.** `llm_phase.py::run_plan()` (line 243), `upgrade=True` branch: the system prompt built at lines 285-297 **literally contains the instruction text** `"Phases MUST include: inventory → port module N → tests → API eval → review."` (lines 288-290). The LLM echoes this instruction back verbatim as a phase heading instead of substituting a real module name — there is no template-substitution step that "silently failed"; none exists. The offline fallback `_offline_plan()` (lines 259-283) independently hardcodes generic phases ("Port module 1 (core)", "Port module 2 (integrations)") used whenever the LLM call itself fails.

This is a prompt-authoring bug, and it directly explains why PLAN never produces a real file-impact list: nothing in `run_plan()` asks the model to enumerate concrete existing/new file paths at all.

### C. AGENT

- `POST /api/coding-agent/missions` → `coding_agent.py:234` (`create_mission`) → `lifecycle.py::start_mission()` (line 1029). `.../approve-plan` → `coding_agent.py:281` → `lifecycle.approve_plan()`.
- Patch proposal: `backend/app/services/coding_engine/propose_patches.py::propose_from_plan()` (line 13). The LLM returns `{"patches_by_repo": {...}}`; the **only** validation before acceptance is `path.replace("\\","/").lstrip("/")` plus an empty/`".."`-traversal check (lines 62-64). **No existence check. No language/extension-vs-repo check.**
- Patch application: `lifecycle.py::_apply_patches()` (line 855) → `mentrix_agent_tools.py`. The `apply_patch` branch (lines 678-715) checks existence **reactively, at apply time** (`if not target.is_file(): return {"ok": False, "error": f"not_found:{rel}"}`, line 685). The `write_file` branch (606-676) has **no existence check at all** — it will create a file at any path.
- On failure, `_run_edit_test_review()` (lines 1487-1504) sets `repo["blocker"]` and `mission["phase"] = "blocked"`.

**Finding C1 (= task_6d5dc3e0), root cause pinned exactly.** `rel/campaign_management.py` is exactly this path: LLM proposes → sanitize-only filter passes it → apply attempt → reactive not-found → mission blocked. There is no proactive validation between proposal and apply, and (per Finding B1) PLAN never gave the model a real file-impact list to propose from in the first place — the two defects are one causal chain, confirmed.

- Worktree isolation itself is **correct and already verified working** (`isolation.py` mode selection, `workspace.py::provision_worktree()`/`dispose_worktree()`) — confirmed live during the CMS benchmark: primary checkout stayed clean, only the isolated worktree branch was touched, and the mission correctly reported `blocked` rather than faking success.

### D. Mission / EventStream

- `lifecycle.py::_emit()` (~line 324-359) appends `{"event","message","data","at"}` to `mission["events"]`, persists via `_save_mission()`, forwards to `observability.emit_event`.
- Phase/status values (`"awaiting_plan_approval"`, `"blocked"`, `"cancelled"`, ...) are **plain string literals**, not a typed enum.
- No `Evidence` class — ad hoc dicts (`verify_mission_evidence()`, line 905) with `code` values like `claimed_file_missing`, `worktree_sha_drift`, `browser_verification_unevidenced` functioning as a de facto taxonomy.

**Finding D1: no Mission streaming.** SSE exists for the separate, older "coding-agent sessions" feature (`coding_agent.py:81-134`) but **Missions have no streaming endpoint at all** — the only read path is `GET /api/coding-agent/missions/{id}`, and the frontend (`api.ts:2112-2135`) only ever polls it. Both golden-test mandates require live Mission activity visibility; today that's poll-based, not push-based, and the event shape is untyped strings rather than OpenHands-style discriminated events (§3.1).

### E. WorkItem lifecycle

- `models.py:1587-1628` — `status` enum (`status.py:6-56`), `plan_version`/`plan_hash`/`approved_plan_hash` (1605-1607) is the **real, working** hash-binding gate: `developer_service.py::start_agent()` (lines 666-669) requires `status in (PLAN_APPROVED, EXECUTING, NEEDS_HUMAN_DECISION)` **and** `approved_plan_hash == plan_hash`, else `409 plan_not_approved`. This part matches the mandate's "approval binds exact hash" requirement already — no fix needed here.
- `coding_mission_id` (line 1614) is a **string pointer, not a real FK** — the code comment at 1609-1613 explicitly documents this: the Mission store is JSON-file-backed, not SQL (per `ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md` Phase B). Set server-side in `coding_agent.py::create_mission()` (253-261).

**Finding E1: one-directional session reconciliation.** `frontend/src/lib/workspaceSession.ts` persists `workItemId`/`activeRepoId`/`codingMissionId` in `localStorage`, independent of server state. `DeveloperWorkspace.tsx:335-360`: on a successful `getWorkItem(workItemId)` fetch it correctly overwrites the stale cached mission id from the server value (341-352) — but on failure (line 354-356, e.g. a 404 for a deleted/foreign WorkItem) it only resets the in-memory mission id, **never clears the stale `workItemId` in `localStorage` itself**. This is exactly the bug that made ASK silently keep answering inside the wrong, leftover WorkItem during the CMS benchmark until it was manually cleared from `localStorage` by hand.

### F. Context Manager

**Finding F1: three independent context-assembly implementations, not one pipeline.**
1. ASK & PLAN share `_build_pack()`/`_build_multi_repo()` (`developer_service.py`).
2. AGENT has its own reimplementation: `agent_context.py::compose_rich_agent_context_pack()` (line 175) — whose own docstring (186-192) **admits** there are two hand-duplicated AGENT-context builders in the same file (the "rich" one and a "thinner, independently-implemented `compose_coding_agent_context`").
3. `@mention` resolution (`coding_agent.py::/context/resolve-mentions`, 434-448) is a **third**, ad hoc builder — calls `MentrixContextEngine().build()` directly with no Project Intelligence snapshot, no Lattice hits, no repo resolution at all.

This directly explains why fixing Finding A2 (wrong repo) in one place won't automatically fix it everywhere — there are three places `repository_id` resolution logic could independently drift.

### G. Graphify / Lattice

Confirmed **working as designed** — no fix needed:
- `lattice/indexer.py` — real persisted code graph; `graphify_snapshot.py` is explicitly "a thin adapter — Lattice is the store, no second graph database" (code comment).
- `get_lattice_status()` (line 760) — real state machine (`NOT_CONFIGURED/NOT_INDEXED/INDEXING/READY/STALE/ERROR/NOT_APPLICABLE/REGRESSION`) driven by clone status, index stats, and commit-SHA drift.

**Finding G1: triplicated grep fallback.** The local-grep fallback exists independently in `developer_service.py::_workspace_file_items()` (229) **and again** in `agent_context.py::_workspace_grep_items()` (255) — same concept, two implementations, feeding Finding F1.

### H. Skills

**Finding H1: no skill-selection step exists in ASK/PLAN/AGENT at all.** `skill_governance.py` is real and used — but exclusively by the Personal Agent domain (`personal_agent/skills_engine.py`, `schedule_executor.py`). Zero references in `developer_service.py` or `lifecycle.py`. `coding_agent.py`'s `SessionCreate.skill_id` field is forwarded to the native runtime but never validated against `skill_governance.tool_allowed()`/`normalize_manifest()` — an unenforced, effectively dead parameter on that path. Both golden-test mandates expect visible "Loaded skill: ..." activity; today nothing loads a skill in this workflow.

### I. Tool Registry / MCP

**Finding I1: no mode-aware tool-permission layer exists — the single biggest structural gap vs. Roo Code.** `mcp/hub.py::_rules_block()` filters by rule type (review/security/deploy) and regex, with zero awareness of ask/plan/agent. `permissions.py`'s `PermissionRule`/`CapabilityGrant` are scoped by global/team/user, not by mode. The *entire* ASK→PLAN→AGENT enforcement today is the WorkItem status-machine gate (Finding E, which does work) — there is no code path anywhere that checks "is tool X allowed in mode Y" before executing it. `mentrix_agent_tools.py`'s tool loop runs the identical tool set regardless of which mode invoked it. This is the direct structural gap Roo Code's `isToolAllowedForMode` (§2.1) closes.

### J. App Runner

Confirmed **working as designed** — no fix needed:
- `app_runner.py` — real, admin-role-gated, workspace-allowlisted subprocess manager, correctly distinct from the PTY (`pty_session.py`, winpty-based).
- Mission-attached for real: `mentrix_agent_tools.py::start_app/restart_app` (250, 270) dispatch into App Runner; `lifecycle.py:1477-1480` stops owned processes after each browser-verification attempt, scoped to the Mission's worktree.

### K. Attachments

**Finding K1 (= task_be45fab8), more precise than first reported.** `DocumentContentVersion` (`models.py:1824-1836`) has `UniqueConstraint(scope, project_id, owner_user_id, content_sha256)`. Dedupe logic **does exist** — `find_reusable_content_version()` (`service.py:258-273`) — but the reuse branch is gated to `if cv and scope == PROJECT_SHARED` (line 369) only. For `USER_PRIVATE` (the default scope, used by essentially all ASK-composer uploads), the computed `cv` is discarded and execution always falls through to a fresh insert (line 511-544), which collides with the same unique key on a byte-identical re-upload → unhandled `IntegrityError` → raw SQL/path leak to the client (no `IntegrityError` handling exists anywhere in this module).
- Attachments reach ASK/PLAN context via `retrieve_document_context()` inside `_build_pack()` (line 163) — wrapped in a bare `try/except Exception` that **silently** falls back to `doc_items = []` (170-171) on any failure. Worth noting as a related, quieter failure mode: a broken document-retrieval call currently fails invisibly rather than surfacing in Context Used.

### L. Explorer / Diff refresh

**Finding L1: no watcher/websocket — refresh is a side effect of the mission API response shape.** `file_watcher.py` exposes a full polling API but is **never called from `frontend/src`** (dead code from the UI's perspective, confirmed by repo-wide search). The actual mechanism: `MentrixCodingAgentPanel.tsx:1216-1239` reads `created.files`/`approved.files` off the mission-creation/approve-plan response bodies and calls `onFilesChanged?.(files)`; `DeveloperWorkspace.tsx:1372-1385` reacts by calling `loadTree()` + `refreshGit()` + conditionally reloading the open file. This works for the specific case tested, but anything that changes files outside that exact response path (a background process, a manual terminal edit, the dead file-watcher) leaves the Explorer stale until a manual "Refresh" click.

### M. Model Router

**Finding M1: no task-complexity router exists anywhere.** Two unrelated, non-competing mechanisms:
1. `model_selection.py`'s static `MODELS` registry + `/api/models/chat` — real, but **not called by the ASK/PLAN/AGENT path at all**; only used by a separate, older `/api/llm/ask` screen (`AskMode.tsx`).
2. `fallback_policy.py::resolve_model_route()` — used by `llm_phase._chat` for ASK/PLAN — chooses **local vs. cloud provider** only (env-driven), not by task complexity; both branches still resolve to one single env-configured model id.

`ModelSelector.tsx`'s value **is** actually sent and used for AGENT mission sessions (`codingAgentCreateSession`) — the cosmetic gap (Finding A1's model-field absence) is specific to ASK's `AskIn`/`developerAsk()`, not universal.

### N. Tests

165 files under `backend/tests/fixes_and_phases/`. Two concrete, confirmed test gaps at exactly the right layer:
- `test_document_intelligence.py`/`test_workitem_attachments.py` test dedupe for `PROJECT_SHARED` cross-user and `USER_PRIVATE` cross-user isolation, but **never** the same-user/same-scope/same-project double-upload — precisely the untested path that crashes (Finding K1).
- `test_multi_repo_developer.py` covers authorization filtering and per-repo build/evidence isolation, but **nothing asserts `context_pack.repository_id` matches the actively-selected repo** when a project has multiple authorized repos — the exact layer Finding A2 lives at.
- No test found asserting a proposed patch target must exist (or be explicitly `CREATE_NEW`) before being applied (Finding C1) — `test_build_diff_apply.py`/`test_diff_viewer_path_allowlist.py` exist but were not confirmed to cover this specific case.

---

## 5. Capability classification matrix

| Capability | Classification | Basis |
|---|---|---|
| WorkItem plan-hash approval gate (start_agent) | **ZECT_WORKING** | Finding E — real, already matches mandate |
| Git worktree isolation for Missions | **ZECT_WORKING** | Finding C — confirmed live during CMS benchmark |
| App Runner (subprocess manager, Mission-attached) | **ZECT_WORKING** | Finding J |
| Lattice/Graphify indexing + status state machine | **ZECT_WORKING** | Finding G |
| Mission "blocked" fail-safe on bad patch (doesn't fake success) | **ZECT_WORKING** | Finding C — the one AGENT behavior that's correct today |
| ASK/PLAN shared context builder (`_build_pack`) | **ZECT_PARTIAL** | Finding A/F — exists and shared, but ungrounded and duplicated elsewhere |
| Attachment dedupe | **ZECT_PARTIAL** | Finding K1 — exists for one scope, missing for the default scope |
| Explorer/Diff refresh after Agent edit | **ZECT_PARTIAL** | Finding L1 — works for the tested path, fragile otherwise |
| Model routing | **ZECT_PARTIAL** | Finding M1 — local/cloud fallback exists, task-complexity routing doesn't; AGENT sessions get a real model choice, ASK doesn't |
| ASK anti-hallucination gate | **ZECT_BROKEN** | Finding A1 — does not exist |
| ASK/AGENT "Context Used" repo truthfulness | **ZECT_BROKEN** | Finding A2 — always first-added repo |
| PLAN file-impact list / placeholder rejection | **ZECT_BROKEN** | Finding B1 |
| AGENT pre-write path/language validation | **ZECT_BROKEN** | Finding C1 |
| Mission live streaming | **ZECT_BROKEN** | Finding D1 — polling only, no push |
| Mode-aware tool-permission registry | **ZECT_BROKEN** (does not exist) | Finding I1 |
| Skill routing in ASK/PLAN/AGENT | **ZECT_BROKEN** (does not exist) | Finding H1 |
| Session↔WorkItem reconciliation on fetch failure | **ZECT_BROKEN** | Finding E1 |
| Canonical single Context Manager pipeline | **ROO_PATTERN + OPENHANDS_PATTERN → REIMPLEMENT** | Roo's on-demand tool-gated retrieval + OpenHands' single append-only event/context log, replacing Findings F1/G1's triplication |
| Mode → tool-group enforcement | **ROO_PATTERN → ADAPT_PATTERN** | §2.1/§2.2 — adopt the two-layer (list-construction + execution-time) enforcement concept, ZECT-native implementation |
| ASK→PLAN handoff primitive | **ROO_PATTERN → ADAPT_PATTERN** | §2.3 — "mode swap" concept fits ZECT's existing same-WorkItem model; no new object needed |
| Mission event schema | **OPENHANDS_PATTERN → REIMPLEMENT** | §3.1/§3.5 — discriminated typed events replacing the current plain-string list |
| Thought/CoT separation in Mission events | **OPENHANDS_PATTERN → ADAPT_PATTERN** | §3.5 |
| Roo/OpenHands source code or branding | **DO_NOT_COPY** | Explicit mandate constraint |
| Existing Mission/WorkItem/Context Manager/Graphify/Lattice/Skills/Tool Registry/App Runner/BrowserTool/Evidence systems themselves | **KEEP_ZECT** | Rebuild the handoff and grounding logic on top of these; do not replace them per mandate |

---

## 6. Proposed focused-PR plan (CP-01..CP-10)

Presented for approval before any code is written, per the Planning Mandate and this rebuild mandate's
own "reconciliation before code" requirement. Each ships as its own PR, no auto-merge, targeting `develop`.

| PR | Scope | Primary findings addressed |
|---|---|---|
| **CP-01** | Active-repo/context truth: fix `merge_context_packs` to select the pack matching the caller's active repo, not `packs[0]`; thread `activeRepoId` through from the frontend's repo-ordering call sites. | A2 |
| **CP-02** | ASK grounding/evidence enforcement: add an explicit "not found" instruction + a post-hoc check that named entities in the answer appear in retrieved `ProvenanceItem` content before returning; wire `EvidenceVerifier` into `ask()`. | A1 |
| **CP-03** | Attachment idempotency + error redaction: extend the `PROJECT_SHARED` reuse branch to `USER_PRIVATE`/all scopes; catch `IntegrityError` and return the existing version instead of a raw 500; strip paths/SQL from any client-facing error. | K1 |
| **CP-04** | ASK→PLAN context package: consolidate the "mode swap" concept (§2.3) so PLAN inherits ASK's assembled context object directly rather than re-deriving it; start collapsing Findings F1/G1's triplicated builders toward one shared assembly path. | F1, G1 |
| **CP-05** | Grounded Plan.md generator + path schema: fix the `run_plan()` prompt (remove the literal "port module N" instruction), require the model to enumerate a typed file-impact list (`MODIFY_EXISTING`/`CREATE_NEW`/`DELETE_EXISTING`/`REFERENCE_ONLY`/`NO_CHANGE`) per the mandate's schema. | B1 |
| **CP-06** | Plan validation + placeholder detection: deterministic pre-approval check that every `MODIFY`/`DELETE` path exists, every `CREATE_NEW` is justified, extensions match the repo's detected language, and reject known placeholder patterns ("Port Module N", "example/file.py", "TBD"). | B1, C1 |
| **CP-07** | Agent approved-path/write guard: `propose_patches.py` and `mentrix_agent_tools.py`'s `write_file`/`apply_patch` must check the target against the approved plan's file-impact list *before* attempting a write, not react after a 404. | C1 |
| **CP-08** | Strong model routing for planning/coding: extend `resolve_model_route`-style routing to consider task complexity (not just local/cloud), and give ASK the same real `model` plumbing AGENT sessions already have (Finding M1). | M1 |
| **CP-09** | Live activity + context provenance: typed Mission event schema (OpenHands-pattern discriminated union) plus a real streaming endpoint for Missions (currently polling-only); fix the session↔WorkItem reconciliation gap (Finding E1) so a stale `localStorage.workItemId` gets cleared on a 404. | D1, E1 |
| **CP-10** | CMS headed golden acceptance: rerun `ZECT_CMS_MCP_PLAYWRIGHT_SELF_HEALING_GOLDEN_TEST_V1.md` end-to-end against `cms-sbigeneral` through the real UI with Playwright/MCP, now that ASK/PLAN/AGENT are grounded. | All of the above |

Not included in this sequence (explicitly deferred, flagged if it resurfaces as a blocker):
- A formal mode-aware Tool Registry/MCP gate (Finding I1) and Skill routing in ASK/PLAN/AGENT (Finding H1) are real structural gaps but are larger, cross-cutting changes; recommend a dedicated CP-11/CP-12 after CP-01..CP-10 land and the grounding/handoff work proves out, rather than widening this sequence now.
- Explorer/Diff watcher-based refresh (Finding L1) — current mission-response-driven refresh is functional for the tested path; revisit only if it causes a real observed staleness bug.

## 7. Human gates

- Architecture gate (this document + the plan in §6): `READY_FOR_HUMAN_ZECT_CURSOR_CLASS_DEVELOPER_REVIEW_V1`
- CMS rerun gate (after CP-10): `READY_FOR_HUMAN_ZECT_CMS_REAL_CODING_AGENT_REVIEW_V2`

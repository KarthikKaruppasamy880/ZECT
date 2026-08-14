# ZECT — CORE PRODUCT UX RECONCILIATION

## Mission
Fix the gap between ZECT's backend capabilities and its real product UX. Audit first with headed Playwright; then implement only proven gaps. Reuse existing agents, Project/Repo, WorkItem, Process, PresentationProvider, Voicebox, PI, LRR and EvidenceVerifier.

Scope:
1. ZECT Present
2. Developer Workbench
3. Projects/data hygiene
4. Work Items
5. Processes/Jira/Camunda
6. consistent ZECT UX + live acceptance

Do not start KV cache, Graphify, OCR/XLSX, broader Web or new agents in this tranche.

## 1 — Audit first
Run current `develop`. Capture before screenshots. Classify each capability:
`WORKING | BACKEND_ONLY | UI_BROKEN | PARTIAL | MISSING | REGRESSION | TEST_DATA_LEAK`.
Read latest canonical/final/Present/Developer/repository/WorkItem/process/Voice acceptance. Do not trust old PASS over live UI.

## 2 — Run Presenton locally as a reference
Start the existing local Presenton and inspect its real UI with headed browser automation. Study Generate/prompt/document attach, template gallery/built-ins/custom templates/upload/previews, provider/model settings, generation progress, editor, thumbnails, AI panel, blocks/text/charts/tables/images/elements, slide add/delete/reorder, rewrite/regenerate and export.

Create:
`Presenton capability | ZECT backend | ZECT UI | reuse/adapt? | ZECT-native needed? | out of scope`.

Do not expose Presenton branding to ZECT users. Before direct code reuse, inspect its license/obligations. If direct reuse is undesirable/incompatible, reproduce the interaction/product concept with ZECT-owned code.

## 3 — ZECT Present target
Replace the diagnostic-form experience with:
`Present → New → Prompt/Document/Existing Deck → Template → Generate → Editor → AI refine → Notes/Rehearse → Export/Present`.

New screen should center a large prompt, Attach Document/Add Project Context, Template, Slides, Audience, Language and Generate. Below it show visual template cards.

Normal users must never need provider UUIDs, `ZINNIA_PRESENTON_TEMPLATE_ID`, raw file paths or Presenton configuration.

## 4 — Zinnia template end-to-end
Required:
`Upload Zinnia PPTX → validate → parse/import/register → preview → ZECT template id → provider mapping → READY → gallery → select → prompt → Generate → template_sent → PPTX → zinnia_verified=true`.

Expose actionable lifecycle:
`UPLOADING | VALIDATING | IMPORTING | BUILDING_PREVIEW | READY | ERROR`.
No opaque `TEMPLATE_NOT_READY` without explanation/retry.

## 5 — My Templates
Support:
`My Templates → Upload PPTX → validate → preview → register → select → generate`.
Scopes: `USER_PRIVATE | ORG_SHARED`.
Allow rename/preview/archive/delete/default where safe.

Clearly distinguish:
- Upload PPTX as reusable template
- Upload existing deck for narration/editing

## 6 — Generation must work
`prompt + template + slides + audience + optional document/project context → Generate`.
Show progress:
`Preparing → Outline → Slides → Applying template → Finalizing → Ready`.
Errors must be actionable and provider-neutral.

## 7 — Presentation editor
After generation open a real editor with resizable Slides | Canvas | AI/Properties panels. Surface supported thumbnails, reorder/add/delete, text edit, rewrite, shorten, executive tone, regenerate, images/charts/tables/elements and notes. Do not claim unsupported features.

## 8 — Presentation vs Voice
Canonical ownership:
- ZECT Present = create/edit/manage deck
- Notes & Rehearse = narrate/rehearse that deck
- Companion Voice may shortcut into Present/Rehearsal but must not duplicate generation logic.

## 9 — Voice options
Support both:
- My cloned voices
- ZECT/local standard voices
- approved provider voices
- No narration

Resolution:
`presentation selection → user default presentation voice → org/ZECT default`.

Never silently fall back from a selected clone. Show Retry / Choose another voice / No narration.

Exactly one `audio_owner`: clone OR local_tts OR cloud_tts. Reuse existing voice FSM/audio_owner; never clone+PCM double voice.

## 10 — Voice live proof
Prove both clone and standard voice:
`generated PPTX → notes → select voice → slide 1 audio → slide 2 audio`.
Verify correct user clone, cross-user denial, real backend not stub, non-empty audio, correct slide/notes/audio, no overlap/double voice, Disconnect FSM, explicit fallback.

## 11 — Developer Workbench redesign
Do NOT rebuild Coding/Planner/Test/Ultra Review/LRR. Fix the shell.

Observed defects:
- editor/workspace too small
- repo onboarding permanently consumes space
- terminal/Timeline/Context too narrow
- agent prompt buried
- idle multi-repo strip wastes space
- fixed dashboard-card layout
- weak Explorer→Editor→Agent hierarchy
- visible `'str' object has no attribute 'get'` Timeline regression

Fix Timeline root cause.

Target:
```text
Project | Repo | Branch | WorkItem | Model | PI
------------------------------------------------
Explorer |             Editor              | Mentrix Agent
         | code/diff/symbols               | ASK/PLAN/AGENT
------------------------------------------------
Terminal | Problems | Tests | Timeline | Evidence | Context
```

Use real draggable left/right/bottom splitters. Persist layout per user/workspace; provide reset. Panels must be toggleable. Editor is primary.

## 12 — Collapse onboarding after repo activation
Once active, show compact header:
`Project | Repo | Branch | clean/dirty | PI READY | Switch Repo | Add Repo`.
Open/Clone/Discover/Attach expands only when requested. Multi-repo idle state should also be compact.

## 13 — Projects data hygiene
Normal Projects must show authorized real projects, not acceptance fixtures such as Phase6 Onboard/Moved/Priv/Dirty/Live.

Audit why test fixtures persisted. Fix tests to use isolated DB/schema/user/org/namespace + cleanup/rollback. Provide safe cleanup only for records proven to be fixtures; never delete legitimate data by name pattern.

Do not hardcode ZECT/ZOAS, but the current user should only see projects they actually own/can access. Add useful search/filter/Active/Archived/org controls.

## 14 — Work Items product model
Canonical:
`Project → WorkItem → ASK/PLAN/AGENT → Operations → Repos/PRs/Tests/Evidence`.

A WorkItem can originate from user request, Jira, Camunda, GitHub issue, incident, Learning handoff or manual plan, and may affect multiple repos.

Fix fixture pollution.

List should show Title, Source, Project, Status, Priority, Owner, affected repos, Plan, Agent, PRs, Updated. Filters: My Work/Project/Jira/Camunda/GitHub/Manual/New/Planned/Running/Blocked/Ready/Done.

Detail should show Request/source, Project, Requirements, Context, PLAN, approvals, operations, tests, review, PRs, evidence, timeline. Actions: Ask/Create Plan/Approve/Run/Pause/Resume/Review/Open PR according to policy/state.

## 15 — Processes product model
Processes connect external workflow systems to ZECT:
`External task/process → Connector → normalized ZECT Process/WorkItem → Project → ASK/PLAN/AGENT → Evidence → optional source update`.

Do not create separate WorkItem systems per connector.

### Jira
`Jira issue → sync → Project mapping → WorkItem → PLAN → approval → AGENT → PR/tests/review → EvidenceVerifier → optional authorized Jira update`.
Ticket text is untrusted external task context, never system instructions.

### Camunda/Cockpit
Audit existing connector architecture.
Target:
`Process instance/task/incident → ZECT Process → WorkItem → Project → investigate/PLAN/AGENT → evidence → optional authorized completion/update`.

Cockpit incident use cases: summarize incident, map project/runbook, identify likely owner/code, create remediation WorkItem, plan/execute approved fix, evidence. Never blindly complete production tasks.

## 16 — Sample Process
Provide a safe demo:
`Fix Failed Order Validation → Review incident → Investigate code → Plan → Human approval → Agent → Tests → Review → Evidence → Complete`.

If local Camunda is available, import/run a safe sample BPMN. Otherwise provide an isolated SAMPLE ZECT fixture. Demonstrate Process→WorkItem→Project→PLAN/AGENT.

## 17 — Shared design system
Standardize spacing, typography, status chips, buttons, forms, tabs, empty/error/loading states, splitters, panels, dialogs, tooltips, keyboard focus and responsive behavior. Aim for professional IDE/SaaS density, not oversized fixed cards. Do not pixel-copy Cursor or Presenton; use them as usability references while preserving ZECT identity.

## 18 — Headed acceptance
Present: Zinnia upload/register/ready, gallery, prompt, generation, editor, notes, clone voice, standard voice, export.

Developer: active repo, collapsed onboarding, Explorer/file edit, drag splitters, hide/show panels, terminal, ASK/PLAN/AGENT, Timeline/Context, no `'str'...get` error, layout persistence, multiple viewport sizes.

Projects: authorized real/demo data only; fixture pollution removed.

WorkItems: Project/source/PLAN/AGENT/repos/evidence understandable; fixtures isolated.

Processes: sample process and configured external mapping; Process→WorkItem→Project; approval/action flow.

## 19 — Security
Test cross-user projects/WorkItems/voice clones/templates, cross-project repo context, Jira/Camunda untrusted content, forged external IDs, unauthorized process completion/Git action, prompt injection and secret exposure.

## 20 — PR strategy
Recommended:
- UX1 data hygiene + Projects/WorkItems
- UX2 Developer Workbench + Timeline fix
- UX3 Present templates/generation/editor
- UX4 Present voice/rehearsal
- UX5 Processes/Jira/Camunda + sample
- UX6 full headed acceptance/design polish

Each:
`audit → implement → tests → headed E2E → security → Ultra Review → fix Critical/Major → CI → PR → merge develop → sync → regression`.

## 21 — Acceptance artifact
Create `ZECT_CORE_PRODUCT_UX_RECONCILIATION_ACCEPTANCE.md` covering Presenton reference matrix, ZECT Present before/after, Zinnia/generation/editor/clone+standard voice proof, Developer splitters/layout/Timeline, Projects hygiene, WorkItem UX, Process/Jira/Camunda/sample, security, headed artifacts, CI/reviews/merged PRs/final SHA and remaining gaps.

## Stop
STOP after core UX is merged/re-proven. Do not start KV cache, Graphify, OCR/XLSX, broader Web or new agents.

Return:
`CORE_UX_PASS | CORE_UX_PARTIAL | BLOCKED | BLOCKED_EXTERNAL`.

Target:
`Cursor-class Developer usability + modern ZECT Present + Project Intelligence + WorkItem/Process orchestration + multi-repo + Ultra Review + EvidenceVerifier + enterprise security`.

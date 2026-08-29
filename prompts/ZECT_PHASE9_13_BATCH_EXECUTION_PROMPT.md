# ZECT PHASES 9–13 — BATCH EXECUTION PROMPT

## Goal
Execute the remaining Master Live Product Fix phases 9–13 sequentially without waiting for confirmation between phases. Stop after Phase 13.

## Frozen baselines
Do not redesign or reopen unless executable regression evidence proves a defect:

- ZECT Present A1–A8 / LIVE_VIABLE
- `zinnia-executive-v1`
- PresentationProvider
- Present Model Gateway routing
- Voicebox async generation
- A6 voice FSM
- Electron single-instance
- Phase 5 Navigation/State
- Phase 6 Repository Onboarding
- Phase 7 Project Intelligence
- Phase 8 ASK/PLAN/AGENT + LongRunningAgentRuntime

## Step 1 — Read current master plan
Read `.cursor/plans/master_live_product_fix_a8c0797d.plan.md`.

Before implementation:
1. enumerate exact current Phase 9–13 operations;
2. identify dependencies;
3. remove operations already satisfied by frozen work;
4. execute only remaining work in dependency order;
5. do not invent new phases or broaden scope.

## Execution policy
For each phase:

```text
implement
→ targeted tests
→ live/runtime proof where applicable
→ security checks
→ acceptance evidence
→ frozen regression smoke
→ PASS / PARTIAL / BLOCKED / BLOCKED_EXTERNAL
→ next phase
```

Do not wait for user confirmation between phases.

If a phase fails, root-cause and fix within scope. If still blocked, record the exact blocker and continue only if later phases do not depend on it. Never fabricate PASS.

## Architecture preservation
Reuse existing:
- WorkItem
- Project/Repo
- Project Intelligence
- Lattice/Blueprint
- Knowledge/Verified Memory
- Skills/Playbooks
- ContextEngine/ContextPack
- Model Gateway
- Permission Broker
- Connector Gateway
- LongRunningAgentRuntime
- Planner/Coding/Test/Review agents
- AcceptanceVerifier/EvidenceVerifier
- PresentationProvider
- ArtifactStore

Do not create parallel agents, orchestrators, repo catalogs, RAG/context engines, model gateways, memory systems, skills systems, connector gateways or evidence systems.

## Learning work
Where Phase 9–13 includes Learning/catalog work, make ZECT Learning usable:

```text
Choose Language/Skill
→ Learning Path
→ Topic/Lesson
→ Practice
→ Code
→ Run Tests
→ Hint
→ Retry
→ Evidence
→ Verified Progress
→ Project
```

Use existing LearningSource/Resource/Project, Skills, Developer Workspace, Coding Agent, Test Agent and EvidenceVerifier.

Initial language/path support where planned:
Python, JavaScript/TypeScript, Java, C#, Go, Rust, C/C++.

Modes:
`GUIDED | PAIR | DEMO | AUTONOMOUS`.

GUIDED teaches/hints and must not silently solve the complete exercise. Progress must come from actual test/evidence results. Preserve source/license/content-policy metadata for external learning resources.

## Gateway/integration work
Where defined in the current master plan, audit through existing gateways:
- Model Gateway
- Connector Gateway
- Permission Broker

Verify configured/unconfigured states, health, provenance, model/provider routing, no duplicate configuration and no silent fallback.

## UI/Recharts work
Where defined:
- fix real runtime warnings/errors;
- remove deprecated Recharts usage correctly;
- preserve chart behavior;
- verify browser/build/tests;
- avoid redesigning frozen Present/Developer surfaces without regression evidence.

## Packaging/Desktop work
Where defined, move toward:

```text
Install ZECT
→ Launch ZECT
→ required local services managed automatically
→ ZECT ready
```

Normal users should not manually start Vite/backend/Electron/Presenton UI/Voicebox/Rancher for ordinary usage where a managed lifecycle is possible.

Verify service lifecycle, secrets/config, logs, shutdown, health, upgrades, user data and Windows behavior before claiming installer-ready.

## Multi-user isolation
Preserve backend-enforced scopes:

```text
USER_PRIVATE
TEAM_SHARED
PROJECT_SHARED
ORG_SHARED
SYSTEM
```

Personal Companion conversations, personal memory, notes, documents, email/calendar, voice profiles, private presentation drafts and personal Learning progress remain private unless explicitly shared.

Authorized project/team members may reuse shared repo+commit intelligence:

```text
RepositorySnapshot
repository_id
commit_sha
Lattice
Blueprint
symbols
repo Knowledge
verified repo Memory
repo Skills/Playbooks
```

Do not duplicate expensive repo intelligence per user when the same authorized repo+commit snapshot can be safely shared.

Backend authorization is mandatory; frontend hiding is not security.

## Security
Check as applicable:
- secrets / `.env` / credentials
- filesystem scope
- network scope
- cross-user leakage
- cross-project leakage
- cross-org leakage
- unauthorized model/provider egress
- shell/tool permissions
- protected Git operations
- sensitive artifacts

Policy remains:

```text
Agent intent
→ Permission Broker
→ Security/DLP/Policy
→ Tool scope
→ Execution
```

The model is never the authority for security decisions.

## Model policy
Preserve:

`FAST | QUALITY | MAX | LOCAL | RESTRICTED | CUSTOM`

Record where applicable:
`requested_model, actual_model, provider, local_or_cloud, fallback_used, fallback_reason, latency`.

No hidden provider switching. RESTRICTED must not silently use an unapproved cloud model.

## Frozen regression smoke after every phase
Run regression smoke for:
- Present A1–A8
- `zinnia-executive-v1`
- PresentationProvider
- Present Model Gateway
- Voicebox async
- A6 voice FSM
- Electron single-instance
- Phase 5
- Phase 6
- Phase 7
- Phase 8

Fix phase-caused regressions before proceeding when possible and record evidence.

## Acceptance per phase
Record:
- objective
- operations
- files changed
- tests
- live evidence
- security checks
- regression results
- status
- blockers

Statuses only:
`PASS | PARTIAL | BLOCKED | BLOCKED_EXTERNAL`.

## Final acceptance
Produce:

`ZECT_PHASE9_13_FINAL_ACCEPTANCE.md`

Include:

```text
Phase | Operation | Implementation | Tests | Live Evidence | Security | Regression | Status | Blocker
```

Also report:
- exact files changed;
- completed operations;
- PARTIAL/BLOCKED/BLOCKED_EXTERNAL items;
- regressions found/fixed;
- unfinished sidebar surfaces;
- internal/advanced surfaces that should move into Settings;
- Learning status;
- packaging status;
- remaining B–D roadmap;
- whether a clean end-to-end release acceptance run is justified.

## Sidebar/Settings review
Report, but do not broadly redesign unless currently in scope.

Preferred user navigation direction:

```text
MENTRIX
  Companion
WORK
  Projects
  Work Items
BUILD
  Developer
  Runs
CREATE
  Present
LEARN
  ZECT Learning
AUTOMATE
  Processes
  Scheduled Tasks
MORE
  Knowledge
  Analytics
  Settings
```

Advanced/internal capabilities can later live under Settings:
Models, Integrations, Voice, Present, Repositories, Intelligence (Lattice/Blueprint/Knowledge/Memory/Skills/Playbooks), Automation, Security, System Health, Advanced.

## WorkItem/evidence integrity
WorkItem/run state remains authoritative across model calls, navigation, pause/resume and restart. LLM text cannot declare completion. EvidenceVerifier remains the authority for `READY_TO_SHIP`.

## Do not start B–D automatically
Unless the current Phase 9–13 master plan explicitly includes them, keep these as the next tranche:

- B — ZECT Document Intelligence
- C — ZECT Web Intelligence
- D — Expanded ZECT Learning

Report their dependencies after Phase 13.

## Stop condition
STOP after Phase 13.

Do not automatically start Document Intelligence, Web Intelligence, local-model expansion, Graphify, Project Intelligence redesign, Present redesign or Developer redesign.

Return the consolidated Phase 9–13 acceptance evidence for review.

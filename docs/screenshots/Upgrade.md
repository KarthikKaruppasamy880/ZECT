You are working on my product ZECT/Mentrix.

Primary repository:
https://github.com/KarthikKaruppasamy880/ZECT

Reference repositories:
- OpenHands:
  https://github.com/OpenHands/OpenHands
- LiveKit Agents:
  https://github.com/livekit/agents
- Browser Use:
  https://github.com/browser-use/browser-use
- Open Interpreter:
  https://github.com/OpenInterpreter/open-interpreter
- Wazuh:
  https://github.com/wazuh/wazuh
- osquery:
  https://github.com/osquery/osquery
- Velociraptor:
  https://github.com/Velocidex/velociraptor

PRODUCT INTENT

ZECT is my own branded commercial development and personal-agent product.

Mentrix is the assistant inside ZECT.

ZECT should eventually provide:

1. A Cursor-like developer workspace.
2. Repository understanding and code search.
3. Ask, Plan, Build and Review modes.
4. An autonomous but controlled coding agent.
5. Pull-request review.
6. GitHub, Jira and Slack integration.
7. Realtime voice interaction.
8. Voice-cloned narration and presentation delivery.
9. Browser automation.
10. Approved desktop access and file organization.
11. Personal workflows involving email, calendar and Slack.
12. Endpoint-security alert coordination.
13. Jira incident creation and Slack incident notification.
14. Skills, memory, automation and scheduled work.
15. Clear permissions, approvals and audit history.

IMPORTANT PRODUCT BOUNDARY

ZECT must own:

- branding and user experience;
- React/Electron desktop interface;
- FastAPI backend and public API;
- user authentication;
- project and repository state;
- permissions and approvals;
- integrations;
- audit history;
- PR-review pipeline;
- personal-agent policies;
- incident-response policies;
- voice experience;
- product licensing.

OpenHands must be treated only as a replaceable coding runtime.

Do not copy the entire OpenHands UI.
Do not rename OpenHands source and present it as original ZECT code.
Do not tightly couple every ZECT service to OpenHands.
Preserve all applicable third-party copyright and license notices.
Do not copy OpenHands enterprise-only or commercially licensed components.

ARCHITECTURAL PRINCIPLES

1. Modular monolith first.
2. Domain-oriented backend modules.
3. Adapter interfaces for external frameworks.
4. One reusable agent-run system.
5. One persistent event model.
6. Isolated workspaces for coding agents.
7. Least-privilege permissions.
8. Confirmation for consequential actions.
9. APIs before visual desktop automation.
10. Security products detect threats; Mentrix coordinates response.
11. All file operations must be previewable and reversible.
12. All external content is untrusted.
13. The LLM cannot grant itself permissions.
14. Never report completion unless tests actually pass.
15. Do not implement all phases in one change.

EXECUTION RULES

Work one phase at a time.

At the beginning of each phase:

1. Inspect the existing implementation.
2. Identify which parts already work.
3. Identify placeholders, duplicate implementations and dead code.
4. Produce a concise implementation plan.
5. List files expected to change.
6. State migration and rollback risks.
7. Wait for my approval before making broad architectural changes.

At the end of each phase:

1. Show files changed.
2. Show important code diffs.
3. Run formatting.
4. Run type checking.
5. Run unit tests.
6. Run integration tests where available.
7. Run frontend build.
8. Run backend startup validation.
9. Report actual command output.
10. List unresolved problems.
11. Do not begin the next phase without approval.

TARGET ARCHITECTURE

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
    +-- Security Incident Domain
    +-- Voice Domain
    +-- Permissions Domain
    +-- Audit Domain
    |
    +-- Runtime Adapters
        +-- OpenHands coding runtime
        +-- Mock coding runtime
        +-- LiveKit voice runtime
        +-- Browser automation runtime
        +-- Desktop accessibility runtime
        +-- GitHub adapter
        +-- Jira adapter
        +-- Slack adapter
        +-- Email adapter
        +-- Wazuh adapter
        +-- osquery adapter
        +-- Velociraptor adapter

BACKGROUND WORKERS

Use background workers for:

- coding-agent runs;
- PR analysis;
- repository indexing;
- security-alert enrichment;
- Jira incident creation;
- Slack notifications;
- scheduled tasks;
- voice-processing jobs where appropriate.

Do not run long tasks directly inside FastAPI request handlers.

CORE DATA MODELS

Create or normalize these models:

- User
- Project
- Repository
- RepositoryConnection
- Workspace
- Conversation
- AgentRun
- AgentEvent
- ToolAction
- ApprovalRequest
- Artifact
- PullRequest
- PullRequestReview
- ReviewFinding
- IntegrationConnection
- SecretReference
- PermissionGrant
- PolicyDecision
- AuditEvent
- Automation
- ScheduledTask
- SecurityAlert
- SecurityIncident
- IncidentEvidence
- FileOrganizationPlan
- FileMoveOperation
- VoiceSession

AGENT RUN STATE MACHINE

Use an explicit state machine:

created
-> queued
-> provisioning
-> running
-> awaiting_approval
-> running
-> validating
-> completed

Terminal states:

failed
cancelled
timed_out

Every state transition must be persisted and audited.

==================================================
PHASE 0 — REPOSITORY AUDIT AND PRODUCT REDUCTION
==================================================

Goal:
Understand ZECT before changing architecture.

Tasks:

1. Inspect the complete repository.
2. Detect frontend, backend, Electron, database and worker architecture.
3. List every sidebar route visible in the current code.
4. Mark each feature:
   - working;
   - partially working;
   - placeholder;
   - duplicate;
   - dead or unreachable.
5. Identify repeated components and repeated agent implementations.
6. Identify hardcoded data and mock API responses.
7. Identify security risks:
   - exposed secrets;
   - unsafe shell execution;
   - unrestricted filesystem access;
   - unvalidated webhooks;
   - browser credentials;
   - missing authorization;
   - permissive CORS;
   - unsafe Electron configuration.
8. Identify existing tests and their actual status.
9. Create:
   docs/CURRENT_ARCHITECTURE.md
   docs/TARGET_ARCHITECTURE.md
   docs/FEATURE_INVENTORY.md
   docs/THREAT_MODEL.md
   docs/ROADMAP.md
10. Do not change user-visible behavior during Phase 0.

Recommended initial navigation:

WORKSPACE
- Dashboard
- Projects
- Repositories
- Pull Requests

DEVELOP
- Ask
- Plan
- Build
- Review
- Runs

AUTOMATE
- Personal Agent
- Scheduled Tasks
- Incidents

PLATFORM
- Integrations
- Permissions
- Audit
- Settings

Hide unfinished items behind typed feature flags.
Do not delete them during the first phase.

Deliver:
- repository audit;
- route inventory;
- dependency diagram;
- duplicate-feature map;
- security findings;
- prioritized roadmap.

Stop after Phase 0.

==================================================
PHASE 1 — CORE PLATFORM AND SHARED AGENT RUNS
==================================================

Goal:
Replace disconnected page logic with one shared execution platform.

Tasks:

1. Refactor the backend into:

backend/app/
  api/
  domains/
  adapters/
  infrastructure/
  workers/

2. Keep business logic out of FastAPI routes.
3. Add services and repositories for:
   - projects;
   - repositories;
   - workspaces;
   - conversations;
   - agent runs;
   - approvals;
   - artifacts;
   - audit events.
4. Add database migrations.
5. Implement AgentRun state transitions.
6. Implement persisted AgentEvent streaming.
7. Implement WebSocket or SSE delivery to the frontend.
8. Add reconnect support using event sequence IDs.
9. Create one reusable frontend AgentWorkspace containing:
   - conversation;
   - execution timeline;
   - current step;
   - terminal output;
   - files changed;
   - diff;
   - test results;
   - approval request;
   - artifacts;
   - cancel;
   - retry.
10. Configure Ask, Plan, Build and Review as modes of this shared screen.
11. Add MockRuntime so tests do not require OpenHands.
12. Add audit records for all state-changing actions.

Do not integrate desktop control or security tools in this phase.

Stop after Phase 1.

==================================================
PHASE 2 — OPENHANDS CODING-RUNTIME INTEGRATION
==================================================

Goal:
Use OpenHands as an isolated coding engine behind ZECT.

Create this internal interface:

CodingAgentRuntime:
- start_run
- get_run
- stream_events
- submit_message
- approve_action
- reject_action
- cancel_run
- get_artifacts
- dispose_workspace

Implement:

- OpenHandsRuntime
- MockRuntime

Rules:

1. ZECT frontend must never call OpenHands directly.
2. ZECT FastAPI must proxy and authorize all requests.
3. OpenHands credentials must never reach the browser.
4. Use an independently running OpenHands Agent Server.
5. Use HTTP for commands and WebSocket streaming for events.
6. Translate OpenHands events into stable ZECT AgentEvent records.
7. Do not expose OpenHands-specific event shapes to React.
8. Add timeouts, retries and cancellation.
9. Add health checks and version reporting.
10. Pin compatible OpenHands dependency versions.
11. Do not install directly from an unpinned main branch in production.
12. Add THIRD_PARTY_NOTICES entries and preserve the MIT notice.

WORKSPACE SAFETY

1. Create one isolated workspace per AgentRun.
2. Prefer Docker or a remote VM.
3. Never provide the complete host filesystem.
4. Mount only the assigned repository.
5. Use a task-specific branch or Git worktree.
6. Block access outside the workspace.
7. Use restricted network access.
8. Never inject all host environment variables.
9. Give the agent only scoped temporary credentials.
10. Remove or expire the workspace after completion.
11. Preserve patches and artifacts before cleanup.

First vertical slice:

User selects repository
-> starts Build
-> ZECT provisions workspace
-> OpenHands reads repository
-> agent proposes plan
-> user approves
-> agent changes one file
-> agent runs tests
-> ZECT streams events
-> ZECT displays diff
-> user approves branch creation
-> run completes

Stop after Phase 2.

==================================================
PHASE 3 — CURSOR-LIKE DEVELOPER WORKSPACE
==================================================

Goal:
Make ZECT useful as a development environment.

Implement:

1. Repository file tree.
2. Monaco-based editor if not already present.
3. Search across repository.
4. Symbols and references where supported.
5. Git status.
6. File diff.
7. Branch and worktree display.
8. Terminal connected only to the assigned workspace.
9. Agent-generated change markers.
10. Apply/revert individual hunks.
11. Inline Ask.
12. Explain selected code.
13. Generate tests for selected code.
14. Fix selected issue.
15. Agent activity timeline.
16. Context selector:
    - selected file;
    - selected lines;
    - repository rules;
    - linked issue;
    - PR;
    - test output.

Do not allow the editor to silently write outside the task workspace.

Stop after Phase 3.

==================================================
PHASE 4 — PR REVIEW PLATFORM
==================================================

Goal:
Build a reliable PR reviewer rather than a single large prompt.

Pipeline:

1. Fetch PR metadata and diff through GitHub APIs.
2. Check out the exact merge base and head commit.
3. Run deterministic checks:
   - formatting;
   - linting;
   - type checking;
   - unit tests;
   - dependency audit;
   - secrets scanning;
   - static security analysis;
   - changed-code coverage where possible.
4. Construct targeted context for each changed section.
5. Run specialist reviews:
   - correctness;
   - security;
   - architecture;
   - maintainability;
   - tests;
   - performance;
   - concurrency;
   - API compatibility.
6. Produce structured findings.
7. Validate every file and line against the current diff.
8. Deduplicate findings.
9. Rank by severity and confidence.
10. Mark deterministic versus AI-generated evidence.
11. Require approval before posting to GitHub.
12. Support creating an OpenHands fix run for accepted findings.

ReviewFinding schema:

- category
- severity
- confidence
- title
- explanation
- repository
- commit_sha
- file
- start_line
- end_line
- evidence
- suggested_fix
- validation_status
- source
- fingerprint

Do not publish speculative findings as facts.
Do not post comments automatically in the first release.

Stop after Phase 4.

==================================================
PHASE 5 — PERMISSIONS, SECRETS AND AUDITING
==================================================

Goal:
Create the safety foundation before desktop and personal access.

Capabilities:

- repository:read
- repository:write_workspace
- command:run_sandbox
- command:run_host
- network:approved_domains
- branch:create
- branch:push
- pull_request:create
- pull_request:merge
- deploy:execute
- desktop:view
- desktop:control
- filesystem:scan
- filesystem:move
- email:read
- email:draft
- email:send
- slack:read
- slack:send
- jira:read
- jira:create
- jira:update
- security:read_alert
- security:collect_evidence
- security:contain_endpoint
- secret:use_reference

Implement:

1. Capability-based authorization.
2. User, agent, tool and workspace scopes.
3. Temporary grants with expiration.
4. Allowlisted resources.
5. Server-side policy evaluation.
6. Approval records.
7. Secret references rather than plaintext values.
8. Encryption at rest using an established secrets mechanism.
9. Secret redaction from logs.
10. Complete audit event chain.
11. Permission diagnostics page.
12. A global emergency-stop control.

Default policies:

Automatically allow:
- read assigned repository;
- search assigned repository;
- edit isolated task workspace;
- run approved tests in sandbox.

Require approval:
- install dependencies;
- access new network domain;
- push branch;
- create PR;
- send Jira, Slack or email;
- move desktop files;
- execute host commands.

Always require explicit approval:
- merge;
- deploy;
- delete files;
- kill processes;
- quarantine files;
- isolate endpoint;
- administrator commands;
- modify firewall;
- reset accounts;
- access password stores.

Stop after Phase 5.

==================================================
PHASE 6 — REALTIME MENTRIX VOICE
==================================================

Goal:
Repair voice latency and separate voice from the coding runtime.

Use LiveKit Agents as the primary realtime voice framework.

Architecture:

Electron microphone
-> LiveKit/WebRTC session
-> VAD or turn detection
-> realtime STT or speech model
-> Mentrix orchestrator
-> streamed TTS
-> persistent audio output

Requirements:

1. One persistent voice session.
2. One persistent AudioContext.
3. Stream LLM output.
4. Begin speech after the first meaningful phrase.
5. Synthesize the next phrase while the current phrase plays.
6. Do not block on each sentence.
7. Support interruption and cancellation.
8. Cancel stale responses with AbortController.
9. Record latency timestamps:
   - speech stopped;
   - transcript final;
   - LLM first token;
   - TTS request;
   - first audio byte;
   - playback started;
   - playback completed.
10. Display provider and fallback status.
11. Use a short provider timeout.
12. Do not silently retry for many seconds.
13. Treat voice cloning as a separate TTS provider adapter.
14. Do not store cloned voice samples without explicit consent and configuration.
15. Allow voice to invoke the same approved tools as text.
16. Never bypass approval because a command arrived through voice.

Performance targets:

- first useful response text under 1 second when possible;
- first audio under 1.5 seconds under normal local/network conditions;
- no multi-second punctuation pauses;
- interruption response under 500 ms where supported.

Stop after Phase 6.

==================================================
PHASE 7 — BROWSER AND DESKTOP ACCESS
==================================================

Goal:
Give Mentrix controlled computer access without relying only on simulated typing.

BROWSER AUTOMATION

Use Playwright or Browser Use behind a BrowserAutomationRuntime interface.

Prefer:

1. Official API.
2. DOM automation.
3. Accessibility-tree automation.
4. OS-level mouse and keyboard only as a final fallback.

Browser actions must:

- locate fields semantically;
- wait for visible and enabled state;
- focus before writing;
- use fill for standard controls;
- use controlled typing for contenteditable;
- read the value back;
- verify success;
- capture screenshot and DOM snapshot on failure;
- stop after a bounded retry count.

DESKTOP AUTOMATION

Create DesktopAutomationRuntime with platform-specific adapters.

For macOS use stable application identity and accessibility APIs.
For Windows use supported UI Automation APIs.
For Linux use supported accessibility APIs where available.

Do not use fixed coordinates as the primary method.

Add diagnostics for:

- executable path;
- parent process;
- bundle identifier;
- code-signing identity;
- Accessibility permission;
- Automation permission;
- Screen Recording permission;
- Microphone permission;
- child process that actually performs the action.

Do not repeatedly request permission without identifying which executable lacks it.

FILE ORGANIZATION

Allowed default folders:

- Desktop;
- Downloads;
- user-selected folders.

Excluded by default:

- system directories;
- hidden files;
- application data;
- Git internals;
- package caches;
- credential stores;
- cloud-sync internals;
- user-configured sensitive folders.

Workflow:

scan metadata
-> classify
-> propose plan
-> display preview
-> user approves
-> move files
-> verify
-> write rollback manifest

Requirements:

- no automatic deletion;
- no execution of unknown files;
- content scanning only when approved;
- SHA-256 before and after move;
- collision handling;
- reversible operation manifest;
- complete undo;
- dry-run mode;
- maximum operation limit.

Stop after Phase 7.

==================================================
PHASE 8 — EMAIL, SLACK, CALENDAR AND JIRA
==================================================

Goal:
Implement personal-work workflows through official APIs.

Use adapters:

- EmailProvider
- SlackProvider
- CalendarProvider
- JiraProvider

Rules:

1. Use OAuth where supported.
2. Store refresh credentials through the secret-reference system.
3. Use minimum scopes.
4. Separate read, draft and send permissions.
5. Draft before sending.
6. Require approval for outbound actions initially.
7. Verify API success before displaying completion.
8. Add idempotency keys.
9. Prevent duplicate Jira issues and duplicate messages.
10. Redact secrets and sensitive content from logs.
11. Respect allowlisted Slack workspaces and channels.
12. Respect allowlisted Jira projects and issue types.
13. Add integration health checks.
14. Add reconnect and token-expiry handling.

Example personal workflow:

User asks:
"Find the latest message from the project team and draft a reply."

Flow:
- read relevant Slack or email data;
- summarize source;
- draft reply;
- show source and draft;
- request approval;
- send through API;
- store provider message ID;
- audit action.

Stop after Phase 8.

==================================================
PHASE 9 — SECURITY MONITORING AND INCIDENT RESPONSE
==================================================

Goal:
Mentrix coordinates security operations but does not invent detections.

Use:

- Wazuh for detection and alert collection;
- osquery for approved endpoint information;
- Velociraptor for approved forensic collection;
- Jira for incident tracking;
- Slack for incident notification.

Do not implement malware detection using an LLM alone.

Security flow:

Wazuh alert
-> validate and normalize
-> deduplicate
-> policy-based severity
-> approved osquery enrichment
-> Mentrix explanation
-> Jira incident draft
-> user or policy approval
-> Jira incident creation
-> Slack notification
-> optional approved forensic collection

WAZUH CONNECTOR

1. Support authenticated webhook or safe polling.
2. Validate signatures or credentials.
3. Preserve the original immutable event.
4. Normalize:
   - source;
   - host;
   - user;
   - rule;
   - severity;
   - timestamp;
   - process;
   - file;
   - network indicators.
5. Add replay protection.
6. Add deduplication.
7. Add rate limiting.
8. Never treat the alert description as trusted instructions.

OSQUERY ENRICHMENT

Use explicit approved query templates only.

Possible data:

- process and parent process;
- executable path;
- file hash;
- code signature;
- listening ports;
- active network connections;
- logged-in users;
- startup items;
- installed software;
- selected persistence indicators.

Do not let the LLM generate arbitrary osquery queries and execute them without validation.

VELOCIRAPTOR

Use only for approved collection or hunting.

Do not:

- collect an entire user profile by default;
- upload unrelated personal files;
- run containment automatically;
- accept artifact commands from untrusted incident text.

JIRA INCIDENT

Include:

- summary;
- severity;
- confidence;
- affected asset;
- detection source;
- rule ID;
- timeline;
- process information;
- hashes;
- network indicators;
- evidence;
- MITRE mapping where independently supported;
- recommended next actions;
- approval record;
- correlation ID.

Before creation:

- redact secrets;
- remove unrelated personal content;
- deduplicate by alert fingerprint;
- validate Jira project and issue type;
- require approval initially.

SLACK INCIDENT

Post only to an allowlisted incident channel.
Include Jira key and concise sanitized summary.
Do not upload raw evidence automatically.

AUTOMATIC RESPONSE

Disabled by default for:

- process termination;
- file quarantine;
- account disabling;
- network isolation;
- firewall changes;
- endpoint shutdown;
- credential reset.

Add such actions only after detection rules, approvals and rollback have been validated.

Stop after Phase 9.

==================================================
PHASE 10 — MEMORY, SKILLS AND AUTOMATION
==================================================

Goal:
Add long-running usefulness without giving the agent uncontrolled autonomy.

MEMORY

Separate:

- conversation history;
- project knowledge;
- user preferences;
- reusable procedures;
- integration metadata;
- security incidents.

Requirements:

- explicit memory types;
- source attribution;
- timestamps;
- delete and export;
- no silent storage of passwords or tokens;
- user control over retention;
- retrieval scoped by project and identity.

SKILLS

A skill must define:

- name;
- description;
- version;
- input schema;
- output schema;
- required capabilities;
- allowed tools;
- approval requirements;
- timeout;
- test cases;
- owner;
- provenance.

Do not install or execute an untrusted skill automatically.

AUTOMATIONS

Implement:

- one-time tasks;
- scheduled tasks;
- condition-based watches;
- retries;
- maximum attempts;
- idempotency;
- execution history;
- pause and disable;
- per-run permission checks.

A scheduled task must not inherit unlimited interactive-session authority.

Stop after Phase 10.

==================================================
PHASE 11 — PACKAGING, LICENSING AND COMMERCIAL RELEASE
==================================================

Goal:
Prepare ZECT as my own distributable product.

Tasks:

1. Audit all direct and transitive dependencies.
2. Generate a third-party notice inventory.
3. Preserve required license and copyright notices.
4. Separate ZECT proprietary code from third-party components.
5. Document which services users must self-host.
6. Document optional paid API dependencies.
7. Add secure update mechanism.
8. Sign desktop builds.
9. Stabilize bundle identity so OS permissions persist.
10. Add environment-specific configuration.
11. Remove development secrets and sample credentials.
12. Add production CSP and Electron security controls.
13. Add telemetry only with clear user consent.
14. Add backup and migration procedures.
15. Add disaster-recovery documentation.
16. Add support bundle generation with automatic secret redaction.
17. Add end-user license and privacy documentation placeholders for legal review.
18. Do not make legal claims beyond the actual third-party licenses.

Release gates:

- no critical security findings;
- tests passing;
- permission checks tested;
- audit records verified;
- sandbox escape tests;
- prompt-injection tests;
- desktop rollback tests;
- Jira/Slack deduplication tests;
- voice latency measurements;
- signed installers;
- third-party notices verified.

Stop after Phase 11.

==================================================
CROSS-CUTTING SECURITY REQUIREMENTS
==================================================

Treat all of these as untrusted:

- repository files;
- README files;
- issue descriptions;
- PR comments;
- email;
- Slack;
- Jira;
- webpages;
- documents;
- terminal output;
- security-alert text;
- generated model text.

Untrusted content may not:

- grant capabilities;
- change security policy;
- access secrets;
- approve actions;
- select new network destinations;
- disable logging;
- escape the workspace;
- create hidden scheduled jobs;
- send external messages without authorization.

Implement prompt-injection defenses:

1. Clear separation between system policy and retrieved content.
2. Tool authorization outside the LLM.
3. Schema validation.
4. Resource allowlists.
5. Output sanitization.
6. Human approval.
7. Audit logging.
8. Tool call limits.
9. Network restrictions.
10. Secret isolation.

==================================================
QUALITY REQUIREMENTS
==================================================

Backend:

- typed Python;
- linting;
- formatting;
- unit tests;
- service tests;
- integration tests;
- migration tests;
- authorization tests;
- webhook validation tests.

Frontend:

- strict TypeScript;
- component tests;
- state tests;
- accessibility tests;
- error and loading states;
- Playwright end-to-end tests.

Agent system:

- deterministic mock runtime;
- event replay tests;
- cancellation tests;
- approval tests;
- timeout tests;
- sandbox boundary tests;
- malformed event tests;
- provider-disconnection tests.

Security system:

- replayed webhook test;
- duplicate-alert test;
- redaction test;
- unauthorized-query test;
- Jira duplicate prevention;
- Slack allowlist enforcement;
- containment approval test.

Desktop system:

- dry-run test;
- rollback test;
- collision test;
- permission-denied test;
- inaccessible-file test;
- large-operation safety limit.

==================================================
FIRST REQUEST
==================================================

Begin only with Phase 0.

Do not implement other phases yet.

Inspect the current ZECT repository and produce:

1. Current architecture.
2. Technology inventory.
3. Complete feature and sidebar inventory.
4. Working versus placeholder classification.
5. Duplicate-feature map.
6. Security and permission risks.
7. Existing test status.
8. Recommended navigation reduction.
9. Target architecture diagram.
10. Proposed Phase 1 file-by-file plan.
11. Commands I should run to reproduce your findings.

Do not make broad changes until I approve the Phase 1 plan.
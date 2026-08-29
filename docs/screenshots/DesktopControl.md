You are working directly inside my existing ZECT/Mentrix repository.

Repository:
https://github.com/KarthikKaruppasamy880/ZECT

Branch to inspect:
develop

PRODUCT GOAL

ZECT is my product and Mentrix is the personal assistant inside it.

Mentrix must eventually support:

1. Typed and spoken commands.
2. Read-only access to approved email, Slack and calendar data.
3. Drafting email and Slack replies based on:
   - my dictated response;
   - the existing conversation;
   - relevant project context;
   - meeting context.
4. Sending messages only after explicit approval.
5. Viewing and organizing approved folders and files.
6. Showing a file-organization preview before moving anything.
7. Moving and renaming approved files only after approval.
8. Never deleting files.
9. Never emptying Trash.
10. Never deleting email, Slack messages or calendar events.
11. Never sending external communications without approval.
12. Verifying every completed action.
13. Maintaining an audit record and a reversible file-move manifest.

IMPORTANT: THIS IS AN EXISTING APPLICATION

Do not begin by creating a new implementation.

The repository already contains significant functionality, including Mentrix,
voice, desktop/computer mode, integrations, permissions, skills, workflows,
tests and UI pages.

First locate and understand everything already implemented.

Do not trust the root README as the complete source of truth. Inspect:

- actual frontend routes;
- actual sidebar configuration;
- backend routers;
- backend services;
- models and migrations;
- Electron main, preload and renderer bridges;
- Mentrix orchestration;
- voice pipeline;
- computer/desktop mode;
- email, Slack, Jira and calendar integrations;
- MCP integrations;
- permissions and approvals;
- secrets management;
- audit logging;
- skills;
- scheduled tasks;
- tests and E2E tests.

Preserve working functionality.

Do not perform a big-bang rewrite.

==================================================
NON-NEGOTIABLE SAFETY POLICY
==================================================

Mentrix may eventually support:

READ:
- approved email;
- approved Slack workspaces and channels;
- approved calendar data;
- approved user-selected folders;
- approved visible applications;
- approved repository workspaces.

DRAFT:
- email replies;
- Slack replies;
- meeting notes;
- meeting summaries;
- file-organization plans.

WRITE WITH APPROVAL:
- send email;
- send Slack messages;
- create or update approved calendar events;
- move or rename approved files;
- type into approved applications.

NEVER ALLOW:
- file deletion;
- Trash emptying;
- email deletion;
- Slack-message deletion;
- calendar-event deletion;
- destructive shell commands;
- administrator commands;
- disabling security controls;
- reading password stores;
- exposing secrets;
- unrestricted access to the full home directory.

Do not merely hide delete buttons.

Enforce prohibited actions in server-side or trusted-process policy code so
that the LLM, frontend, skill or external content cannot bypass the policy.

==================================================
DESIRED RUNTIME ARCHITECTURE
==================================================

All typed and spoken requests should use one shared flow:

User input
-> text or voice normalization
-> Mentrix orchestrator
-> context retrieval
-> intent and parameters
-> capability-policy decision
-> approval when required
-> runtime/tool execution
-> structured verification
-> audit event
-> visual and spoken result

Introduce or normalize ZECT-owned interfaces only where needed:

MentrixOrchestrator
VoiceRuntime
DesktopAutomationRuntime
BrowserAutomationRuntime
FileOrganizationRuntime
EmailProvider
SlackProvider
CalendarProvider
PermissionService
ApprovalService
AuditService

External or existing implementations must be isolated behind these interfaces.

Do not rename or rewrite working implementations solely to match this diagram.

==================================================
EXECUTION MODEL
==================================================

Use this priority for actions:

For email, Slack and calendar:
1. Official provider API.
2. Existing authenticated MCP/provider integration.
3. Browser DOM automation only when an API is unavailable.
4. Accessibility automation.
5. Keyboard and mouse simulation only as the last fallback.

For browser applications:
1. Semantic locator and DOM.
2. Accessibility tree.
3. Vision-assisted location.
4. Keyboard and mouse fallback.

For native desktop applications:
1. Native application API or integration.
2. OS accessibility tree.
3. Application-specific automation adapter.
4. Vision-assisted location.
5. Keyboard and mouse fallback.

Never claim success merely because a key or click was sent.

Verify with:
- API response and provider object ID;
- DOM value;
- accessibility state;
- filesystem state;
- active-window state;
- screenshot only when structured verification is unavailable.

==================================================
FILE ORGANIZATION REQUIREMENTS
==================================================

Default allowed locations:

- Desktop;
- Downloads;
- Documents subfolders explicitly selected by the user;
- other folders explicitly added to an allowlist.

Default exclusions:

- operating-system folders;
- hidden files;
- application data;
- .git directories;
- credential files;
- browser profiles;
- cloud-provider internal folders;
- package caches;
- build output unless explicitly selected;
- user-configured sensitive folders.

Required workflow:

scan
-> classify
-> create proposal
-> show before/after paths
-> request approval
-> move or rename
-> verify
-> save rollback manifest
-> offer Undo

Each proposal must include:

- original path;
- proposed destination;
- reason;
- confidence;
- collision status;
- sensitive-file warning;
- operation count.

Each completed operation must include:

- original path;
- final path;
- SHA-256 before;
- SHA-256 after;
- timestamp;
- approval ID;
- run ID;
- rollback status.

Never overwrite an existing file silently.

Never delete the original as a workaround for a failed move.

A cross-filesystem move must be verified before removing its source, and it must
still follow the no-delete product policy. If safe implementation is not
possible under that policy, block the action and explain why.

==================================================
EMAIL, SLACK AND CALENDAR REQUIREMENTS
==================================================

Email:

- read only approved mailboxes;
- fetch only the minimum message content needed;
- summarize threads;
- generate drafts;
- display recipients, subject and final body;
- require approval immediately before sending;
- verify the provider message ID;
- never delete, archive or mark as spam;
- do not auto-send based only on model confidence.

Slack:

- read only approved workspaces and channels;
- preserve thread context;
- prepare drafts;
- display destination channel or user;
- require approval immediately before sending;
- verify Slack timestamp/message ID;
- never delete or edit an existing message without a future explicit policy;
- prevent duplicate sends.

Calendar:

- read approved calendars;
- prepare daily and meeting briefings;
- draft meeting additions or updates;
- require approval before creating or updating;
- never delete events;
- clearly show attendees, time zone, time and recurrence.

Dictation:

- transcribe the user's words;
- preserve a verbatim transcript separately;
- optionally produce a polished draft;
- show what changed between transcript and polished draft;
- require approval before sending;
- never invent commitments, dates, recipients or decisions.

Autonomous drafting:

Mentrix may generate a suggested reply from context, but it must clearly label:

- source messages used;
- assumptions;
- unresolved questions;
- proposed reply;
- whether the reply is unsent.

==================================================
VOICE REQUIREMENTS
==================================================

Reuse and repair the existing voice implementation.

Do not replace it without first proving replacement is necessary.

Required behavior:

- persistent session where supported;
- fast first audio;
- no long pause after punctuation;
- interruption/barge-in;
- immediate stop/cancel;
- one active response at a time;
- spoken and typed commands use identical permissions;
- visible microphone and desktop-control indicators;
- no silent continuous recording;
- local wake word or push-to-talk where practical.

Instrument:

- user speech stopped;
- transcript final;
- intent ready;
- policy decision;
- tool started;
- tool completed;
- LLM first token;
- TTS first byte;
- playback started;
- playback completed.

==================================================
PHASED DELIVERY — ONE PR PER PHASE
==================================================

Do not implement all phases at once.

Create one focused branch and PR for every phase.

Do not begin the next phase until the current PR is reviewed and approved.

Security monitoring and incident response remain deferred.

--------------------------------------------------
PHASE PA-0 — CURRENT-STATE AUDIT
--------------------------------------------------

Do not change product behavior.

Audit all existing functionality related to:

- Mentrix;
- voice;
- computer mode;
- desktop control;
- browser control;
- file operations;
- email;
- Slack;
- calendar;
- Jira;
- MCP;
- permissions;
- approvals;
- audit;
- secrets;
- skills;
- scheduled tasks.

Search for duplicate implementations and direct provider calls.

Identify:

- working behavior;
- partial behavior;
- placeholders;
- dead code;
- unsafe behavior;
- missing verification;
- missing approval;
- missing project/user scoping;
- unprotected destructive actions;
- typing implemented only through SendKeys;
- repeated OS permission prompts;
- frontend-only permission checks;
- secrets reaching the renderer/browser;
- external actions reported successful without verification.

Create:

docs/personal-agent/CURRENT_STATE_AUDIT.md
docs/personal-agent/CAPABILITY_MATRIX.md
docs/personal-agent/CURRENT_REQUEST_FLOW.md
docs/personal-agent/TARGET_ARCHITECTURE.md
docs/personal-agent/SAFETY_POLICY.md
docs/personal-agent/IMPLEMENTATION_ROADMAP.md

CAPABILITY_MATRIX.md must include:

- capability;
- existing implementation;
- files;
- backend endpoint;
- trusted execution process;
- provider;
- permission;
- approval requirement;
- verification method;
- tests;
- status;
- recommended action.

TARGET_ARCHITECTURE.md must include Mermaid diagrams for:

1. Typed command flow.
2. Voice command flow.
3. Email/Slack draft-and-send flow.
4. Desktop action flow.
5. File-organization and Undo flow.
6. Permission and approval flow.

Run existing checks, but do not fix unrelated failures in this phase.

Stop after PA-0 and report:

- files created;
- findings;
- current test failures;
- proposed PA-1 scope;
- expected PA-1 files;
- migration requirements;
- risks;
- rollback plan.

--------------------------------------------------
PHASE PA-1 — SHARED COMMAND AND POLICY FOUNDATION
--------------------------------------------------

Implement only after PA-0 approval.

Goal:

Unify typed and spoken commands behind one orchestration and policy path.

Requirements:

- stable command schema;
- actor and user identity;
- run ID and correlation ID;
- intent;
- parameters;
- requested capability;
- target resource;
- risk classification;
- policy decision;
- approval status;
- execution status;
- verification status;
- result.

Implement or normalize:

- MentrixOrchestrator;
- PermissionService;
- ApprovalService;
- AuditService;
- emergency stop;
- action cancellation;
- idempotency key;
- server-side no-delete policy.

Do not implement new desktop automation in this phase.

--------------------------------------------------
PHASE PA-2 — EMAIL, SLACK AND CALENDAR READ/DRAFT
--------------------------------------------------

Goal:

Reliable read and drafting workflows with no sending yet.

Requirements:

- use existing working integrations;
- provider-independent interfaces;
- minimum OAuth/scopes;
- mailbox/channel/calendar allowlists;
- thread context;
- source citations in drafts;
- dictation transcript and polished version;
- duplicate prevention;
- no destructive operations.

Deliver read and draft only.

--------------------------------------------------
PHASE PA-3 — APPROVED SEND/WRITE
--------------------------------------------------

Goal:

Add explicit approval immediately before an external write.

Requirements:

- immutable approval preview;
- recipient/destination shown;
- approval expires after a configurable period;
- draft hash must match the approved body;
- provider execution ID;
- result verification;
- retry without duplicate send;
- audit trail.

No automatic sending.

--------------------------------------------------
PHASE PA-4 — BROWSER AUTOMATION
--------------------------------------------------

Goal:

Replace fragile browser typing with verified DOM-first automation where APIs
are unavailable.

Requirements:

- semantic locators;
- visible/enabled waits;
- focus verification;
- input and contenteditable support;
- read-back verification;
- bounded retries;
- failure screenshot and DOM snapshot;
- browser-session isolation;
- no password scraping.

--------------------------------------------------
PHASE PA-5 — NATIVE DESKTOP ACCESS
--------------------------------------------------

Goal:

Implement controlled native desktop access.

Requirements:

- inspect the current Electron and computer-mode implementation;
- identify the exact process performing automation;
- stable executable and bundle identity;
- permission diagnostics;
- accessibility-tree operations;
- app and window allowlists;
- active target indicator;
- result verification;
- keyboard/mouse only as fallback;
- emergency stop.

Do not grant unrestricted home-directory access.

--------------------------------------------------
PHASE PA-6 — SAFE FILE ORGANIZATION
--------------------------------------------------

Goal:

Preview, approve, move, verify and undo file organization.

No deletion.

Implement:

- folder allowlist;
- exclusions;
- dry run;
- classification;
- proposal UI;
- approval;
- collision handling;
- move manifest;
- SHA-256 verification;
- Undo;
- tests for partial failure and rollback.

--------------------------------------------------
PHASE PA-7 — VOICE STABILIZATION
--------------------------------------------------

Goal:

Make realtime Mentrix voice reliable and connect it to the shared command flow.

Repair:

- latency;
- punctuation pauses;
- duplicate sessions;
- stale playback;
- fallback delays;
- interruption;
- cancellation;
- result narration.

Do not let voice bypass approval.

--------------------------------------------------
PHASE PA-8 — MEETING ASSISTANT
--------------------------------------------------

Goal:

Use email, Slack and calendar read access to prepare meetings.

Features:

- upcoming meeting view;
- attendee and agenda summary;
- related email and Slack context;
- project context;
- pre-meeting briefing;
- notes draft;
- follow-up draft;
- no automatic sending;
- no recording without explicit session consent.

--------------------------------------------------
PHASE PA-9 — SKILLS AND AUTOMATIONS
--------------------------------------------------

Goal:

Package repeatable personal-assistant workflows as governed skills.

Every skill must declare:

- inputs;
- outputs;
- required capabilities;
- allowed resources;
- approval points;
- prohibited operations;
- timeout;
- retry policy;
- verification;
- test cases.

Scheduled tasks receive separate limited grants and may not inherit unrestricted
permissions from an interactive session.

==================================================
GIT AND PR RULES
==================================================

For each phase:

1. Pull the latest develop branch.
2. Verify clean working tree.
3. Create a branch:
   feature/personal-agent-pa-N-short-name
4. Implement only the approved phase.
5. Add or update tests.
6. Run:
   - backend formatter and linter;
   - backend type checks if configured;
   - backend unit and integration tests;
   - frontend lint;
   - frontend type check;
   - frontend unit tests;
   - Playwright tests where applicable;
   - production frontend build;
   - Electron build/check where applicable.
7. Report actual command outputs.
8. Commit in coherent units.
9. Create one PR.
10. Do not merge without explicit approval.
11. Do not start the next phase automatically.

If PR creation is unavailable:

- push the branch;
- provide branch name;
- provide PR title;
- provide complete PR description;
- provide the compare URL or exact command needed to create it.

==================================================
FIRST ACTION
==================================================

Start with PA-0 only.

Do not modify runtime behavior.

Inspect the actual current repository and produce the six audit documents.

Do not assume a capability is absent merely because it is missing from the
README.

Do not assume a capability works merely because a page or route exists.

Trace each workflow end to end and cite exact file paths and symbols.

Stop and wait for approval.
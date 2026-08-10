# ZECT / MENTRIX — LONG-RUNNING ENGINEERING AGENT RUNTIME

## Purpose

Use this file in Cursor after the current Companion + Presentation + Learning + Automation Loops work on PR #130 is safely merged.

This specification extends the existing ZECT/Mentrix architecture into a **durable long-running agentic coding platform** with Planner, Coding Agent, Test Agent, Review Agent, AcceptanceVerifier, and persistent Automation Loops.

It must **reuse** the systems already built. It must not create a competing second architecture.

---

# 0. FIRST — VERIFY CURRENT PR #130 STATE

Before product-code changes:

1. Fetch remote state.
2. Inspect PR #130 and the current feature branch.
3. Compare local HEAD, remote feature branch, and `develop`.
4. Confirm CI backend/frontend/e2e state.
5. Confirm current security hardening and Automation Loop commits are actually pushed.
6. Do not trust stale PR-page metadata if local/remote git proves a newer HEAD.
7. Do not merge if a new regression or unresolved HIGH/CRITICAL security finding exists.
8. Live connectors without credentials remain `BLOCKED_EXTERNAL`, not fake PASS.

Expected current feature set from the latest Cursor run:

- Companion + Presentation + Learning hardening
- PersonalAction user isolation
- connector provenance
- untrusted-content sanitization
- Learning ownership/error UX
- existing `MentrixAutomationLoop`
- five initial loops:
  - `daily_brief`
  - `pr_ci_watch`
  - `jira_triage`
  - `presentation_prep`
  - `personal_followup`
- budgets
- checkpoints
- circuit breaker
- `NEEDS_HUMAN_DECISION`
- pause / resume / kill
- evidence
- CI green for exercised backend/frontend/e2e paths

If PR #130 is safe and repository policy permits, merge it to `develop`. Otherwise stop at `READY_TO_MERGE`.

After merge:

```text
checkout develop
pull origin develop
verify clean intended baseline
create a new feature branch for this work
```

Suggested branch:

```text
feat/mentrix-long-running-engineering-runtime
```

Do not continue implementation directly on the merged feature branch.

---

# 1. ABSOLUTE ARCHITECTURAL RULE

Do **not** create:

- another user-facing assistant;
- another loop engine;
- another ForgeLoop;
- another WorkItem system;
- another ContextEngine;
- another Project Intelligence store;
- another memory system;
- another model gateway;
- another Coding Agent;
- another permission system;
- another evidence/completion system.

Reuse:

```text
Mentrix
MentrixAutomationLoop
ForgeLoop
WorkItem
ArtifactStore
EXECUTION_MANIFEST
EXECUTION_STATE
WorkItemEvent
ProjectIntelligence
ContextEngine
Mentrix Coding Agent (mentrix_native)
Ultra Review
EvidenceVerifier
Permission Broker
Model Gateway
Skills
Playbooks
Jira
Camunda
Git / PR / CI
```

---

# 2. FINAL PRODUCT MODEL

```text
                         MENTRIX
                            │
            ┌───────────────┼────────────────┐
            │               │                │
        Companion       Developer        Learning
            │               │                │
            └───────────────┼────────────────┘
                            ▼
                   AUTOMATION LOOPS
              schedule / event / manual
                            │
              budgets / policy / state
                            │
                            ▼
              WorkItem / PersonalAction
                            │
                            ▼
                  Project Intelligence
                            │
                   Context Engine
                            │
                            ▼
                       ForgeLoop
                            │
                            ▼
                         PLANNER
                            │
                         PLAN.md
                            │
                     Approval / Policy
                            │
                            ▼
                     CODING AGENT
                            │
                            ▼
                       TEST AGENT
                         │      │
                      FAIL     PASS
                         │      │
                         └──► CODER
                                │
                                ▼
                           REVIEW AGENT
                              │     │
                         BLOCKING  CLEAN
                              │     │
                              └──► CODER
                                    │
                                    ▼
                          ACCEPTANCE VERIFIER
                                    │
                                    ▼
                           EVIDENCE VERIFIER
                              │           │
                            FAIL         PASS
                              │           │
                      BLOCK / LOOP   READY_TO_SHIP
                                          │
                                          ▼
                                      PR / CI
                                          │
                                    Jira / Camunda
                                          │
                                          ▼
                                  Persist State
                                          │
                                          └────↺
```

---

# 3. KEY PRINCIPLE — THE JOB LIVES IN ZECT, NOT IN THE MODEL

Do not implement long-running coding by keeping one HTTP request, one LLM call, or one enormous context alive.

The durable job belongs to ZECT.

A 100+ file task should work like:

```text
WorkItem
  ↓
Execution Manifest: 150 operations
  ↓
OP-001
  retrieve bounded context
  execute
  verify
  checkpoint
  ↓
OP-002
  retrieve bounded context
  execute
  verify
  checkpoint
  ↓
...
  ↓
OP-150
```

If the model, backend, Electron app, or workstation session stops after OP-074:

```text
Completed: 74
Pending: 76
Resume: OP-075
```

Restarting ZECT must resume from persisted state rather than restart from zero.

---

# 4. DURABLE LONG-RUNNING AGENT RUNTIME

Create or consolidate a ZECT-owned runtime, preferably behind the existing Automation Loop and ForgeLoop services.

Suggested conceptual name:

```text
LongRunningAgentRuntime
```

Do not expose it as another product.

The runtime owns:

```text
run_id
work_item_id
loop_run_id
repository_id
worktree_path
base_commit_sha
current_commit_sha
current_operation_id
operation_queue
operation_attempt
model_profile
requested_model
actual_model
provider
context_refs
token_budget
cost_budget
runtime_budget
action_budget
retry_budget
coder_test_cycles
coder_review_cycles
last_progress_at
failure_signature
same_failure_count
checkpoint_id
resume_operation
status
created_at
updated_at
```

Persist material changes transactionally where practical.

---

# 5. BACKGROUND EXECUTION

Long-running work must not depend on:

```text
POST /agent
→ HTTP connection remains open for hours
```

Use the existing job/background infrastructure or add a thin durable worker abstraction.

Target:

```text
User starts Agent
      ↓
Run record created
      ↓
Background worker claims run
      ↓
LongRunningAgentRuntime
      ↓
persistent state/checkpoints
      ↓
UI polls/subscribes to status/events
```

Support:

```text
start
pause
resume
cancel
retry blocked operation
approve gated operation
```

Backend restart must not lose the run.

If a worker dies, another compatible worker should be able to resume a recoverable run after lease/lock expiry.

Prevent two workers from executing the same operation concurrently.

---

# 6. RUN LEASE / CONCURRENCY SAFETY

Add durable run ownership/lease semantics if not already available.

Track:

```text
worker_id
lease_acquired_at
lease_expires_at
heartbeat_at
```

Rules:

- one active executor per operation;
- expired lease can be reclaimed safely;
- completion/checkpoint writes should be idempotent where possible;
- duplicate command execution must be prevented or clearly detected;
- git/worktree state must be verified before resume.

---

# 7. MENTRIX PLANNER

Planner responsibilities:

- understand User / Jira / Camunda WorkItem;
- retrieve bounded Project Intelligence;
- identify requirements;
- identify affected surfaces;
- identify dependencies/risks;
- define verification;
- define acceptance evidence;
- generate/update:

```text
REQUIREMENTS.md
PLAN.md
ACCEPTANCE.md
RISKS.md
EXECUTION_MANIFEST.json
```

Every requirement maps to:

```text
requirement
→ operation(s)
→ verification
→ acceptance evidence
```

Planner must not:

- edit production code;
- mark implementation complete;
- set READY_TO_SHIP;
- bypass approvals.

---

# 8. MENTRIX CODING AGENT

Reuse the existing real `mentrix_native` Coding Agent.

Do not create another coder.

Inputs:

```text
approved PLAN.md
WorkItem
current operation
bounded ContextPack
Project Intelligence
Skills
Playbook
previous test/review errors
permissions
budgets
```

Tools:

```text
read
search
inspect
edit
create
run
test
git status
git diff
```

Every material operation:

```text
START
→ checkpoint
→ execute
→ record changed files
→ verify
→ checkpoint
→ COMPLETE / FAILED / BLOCKED
```

Coder cannot set READY_TO_SHIP.

---

# 9. MENTRIX TEST AGENT

Create an independent logical Test Agent using existing deterministic test tools.

Inputs:

```text
requirements
acceptance criteria
changed files
manifest
risk/security context
repository test conventions
```

Applicable verification:

```text
unit
integration
API
frontend
Playwright/e2e
build
lint
typecheck
migration
security
performance
```

Use tools first; use LLM reasoning for:

- test selection;
- test design;
- failure diagnosis;
- coverage-gap analysis.

Persist:

```text
TEST_RESULTS.json
```

Failure flow:

```text
Test Agent FAIL
→ structured evidence
→ Coding Agent
→ fix
→ rerun affected verification
```

Do not silently ignore failing tests.

---

# 10. MENTRIX REVIEW AGENT

Reuse/evolve Ultra Review.

Do not create another separate review product.

Reviewer sees:

```text
actual diff
relevant source
requirements
PLAN
test results
Project Intelligence
security context
```

Check:

```text
correctness
architecture
maintainability
security
authorization
API compatibility
backwards compatibility
performance
concurrency
error handling
test quality
scope creep
requirement coverage
```

Persist:

```text
REVIEW.json
```

Finding shape:

```text
id
severity
category
file
line
claim
evidence
requirement_id
recommended_action
confidence
verification_status
```

Statuses:

```text
verified
likely
unverified
false_positive
waived
```

Only verified blocking findings automatically route back to Coding Agent.

---

# 11. ACCEPTANCE + EVIDENCE

Reuse EvidenceVerifier as completion authority.

Verify:

```text
mandatory operation coverage
requirement coverage
acceptance criteria coverage
test evidence
review blockers
security blockers
required approvals
```

Example:

```text
Operations: 150 / 150
Requirements: 18 / 18 verified
Acceptance Criteria: 12 / 12 verified
Tests: PASS
Blocking Review Findings: 0
Security Blockers: 0
```

Only then:

```text
READY_TO_SHIP
```

LLM text alone can never complete the run.

A manifest with:

```text
149 / 150
```

must remain NOT COMPLETE.

---

# 12. ENGINEERING AUTOMATION LOOPS

Extend the existing `MentrixAutomationLoop`.

Do not add a new loop engine.

Required definitions:

```text
engineering_delivery
bug_fix
jira_delivery
ci_fix
pr_review_fix
```

Canonical `engineering_delivery`:

```text
Trigger
  ↓
WorkItem
  ↓
Planner
  ↓
Plan Approval
  ↓
Coding Agent
  ↓
Test Agent
  │
  ├── FAIL → Coding Agent
  │
  └── PASS
        ↓
     Review Agent
        │
        ├── BLOCKING → Coding Agent
        │
        └── CLEAN
              ↓
     AcceptanceVerifier
              ↓
      EvidenceVerifier
              ↓
       READY_TO_SHIP
              ↓
           PR / CI
```

---

# 13. AUTONOMY LEVELS

Reuse current Automation Loop autonomy:

```text
L0 OBSERVE
report only

L1 RECOMMEND
analyze and recommend

L2 ASSISTED
execute safe/approved steps, ask for governed actions

L3 AUTONOMOUS
execute within explicitly configured policy
```

New engineering loops default to L0/L1.

L2/L3 require explicit configuration.

L3 does **not** bypass:

- permissions;
- path restrictions;
- security classifications;
- model policy;
- cost/runtime budgets;
- PR/merge policy;
- EvidenceVerifier.

---

# 14. BUDGETS

Every long-running engineering run must support:

```text
max_runtime
max_tokens
max_cost
max_actions
max_retries
max_files_changed optional
max_coder_test_cycles
max_coder_review_cycles
same_failure_threshold
no_progress_threshold
```

Budget exhaustion:

```text
BLOCKED / NEEDS_HUMAN_DECISION
```

Persist exact consumed/remaining budget.

---

# 15. CIRCUIT BREAKER / NO-PROGRESS

Detect repeated failure signatures.

Example:

```text
attempt 1: same compiler error
attempt 2: same compiler error
attempt 3: same compiler error
        ↓
CIRCUIT BREAKER
        ↓
NEEDS_HUMAN_DECISION
```

Also detect:

- repeated identical diff with no test improvement;
- repeated review finding;
- operation repeatedly produces no file/state change;
- repeated tool/credential/environment failure.

Persist:

```text
blocker
failure signature
attempt count
last progress
last successful operation
resume point
recommended human decision
```

---

# 16. CONTEXT MANAGEMENT FOR LONG RUNS

Do not keep entire run history in every prompt.

Each operation gets a fresh bounded ContextPack containing only relevant:

```text
system policy
role
WorkItem
current requirement
current PLAN section
current operation
relevant files
Lattice hits
Blueprint
Knowledge
verified Memory
Skills
Playbook
related work
previous relevant errors
permissions
output contract
```

Persist references/provenance instead of giant prompt transcripts.

Long-running execution must survive context-window rollover.

---

# 17. MODEL ROUTING

Use the existing Model Gateway.

Support role-based configurable routing.

Do not hard-code one vendor/model.

Profiles:

```text
FAST
QUALITY
MAX
LOCAL
RESTRICTED
CUSTOM
```

Example policy:

```text
Planner
→ strongest configured reasoning model

Coder
→ strongest configured coding model

Tester
→ deterministic tools first + configured reasoning model for analysis

Reviewer
→ independently configured strong reviewer model

Acceptance
→ deterministic EvidenceVerifier first
```

The architecture must support Anthropic-class, OpenAI/Codex-class, and approved local models through existing provider contracts when configured.

Preserve telemetry:

```text
requested_model
actual_model
provider
local_or_cloud
fallback_used
fallback_reason
latency
work_item_id
operation_id
```

Restricted policy:

```text
cloud fallback = NEVER
```

when configured.

Do not claim fully local unless runtime verified.

---

# 18. MODEL SWITCH DURING A RUN

A long run may switch models only if policy allows.

Example:

```text
OP-001..OP-050 → model A
model unavailable
policy allows alternate
OP-051.. → model B
```

Persist the model used for every operation.

Never silently change provider for confidential/restricted work.

---

# 19. AGENT COMMUNICATION

Do not create uncontrolled Planner↔Coder↔Tester↔Reviewer conversation loops.

Communicate through:

```text
WorkItem
REQUIREMENTS.md
PLAN.md
ACCEPTANCE.md
RISKS.md
EXECUTION_MANIFEST.json
EXECUTION_STATE.json
TEST_RESULTS.json
REVIEW.json
EVIDENCE.json
WorkItemEvent
```

This keeps execution auditable, resumable, and token-efficient.

---

# 20. WORKTREE SAFETY

Each large engineering run should use an isolated worktree/workspace when supported.

Persist:

```text
repository
branch
worktree path
base SHA
current SHA
dirty state
```

On resume:

1. verify worktree exists;
2. verify expected base/current commit;
3. detect external modifications;
4. stop with `NEEDS_HUMAN_DECISION` if safe continuation cannot be proven.

Never overwrite unrelated user changes to make the loop continue.

---

# 21. UI FOR LONG-RUNNING AGENT

Developer Workspace should expose a run view similar to:

```text
PAY-842

RUNNING · 2h 18m

Requirements       9 / 12
Acceptance         7 / 10
Operations        74 / 112
Files changed           38
Tests             241 passed

Current:
OP-075 — Add audit integration

Role:
Coding Agent

Model:
<actual model/provider>

Budget:
runtime / tokens / cost / actions

[Pause] [Resume] [Cancel]
[View Plan] [View Diff] [View Tests]
[View Review] [View Evidence]
```

Show:

```text
Planner status
Coder status
Tester status
Reviewer status
Acceptance status
loop iteration
checkpoint
circuit-breaker status
```

Do not expose raw internal chain-of-thought.

---

# 22. RESTART / RECOVERY ACCEPTANCE

Mandatory test:

1. Create synthetic engineering WorkItem with 100+ operations.
2. Start execution.
3. Complete a meaningful subset.
4. Persist checkpoints.
5. Stop/kill backend worker/process.
6. Restart backend/worker.
7. Resume run.
8. Verify it starts from the persisted next operation.
9. Verify completed operations are not repeated unnecessarily.
10. Verify worktree and commit identity.
11. Finish remaining operations.
12. Verify READY_TO_SHIP only after 100% mandatory evidence.

Also test:

```text
100 operations
99 completed
1 pending
LLM says "done"
→ EvidenceVerifier must reject completion
```

---

# 23. FAILURE ACCEPTANCE

Test:

- model API outage;
- local model outage;
- test process timeout;
- backend restart;
- worker crash;
- invalid credential;
- git conflict;
- worktree changed externally;
- circuit breaker;
- token budget exhausted;
- cost budget exhausted;
- runtime budget exhausted;
- permission denied;
- repeated review finding.

Every failure must end in a truthful state:

```text
RUNNING
PAUSED
BLOCKED
NEEDS_HUMAN_DECISION
FAILED_VERIFICATION
CANCELLED
READY_TO_SHIP
```

Never fabricate success.

---

# 24. SECURITY

Long-running autonomy increases blast radius.

Keep existing controls mandatory:

```text
Permission Broker
RBAC/ABAC
data classification
model policy
secret protection
path allowlists
connector scopes
audit
human approval gates
EvidenceVerifier
```

L3 autonomous runs must have tighter, not weaker, limits.

High-risk actions remain governed:

```text
secret access
external message
git push
PR merge
deployment
destructive filesystem changes
production access
```

---

# 25. REQUIRED TESTS

Add tests proving at minimum:

1. Planner cannot edit production files.
2. Planner cannot set READY_TO_SHIP.
3. Coding Agent cannot set READY_TO_SHIP.
4. Coder follows manifest operations.
5. Tester failure routes to Coder.
6. Blocking verified Reviewer finding routes to Coder.
7. False-positive/unverified finding does not trigger arbitrary fix.
8. Incomplete requirement blocks acceptance.
9. Incomplete acceptance criterion blocks acceptance.
10. 99/100 operations blocks completion.
11. repeated failure triggers circuit breaker.
12. no-progress triggers escalation.
13. pause/resume works.
14. backend restart/resume works.
15. worker lease prevents double execution.
16. stale worktree is detected.
17. L3 obeys Permission Broker.
18. L3 obeys restricted model policy.
19. token budget enforced.
20. cost budget enforced.
21. runtime budget enforced.
22. model switching is logged and policy-controlled.
23. operation-level model telemetry is persisted.
24. successful 100+ operation flow reaches READY_TO_SHIP with evidence.
25. PR/CI stage cannot bypass EvidenceVerifier.

---

# 26. ACCEPTANCE ARTIFACT

Produce:

```text
MENTRIX_LONG_RUNNING_ENGINEERING_ACCEPTANCE.md
```

Include:

- `VIABLE / BLOCKED`
- current merged baseline
- runtime architecture
- role boundaries
- durable run model
- worker/background architecture
- lease/concurrency behavior
- loop definitions
- autonomy levels
- model-routing profiles
- model/provider telemetry
- budgets
- checkpoint/resume
- backend restart test
- 100+ operation test
- Tester/Reviewer loops
- circuit breaker
- permissions/security
- evidence/acceptance gates
- UI status
- tests
- remaining blockers
- external credential/model blockers
- explicit non-claims

Do not claim:

- perfect code generation;
- 100% error-free coding;
- zero hallucination;
- unlimited autonomy;
- unhackable system;
- fully local execution unless actually proven.

---

# 27. FINAL ARCHITECTURAL OWNERSHIP

```text
Mentrix
= user-facing intelligence

MentrixAutomationLoop
= triggers, repetition, autonomy, budgets, checkpointing, circuit breaker

LongRunningAgentRuntime
= durable execution lifecycle across hours/restarts

ForgeLoop
= engineering SDLC orchestration

Mentrix Planner
= requirements and plan worker

Mentrix Coding Agent
= only code-editing worker

Mentrix Test Agent
= independent test/verification worker

Mentrix Review Agent / Ultra Review
= independent review worker

AcceptanceVerifier / EvidenceVerifier
= completion authority

Model Gateway
= configurable model/provider routing

Permission Broker
= action authorization
```

---

# 28. FINAL USER EXPERIENCE

The user says:

```text
Mentrix, implement JIRA-842.
```

ZECT executes:

```text
Jira
  ↓
WorkItem
  ↓
Project Intelligence
  ↓
Planner
  ↓
PLAN.md
  ↓
Approval / policy
  ↓
LongRunningAgentRuntime
  ↓
Coding Agent
  ↓
Test Agent
  ↕
Coding Agent
  ↓
Review Agent
  ↕
Coding Agent
  ↓
AcceptanceVerifier
  ↓
EvidenceVerifier
  ↓
READY_TO_SHIP
  ↓
PR / CI
  ↓
Jira / Camunda
```

The run may continue for minutes, hours, or across process restarts without depending on a single model context or HTTP request.

That is the target ZECT/Mentrix agentic coding platform.

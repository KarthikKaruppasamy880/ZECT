# MENTRIX ENGINEERING AGENTS + AUTOMATION LOOPS

## Purpose

Use this file in Cursor to extend the existing ZECT/Mentrix Automation Loop architecture with internal engineering roles for planning, coding, testing, review, and acceptance.

Work from the current merged `develop` after PR #130 is merged.

Do **not** create:
- another loop engine;
- another orchestrator;
- another WorkItem system;
- another ContextEngine;
- another memory system;
- another model gateway;
- another Coding Agent.

Reuse the existing ZECT/Mentrix architecture:
- Mentrix
- WorkItem
- ProjectIntelligence
- ContextEngine
- ForgeLoop
- Mentrix Coding Agent (`mentrix_native`)
- Ultra Review
- EvidenceVerifier
- Automation Loops
- Permission Broker
- Model Gateway
- ArtifactStore
- WorkItemEvent
- Jira / Camunda
- Skills / Playbooks
- Checkpoint / Resume / Circuit Breaker

The goal is to make Planner, Coder, Tester, Reviewer, and Acceptance specialized **internal roles** under Mentrix.

---

## 1. Canonical Architecture

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
                   Context Engine
                            │
                  Project Intelligence
                            │
                            ▼
                       ForgeLoop
                            │
                            ▼
                         PLANNER
                            │
                         PLAN.md
                            │
                       Approval Gate
                            │
                            ▼
                     CODING AGENT
                            │
                            ▼
                       TEST AGENT
                         │      │
                      FAIL     PASS
                         │      │
                         └────► │
                       CODER    ▼
                           REVIEW AGENT
                              │     │
                         BLOCKING  CLEAN
                              │     │
                              └─► CODER
                                    │
                                    ▼
                          ACCEPTANCE VERIFIER
                                    │
                                    ▼
                           EVIDENCE VERIFIER
                              │           │
                            FAIL         PASS
                              │           │
                        BLOCK/LOOP   READY_TO_SHIP
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

## 2. Product Boundary

Do not expose Planner, Coder, Tester, Reviewer, or Acceptance as separate products.

The user-facing model remains:

```text
User
  ↓
Mentrix
```

Internal responsibility:

```text
Mentrix
    ↓
ForgeLoop
    ↓
Engineering Team
    ├── Mentrix Planner
    ├── Mentrix Coding Agent
    ├── Mentrix Test Agent
    └── Mentrix Review Agent
    ↓
Acceptance Verifier
    ↓
EvidenceVerifier
```

Rules:
- **Mentrix** = user-facing intelligence.
- **ForgeLoop** = SDLC manager/orchestrator.
- **Automation Loops** = repetition, trigger, budgets, checkpointing, escalation.
- **Specialized agents** = internal workers.
- **EvidenceVerifier** = final completion authority.

---

## 3. Trigger and Loop Runtime

PR #130 Automation Loops are the canonical loop framework.

Use the existing `MentrixAutomationLoop`.

Do not install or introduce a competing loop runtime.

Runtime:

```text
Trigger
  ↓
WorkItem / PersonalAction
  ↓
Context + Skills / Playbook
  ↓
Existing Mentrix Executor
  ↓
EvidenceVerifier
  ↓
Policy / Human Gate
  ↓
Persist State
  ↓
Next Iteration
```

Triggers:

```text
Scheduled Trigger
Event Trigger
Manual Trigger
```

Autonomy levels:

```text
L0 — Observe
L1 — Recommend
L2 — Assisted
L3 — Autonomous
```

L0/L1 should be the default for new loops.

L2/L3 require explicit policy/configuration.

---

## 4. Mentrix Planner

Planner must:
- analyze User / Jira / Camunda requirements;
- retrieve bounded Project Intelligence;
- inspect relevant repository architecture;
- identify affected surfaces, dependencies, risks, tests, and acceptance evidence;
- create/update:

```text
REQUIREMENTS.md
PLAN.md
ACCEPTANCE.md
RISKS.md
EXECUTION_MANIFEST.json
```

Every requirement must map to implementation operations, verification, and acceptance evidence.

Planner must not:
- modify production code;
- declare implementation complete;
- set READY_TO_SHIP;
- bypass approvals.

---

## 5. Mentrix Coding Agent

Reuse the existing real `mentrix_native` Coding Agent only.

Inputs:

```text
approved PLAN.md
current WorkItem
current operation
relevant source files
Project Intelligence
Skills / Playbooks
permissions
previous errors
```

Tools:

```text
read
search
inspect symbols
edit
create
run
test
git status
git diff
```

For each operation:

```text
OP start
  ↓
load bounded context
  ↓
perform change
  ↓
record changed files
  ↓
run verification
  ↓
checkpoint
  ↓
update state
```

Coder must not:
- self-declare READY_TO_SHIP;
- skip mandatory operations;
- silently ignore failing tests;
- exceed permissions/budgets/path constraints.

---

## 6. Mentrix Test Agent

Add an explicit independent Test Agent role.

Inputs:

```text
requirements
acceptance criteria
changed files
execution manifest
repository test architecture
risk/security context
```

Determine applicable verification:

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

Use deterministic tools first.

Write structured:

```text
TEST_RESULTS.json
```

Failure loop:

```text
Coding Agent
    ↓
Test Agent
    ↓
FAIL
    ↓
Coding Agent fixes
    ↓
Test Agent reruns
```

Tester must not hide or skip failures because the code looks correct.

---

## 7. Mentrix Review Agent

Reuse/evolve Ultra Review.

Reviewer must inspect:
- actual git diff;
- relevant source;
- requirements;
- PLAN.md;
- test results;
- architecture/security context.

Review categories:

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
requirements coverage
```

Finding schema:

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
false-positive
waived
```

Verified blocking findings route back to Coding Agent.

Unverified/false-positive findings must not trigger arbitrary edits.

---

## 8. Acceptance Verifier

Reuse/extend deterministic EvidenceVerifier behavior.

Verify:
- operation coverage;
- requirement coverage;
- acceptance-criteria coverage;
- test results;
- review blockers;
- security blockers;
- required approvals.

Only verified success can transition to:

```text
READY_TO_SHIP
```

LLM text alone can never pass this gate.

---

## 9. Engineering Loop

```text
Trigger
   ↓
WorkItem
   ↓
Project Intelligence
   ↓
Planner
   ↓
PLAN.md
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
      Acceptance Verifier
               ↓
       EvidenceVerifier
               │
         ┌─────┴─────┐
         │           │
       FAIL         PASS
         │           │
    BLOCK/LOOP   READY_TO_SHIP
                     │
                     ▼
                  PR / CI
                     │
               Jira / Camunda
                     │
                     ▼
               Persist State
```

---

## 10. Required Engineering Loop Definitions

Add these loop definitions:

```text
engineering_delivery
bug_fix
jira_delivery
ci_fix
pr_review_fix
```

### engineering_delivery

```text
Planner
  ↓
approval
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
PR
```

---

## 11. Budgets and Infinite-Loop Protection

Every engineering loop must support:

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

Circuit breaker:

```text
Attempt 1
Attempt 2
Attempt 3
same failure
    ↓
CIRCUIT BREAKER
    ↓
NEEDS_HUMAN_DECISION
```

Persist:
- exact blocker;
- last successful operation;
- failed operation;
- last evidence;
- resume point;
- budget consumed.

---

## 12. Checkpoint / Resume

Persist after:
- operation start;
- file changes;
- command execution;
- test result;
- review result;
- operation completion;
- operation failure;
- block/escalation.

Store:

```text
WorkItem
EXECUTION_MANIFEST.json
EXECUTION_STATE.json
worktree_path
base_commit_sha
current_commit_sha
evidence
resume_operation
```

---

## 13. Model Routing

Use the existing Model Gateway.

Recommended routing:

```text
Planner
→ strong reasoning model

Coding Agent
→ strongest configured coding model

Test Agent
→ deterministic tools first; model for test design/failure analysis

Review Agent
→ independent strong reviewer model

Acceptance / Evidence
→ deterministic rules first
```

Preserve telemetry:
- requested model;
- actual model;
- provider;
- local/cloud;
- fallback_used;
- fallback_reason;
- latency.

Restricted/confidential work must honor local-only policy and never silently fallback to cloud.

---

## 14. Agent Communication

Agents communicate through durable artifacts/state, not uncontrolled agent chat.

Canonical artifacts:

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

---

## 15. Permissions and Security

All agents remain subject to:
- Permission Broker;
- data classification;
- path allowlists;
- connector scopes;
- model policy;
- audit;
- secret protection.

L3 Autonomous mode does **not** bypass permissions.

High-risk actions remain policy-controlled:

```text
git push
PR merge
deployment
secret access
external message
destructive filesystem operation
```

Use:

```text
ALLOW
CONFIRM
DENY
```

---

## 16. Required Tests

Add tests proving:

1. Planner cannot edit production code.
2. Planner cannot mark READY_TO_SHIP.
3. Coder cannot mark READY_TO_SHIP.
4. Coder executes only approved manifest operations.
5. Test failure routes back to Coder.
6. Reviewer blocking verified finding routes back to Coder.
7. False/unverified review finding does not cause arbitrary edits.
8. Incomplete requirement cannot pass AcceptanceVerifier.
9. Incomplete acceptance criterion cannot pass AcceptanceVerifier.
10. 100-operation manifest cannot finish at 99/100.
11. Repeated identical failures trigger circuit breaker.
12. No-progress condition triggers escalation.
13. Resume continues from persisted checkpoint.
14. L3 still obeys permissions.
15. L3 still obeys security/data-classification policy.
16. Token/cost/runtime budgets are enforced.
17. Coding Agent uses the real native path where required.
18. Successful full engineering flow reaches READY_TO_SHIP with evidence.
19. Failed tests prevent READY_TO_SHIP.
20. Blocking security/review findings prevent READY_TO_SHIP.

---

## 17. Acceptance Artifact

Produce:

```text
MENTRIX_ENGINEERING_AGENTS_ACCEPTANCE.md
```

Include:
- `VIABLE / BLOCKED`
- canonical architecture
- role boundaries
- loop definitions
- autonomy levels
- model routing
- budgets
- circuit breaker
- checkpoint/resume
- permission/security behavior
- planner tests
- coder tests
- tester tests
- reviewer tests
- acceptance/evidence tests
- end-to-end engineering loop result
- external blockers
- remaining gaps
- non-claims

Do not claim:
- perfect code generation;
- zero errors;
- zero hallucinations;
- unrestricted autonomy;
- fully local execution unless runtime verified.

Only claim capabilities backed by executable evidence.

---

## 18. Final Architectural Rule

```text
Mentrix = user-facing intelligence

Automation Loops = triggers, repetition, budgets, state, circuit breakers

ForgeLoop = SDLC orchestration

Planner = planning worker

Mentrix Coding Agent = code execution worker

Test Agent = independent verification worker

Review Agent / Ultra Review = independent code-quality worker

AcceptanceVerifier + EvidenceVerifier = completion authority
```

No internal agent may independently declare the WorkItem complete.

---

## Final Goal

Allow the user to say:

```text
"Mentrix, implement JIRA-842."
```

and have ZECT safely execute:

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
Approval
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
Jira / Camunda update
```

with persistent state, bounded context, budgets, permissions, security, evidence, and human escalation when required.

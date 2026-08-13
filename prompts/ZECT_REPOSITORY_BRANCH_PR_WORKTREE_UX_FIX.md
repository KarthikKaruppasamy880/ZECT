# ZECT — Repository / Branch / PR / Worktree UX Audit, Fix & Live Acceptance

## Goal

Audit, fix, and LIVE-verify the complete ZECT Project/Repository/Branch/PR onboarding experience.

Reuse the existing Phase 6 repository architecture. Do not create another repository catalog, Git orchestration system, Project model, or parallel Developer workflow.

Perform this work only after the currently active PR/work is safely completed or frozen.

---

## 1. Required User-Facing Capabilities

From the real `/projects` UI, a normal authorized user must be able to discover and use all of these flows.

### Open Existing Local Repository

Provide a visible action:

```text
Open Existing Local Repository
```

The user must be able to browse/select an existing local Git folder.

Example use case:

```text
C:\Users\<user>\...\ZECT
```

Required behavior:
- validate that the selected folder is a Git repository;
- detect remote/origin;
- detect current branch;
- detect HEAD SHA;
- detect dirty/clean state;
- bind through the existing Project + Repo architecture;
- activate the repository for Developer;
- do not duplicate an already registered repository.

### Clone Remote Repository

Provide:

```text
Clone Remote Repository
```

Accept a Git URL such as:

```text
https://github.com/KarthikKaruppasamy880/ZECT.git
```

Allow the user to choose/approve the destination.

Required:

```text
Git URL
→ authorization/policy
→ destination
→ clone
→ repository identity
→ Project/Repo binding
→ branch/HEAD
→ activate
→ Project Intelligence bootstrap
→ Developer
```

Never expose Git credentials in logs/UI.

### Discover Local Repositories

Provide:

```text
Discover Local Repositories
```

Only scan folders explicitly approved by the user.

Do not crawl the entire filesystem without consent.

For each discovered repository show enough identity to distinguish it:
- repository name;
- local path;
- origin/remote where available;
- current branch;
- dirty/clean status;
- whether already registered.

Allow an authorized discovered repository to be attached/bound without duplication.

### Create New Project

Improve the existing Create Project experience.

It must support choices such as:

```text
Create Empty Project
Use Existing Registered Repository
Open Existing Local Repository
Clone Remote Repository
```

Do not limit repository setup to GitHub owner/repository metadata only.

### Attach Existing Repository

Allow an already registered ZECT Repo to be attached to an existing Project without cloning or creating a duplicate Repo record.

### Select Repo

The top-level `Select Repo` control should:
- list registered/authorized repositories;
- identify active repo;
- support switching active repo safely;
- expose discoverable actions for Open / Clone / Discover / Add where appropriate.

It must not be only an opaque selector if onboarding actions otherwise remain hidden.

---

## 2. Branch Management

For an active repository expose:

```text
Current branch
Local branches
Remote branches
HEAD SHA
Dirty / clean state
Fetch / refresh
```

Support safe branch switching.

Before switching:

```text
git status
   ↓
clean?
 ├─ YES → switch
 └─ NO  → require safe user decision
           ├─ Cancel
           ├─ Stash
           ├─ Commit
           └─ other existing approved policy action
```

Never silently discard local changes.

Do not use destructive reset/clean operations without explicit authorization.

After branch change:
- refresh HEAD SHA;
- update active repository/session state;
- invalidate stale Project Intelligence correctly;
- preserve repo/workspace identity.

---

## 3. Pull Request Support

For supported GitHub-backed repositories, provide a PR workflow.

Support either/both:

```text
List Pull Requests
Open Pull Request by URL/number
```

Resolve:

```text
PR
→ repository
→ base branch
→ head branch
→ head SHA
→ current PR state
```

A user should be able to select a PR and open it for Developer/Review without manually preparing the branch outside ZECT.

---

## 4. PR Worktrees

Prefer isolated Git worktrees for PR/agent work instead of disturbing the user's main checkout.

Target:

```text
Main repository
   │
   ├── develop/main working copy
   │
   └── ZECT-managed worktrees
         ├── pr-136
         ├── pr-137
         └── workitem-...
```

Bind the Developer/LRR session to:

```text
project_id
repository_id
branch
worktree_path
base_commit_sha
current_commit_sha
pr_id where applicable
```

The Coding Agent/Test Agent/Ultra Review must operate against the correct worktree.

Never allow one active agent run to accidentally edit another PR/worktree.

---

## 5. Project Intelligence Integration

After repository/branch/PR/worktree changes:

```text
new active repo/HEAD
        ↓
Project Intelligence compares provenance
        ↓
matching?
 ├─ YES → READY
 └─ NO  → STALE / NOT_INDEXED
                ↓
             re-index
                ↓
              READY
```

Reuse Phase 7:
- Lattice;
- Blueprint;
- Knowledge;
- Verified Memory;
- Skills/Playbooks;
- ContextPack;
- repo+commit provenance.

Do not create another indexing/intelligence stack.

ASK/PLAN/AGENT must not silently use stale repository intelligence.

---

## 6. Security / Authorization

Preserve Phase 13 and later security rules.

Users may only list/open/clone/attach/switch repositories and Projects they are authorized to access.

Never trust client-provided:
- `project_id`;
- `repository_id`;
- local path;
- branch;
- PR ID/URL;
- worktree path;

as authorization proof.

Backend must independently authorize operations.

Local filesystem access must:
- use existing Permission Broker/policy;
- remain within user-approved roots;
- prevent path traversal;
- prevent arbitrary sensitive-directory access;
- avoid secrets exposure.

Git credentials/tokens must never be printed.

Protected branch and Git write policies remain enforced.

---

## 7. Audit Before Implementation

First inspect the existing Phase 6 and later repository functionality.

For every capability classify:

```text
ALREADY_BUILT
VISIBLE_AND_WORKING
BACKEND_ONLY
PARTIAL
MISSING
```

Audit at minimum:

```text
Create Project
Open Existing Local Repo
Browse local folder
Clone Git URL
Discover local repos
Attach registered repo
Select Repo
Repo activation
Branch listing
Remote branch listing
Fetch
Safe branch switch
Dirty-repo handling
PR listing
PR URL/number open
PR → head resolution
Git worktree creation/reuse
Developer worktree binding
LRR worktree binding
PI stale/re-index after HEAD change
```

Include exact code/API/UI/test locations.

Then implement only missing/broken wiring.

Do not rebuild already working infrastructure.

---

## 8. Real UI Requirements

The `/projects` experience should clearly expose repository onboarding.

Suggested user flow:

```text
Projects
   ↓
Add Project / Repository
   ├── Open Local Repository
   ├── Clone Git Repository
   ├── Discover Local Repositories
   ├── Select Registered Repository
   └── Open Pull Request
```

After selection:

```text
Project
Repository
Local path
Origin
Branch
HEAD
Status
Project Intelligence
```

Provide actions appropriate to the current state.

Avoid requiring users to know hidden routes or manually type internal URLs.

---

## 9. LIVE Headed Playwright Acceptance

LIVE acceptance is mandatory.

Start the real ZECT backend and frontend.

Use headed Playwright/browser automation against the actual application.

Do not rely only on unit/API tests.

Use controlled/disposable repositories/worktrees for destructive Git scenarios.

Do NOT reset, clean, or destructively modify the user's real ZECT working copy during acceptance.

### Flow A — Existing Local Repo

Prove visually and automatically:

```text
Projects
→ Open Existing Local Repo
→ select controlled local Git repo
→ bind
→ activate
→ Developer
→ correct repository files visible
→ branch list visible
→ correct HEAD shown
```

### Flow B — Branch Switch

```text
active repo
→ select another safe test branch
→ HEAD changes
→ Project Intelligence becomes STALE/NOT_INDEXED
→ re-index
→ READY
→ Developer uses new branch/context
```

### Flow C — Dirty Repo Safety

```text
controlled repo with uncommitted change
→ attempt branch switch
→ ZECT warns/blocks
→ choose safe action
→ verify no change is lost
```

No silent discard.

### Flow D — Clone Remote Repo

Using a safe test repository:

```text
Projects
→ Clone Remote Repository
→ Git URL
→ approved destination
→ clone
→ bind
→ activate
→ Developer
```

Do not use credentials that may be exposed in test artifacts.

### Flow E — Discover

```text
Projects
→ Discover Local Repositories
→ choose approved test root
→ repository discovered
→ attach/bind
→ no duplicate catalog record
```

### Flow F — PR / Worktree

Using a controlled PR/test repo:

```text
Projects/Repository
→ Pull Requests
→ select/open PR
→ resolve head branch/SHA
→ create/reuse isolated worktree
→ Developer opens worktree
→ correct branch/SHA shown
→ Coding/Test context bound to worktree
```

Verify the main checkout was not switched or modified.

---

## 10. Visual Evidence

Capture:
- headed browser run;
- screenshots for each major flow;
- Playwright trace;
- video where supported;
- API/runtime evidence;
- Git status/branch/SHA evidence for controlled test repos.

Pause at useful final screens for manual inspection where practical.

If headed browser execution is unavailable, explicitly report:

```text
HEADED_BROWSER_NOT_AVAILABLE
```

Do not claim the user visually observed the run.

---

## 11. Automated Tests

Add/update tests for:
- local repo validation;
- duplicate repo prevention;
- clone;
- discovery approved-root boundary;
- repo authorization;
- branch listing;
- dirty branch-switch protection;
- branch/HEAD refresh;
- PR resolution;
- worktree identity/isolation;
- Project Intelligence stale transition;
- re-index → READY;
- Developer correct repo/worktree;
- cross-user/project authorization;
- path traversal rejection;
- secret-safe Git operations.

Use deterministic Git fixtures/repos where possible.

---

## 12. Acceptance Artifact

Create:

```text
ZECT_REPOSITORY_BRANCH_PR_UX_ACCEPTANCE.md
```

Include:
- audit matrix;
- existing architecture reused;
- missing UX/wiring implemented;
- local repo proof;
- clone proof;
- discover proof;
- attach proof;
- branch proof;
- dirty-state safety proof;
- PR proof;
- worktree proof;
- Project Intelligence stale/re-index proof;
- authorization/security proof;
- headed Playwright evidence;
- screenshots/trace/video paths;
- tests;
- frozen regressions;
- remaining PARTIAL/BLOCKED items.

Allowed status:

```text
PASS
PARTIAL
BLOCKED
BLOCKED_EXTERNAL
```

No fabricated evidence.

---

## 13. Frozen Regression

After implementation run the current authoritative frozen regression baseline, including where applicable:

```text
Present A1–A8
Phase 5–13
B Document Intelligence
C Web Intelligence
D Learning Expansion
Developer ASK/PLAN/AGENT
LongRunningAgentRuntime
Project Intelligence
Companion
Voice
```

Read the latest master plan/acceptance files for the exact current frozen set.

---

## 14. Stop Condition

STOP after repository/branch/PR/worktree UX acceptance.

Do not auto-merge.

Do not start unrelated:
- Graphify;
- OCR/XLSX;
- packaging completion;
- Ultra Review closed-loop redesign;
- new agents;
- new RAG/vector systems;
- additional product roadmap work.

Return the acceptance evidence for human review.

---

# Final Target

A normal ZECT user should be able to do this without leaving the application:

```text
Projects
   ↓
Open Local / Clone / Discover / Existing Repo / PR
   ↓
Repository
   ↓
Branch or isolated PR Worktree
   ↓
Project Intelligence
   ↓
ASK / PLAN / AGENT
```

Repository onboarding and Git operations must be discoverable, safe, authorized, provenance-aware, and proven in the real ZECT UI.

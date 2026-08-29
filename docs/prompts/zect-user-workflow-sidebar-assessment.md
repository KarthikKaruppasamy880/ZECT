You are a Principal AI Product Architect, Enterprise UX Architect, Agentic Workflow Engineer, Context Engineering Specialist, and Technical Documentation Lead.

Analyze the complete ZECT repository and all documentation located under:

C:\Users\karuppk\Downloads\ZECT\docs

The goal is to determine exactly how a user should use ZECT, whether the current sidebar supports that journey, how Mentrix helps, whether Mentrix Delivery is necessary, and how ZECT can reduce prompting effort, context size, and LLM cost.

IMPORTANT RULES

1. Do not write or modify production code.
2. Do not assume a feature works because it appears in the sidebar.
3. Verify each feature using:
   - UI routes
   - frontend components
   - backend endpoints
   - services
   - database models
   - agents
   - prompts
   - orchestration logic
   - documentation
   - tests
4. Clearly separate:
   - Verified
   - Partially Verified
   - UI Only
   - Backend Only
   - Disconnected
   - Duplicate
   - Not Implemented
   - Unable to Verify
   - Recommended Future State
5. Do not accept “100% complete” claims without verifying the actual implementation.
6. Do not implement changes during this assessment.
7. Support every major conclusion with file paths, route names, functions, APIs, services, and documentation references.

# PRODUCT AREAS TO VERIFY

The current product areas are described as:

- Workspace — Project management
- Understand — Lattice code analysis
- Deliver — Ask → Plan → Build → Review → Deploy
- Quality — Code review and CWE/OWASP mapping
- Enterprise — RBAC, audit trail, token budgets
- Labs — Memory System, Dream Engine, Data Flywheel

The sidebar also contains many modules, including:

## Workflow

- Mentrix Companion
- Mentrix Delivery

## Workspace

- Dashboard
- Projects
- Repo Workspace
- Settings

## Understand

- Lattice Graph
- Repo Analysis
- Blueprint
- Doc Generator
- Code Index
- Docs Center

## Deliver

- Agent Mode
- Ask
- Plan
- Build
- Snippet Review
- Deploy
- Orchestration

## Quality

- Mentrix Ultra Review
- Rules Engine
- Sandbox Gate
- CI Monitor
- Git Operations

## Enterprise

- Integrations
- Audit Trail
- Export/Share
- Output History
- Analytics
- Token Controls
- Secrets Manager

## Labs

- Skill Library
- Skills Engine
- Memory System
- Dream Engine
- Data Layer
- Data Flywheel
- Permissions
- Transfer & Onboard
- Knowledge Base
- Playbooks
- Scheduled Tasks
- Session Insights
- Conversations
- App Runner
- File Explorer

# PHASE 1 — DOCUMENTATION INVENTORY

Read all files under the docs directory.

Create an inventory:

| Document | Purpose | Product Area | Current or Outdated | Related UI Module | Related Backend | Gaps |

Identify:

- Duplicate documents
- Conflicting workflows
- Outdated architecture
- Missing user guides
- Missing implementation guides
- Documentation that claims functionality not present in the code
- Features present in code but missing from documentation
- Terminology inconsistencies, especially:
  - Mentrix
  - Mentrix Companion
  - Mentrix Delivery
  - Lattice
  - Dream Engine
  - Agent Mode
  - Orchestration
  - Build
  - App Runner
  - Memory System
  - Data Flywheel

# PHASE 2 — SIDEBAR AUDIT

Inspect the actual sidebar configuration and every sidebar route.

For each sidebar option identify:

| Section | Module | User Purpose | Route | Frontend Component | Backend API | Database | Agent/LLM | Connected? | Status | Recommendation |

Determine:

- Which options are truly needed
- Which options are duplicates
- Which options overlap
- Which options should be merged
- Which options should be hidden under Advanced
- Which Labs features should remain experimental
- Which items confuse users
- Which modules require too many clicks
- Which modules have no obvious next action
- Which modules are not connected to Mentrix
- Which modules have UI but no working backend
- Which modules have backend functionality but poor discoverability

Do not recommend keeping a sidebar item just because it exists.

# PHASE 3 — DEFINE THE USER TYPES

Evaluate ZECT for these user types:

1. Developer with an existing legacy repository
2. Developer starting a new application
3. QA engineer
4. Architect
5. Product manager or business analyst
6. DevOps engineer
7. Engineering manager
8. Nontechnical user
9. Enterprise administrator

For each user type document:

- Main goal
- Starting point
- Required modules
- Modules they should not need to see
- Expected outputs
- Approval points
- Common failure paths
- Required documentation
- How Mentrix assists
- How many prompts should normally be required

# PHASE 4 — LEGACY REPOSITORY USER JOURNEY

Define the complete workflow for a user who already has a legacy repository.

The expected journey should be validated against the real product:

1. Sign in
2. Create or select a project
3. Connect, clone, or select a repository
4. Choose branch
5. Configure repository permissions
6. Ingest the repository
7. Build the Lattice/code graph
8. Index symbols, dependencies, APIs, databases, tests, and documentation
9. Run repository analysis
10. Generate architecture and blueprint
11. Identify risks and technical debt
12. Ask questions about the repository
13. Create an implementation or modernization plan
14. Review generated tasks
15. Execute changes in a sandbox
16. Run quality, security, and test gates
17. Review changes
18. Request human approval
19. Create commit or pull request
20. Deploy or export
21. Update documentation
22. Store project memory for future work

For every step provide:

| Step | Where User Goes | User Action | Mentrix Action | Context Used | Output | Approval | Failure Path | Cost Control |

Identify any step where the user must leave ZECT and use another tool.

Identify any step that requires manually repeating repository context.

Generate a Mermaid user-journey diagram.

# PHASE 5 — NEW APPLICATION USER JOURNEY

Define the complete workflow for a user starting from an idea.

Validate whether Dream Engine is intended for this workflow.

Expected flow:

1. Describe idea
2. Clarify requirements
3. Generate PRD
4. Generate functional and technical requirements
5. Recommend architecture
6. Select technology stack
7. Generate project structure
8. Create implementation plan
9. Generate tasks
10. Generate code
11. Run application
12. Test
13. Review security and quality
14. Generate documentation
15. Approve
16. Commit and create pull request
17. Deploy
18. Monitor
19. Continue the project later using memory

For every step explain:

- Current ZECT module
- Mentrix role
- Required context
- Output
- Human approval
- Missing implementation
- Recommended simplification

Generate a Mermaid workflow.

# PHASE 6 — MENTRIX ROLE ANALYSIS

Determine exactly what Mentrix is today.

Classify Mentrix as one or more of:

- Persona
- Chat assistant
- Workflow coordinator
- Delivery orchestrator
- Agent
- Multi-agent supervisor
- Voice assistant
- Repository-aware assistant
- Human approval interface
- Product navigation assistant
- Personal engineering assistant

Verify whether Mentrix can:

- Understand the selected project
- Understand the selected repository
- Read the Lattice graph
- Use code indexes
- Use documentation
- Retrieve conversation memory
- Retrieve project memory
- Select the correct agent
- Select the correct tool
- Plan tasks
- Build code
- Run tests
- Review code
- Check security
- Request approval
- Create a pull request
- Deploy
- Explain progress
- Resume prior work
- Respond through voice
- Reduce the need for manual navigation

For each capability provide evidence and status.

# PHASE 7 — IS MENTRIX DELIVERY NECESSARY?

Analyze whether “Mentrix Delivery” should be:

1. A separate sidebar page
2. The primary home page
3. A workflow dashboard
4. A unified interface replacing Ask, Plan, Build, Review, and Deploy
5. A shortcut into existing modules
6. Removed because it duplicates existing functionality
7. Renamed

Compare Mentrix Delivery with:

- Agent Mode
- Ask
- Plan
- Build
- Snippet Review
- Deploy
- Orchestration
- Mentrix Companion
- Dream Engine

Create this matrix:

| Capability | Mentrix Delivery | Agent Mode | Ask | Plan | Build | Review | Deploy | Orchestration | Dream Engine |

Identify duplication and ownership.

Answer directly:

- What unique problem does Mentrix Delivery solve?
- Why should a user open it?
- What happens after “Mentrix Engage”?
- Does it truly orchestrate all stages?
- Does it only redirect to existing modules?
- Does it preserve context between stages?
- Does it provide progress, approvals, and recovery?
- Should the user need to enter source language, target language, workspace path, and project key manually?
- Can these values be inferred automatically?
- Should “Mode” be visible to normal users?
- Should Mentrix choose the mode automatically based on intent?

# PHASE 8 — LESS-PROMPT WORKFLOW

Design how ZECT should allow users to solve problems with minimal prompting.

A user should be able to give one high-level instruction such as:

“Analyze this legacy Java application, identify security and architecture risks, create a modernization plan, upgrade one module safely, run tests, update documentation, and prepare a pull request.”

ZECT should automatically:

1. Detect the active project and repository
2. Retrieve relevant repository context
3. Understand the user’s intent
4. Ask only essential clarification questions
5. Create a structured plan
6. Select agents and tools
7. Estimate context and token requirements
8. Execute approved steps
9. Validate results
10. Preserve context between stages
11. Show progress
12. Request approval for dangerous actions
13. Save the run for later continuation

Document:

- What can be inferred
- What must be asked
- What defaults can be applied
- What should require approval
- What context must persist
- How the user can correct the assistant
- How to avoid repeatedly prompting with repository details

Generate an optimized one-prompt workflow diagram.

# PHASE 9 — CONTEXT MANAGEMENT

Analyze the current context architecture.

Determine how ZECT handles:

- Project context
- Repository context
- Branch context
- File context
- Symbol context
- Dependency context
- Database-schema context
- API context
- Documentation context
- User conversation history
- Project memory
- Task history
- Agent state
- Tool results
- Lattice graph
- Code index
- Vector retrieval
- Keyword retrieval
- Graph retrieval
- Context compression
- Context summaries
- Context freshness
- Token budgeting

Identify whether the same repository data is repeatedly sent to the LLM.

Identify whether context is reused across:

- Ask
- Plan
- Build
- Review
- Deploy
- Mentrix Delivery
- Dream Engine

Create:

| Context Type | Current Source | Storage | Retrieval | Reused? | Risk | Recommended Change |

# PHASE 10 — LLM COST OPTIMIZATION

Analyze how ZECT can reduce LLM costs without reducing quality.

Evaluate:

- Model routing
- Small model for classification
- Small model for summaries
- Strong model only for complex reasoning
- Cached repository summaries
- Cached file summaries
- Incremental indexing
- Retrieval before prompting
- Graph-based neighborhood retrieval
- Symbol-level context
- Diff-only reviews
- Prompt deduplication
- Conversation summarization
- Session checkpointing
- Reusing prior plans
- Reusing tool output
- Token budgets
- Per-project budgets
- Per-user budgets
- Agent iteration limits
- Retry limits
- Early stopping
- Parallel execution controls
- Local/static analysis before LLM use
- Rule-engine checks before AI review
- Batch requests
- Embedding reuse
- Provider fallback
- Cost visibility

For every recommendation provide:

| Recommendation | Current Problem | Expected Benefit | Quality Risk | Complexity | Priority |

Do not invent unsupported dollar savings.

Explain where LLM usage is unnecessary and deterministic tools should be used instead.

# PHASE 11 — RECOMMENDED SIDEBAR

Design a simplified sidebar for normal users.

Consider a structure such as:

## Start

- Home
- Projects
- Mentrix

## Understand

- Repository
- Architecture
- Documentation

## Deliver

- Plan
- Build
- Review
- Release

## Operate

- Deployments
- Monitoring
- History

## Enterprise

- Integrations
- Security
- Audit
- Usage and Cost
- Administration

## Advanced or Labs

- Skills
- Memory
- Dream Engine
- Data Flywheel
- Graph Explorer
- App Runner
- Developer Tools

Do not use this structure blindly.

Base the final recommendation on the verified implementation.

For every existing sidebar option decide:

- Keep
- Rename
- Merge
- Move
- Hide under Advanced
- Keep in Labs
- Remove
- Unable to determine

Create:

| Current Item | Decision | New Location | Reason | User Impact |

# PHASE 12 — DOCUMENTATION REQUIRED FOR USERS

Create a documentation plan covering:

1. Getting Started
2. First Project
3. Connecting a Repository
4. Working with a Legacy Repository
5. Starting a New Application
6. Using Mentrix
7. Using Lattice Graph
8. Asking Repository Questions
9. Creating Plans
10. Building and Modifying Code
11. Running Applications
12. Quality and Security Review
13. Pull Requests
14. Deployments
15. Memory and Context
16. Token and Cost Controls
17. Enterprise Administration
18. Troubleshooting
19. Common Workflows
20. Glossary

Each guide must explain:

- When to use the feature
- Where to find it
- Prerequisites
- Step-by-step workflow
- Expected output
- Error conditions
- Related modules
- Screenshots needed
- Role permissions

# REQUIRED CURRENT-STATE DIAGRAMS

Generate Mermaid diagrams for:

1. Current ZECT product architecture
2. Current sidebar-module map
3. Current Mentrix Delivery flow
4. Current legacy repository workflow
5. Current new-application workflow
6. Current Ask → Plan → Build → Review → Deploy flow
7. Current context-management flow
8. Current LLM-request flow
9. Current approval workflow
10. Current user-navigation flow

# REQUIRED TARGET-STATE DIAGRAMS

Generate Mermaid diagrams for:

1. Simplified target product architecture
2. Target sidebar and navigation
3. Target Mentrix orchestration
4. Target one-prompt legacy modernization workflow
5. Target new-application workflow
6. Target context-management architecture
7. Target cost-optimized LLM routing
8. Target human-approval workflow
9. Target repository intelligence architecture
10. Current-to-target migration flow

# REQUIRED OUTPUT FILES

Create:

docs/zect-user-experience-assessment/

Generate:

1. 01-executive-summary.md
2. 02-documentation-inventory.md
3. 03-sidebar-audit.md
4. 04-user-personas.md
5. 05-legacy-repository-user-guide.md
6. 06-new-application-user-guide.md
7. 07-mentrix-role-analysis.md
8. 08-mentrix-delivery-assessment.md
9. 09-one-prompt-workflow.md
10. 10-context-management-analysis.md
11. 11-llm-cost-optimization.md
12. 12-recommended-sidebar.md
13. 13-current-state-diagrams.md
14. 14-target-state-diagrams.md
15. 15-user-documentation-plan.md
16. 16-product-gap-analysis.md
17. 17-prioritized-roadmap.md
18. 18-end-user-tool-guide.md
19. 19-administrator-guide.md
20. 20-validation-report.md

Also create:

- zect-sidebar-inventory.csv
- zect-module-connection-matrix.csv
- zect-user-journey-matrix.csv
- zect-context-inventory.csv
- zect-cost-optimization-backlog.csv
- zect-navigation-change-register.csv
- zect-documentation-gap-register.csv

# FINAL REQUIRED ANSWERS

At the end, answer clearly:

1. How should a first-time user start using ZECT?
2. How should a user with a legacy repository use ZECT?
3. What is the shortest successful workflow?
4. What is Mentrix responsible for?
5. Why does Mentrix Delivery exist?
6. Is Mentrix Delivery currently necessary?
7. Which modules duplicate Mentrix Delivery?
8. Which sidebar options should be removed, merged, or hidden?
9. Is the current sidebar understandable for a new user?
10. Are all modules really 100% complete?
11. Which modules are disconnected or UI-only?
12. How is context currently managed?
13. Is context preserved across Ask, Plan, Build, Review, and Deploy?
14. How can ZECT require fewer prompts?
15. How can ZECT avoid repeatedly sending the same context?
16. How can ZECT reduce LLM cost?
17. Which operations should not use an LLM?
18. What should the simplified sidebar look like?
19. What documentation is missing?
20. What are the first 20 improvements to implement?

Start with:

- Repository map
- Documentation inventory
- Sidebar route inventory
- Assessment plan

Complete the verified current-state analysis before proposing the future-state design.

Do not code or modify production files.
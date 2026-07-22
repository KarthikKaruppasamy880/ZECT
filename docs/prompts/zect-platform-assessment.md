You are a principal AI platform architect, senior full-stack engineer, UX reviewer, and technical documentation specialist.

Your task is to perform a complete technical, architectural, functional, and user-experience assessment of the ZECT platform.

ZECT is intended to be an all-in-one AI engineering platform comparable in capability to tools such as Cursor, Devin, and other agentic development environments. A user should be able to plan, design, build, test, document, troubleshoot, and manage an application without needing to move to another tool.

Do not make assumptions based only on folder names or UI labels. Inspect the actual implementation, imports, routes, APIs, database connections, services, state management, events, hooks, agent definitions, prompts, workflows, and runtime behavior.

## Primary objectives

1. Understand the complete ZECT architecture.
2. Analyze every sidebar section and module.
3. Verify how the modules are connected.
4. Identify modules that are only UI placeholders or partially implemented.
5. Review the Dream Engine, Harness, Hooks, orchestration, documentation generation, and other AI capabilities.
6. Determine whether ZECT currently provides a complete end-to-end development experience.
7. Identify missing capabilities required to compete with Cursor, Devin, and similar tools.
8. Produce architecture diagrams, workflow diagrams, implementation guidance, and user documentation.

## Phase 1: Repository discovery

Inspect the complete repository and identify:

* Frontend applications
* Backend services
* API gateways
* AI or LLM services
* Agent definitions
* Prompt templates
* Tool definitions
* MCP integrations
* Database schemas
* Vector databases
* Authentication and authorization
* Workspace or project management
* File-system access
* Code-generation services
* Terminal or command-execution services
* Git integrations
* Deployment integrations
* Testing modules
* Documentation-generation modules
* Observability and logging
* Queue, event, and background-job systems
* State management
* Configuration and environment variables
* Feature flags
* Plugin or extension frameworks

Create a repository map showing the purpose of each major folder, service, and package.

## Phase 2: Sidebar and module analysis

Identify every item displayed in the ZECT sidebar.

For each sidebar section, document:

* Module name
* User purpose
* Frontend route
* Main UI components
* Backend API or service
* Database tables or storage
* AI model or agent used
* Prompt or context source
* Tools available to the module
* Input and output
* Dependencies
* Upstream and downstream modules
* Authentication and permissions
* Current implementation status
* Known limitations
* Missing error handling
* Missing empty states
* Missing loading states
* Missing user guidance
* Duplicate or overlapping functionality

Classify every sidebar item as:

* Fully implemented
* Partially implemented
* UI only
* Backend only
* Not connected
* Deprecated
* Duplicate
* Broken
* Unable to verify

Create a sidebar integration matrix with the following columns:

| Sidebar Module | Route | Frontend | Backend | Database | AI Agent | Connected Modules | Status | Gaps | Recommendation |

Also check whether the additional sidebar modules recently introduced are correctly wired into the application.

## Phase 3: Core AI capability review

Perform a detailed review of the following capabilities.

### Dream Engine

Determine:

* What the Dream Engine is intended to do
* How a user starts a Dream Engine workflow
* What inputs it accepts
* How it converts an idea into requirements, architecture, tasks, code, tests, and documentation
* Which AI models and prompts it uses
* How context is stored and transferred between stages
* Whether outputs are persistent
* Whether users can resume or modify a workflow
* How it connects to other ZECT modules
* Whether it is production-ready

### Harness

Determine whether an agent or execution harness exists.

Review:

* Agent runtime
* Tool registration
* Tool permissions
* Execution lifecycle
* Retry handling
* Timeout handling
* Failure recovery
* Human approval points
* Sandboxing
* Resource limits
* Audit logging
* Agent memory
* Session state
* Multi-agent coordination

Clearly distinguish between:

* A true agent execution harness
* A prompt wrapper
* A workflow engine
* A simple API integration

### Hooks

Identify all supported hooks, such as:

* Before-agent execution
* After-agent execution
* Before-tool execution
* After-tool execution
* On task creation
* On code generation
* On file modification
* On test completion
* On build failure
* On deployment
* On documentation generation
* On user approval
* On workflow completion

For each hook, identify where it is implemented, how it is registered, and whether users or plugins can extend it.

If hooks are missing, design a recommended hook framework.

### Orchestration

Analyze how ZECT orchestrates:

* User requests
* Context collection
* Requirement analysis
* Planning
* Agent selection
* Tool selection
* Task decomposition
* Code generation
* File modification
* Testing
* Debugging
* Documentation
* Deployment
* Human approval
* Failure recovery

Determine whether orchestration is:

* Hard-coded
* Rule-based
* Prompt-based
* Graph-based
* Event-driven
* Queue-based
* Multi-agent
* Hybrid

Document the full orchestration lifecycle from user request to final output.

Review whether agent state, task state, context, and execution history are persisted correctly.

## Phase 4: Context and memory architecture

Review how ZECT builds and manages context.

Check for:

* Repository indexing
* File selection
* Semantic search
* Keyword search
* Embeddings
* Vector storage
* Conversation memory
* Project memory
* User preferences
* Agent memory
* Task history
* Dependency graphs
* Code-symbol graphs
* Database-schema context
* API contract context
* Token-budget management
* Context compression
* Context summarization
* Context freshness
* Context isolation between projects and users

Identify risks such as:

* Sending too much context
* Missing relevant files
* Stale context
* Cross-project data leakage
* Token-limit failures
* Hallucinated dependencies
* Repeated indexing
* Inconsistent context between agents

Recommend a context-engineering architecture suitable for an enterprise AI development platform.

## Phase 5: Graph capability decision

Evaluate whether ZECT should use a graph-based solution such as a knowledge graph, code graph, dependency graph, workflow graph, or GraphRAG-style retrieval.

Do not recommend graph technology only because it is popular.

Determine whether graph capabilities would provide measurable value for:

* Code dependency analysis
* Module relationships
* Database relationships
* User-story traceability
* Requirement-to-code mapping
* Requirement-to-test mapping
* Agent workflow state
* Impact analysis
* Root-cause analysis
* Documentation navigation
* Cross-project knowledge
* Tool and plugin relationships

Compare these approaches:

1. Relational database only
2. Vector search only
3. Graph database only
4. Vector plus relational database
5. Vector plus graph database
6. Hybrid relational, vector, and graph architecture

For each option, explain:

* Benefits
* Complexity
* Operational cost
* Scalability
* Query patterns
* Data synchronization needs
* Suitability for ZECT

Provide a clear recommendation:

* Use graph now
* Introduce graph in a later phase
* Do not use graph
* Use graph only for selected capabilities

If graph functionality is recommended, provide:

* Suggested graph entities
* Suggested relationships
* Example graph schema
* Ingestion strategy
* Update strategy
* Query examples
* Integration points
* Migration plan
* Proof-of-concept scope

## Phase 6: End-to-end user workflow

Analyze the experience of a new user who wants to build an application using ZECT.

Document the ideal and current workflow:

1. Sign in
2. Create a workspace
3. Create or import a project
4. Connect a Git repository
5. Describe an idea
6. Generate requirements
7. Review architecture
8. Create implementation tasks
9. Generate or modify code
10. Run the application
11. Execute tests
12. Debug failures
13. Generate documentation
14. Review security and quality
15. Commit changes
16. Create a pull request
17. Deploy the application
18. Monitor the deployed application
19. Continue development later

For every step, identify:

* Current ZECT module
* User action
* System action
* Agent action
* Required context
* Tools invoked
* Data stored
* Approval point
* Output
* Failure path
* Recovery path
* Missing capability

Identify all points where the user currently needs to leave ZECT and use another product.

Provide recommendations to eliminate unnecessary tool switching.

## Phase 7: Documentation-generation review

Review the complete documentation-generation capability.

Check whether ZECT can generate and maintain:

* README files
* Product requirement documents
* Business requirement documents
* Functional specifications
* Technical design documents
* Architecture documents
* API documentation
* Database documentation
* Data-flow diagrams
* Sequence diagrams
* Deployment guides
* Installation guides
* Configuration guides
* Testing strategies
* Test plans
* Test cases
* Traceability matrices
* User manuals
* Troubleshooting guides
* Release notes
* Change logs
* Operational runbooks
* Support documentation

Verify:

* Whether generated documents use actual repository information
* Whether documents are updated after code changes
* Whether documents are version-controlled
* Whether users can select document templates
* Whether organization standards can be applied
* Whether diagrams are generated automatically
* Whether citations or source references are included
* Whether unsupported claims are introduced

Design a documentation workflow that keeps code and documentation synchronized.

## Phase 8: User experience and usability review

Review ZECT from the perspective of:

* New developers
* Senior developers
* QA engineers
* Product managers
* Architects
* Business analysts
* DevOps engineers
* Nontechnical users

Evaluate:

* Navigation
* Sidebar organization
* Naming consistency
* Discoverability
* Onboarding
* Tooltips
* Empty states
* Error messages
* Progress visibility
* Agent activity visibility
* Approval experience
* Accessibility
* Responsiveness
* Search
* Command palette
* Keyboard shortcuts
* Context awareness
* Workspace switching
* Project switching
* User confidence and trust

Identify confusing, redundant, hidden, or overly technical features.

Recommend a revised sidebar hierarchy and information architecture.

The proposed sidebar should clearly separate areas such as:

* Home
* Projects
* Dream Engine
* Agent Workspace
* Code
* Tasks
* Testing
* Documentation
* Integrations
* Deployments
* Monitoring
* Knowledge
* Settings

Only recommend these labels when they accurately match the product capabilities.

## Phase 9: Cursor and Devin capability comparison

Create an evidence-based capability comparison between ZECT and modern AI development environments.

Compare capabilities such as:

* Codebase understanding
* Repository indexing
* Inline editing
* Multi-file changes
* Terminal execution
* Autonomous task execution
* Planning
* Debugging
* Test generation
* Browser interaction
* Git support
* Pull-request workflows
* Deployment
* Documentation
* Agent memory
* Parallel agents
* Human approval
* MCP support
* Plugin framework
* Security
* Enterprise controls
* Observability
* Cost controls

Do not claim that ZECT supports a capability unless it is verified in the code.

Classify each capability as:

* Better than comparable tools
* Comparable
* Partially comparable
* Missing
* Unable to verify

## Required architecture diagrams

Generate diagrams using Mermaid syntax.

Create at least the following:

1. ZECT high-level system architecture
2. Frontend-to-backend component diagram
3. Sidebar-module dependency diagram
4. AI agent and tool architecture
5. Context and memory architecture
6. Dream Engine workflow
7. Agent orchestration workflow
8. Code-generation and validation workflow
9. Documentation-generation workflow
10. User end-to-end journey
11. Deployment workflow
12. Data-flow diagram
13. Sequence diagram for a complete build request
14. Recommended future-state architecture
15. Current-state versus target-state comparison

Every diagram must reflect verified implementation. Clearly label proposed components as “Recommended” or “Future State.”

## Required deliverables

Create the following files under a `/docs/zect-assessment/` directory:

1. `01-executive-summary.md`
2. `02-repository-map.md`
3. `03-current-architecture.md`
4. `04-sidebar-module-analysis.md`
5. `05-dream-engine-analysis.md`
6. `06-harness-and-hooks-analysis.md`
7. `07-orchestration-analysis.md`
8. `08-context-and-memory-analysis.md`
9. `09-graph-technology-assessment.md`
10. `10-user-workflow.md`
11. `11-documentation-system-analysis.md`
12. `12-ux-and-navigation-review.md`
13. `13-competitive-capability-matrix.md`
14. `14-security-and-enterprise-readiness.md`
15. `15-gap-analysis.md`
16. `16-prioritized-implementation-roadmap.md`
17. `17-developer-implementation-guide.md`
18. `18-administrator-guide.md`
19. `19-end-user-tool-guide.md`
20. `20-testing-and-validation-plan.md`
21. `21-current-state-diagrams.md`
22. `22-future-state-diagrams.md`

Also create:

* `zect-module-inventory.csv`
* `zect-api-inventory.csv`
* `zect-agent-tool-inventory.csv`
* `zect-gap-register.csv`
* `zect-implementation-backlog.csv`

## Implementation roadmap

Organize recommendations into:

### Critical fixes

Issues that prevent core workflows, create security risks, cause data loss, or make modules unusable.

### Phase 1: Foundation

Architecture cleanup, module wiring, authentication, permissions, project context, error handling, and observability.

### Phase 2: Integrated developer workflow

Repository management, code editing, terminal, testing, Git, documentation, and deployment integration.

### Phase 3: Agentic orchestration

Planning agents, specialized agents, execution harness, hooks, approvals, recovery, memory, and multi-agent workflows.

### Phase 4: Enterprise readiness

Security, governance, auditability, model controls, cost controls, scalability, compliance, and administrative features.

For each recommendation provide:

* Problem
* Evidence
* Business impact
* Technical impact
* Proposed solution
* Components affected
* Dependencies
* Complexity: Small, Medium, Large, or Extra Large
* Priority: P0, P1, P2, or P3
* Estimated implementation sequence
* Acceptance criteria
* Testing requirements

Do not provide unsupported time or cost estimates.

## Validation requirements

Where possible:

* Run the application locally
* Test sidebar navigation
* Verify routes
* Call APIs
* Validate database operations
* Test agent workflows
* Run unit tests
* Run integration tests
* Run end-to-end tests
* Test error paths
* Review logs
* Confirm whether generated documentation matches the code
* Identify dead code and unused modules
* Identify incomplete feature flags
* Identify environment-specific failures

Do not make destructive changes.

Do not modify production configurations, secrets, databases, or deployment environments.

## Evidence requirements

Every major finding must include evidence such as:

* File path
* Class or function name
* Route
* API endpoint
* Database table
* Configuration key
* Relevant code reference
* Test result
* Runtime observation

Use the following status labels:

* Verified
* Partially Verified
* Inferred
* Not Implemented
* Unable to Verify

Never present an inferred capability as verified.

## Final response format

After completing the assessment, provide:

1. Overall readiness score from 0–100
2. Architecture maturity score
3. AI and agent maturity score
4. User-experience score
5. Documentation maturity score
6. Enterprise-readiness score
7. Top 10 strengths
8. Top 10 critical gaps
9. Modules that are fully connected
10. Modules that are disconnected or incomplete
11. Whether Dream Engine is production-ready
12. Whether a true execution harness exists
13. Whether a usable hooks framework exists
14. How orchestration currently works
15. Whether graph technology is justified
16. The recommended sidebar structure
17. The recommended target architecture
18. The first 20 implementation tasks
19. The exact documentation files created
20. Commands used to validate the platform

Start by showing the repository map and your assessment plan. Then perform the analysis in phases. Do not begin implementing major changes until the current-state assessment is complete.

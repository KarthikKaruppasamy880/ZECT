You are a Principal AI Product Architect, Agentic Systems Architect, Voice AI Architect, Knowledge-Graph Specialist, and Enterprise UX Reviewer.

Perform a complete architecture and product assessment using these two repositories:

ZECT:
https://github.com/KarthikKaruppasamy880/ZECT

Brain Map:
https://github.com/zubair-trabzada/brain-map

## Important restrictions

* Do not write or modify production code.
* Do not begin implementation.
* Do not create speculative features and describe them as already implemented.
* Do not rely only on README claims.
* Inspect the actual latest code on the default and active development branches.
* Review recent commits, open pull requests, configuration, routes, services, components, prompts, models, APIs, and runtime connections.
* Clearly distinguish verified functionality from proposed functionality.
* Do not expose secrets, access tokens, or private configuration values.

Use these status labels throughout the assessment:

* Verified
* Partially Verified
* Inferred
* Not Implemented
* Broken
* Disconnected
* Unable to Verify
* Recommended Future State

## Background and problem

ZECT is intended to become an all-in-one AI engineering platform and intelligent personal engineering assistant.

However, the current assistant experience is not responding as expected:

* I tried calling the assistant/persona, but there was no response.
* Voice interaction did not work.
* There was no real-time response.
* It is unclear whether microphone input, speech-to-text, assistant reasoning, text-to-speech, and live audio playback are connected.
* It is unclear whether the configured assistant persona is actually used during runtime.
* It is unclear whether sessions, memory, interruptions, and continuous conversation work.
* It is unclear whether repository analysis uses a real knowledge graph or only basic file and dependency analysis.

I need a complete architecture assessment—not code—to understand:

1. How ZECT currently works.
2. Why the assistant and voice experience are not responding.
3. Whether the personal-assistant persona is real, partially implemented, or only represented in the UI.
4. What Brain Map actually provides.
5. Whether Brain Map should be adopted in ZECT.
6. Whether Brain Map can support repository graphing.
7. Whether another graph solution is needed.
8. How ZECT should evolve into a responsive real-time engineering assistant.
9. The benefits, drawbacks, risks, complexity, and implementation sequence.

# Part 1: Synchronize and inspect the latest repositories

Before analyzing architecture:

1. Confirm the branch being analyzed in each repository.
2. Identify the latest commit hash and commit date.
3. Review recent commits and open pull requests.
4. Determine whether significant work exists outside the default branch.
5. Identify unmerged architectural changes where visible.
6. Record the exact repository state used for the assessment.

Produce:

| Repository | Branch | Commit | Commit Date | Open PRs Reviewed | Assessment Notes |

Do not modify either repository.

# Part 2: Build the actual ZECT repository map

Inspect the complete ZECT repository.

Identify:

* Frontend application
* Backend application
* Electron or desktop integration
* API routes
* Authentication
* GitHub integration
* Repository-analysis engine
* Ask mode
* Plan mode
* Blueprint generation
* Documentation generation
* Orchestration pages or services
* AI model integrations
* Prompt-management logic
* Context-building logic
* Agent definitions
* Persona configuration
* Memory
* Session management
* Voice components
* Microphone access
* Speech-to-text
* Text-to-speech
* Streaming transport
* WebSocket or Server-Sent Events
* Real-time events
* Tool registry
* MCP integration
* Hooks
* Skills
* Knowledge or graph functionality
* Database and persistence
* Logging and observability
* Error handling
* Deployment configuration
* Tests

Create this inventory:

| Component | Purpose | File Path | Entry Point | Dependencies | Connected To | Runtime Status | Evidence |

Do not assume a component works because a file or menu item exists.

# Part 3: Trace the current assistant runtime

Trace the complete runtime path when a user sends a message to the ZECT assistant.

Start from:

* User enters text
* User clicks Send
* User activates the microphone
* User calls or invokes the configured assistant persona

Trace every step through:

1. Frontend event
2. State management
3. API client
4. Backend endpoint
5. Request validation
6. Session lookup
7. Persona selection
8. Prompt construction
9. Repository context
10. Conversation context
11. Model selection
12. LLM request
13. Streaming or non-streaming response
14. Tool invocation
15. Response processing
16. Frontend rendering
17. Voice synthesis
18. Audio playback
19. Memory persistence
20. Logging and error handling

Create:

| Step | Component | File/Function | Input | Output | Connected? | Failure Risk | Evidence |

Generate a Mermaid sequence diagram representing the verified current runtime.

# Part 4: Diagnose why there is no response

Investigate the no-response issue systematically.

Check:

## Frontend

* Is the button event connected?
* Is microphone permission requested correctly?
* Is recording actually started?
* Is recorded audio captured in a supported format?
* Is the message request sent?
* Is there a loading state?
* Are API errors hidden?
* Are browser-console errors present?
* Does the frontend expect streaming while the backend returns a normal response?
* Does the frontend wait indefinitely?
* Is audio playback blocked by browser policies?
* Is the wrong API base URL being used?
* Does Electron behave differently from the web application?

## Backend

* Does the expected route exist?
* Is the router registered in the application?
* Is the request schema correct?
* Is the model provider configured?
* Does a missing API key cause a silent failure?
* Are requests timing out?
* Is streaming implemented correctly?
* Are errors swallowed?
* Is Cross-Origin Resource Sharing configured correctly?
* Does the backend return the format expected by the frontend?
* Is the persona passed into the model request?
* Is the repository context too large?
* Are external providers reachable?
* Are rate limits handled?
* Are sessions and memory initialized?

## Voice pipeline

Verify the existence and connection of:

* Microphone permission
* Audio capture
* Voice activity detection
* Audio encoding
* Audio upload or stream
* Speech-to-text provider
* Partial transcript streaming
* Final transcript
* Assistant request
* LLM response streaming
* Text chunking
* Text-to-speech
* Audio streaming
* Playback
* Barge-in or interruption
* Cancellation
* Error recovery

Classify every component as:

* Working
* Partially Working
* Present but Disconnected
* Missing
* Unable to Verify

Create a root-cause tree for the no-response problem.

Do not fix anything. Provide diagnostic evidence and recommended validation steps.

# Part 5: Determine whether real-time voice exists

Do not describe ordinary audio upload as real-time voice.

Determine whether ZECT currently supports:

* Full-duplex conversation
* Streaming speech-to-text
* Streaming LLM output
* Streaming text-to-speech
* Low-latency audio delivery
* Voice activity detection
* Barge-in
* Interrupting the assistant
* Turn detection
* Echo cancellation
* Reconnection
* Session continuity
* WebSocket transport
* WebRTC transport
* Server-Sent Events
* Audio buffering
* Back-pressure handling
* Latency monitoring

Measure or estimate only from evidence.

Explain the difference between:

1. Push-to-talk audio upload
2. Recorded-message voice interaction
3. Near-real-time streaming
4. True full-duplex voice conversation

State which level ZECT currently supports.

# Part 6: Analyze the personal-assistant persona

Identify what the assistant persona currently is.

Check whether it is:

* A display name only
* A static system prompt
* A configurable persona
* A true agent
* A tool-using agent
* A persistent personal assistant
* A repository-aware engineering assistant
* A multi-agent coordinator

Inspect:

* Persona prompts
* Persona selection
* User preferences
* Long-term memory
* Project memory
* Conversation history
* Skills
* Tools
* Planning
* Execution
* Proactive suggestions
* Notifications
* User approval
* Safety policies
* Voice identity
* Speech configuration
* Model routing

Answer clearly:

* Does the persona influence runtime behavior?
* Is the persona passed to the LLM?
* Does the persona have memory?
* Can it use tools?
* Can it understand repositories?
* Can it perform multi-step work?
* Can it speak?
* Can it listen?
* Can it operate continuously?
* Can it resume prior work?

# Part 7: Analyze Brain Map completely

Inspect the Brain Map repository beyond the README.

Determine:

* What input formats it supports
* Whether it supports only Markdown
* How nodes are identified
* How edges are produced
* Whether relationships are explicit or inferred
* Whether backlinks are used
* Whether parsing is static or semantic
* Whether embeddings are used
* Whether an LLM is used
* Whether a graph database is used
* Whether the graph is persisted
* Whether it has an API
* Whether it has a reusable library
* Whether it supports incremental updates
* Whether it can process large repositories
* Whether it understands programming-language symbols
* Whether it parses imports
* Whether it parses function calls
* Whether it understands classes and inheritance
* Whether it maps routes to services
* Whether it maps services to databases
* Whether it supports impact analysis
* Whether it supports search or retrieval
* Whether agents can query it
* Whether it is mainly a visualization layer

Create:

| Brain Map Capability | Verified Behavior | Evidence | Limitation | ZECT Relevance |

# Part 8: Brain Map versus repository Graphify requirements

ZECT needs to graphify repositories so that the assistant can understand:

* Files
* Packages
* Modules
* Classes
* Functions
* Methods
* Imports
* Function calls
* API routes
* UI components
* Backend services
* Database models
* Database relationships
* Tests
* CI/CD workflows
* Documentation
* Requirements
* Pull requests
* Commits
* Code ownership
* Cross-repository dependencies

Evaluate Brain Map against each requirement.

Use this matrix:

| Requirement | Brain Map Native Support | Adaptation Required | Recommended Supporting Technology | Risk |

Determine whether Brain Map can serve as:

* The entire repository-intelligence engine
* The graph visualization layer only
* A documentation-graph subsystem
* A prototype
* A user-interface inspiration
* A reusable parser
* An unsuitable dependency

Do not force adoption if it is not technically appropriate.

# Part 9: Compare architecture options

Compare these options:

## Option A: Adopt Brain Map directly

Use Brain Map mostly as it exists.

## Option B: Extend Brain Map

Add source-code parsing, symbol extraction, dependency detection, storage, APIs, and agent retrieval.

## Option C: Use Brain Map only for visualization

Build the underlying repository graph separately and use Brain Map concepts or UI to visualize it.

## Option D: Build a ZECT-native graph engine

Create a language-aware indexing and graph abstraction designed for ZECT.

## Option E: Integrate a mature code-graph technology

Use tools such as language parsers, Language Server Protocol data, Tree-sitter, static-analysis tools, a graph database, or another proven repository-intelligence platform.

## Option F: Hybrid design

Use:

* Static analysis for code structure
* Relational storage for canonical entities
* Vector search for semantic retrieval
* Graph relationships for dependencies
* Brain Map-style visualization for users
* Agent tools for graph queries

For every option evaluate:

* Functional fit
* Technical complexity
* Scalability
* Accuracy
* Incremental indexing
* Multi-language support
* Multi-repository support
* Agent usability
* User experience
* Security
* Maintenance
* Vendor dependency
* Migration effort
* Operational overhead
* Benefits
* Drawbacks

Do not provide unsupported calendar-time or budget estimates.

# Part 10: Define the current ZECT architecture

Create an evidence-based current-state architecture showing:

* User interface
* Desktop or Electron layer
* Frontend routes
* API client
* FastAPI backend
* Authentication
* GitHub integration
* Repository analysis
* LLM Ask mode
* Plan mode
* Blueprint generation
* Documentation generation
* Database
* Current context flow
* Current persona flow
* Current voice flow
* Current orchestration
* Logging
* Deployment

Use Mermaid.

Use solid arrows for verified connections.

Use dashed arrows for partially connected or inferred connections.

Use red-labeled nodes for broken or disconnected components.

Do not mix proposed components into the current-state diagram.

# Part 11: Design the enhanced ZECT architecture

Create a separate target architecture titled:

“ZECT Real-Time Engineering Assistant — Enhanced Architecture”

Include the following only when justified:

## Experience layer

* Web interface
* Electron desktop interface
* IDE integration
* Voice interface
* Assistant avatar or persona
* Repository graph explorer
* Chat
* Command palette
* Approval center
* Notifications

## Real-time interaction layer

* WebSocket or WebRTC gateway
* Session manager
* Audio-stream manager
* Voice activity detection
* Streaming speech-to-text
* Turn manager
* Streaming LLM response
* Streaming text-to-speech
* Audio playback
* Barge-in
* Cancellation
* Reconnection
* Latency metrics

## Assistant and orchestration layer

* Persona manager
* Request router
* Planner
* Custom ForceLoop or LangGraph abstraction
* Agent registry
* Tool registry
* Workflow state
* Checkpoints
* Retry and recovery
* Human approval
* Policy engine
* Cost and token controls

## Specialized agents

Assess whether ZECT needs:

* Repository Analysis Agent
* Architecture Agent
* Coding Agent
* Testing Agent
* Documentation Agent
* Pull Request Review Agent
* DevOps Agent
* Security Agent
* Personal Productivity Agent
* Voice Conversation Agent

## Repository-intelligence layer

* Repository ingestion
* Language detection
* Tree-sitter or abstract syntax tree parsing
* Language Server Protocol integration
* Symbol extraction
* Dependency extraction
* API relationship mapping
* Database relationship mapping
* Cross-repository links
* Incremental indexing
* Graph storage
* Vector retrieval
* Keyword retrieval
* Hybrid retrieval
* Graph query service
* Repository-context builder
* Brain Map-inspired graph visualization

## Memory and knowledge layer

* Conversation memory
* Project memory
* User preferences
* Repository memory
* Task memory
* Architectural decisions
* Documentation
* Requirements
* Permission-aware retrieval
* Context compression
* Context freshness

## Integration layer

* GitHub
* GitLab, if justified
* Jira
* Slack or Teams
* CI/CD
* MCP
* Terminal
* Browser
* Testing tools
* Documentation tools
* Deployment tools

## Platform layer

* Relational database
* Vector database
* Graph database, if justified
* Cache
* Object storage
* Event bus
* Task queue
* Secrets management
* Audit logging
* Tracing
* Metrics
* Alerting
* Model routing
* Provider fallback
* Rate limiting
* Tenant isolation

Create:

1. High-level target architecture
2. Real-time voice architecture
3. Repository graphing architecture
4. Assistant orchestration architecture
5. Context and memory architecture
6. End-to-end sequence diagram
7. Failure and recovery workflow

# Part 12: Real-time assistant workflow

Design the target interaction from beginning to end.

Example user journey:

1. User opens ZECT.
2. ZECT loads the user profile and current project.
3. User speaks to the assistant.
4. Microphone audio begins streaming.
5. Voice activity detection identifies speech.
6. Speech-to-text produces partial transcripts.
7. The assistant updates its understanding in real time.
8. The request router determines the task type.
9. The planner determines required repository context.
10. Repository-intelligence services retrieve symbols, dependencies, documents, and recent Git changes.
11. The orchestrator invokes appropriate agents and tools.
12. The assistant streams an initial verbal acknowledgment.
13. Tools execute with appropriate approval.
14. The assistant streams progress updates.
15. Results are validated.
16. The assistant speaks and displays the final answer.
17. Memory and audit history are updated.
18. The user can interrupt, correct, or continue the conversation.

For every step provide:

| Step | Component | Input | Output | Latency Concern | Failure Path | Recovery |

# Part 13: Pros, cons, and risks

Provide detailed advantages and disadvantages for:

* Adding real-time voice
* Creating a persistent personal assistant
* Adopting Brain Map
* Extending Brain Map
* Building a custom graph engine
* Adding a graph database
* Adding vector retrieval
* Using hybrid retrieval
* Adding multi-agent orchestration
* Using LangGraph
* Continuing a custom ForceLoop
* Supporting Electron and web simultaneously

Include risks such as:

* Complexity
* Latency
* Cost
* Privacy
* Security
* Voice-data handling
* Prompt injection
* Tool misuse
* Inaccurate graphs
* Stale indexes
* Cross-repository leakage
* Graph/vector synchronization
* Infinite agent loops
* Hidden provider failures
* Browser audio restrictions
* Poor user trust
* Operational burden

# Part 14: Provide a clear recommendation

At the end, answer directly:

1. Why does the assistant currently provide no response?
2. Is the voice feature implemented or only represented in the UI?
3. Is real-time communication implemented?
4. Is the assistant persona connected to runtime?
5. Is Brain Map appropriate for ZECT?
6. Should Brain Map be adopted directly?
7. Should it be used only as a visualization layer?
8. Can it graphify source-code repositories accurately?
9. What additional parsing and indexing capabilities are required?
10. Does ZECT need a graph database?
11. Does ZECT need a vector database?
12. Should ZECT use a hybrid relational, vector, and graph architecture?
13. What should be built first?
14. What should not be built yet?
15. What is the safest migration path?

Give one primary recommendation and one fallback option.

# Part 15: Implementation roadmap without coding

Create a phased roadmap.

## Phase 0: Diagnose and stabilize

* Find no-response failures
* Surface frontend and backend errors
* Validate model-provider configuration
* Validate persona configuration
* Validate audio permissions
* Validate API connectivity
* Add observability recommendations

## Phase 1: Reliable text assistant

* Stable request/response flow
* Streaming text
* Session management
* Persona management
* Repository context
* Error handling
* Model fallback

## Phase 2: Repository intelligence

* Source-code parsing
* Symbol and dependency extraction
* Incremental indexing
* Hybrid retrieval
* Graph-query service
* Repository graph visualization

## Phase 3: Voice assistant

* Streaming speech-to-text
* Turn detection
* Streaming response
* Streaming text-to-speech
* Interruption
* Reconnection
* Latency monitoring

## Phase 4: Agentic engineering assistant

* Planning
* Tool use
* Approvals
* Checkpointing
* Recovery
* Specialized agents
* Project memory

## Phase 5: Enterprise readiness

* Security
* Tenant isolation
* Audit
* Governance
* Cost controls
* Reliability
* Scalability
* Administrative controls

For each task include:

| Task ID | Task | Current Gap | Proposed Outcome | Dependency | Priority | Complexity | Acceptance Criteria |

Use priorities:

* P0
* P1
* P2
* P3

Use complexity:

* Small
* Medium
* Large
* Extra Large

Do not provide unsupported time or budget estimates.

# Required output documents

Create an analysis-only directory:

`docs/architecture/brain-map-zect-assessment/`

Create:

1. `01-assessment-scope.md`
2. `02-repository-version-report.md`
3. `03-zect-repository-map.md`
4. `04-current-zect-architecture.md`
5. `05-assistant-runtime-trace.md`
6. `06-no-response-root-cause-analysis.md`
7. `07-current-voice-capability.md`
8. `08-persona-and-memory-analysis.md`
9. `09-brain-map-technical-assessment.md`
10. `10-brain-map-fit-for-zect.md`
11. `11-repository-graphing-options.md`
12. `12-current-vs-target-architecture.md`
13. `13-enhanced-zect-architecture.md`
14. `14-real-time-voice-architecture.md`
15. `15-repository-intelligence-architecture.md`
16. `16-orchestration-and-agent-architecture.md`
17. `17-pros-cons-and-risks.md`
18. `18-recommended-adoption-strategy.md`
19. `19-phased-roadmap.md`
20. `20-validation-plan.md`
21. `21-executive-summary.md`

Also create:

* `zect-component-inventory.csv`
* `zect-assistant-runtime.csv`
* `zect-voice-gap-register.csv`
* `brain-map-capability-matrix.csv`
* `brain-map-zect-fit-matrix.csv`
* `repository-graph-options.csv`
* `architecture-enhancement-backlog.csv`

# Validation plan

Where possible, validate without changing code:

* Install dependencies in an isolated environment
* Build frontend
* Type-check frontend
* Run backend tests
* Start backend locally
* Start frontend locally
* Check browser console
* Check network requests
* Check backend logs
* Test the text assistant
* Test microphone permission
* Inspect audio-capture events
* Test the expected voice endpoint
* Test model-provider configuration
* Trace one full request
* Verify whether streaming occurs
* Verify whether the persona prompt is transmitted
* Test Brain Map with a small Markdown sample
* Test Brain Map with source files and record its behavior
* Check scalability assumptions against repository size

Do not commit generated code or make architectural changes.

# Final response format

Return:

1. Repository versions analyzed
2. How ZECT currently works
3. Why the assistant is not responding
4. Current text-assistant readiness score from 0–100
5. Current voice readiness score from 0–100
6. Current real-time readiness score from 0–100
7. Current repository-intelligence score from 0–100
8. Current persona and memory score from 0–100
9. What Brain Map actually does
10. Whether Brain Map fits ZECT
11. Brain Map’s main benefits
12. Brain Map’s main limitations
13. Recommended architecture
14. Recommended technology combination
15. Top 10 critical gaps
16. First 20 recommended tasks
17. Components that must not be added yet
18. Validation commands used
19. Documents generated
20. Anything that could not be verified

Begin with repository synchronization, repository mapping, and an assessment plan.

Complete the current-state and root-cause analysis before designing the enhanced architecture.

Do not code or implement changes.

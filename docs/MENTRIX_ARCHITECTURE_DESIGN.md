# Mentrix Architecture Design: Smart Orchestration Layer

**Status:** Design Document  
**Date:** July 23, 2026  
**Version:** 1.0  
**Scope:** Mentrix evolution to intelligent orchestration layer

---

## Executive Summary

Mentrix is ZECT's **dual-mode AI agent**: a voice-enabled **Companion** (19 tools, permission-gated) running alongside a **Delivery Orchestrator** (multi-phase code generation via ForgeLoop).

**Vision:** Transform Mentrix into a **unified intelligent orchestration layer** that:
- Understands the repository (deep code graph)
- Understands business context (stored in project model)
- Understands user intent (via conversation history + working memory)
- Coordinates across all ZECT modules (Deliver, Quality, Enterprise, Labs)
- Manages long-term context and learning (memory system + Dream Engine)

---

## Current Mentrix Architecture

### Dual-Mode Design

```
┌─────────────────────────────────────────────────────────────┐
│                         MENTRIX v3.0                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MODE 1: COMPANION                 MODE 2: DELIVERY       │
│  ─────────────────────────────────  ──────────────────     │
│  Voice-enabled personal agent      Multi-phase orchestrator │
│  19 integrated tools               ForgeLoop FSM            │
│  Real-time chat interface         Ask→Plan→Build→Review   │
│  Permission-gated execution        Quality gates enforced   │
│  Per-turn stateless               Approval workflows       │
│                                                             │
│  Backend: companion.py (1220 lines) | orchestrator.py (900+) │
│  Frontend: MentrixCompanion.tsx     | Mentrix.tsx         │
│  WebSocket: realtime.ts            | polling via API       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Current Integration Points

#### 1. Lattice (Code Understanding)

**Current:**
```python
# companion.py:516-578 (lattice_query tool)
- Query code graph: lattice.query_graph(project_key, q)
- Returns: symbol matches (name, kind, path)
- Optional: backlinks for doc nodes
- Output: table artifact + spoken summary
```

**Data Flowing:**
- CodeSymbol table (50K-100K indexed symbols)
- EmbeddingChunk (1K-10K RAG vectors)
- LatticeStructuralBlueprint (1 blueprint per repo)

**Limitations:**
- Only symbol indexing, no type analysis
- No call-graph depth analysis
- No semantic code understanding
- Lattice accessed via tool call (not injected into context)

#### 2. ForgeLoop Orchestrator (Multi-Phase Execution)

**Current:**
```python
# orchestrator.py:49-74 (MODE_PIPELINE)
Delivery workflow:
  Scout → Planner → Builder → (Lint) → Sandbox → 
  Reviewer → Fixer (recovery) → Integrator → Done
```

**Data Flowing:**
- Project scope (from Workspace module)
- Lattice context (code graph)
- Agent steps (6-20 per run)
- Quality gates (lint_ok, sandbox_ready, review_ok)
- Events journal (MentrixRun.events_json)

**Limitations:**
- Mentrix Companion is separate from Delivery orchestrator
- No bidirectional communication
- No Companion awareness of active Delivery runs
- No Companion input into Delivery decisions

#### 3. Permission Broker (Tool Access Control)

**Current:**
```python
# permission_broker.py:71-136
check_tool_permission(db, tool_name, user_id, project_id)
  → Returns: granted | denied | pending_approval

ALWAYS_CONFIRM_TOOLS = {
    slack_send, email_send, start_delivery, 
    desktop_screenshot, computer_*, media_*, ...
}
```

**Integration:**
- Tool execution gated by permission rules
- 40+ predefined rules (allow, require_approval, never)
- Approval shown in Mentrix overlay modal
- PermissionAudit logged for all tool calls

**Limitations:**
- Permission checking based on tool name only
- No phase-aware gating (e.g., different rules during Build vs. Analyze)
- No context-aware permission decisions

---

## Gaps in Current Implementation

### 1. No Persistent Conversation Memory

**Problem:** Each turn is isolated
- Single HTTP request = one turn
- Previous turns not accessible
- Realtime voice: no session memory across calls
- User asks same question → no recognition

**Evidence:**
```python
# companion.py:83-124 (build_agent_context)
# Context rebuilt per request from:
#   - skill_id (max 1200 chars)
#   - project_id lessons (max 220 chars each)
# Total: 4KB max
# Result: no conversation state
```

**Impact:**
- Mentrix can't track conversation flow
- No ability to reference prior decisions
- User has to re-explain context repeatedly

### 2. No Semantic Code Understanding

**Problem:** Only symbol indexing, no deep analysis
- Can't trace function calls across files
- Can't infer types or return values
- Can't identify unused code or dead branches
- Can't understand architectural patterns

**Evidence:**
```python
# lattice.py: indexed symbols have:
#   - name, kind, path, line_start, line_end
# Missing:
#   - return_type (from AST)
#   - parameter_types (from AST)
#   - call_chain (who calls me)
#   - type_flow (what's passed in/out)
```

**Impact:**
- Mentrix queries return symbol names, not deep understanding
- Code generation uses shallow context
- Can't reason about architecture impact

### 3. No Business Context Store

**Problem:** Context injected at request time, not durable
- Business logic stored in Skills table (4KB limit)
- Lessons staged but not actively used
- Project model not enriched with domain knowledge
- Context lost between sessions

**Evidence:**
```python
# Current approach:
skills = db.query(Skill).filter(skill_id=req.skill_id).first()
context = skills.template[:4000]  # String truncation
# Problem: Can't store rich project context
```

**Implementation Path:**
```python
# New: ProjectContext table
class ProjectContext(Base):
    project_id: int
    tech_stack: dict  # {python: "3.12", react: "18.3", etc}
    domain_knowledge: str  # Business domain, DDD model
    architectural_patterns: list  # MVC, CQRS, microservices, etc.
    integration_points: list  # External APIs, databases
    constraints: list  # "no force_push_main", "test_required"
    business_rules: str  # Domain-specific rules
    updated_at: DateTime
```

### 4. No Persona Injection Framework

**Problem:** Fixed system prompt, not customizable per user/project

**Current:**
```python
# realtime.py:36-56
def mentrix_instructions() -> str:
    return """
    Brand: Mentrix, Lattice, ForgeLoop, ZECT only
    Navigation: 20+ path mappings
    Persona: "ZECT company personal operator"
    Constraints: [hardcoded]
    """
```

**Missing:**
- User preferences (tone, verbosity, style)
- Project-specific persona (backend focused vs. frontend)
- Role-based persona (architect vs. junior dev)
- Constraint injection (company policies, security rules)

**Implementation Path:**
```python
# New: MentrixPersona table
class MentrixPersona(Base):
    project_id: int? nullable
    user_id: int? nullable
    name: str = "Mentrix"
    tone: str = "professional"  # or casual, technical
    constraints: list  # ["no force_push", "always test"]
    background: str  # Project history, team info
    preferences: dict  # {prefer_rest_over_graphql: true}
    is_active: bool = True

# Usage:
persona = fetch_persona(project_id, user_id)
instructions = persona.build_system_prompt()
```

### 5. No Phase-Aware Tool Gating

**Problem:** All tools available all the time
- Tool availability: permission-based
- Missing: phase-based availability
- Example: During Build phase, prefer build tools; during Analyze, prefer research

**Current:**
```python
# permission_broker.py: only checks action_pattern
# Example: "slack_send" always requires approval
# Missing: "slack_send during Build phase" has different rules
```

**Implementation Path:**
```python
# Enhanced PermissionRule:
class PermissionRule(Base):
    action_pattern: str
    phase: str? = None  # ask|plan|build|review|deploy|None(always)
    permission_level: str  # allow|require_approval|never
    
# Usage:
phase = get_active_phase(project_id)
rule = check_tool_permission(tool, phase=phase)
```

### 6. Limited Error Recovery Context

**Problem:** Fixer generates fixes but doesn't understand root cause

**Current:**
```python
# orchestrator.py:345-395 (Error Classifier)
classify_error(prior_error, gate, findings)
  → Returns: next_step (re_review|re_build|await_human)
# Missing: code-specific suggestions
```

**Impact:**
- Generic fix attempts (re-lint, re-sandbox)
- No learning from failures
- User doesn't understand what was wrong

**Implementation Path:**
```python
# Enhanced error handling:
def analyze_error_context(error, code, findings):
    # 1. Map error to code location (Lattice)
    # 2. Understand error type (syntax, logic, test)
    # 3. Extract similar past lessons (Dream)
    # 4. Generate targeted fix
    # 5. Store as episodic memory
```

---

## Mentrix as Unified Orchestration Layer

### Architectural Vision

```
┌──────────────────────────────────────────────────────────────┐
│                     MENTRIX ORCHESTRATOR                     │
│              (Unified Intelligent Coordination)              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. CONTEXT ENGINE                                  │    │
│  │  • Repository understanding (Lattice + AST)        │    │
│  │  • Business context store (ProjectContext)         │    │
│  │  • Conversation memory (MentrixCompanionSession)   │    │
│  │  • Working memory (current task state)             │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 2. UNIFIED PROMPT ENGINE                           │    │
│  │  • Phase-aware persona injection                    │    │
│  │  • Context prioritization (what's most relevant)    │    │
│  │  • Token budget awareness                           │    │
│  │  • Role-specific instructions                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 3. MULTI-MODE AGENT COORDINATOR                    │    │
│  │  • Companion mode: voice chat + tools              │    │
│  │  • Delivery mode: orchestrated code generation     │    │
│  │  • Bridge mode: hybrid (voice + structured phases) │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 4. MODULE COORDINATION                             │    │
│  │  • Understand: deep code analysis (Tree-Sitter)   │    │
│  │  • Deliver: orchestrated workflows (ForgeLoop)     │    │
│  │  • Quality: review gates + auto-fix                │    │
│  │  • Enterprise: permission + approval workflow      │    │
│  │  • Labs: memory, learning, event logging           │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 5. LEARNING & MEMORY SYSTEM                        │    │
│  │  • Conversation clustering (episodic)              │    │
│  │  • Pattern extraction (Dream Engine)               │    │
│  │  • Lesson storage & application (semantic)         │    │
│  │  • Personal preferences (user memory)              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation Strategy

### Phase A: Foundation (Weeks 1-4)

**Goal:** Build persistent context and unified prompt engine

#### 1. Conversation Memory Module

```python
# New table: MentrixCompanionSession
class MentrixCompanionSession(Base):
    __tablename__ = "mentrix_companion_sessions"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="active")
    goal = Column(Text, default="")
    working_memory = Column(JSON, default=dict)
    total_turns = Column(Integer, default=0)
    created_at = Column(DateTime)
    last_turn_at = Column(DateTime)

# Extract after each turn:
def extract_turn_summary(turn: dict) -> dict:
    return {
        "decisions": ["what was decided"],
        "blockers": ["what needs approval"],
        "artifacts": ["code/docs created"],
        "questions": ["what was unclear"],
        "next_step": "what's next"
    }

# Inject at turn start:
def build_session_context(project_id: int) -> str:
    session = db.query(MentrixCompanionSession)\
        .filter(status="active")\
        .first()
    if session:
        memory = session.working_memory
        return f"""
        Active session goal: {memory.get('goal')}
        Prior decisions: {', '.join(memory.get('decisions', []))}
        Open blockers: {', '.join(memory.get('blockers', []))}
        """
    return ""
```

**Effort:** 2 weeks

#### 2. Project Context Store

```python
# New table: ProjectContext
class ProjectContext(Base):
    __tablename__ = "project_contexts"
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    
    # Technical context
    tech_stack = Column(JSON, default=dict)  # {python: "3.12", react: "18.3"}
    architectural_patterns = Column(JSON, default=list)  # ["MVC", "REST"]
    integration_points = Column(JSON, default=list)  # ["PostgreSQL", "OpenAI"]
    
    # Business context
    domain_knowledge = Column(Text, default="")  # Business domain
    business_rules = Column(JSON, default=list)  # Domain rules
    constraints = Column(JSON, default=list)  # Company policies
    
    # Mentrix preferences
    persona_name = Column(String, default="Mentrix")
    tone = Column(String, default="professional")
    
    updated_at = Column(DateTime)

# Usage in companion:
context = db.query(ProjectContext).get(project_id)
tech_context = f"Tech: {context.tech_stack}"
domain_context = f"Domain: {context.domain_knowledge}"
```

**Effort:** 1 week

#### 3. Unified Prompt Engine

```python
# New service: mentrix_prompt.py
class MentrixSystemPrompt:
    def __init__(self, context: dict):
        self.project = context.get("project")
        self.phase = context.get("phase")
        self.session = context.get("session")
        self.persona = context.get("persona")
        self.available_tools = context.get("available_tools", [])
    
    def build_instructions(self) -> str:
        parts = []
        
        # 1. Brand & persona
        parts.append(f"You are {self.persona.name}, {self.persona.tone}.")
        
        # 2. Project context
        if self.project:
            parts.append(f"Project: {self.project.name}")
            parts.append(f"Tech stack: {self.project.context.tech_stack}")
            parts.append(f"Domain: {self.project.context.domain_knowledge}")
        
        # 3. Phase-specific instructions
        if self.phase == "build":
            parts.append("Phase: Building code. Prefer generation tools.")
        elif self.phase == "analyze":
            parts.append("Phase: Analyzing code. Prefer research tools.")
        
        # 4. Session context
        if self.session:
            parts.append(f"Goal: {self.session.goal}")
            parts.append(f"Prior decisions: {self.session.working_memory.get('decisions')}")
        
        # 5. Available tools
        parts.append(f"Available tools: {', '.join(self.available_tools)}")
        
        # 6. Constraints
        if self.persona.constraints:
            parts.append(f"Constraints: {', '.join(self.persona.constraints)}")
        
        return "\n\n".join(parts)

# Usage:
prompt = MentrixSystemPrompt({
    "project": project,
    "phase": "build",
    "session": session,
    "persona": persona,
    "available_tools": ["lattice_query", "start_delivery"]
})
system_instructions = prompt.build_instructions()
```

**Effort:** 1 week

### Phase B: Code Understanding (Weeks 5-12)

**Goal:** Deep code analysis via Tree-Sitter integration

#### 1. Tree-Sitter Integration

```python
# New service: lattice_ast.py
import tree_sitter
from tree_sitter import Language, Parser

# Initialize parsers for multiple languages
PARSERS = {
    "python": Parser("python"),
    "typescript": Parser("typescript"),
    "javascript": Parser("javascript"),
}

def extract_function_signature(file_path: str) -> list[dict]:
    """Extract function signatures with types."""
    with open(file_path) as f:
        code = f.read()
    
    parser = PARSERS.get(detect_language(file_path))
    tree = parser.parse(code.encode())
    
    functions = []
    for node in find_nodes(tree.root_node, "function_declaration"):
        sig = {
            "name": get_node_text(node, "name"),
            "line": node.start_point[0],
            "parameters": extract_parameters(node),
            "return_type": extract_return_type(node),
            "docstring": extract_docstring(node),
        }
        functions.append(sig)
    
    return functions

def extract_call_graph(project_path: str) -> dict:
    """Build complete call graph."""
    graph = {}  # node -> list[callers]
    
    for file_path in find_code_files(project_path):
        tree = parse_file(file_path)
        
        for call_node in find_nodes(tree.root_node, "call_expression"):
            callee = get_callee_name(call_node)
            caller = get_enclosing_function(call_node)
            
            if callee not in graph:
                graph[callee] = []
            graph[callee].append({
                "file": file_path,
                "caller": caller,
                "line": call_node.start_point[0]
            })
    
    return graph
```

**Effort:** 4 weeks

#### 2. Semantic Code Understanding

```python
# New service: lattice_semantics.py

def analyze_code_semantics(project_path: str) -> dict:
    """Extract semantic properties."""
    
    # 1. Type inference
    types = extract_types_pyright(project_path)  # Python: use Pyright
    
    # 2. Call-graph analysis
    graph = extract_call_graph(project_path)
    
    # 3. Identify patterns
    patterns = {
        "unused_functions": find_unused(graph),
        "dead_code": find_dead_branches(graph),
        "cycles": find_circular_dependencies(graph),
        "hot_paths": find_frequently_called(graph),
    }
    
    return {
        "types": types,
        "call_graph": graph,
        "patterns": patterns,
    }

def find_circular_dependencies(call_graph: dict) -> list[list[str]]:
    """Find cycles in call graph."""
    cycles = []
    for node in call_graph:
        visited = set()
        if has_cycle(node, call_graph, visited):
            cycles.append(extract_cycle_path(node, call_graph))
    return cycles
```

**Effort:** 3 weeks

### Phase C: Orchestration (Weeks 13-20)

**Goal:** Unified Delivery ↔ Companion coordination

#### 1. Active Run Awareness

```python
# Companion: inject active Delivery run state
def build_delivery_context(project_id: int) -> str:
    active_run = db.query(MentrixRun)\
        .filter(project_id=project_id, status="running")\
        .first()
    
    if active_run:
        events = active_run.events_json[-5:]  # Last 5 events
        return f"""
        Active Delivery: {active_run.goal}
        Current phase: {active_run.current_agent}
        Recent events:
        {json.dumps(events, indent=2)}
        """
    return ""

# Delivery: accept input from Companion
def companion_input_hook(run_id: str, user_message: str):
    """User sends message via Companion during Delivery."""
    run = db.query(MentrixRun).get(run_id)
    
    # Store user input
    run.events_json.append({
        "ts": now(),
        "event": "companion_input",
        "message": user_message,
        "agent": run.current_agent,
    })
    
    # If in approval gate: process approval
    if "awaiting_approval" in run.status:
        run.approved_by = current_user.id
        run.status = "approved"
        return {"status": "approved", "next": "create_pr"}
```

**Effort:** 2 weeks

#### 2. Phase-Aware Tool Gating

```python
# Enhanced permission checking
def check_tool_permission_with_phase(
    db: Session,
    tool_name: str,
    user_id: int,
    project_id: int,
    phase: str? = None
) -> Tuple[str, PermissionRule]:
    """Check permission considering active phase."""
    
    # 1. Look for phase-specific rule
    if phase:
        rule = db.query(PermissionRule).filter(
            PermissionRule.action_pattern == tool_name,
            PermissionRule.phase == phase,
            PermissionRule.project_id == project_id,
        ).first()
        if rule:
            return rule.permission_level, rule
    
    # 2. Fall back to global rule
    rule = db.query(PermissionRule).filter(
        PermissionRule.action_pattern == tool_name,
        PermissionRule.phase.is_(None),
        PermissionRule.project_id == project_id,
    ).first()
    
    return rule.permission_level if rule else "allow", rule

# Usage:
phase = get_active_phase(project_id)
permission, rule = check_tool_permission_with_phase(
    db, "slack_send", user_id, project_id, phase
)
```

**Effort:** 2 weeks

#### 3. Error Context Enrichment

```python
# Enhanced error recovery with code context
def analyze_error_with_context(
    error: Exception,
    code_snippet: str,
    findings: list[ReviewFinding],
    project_key: str
) -> dict:
    """Analyze error and suggest fixes using code context."""
    
    # 1. Classify error
    error_type = classify_error(error)  # syntax|logic|test|type
    
    # 2. Find similar code locations in Lattice
    locations = find_similar_patterns(code_snippet, project_key)
    
    # 3. Extract lessons from Dream (similar fixes)
    lessons = db.query(Lesson).filter(
        Lesson.project_id == project_id,
        Lesson.claim.contains(error_type),
        Lesson.status == "accepted"
    ).all()
    
    # 4. Generate targeted fix suggestion
    fix_suggestion = llm_generate_fix(
        error=error,
        code=code_snippet,
        similar_locations=locations,
        past_fixes=lessons,
    )
    
    # 5. Store as episodic memory
    store_episodic_memory({
        "error_type": error_type,
        "code": code_snippet,
        "fix": fix_suggestion,
        "success": validate_fix(fix_suggestion),
    })
    
    return {
        "error_type": error_type,
        "fix_suggestion": fix_suggestion,
        "similar_locations": locations,
        "past_lessons": [l.claim for l in lessons],
    }
```

**Effort:** 3 weeks

### Phase D: Advanced Features (Weeks 21+)

**Goal:** Long-running projects, handoffs, cross-project learning

#### 1. Multi-Day Project Memory

```python
# Support resuming projects across days
class MentrixProjectMemory(Base):
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    
    # Checkpoints
    last_checkpoint = Column(JSON)  # {phase, code, tests, docs}
    checkpoint_timestamp = Column(DateTime)
    
    # Decisions log
    decisions = Column(JSON, default=list)  # [{decision, rationale, date}]
    
    # Blockers
    known_issues = Column(JSON, default=list)  # [{issue, workaround, priority}]
    
    # Progress
    completion_percent = Column(Float, default=0.0)
    estimated_remaining_hours = Column(Float)

# Usage:
memory = get_project_memory(project_id)
instructions = f"""
Resume context:
- Phase: {memory.last_checkpoint['phase']}
- Prior decisions: {memory.decisions[-3:]}
- Known issues: {memory.known_issues}
- Progress: {memory.completion_percent}%
"""
```

**Effort:** 3 weeks

#### 2. Agent Handoff System

```python
# Allow agents to hand off work to each other
class AgentHandoff(Base):
    from_agent = Column(String)  # "planner"
    to_agent = Column(String)    # "builder"
    project_id = Column(Integer)
    run_id = Column(String)
    
    context = Column(JSON)  # What handoff carries
    # {plan, assumptions, risks, code_outline, test_plan}
    
    status = Column(String)  # initiated|accepted|completed|failed

def orchestrate_handoff(from_agent: str, to_agent: str, context: dict):
    """Handoff work between agents."""
    
    # 1. Package context for handoff
    handoff = AgentHandoff(
        from_agent=from_agent,
        to_agent=to_agent,
        context=context,
    )
    db.add(handoff)
    
    # 2. Log in event journal
    run.events_json.append({
        "ts": now(),
        "event": "handoff",
        "from": from_agent,
        "to": to_agent,
        "context_size": len(str(context)),
    })
    
    # 3. Activate next agent
    activate_agent(to_agent, context)
```

**Effort:** 3 weeks

---

## Dependency Graph

```
Foundation (Weeks 1-4)
├─ Conversation Memory
├─ Project Context Store
└─ Unified Prompt Engine
    ↓
Code Understanding (Weeks 5-12)
├─ Tree-Sitter Integration
└─ Semantic Analysis
    ↓
Orchestration (Weeks 13-20)
├─ Active Run Awareness
├─ Phase-Aware Tool Gating
└─ Error Context Enrichment
    ↓
Advanced Features (Weeks 21+)
├─ Multi-Day Project Memory
└─ Agent Handoff System
```

---

## Success Criteria

### Phase A (Foundation)
- ✅ Sessions persist across HTTP requests
- ✅ Working memory injected into prompts
- ✅ Project context stored and accessible
- ✅ Phase-aware persona selection working

### Phase B (Code Understanding)
- ✅ Tree-Sitter parsing all supported languages
- ✅ Call graphs generated correctly
- ✅ Type inference working (Python/TypeScript)
- ✅ Dead code detection functional

### Phase C (Orchestration)
- ✅ Mentrix Companion aware of active Delivery runs
- ✅ Tool availability changes based on phase
- ✅ Error recovery with code-specific suggestions
- ✅ Bidirectional Companion ↔ Delivery communication

### Phase D (Advanced)
- ✅ Multi-day projects resumable with context
- ✅ Handoffs between agents preserve context
- ✅ Cross-project pattern learning working
- ✅ Long-running workflows supported

---

## Conclusion

Mentrix evolution from a **dual-mode agent** to a **unified orchestration layer** requires:

1. **4-phase implementation** (20+ weeks total)
2. **Persistent context** (sessions, memory, project model)
3. **Deep code understanding** (Tree-Sitter + semantics)
4. **Unified coordination** (all modules synchronized)
5. **Learning system** (memory + Dream Engine)

The result: **Mentrix as an intelligent hub** coordinating all ZECT workflows with repository and business context awareness, multi-day project memory, and self-improving capabilities via the Dream Engine.

This transforms Mentrix from a **tool executor** to a **true orchestration layer** capable of understanding complex projects and guiding teams through sophisticated delivery workflows.

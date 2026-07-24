# ZECT Enhancement Blueprint & Roadmap

**Status:** Comprehensive implementation blueprint  
**Date:** July 23, 2026  
**Planning Horizon:** 24+ weeks  
**Version:** 1.0

---

## Executive Summary

ZECT is a **production-grade platform with complete core functionality** (6 workflow modules, 59 routers, 50+ database models). This roadmap prioritizes enhancements across three dimensions:

1. **Security Hardening** (4 weeks, blocking production deployment)
2. **Mentrix Orchestration** (20+ weeks, transforms voice/AI capabilities)
3. **Code Understanding** (6-8 weeks in parallel, enables semantic analysis)

**Total Effort:** 6-8 full-time engineers, 24-30 weeks  
**Impact:** Enterprise-grade platform with AI-driven orchestration and self-improving capabilities

---

## Part 1: Security Hardening Sprint (Weeks 1-4)

### Priority: 🔴 BLOCKING (Must complete before production)

**Rationale:** Security gaps prevent enterprise deployment. Address critical XOR encryption, CORS, prompt injection vulnerabilities.

#### Week 1: CRITICAL Fixes

| Fix | Effort | Risk Reduction | Blocking |
|-----|--------|-----------------|----------|
| Replace XOR encryption with Fernet | 2-3 days | CRITICAL → HIGH | Yes |
| Fix CORS misconfiguration | 1 day | MEDIUM-HIGH | Yes |
| Disable git hooks during clone | 0.5 day | MEDIUM | Yes |
| Implement per-user rate limiting | 3-4 days | HIGH | Yes |

**Deliverables:**
- [ ] `security/encryption.py` rewritten with Fernet
- [ ] CORS headers fixed in main.py
- [ ] `repo_clone()` patched with `--config core.hooksPath=/dev/null`
- [ ] Rate limiter decorator: `@rate_limit(rpm_per_user=60)`

**Testing:**
- [ ] Encryption roundtrip tests
- [ ] CORS origin validation tests
- [ ] Rate limit bucket tests

---

#### Week 2: HIGH Priority Fixes

| Fix | Effort | Risk Reduction | Blocking |
|-----|--------|-----------------|----------|
| Add role enforcement on endpoints | 4-5 days | HIGH | Yes |
| Implement resource-level ACLs | 4-5 days | HIGH | Yes |
| Add prompt injection sanitizer | 2-3 days | HIGH | No |
| MCP tool whitelist validation | 2-3 days | HIGH | No |

**Deliverables:**
- [ ] `@require_role("admin")` decorator on 20+ endpoints
- [ ] `ProjectAccessControl` class checking user permissions
- [ ] `PromptSanitizer` removing `[SYSTEM`, `OVERRIDE`, etc.
- [ ] MCP tool registry with whitelist check

**Testing:**
- [ ] Permission enforcement tests (negative cases)
- [ ] Cross-user access denial tests
- [ ] Prompt injection payload tests
- [ ] Tool whitelist bypass tests

---

#### Week 3: MEDIUM Priority Fixes

| Fix | Effort | Risk Reduction | Timeline |
|-----|--------|-----------------|----------|
| MFA support (TOTP) | 4-5 days | MEDIUM | Post-launch |
| CSP headers + security headers | 1-2 days | MEDIUM | Week 3 |
| Secret rotation workflow | 2-3 days | MEDIUM | Week 3 |
| Dependency vulnerability scanning (CI) | 1-2 days | MEDIUM | Week 3 |

**Deliverables:**
- [ ] TOTP generator/validator in auth service
- [ ] `X-Content-Security-Policy` header added
- [ ] `/api/secrets/rotate` endpoint
- [ ] `safety check` + `bandit` in GitHub Actions

---

#### Week 4: Verification & Polish

| Activity | Effort | Outcome |
|----------|--------|---------|
| Security code review | 3-4 days | All fixes reviewed by security expert |
| Penetration testing (basic) | 2-3 days | Manual testing against OWASP Top 10 |
| Documentation | 1-2 days | Security guide for operators |
| Production deployment checklist | 1 day | GO/NO-GO decision matrix |

**Testing:**
- [ ] Full OWASP Top 10 test suite
- [ ] Automated security scanning
- [ ] Manual penetration testing

**Risk Mitigation:**
- All critical/high issues resolved
- Medium issues on backlog (track, non-blocking)
- Security testing automated in CI/CD

---

### Security Hardening Metrics

**Before/After:**

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Critical issues | 1 | 0 | 0 |
| High issues | 6 | 1-2 | 0-1 |
| Medium issues | 5 | 2-3 | <5 |
| CVSS avg score | 7.2 | 4.5 | <4.0 |
| Encryption strength | XOR (broken) | Fernet (256-bit) | Military-grade |
| CORS policy | `["*"]` | Whitelist | Whitelist |

---

## Part 2: Mentrix Smart Orchestration (Weeks 5-24)

### Priority: 🟠 HIGH (Transforms platform capabilities)

**Rationale:** Mentrix evolution from tool executor to intelligent orchestration layer enables:
- Conversation context persistence
- Deep code understanding
- Business context awareness
- Cross-module coordination
- Self-improving via Dream Engine

#### Phase A: Foundation (Weeks 5-8)

**Goal:** Persistent context + unified prompts

| Component | Effort | Deliverable |
|-----------|--------|-------------|
| Conversation Memory System | 2 weeks | MentrixCompanionSession table + context injection |
| Project Context Store | 1 week | ProjectContext table with tech stack, domain, rules |
| Unified Prompt Engine | 1 week | MentrixSystemPrompt class with phase awareness |
| Integration with Lattice | 0.5 week | Session context injected into lattice queries |

**Workflow:**
```
Week 5: Database schema + ORM models
Week 6: Context extraction logic
Week 7: Unified prompt builder
Week 8: Integration testing + demos
```

**Acceptance Criteria:**
- [ ] Session context persists across HTTP requests
- [ ] Working memory injected into all prompts
- [ ] ProjectContext populated for existing projects
- [ ] Phase-aware persona selection working
- [ ] Token budget awareness in prompts

**Testing:**
- [ ] Session persistence tests
- [ ] Context injection tests
- [ ] Prompt template tests
- [ ] Integration tests with Companion

**Success Demo:**
- User starts conversation
- Mentrix remembers prior goals
- Context updates after each turn
- Persona adjusts based on phase

---

#### Phase B: Code Understanding (Weeks 9-14)

**Goal:** Deep AST analysis via Tree-Sitter

| Component | Effort | Deliverable |
|-----------|--------|-------------|
| Tree-Sitter integration | 2 weeks | Parser setup for Python, TS, JS, Go, Rust, Java |
| Function signature extraction | 1 week | Extract params, return types, docstrings |
| Call-graph analysis | 1 week | Build complete call chains, identify cycles |
| Type inference | 1 week | Type flow analysis (Pyright for Python, TSC for TS) |
| Semantic pattern detection | 1 week | Find dead code, unused functions, bad patterns |

**Workflow:**
```
Week 9: Tree-Sitter setup + Python parser
Week 10: TS/JS/Go parsers
Week 11: Call graph + type inference
Week 12: Pattern detection
Week 13: Lattice integration
Week 14: Testing + optimization
```

**Acceptance Criteria:**
- [ ] All major languages parsed correctly
- [ ] Call graphs accurate (matches manual verification)
- [ ] Type inference working for 90%+ of code
- [ ] Dead code detection finds real unused code
- [ ] Performance: <2s per 100K LOC

**Testing:**
- [ ] Parser correctness tests (known repos)
- [ ] Call graph validation
- [ ] Type inference accuracy
- [ ] Performance benchmarks

**Success Demo:**
- Upload repo → call graph visualization
- Hover function → see all callers
- Identify dead code automatically
- Type annotations extracted

---

#### Phase C: Orchestration Layer (Weeks 15-20)

**Goal:** Unified Delivery ↔ Companion coordination

| Component | Effort | Deliverable |
|-----------|--------|-------------|
| Active run awareness | 1 week | Companion shows active Delivery status |
| Phase-aware tool gating | 1 week | Tool availability based on project phase |
| Error context enrichment | 1 week | Code-specific recovery suggestions |
| Feedback loops | 1 week | Delivery → Companion event streaming |
| Shared event journal | 1 week | Unified events_json format |
| LangGraph migration (optional) | 2 weeks | Migrate from FSM to LangGraph (future) |

**Workflow:**
```
Week 15: Active run context injection
Week 16: Phase-aware permission rules
Week 17: Error analysis + suggestion
Week 18: Event streaming
Week 19: Integration testing
Week 20: Hardening + optimization
```

**Acceptance Criteria:**
- [ ] Companion shows real-time Delivery status
- [ ] Tools available based on phase
- [ ] Error fixes targeted to code context
- [ ] Events streamed in real-time
- [ ] No latency regression

**Testing:**
- [ ] Active run context tests
- [ ] Tool gating tests
- [ ] Error recovery tests
- [ ] Event streaming tests
- [ ] Integration tests

**Success Demo:**
- Start Delivery → Companion aware
- Build phase → build tools preferred
- Error occurs → code-specific recovery
- Both modes synchronized

---

#### Phase D: Learning System (Weeks 21-24)

**Goal:** Self-improving via memory + Dream Engine

| Component | Effort | Deliverable |
|-----------|--------|-------------|
| Conversation clustering | 1 week | Episodic turns clustered by similarity |
| Pattern extraction | 1 week | Common decisions/blockers identified |
| Lesson staging | 1 week | Patterns staged for human review |
| Lesson application | 1 week | Staged lessons injected into prompts |

**Workflow:**
```
Week 21: Clustering algorithm + implementation
Week 22: Pattern extraction
Week 23: Lesson staging UI
Week 24: Integration with decision-making
```

**Acceptance Criteria:**
- [ ] Clustering finds semantically similar turns
- [ ] Extracted patterns are actionable
- [ ] Lessons staged for human review
- [ ] Injected lessons improve Mentrix decisions
- [ ] Learning metrics tracked (confidence, accuracy)

**Testing:**
- [ ] Clustering accuracy tests
- [ ] Pattern extraction tests
- [ ] Lesson quality tests
- [ ] A/B testing (with vs. without lessons)

**Success Demo:**
- Run multiple similar projects
- Dream Engine identifies patterns
- Mentrix learns from successes
- New projects benefit from past learnings

---

### Mentrix Roadmap Timeline

```
┌─────────────────────────────────────────────────────────┐
│ SECURITY (Weeks 1-4)                                   │
│ ├─ Encryption fix (Fernet)                             │
│ ├─ CORS fix                                            │
│ ├─ RBAC enforcement                                    │
│ └─ Rate limiting                                       │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE A: Foundation (Weeks 5-8)                        │
│ ├─ Conversation memory                                 │
│ ├─ Project context store                               │
│ ├─ Unified prompt engine                               │
│ └─ Integration tests                                   │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE B: Code Understanding (Weeks 9-14)              │
│ ├─ Tree-Sitter integration                             │
│ ├─ Call graph analysis                                 │
│ ├─ Type inference                                      │
│ ├─ Pattern detection                                   │
│ └─ Lattice integration                                 │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE C: Orchestration (Weeks 15-20)                  │
│ ├─ Active run awareness                                │
│ ├─ Phase-aware tool gating                             │
│ ├─ Error context enrichment                            │
│ ├─ Feedback loops                                      │
│ └─ Event streaming                                     │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE D: Learning System (Weeks 21-24)                │
│ ├─ Conversation clustering                             │
│ ├─ Pattern extraction                                  │
│ ├─ Lesson staging                                      │
│ └─ Self-improvement loop                               │
└─────────────────────────────────────────────────────────┘
```

---

## Part 3: Parallel Work Streams

### AI Technologies Integration

#### LangGraph Migration (Weeks 15-24, optional parallel)

**Current State:** FSM-based orchestration in `orchestrator.py`

**Upgrade Path:**
```python
# Current: orchestrator.py (900+ lines)
# Future: LangGraph-based workflow
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

# Add agent nodes
workflow.add_node("scout", scout_agent)
workflow.add_node("planner", planner_agent)
workflow.add_node("builder", builder_agent)

# Add edges with conditions
workflow.add_conditional_edges(
    "scout",
    should_plan,
    {True: "planner", False: END}
)

# Compile to runnable
app = workflow.compile()

# Execute
result = app.invoke({"goal": "..."})
```

**Benefits:**
- Built-in state management
- Better error handling
- Streaming support
- Visualization
- Community ecosystem

**Effort:** 2-3 weeks (parallel track)

---

#### Structured Output Implementation

**Goal:** Enforce JSON/schema responses from LLM

**Current:** Unstructured string responses  
**Target:** Pydantic models with validation

```python
from pydantic import BaseModel
from instructor import llm_with_instructor

class PlanResponse(BaseModel):
    stages: list[str]
    estimated_tokens: int
    risks: list[str]
    next_step: str

@llm_with_instructor
def generate_plan(goal: str, context: str) -> PlanResponse:
    """Generate plan with structured output."""
    pass

plan = generate_plan(goal, context)
# Guaranteed: plan.stages, plan.risks, plan.next_step all present
```

**Implementation:** Week 10  
**Effort:** 1 week

---

#### Multi-Agent Reasoning

**Goal:** Reasoning about complex decisions

**Pattern: "Thought Partner"**
```python
# Scout + Reviewer reason together
scout_findings = scout_agent(goal, context)

# Reviewer critiques scout's findings
reviewer_critique = reviewer_agent(
    goal=goal,
    scout_findings=scout_findings,
    instruction="Find flaws in scout's analysis"
)

# Planner incorporates both
plan = planner_agent(
    goal=goal,
    scout_findings=scout_findings,
    reviewer_critique=reviewer_critique,
)
```

**Implementation:** Week 19  
**Effort:** 1 week

---

#### Prompt Engineering Improvements

**Technique 1: Few-Shot Learning**
```python
# Inject examples of good outputs
examples = [
    {
        "goal": "Add async support",
        "good_plan": [
            "Analyze current sync code",
            "Design async API",
            "Generate async methods",
            ...
        ]
    },
    ...
]

prompt = build_fewshot_prompt(goal, examples)
```

**Technique 2: Chain-of-Thought**
```python
prompt = """
Goal: {goal}

Let's think step by step:
1. What is the current state?
2. What needs to change?
3. What could go wrong?
4. How do we mitigate risks?

Now, generate the plan:
"""
```

**Technique 3: Prompt Compression**
```python
# Remove redundant context, keep essential
compressed_context = compress_context(full_context, token_budget)
# Result: 40-60% reduction without quality loss
```

**Implementation:** Weeks 10, 15, 18  
**Effort:** Ongoing (1-2 days per technique)

---

### Observability & Monitoring

#### Structured Logging

**Goal:** Complete visibility into LLM operations

```python
# Structured logging for every LLM call
log_structured({
    "type": "llm_call",
    "model": "gpt-4o",
    "phase": "build",
    "tokens_in": 2048,
    "tokens_out": 512,
    "latency_ms": 1234,
    "cost_usd": 0.042,
    "success": True,
    "prompt_hash": "sha256:...",
    "output_hash": "sha256:...",
})
```

**Implementation:** Week 5  
**Effort:** 2-3 days

---

#### Token Usage Dashboard

**Goal:** Real-time visibility into LLM costs

```python
# Dashboard shows:
- Tokens used (today/month)
- Cost (today/month)
- Model breakdown (gpt-4o vs. gpt-4o-mini)
- Phase breakdown (ask vs. plan vs. build)
- User breakdown (top users, usage trends)
- Cost per phase (most expensive operations)

GET /api/analytics/tokens
  → {total_tokens, cost_usd, breakdown_by_model, breakdown_by_phase}
```

**Implementation:** Week 12  
**Effort:** 1 week

---

#### Distributed Tracing

**Goal:** Follow requests across services

**Tool:** OpenTelemetry + Jaeger

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("ask_operation") as span:
    span.set_attribute("project_id", project_id)
    span.set_attribute("model", "gpt-4o")
    
    # Lattice call
    with tracer.start_as_current_span("lattice_query"):
        context = lattice.query(project_key, q)
    
    # LLM call
    with tracer.start_as_current_span("llm_inference"):
        response = llm.ask(context)
```

**Implementation:** Week 8  
**Effort:** 2-3 days

---

## Part 4: Testing & Validation Strategy

### Unit Testing

**Coverage Target:** 85%+ (up from current ~60%)

**Priority Areas:**
1. Security fixes (100% coverage)
2. Mentrix orchestration (95% coverage)
3. Error handling (100% coverage)
4. Core business logic (90% coverage)

**Timeline:** Weeks 3, 9, 15, 21 (integrated into feature work)

---

### Integration Testing

**Test Suite Expansion:**

| Scenario | Current | Target |
|----------|---------|--------|
| End-to-end ask→plan→build | Partial | Full |
| Multi-repo orchestration | No | Yes |
| Permission enforcement | Partial | Full |
| Error recovery loop | No | Yes |
| Memory persistence | No | Yes |
| Cross-module coordination | Partial | Full |

**Timeline:** Weeks 8, 14, 20 (per phase)

---

### Security Testing

**Automated Security Scanning:**
```bash
# Static analysis
bandit backend/app/**/*.py
ruff check backend/
eslint frontend/src/**/*.tsx

# Dependency scanning
safety check --json
pip-audit --json

# SAST (static application security testing)
semgrep --config=p/security-audit
```

**Manual Testing:**
- OWASP Top 10 test cases
- Prompt injection payloads
- Permission bypass attempts
- Rate limit testing

**Timeline:** Weeks 4, 10, 16, 22

---

### Performance Testing

**Benchmarks:**

| Operation | Current | Target | Effort |
|-----------|---------|--------|--------|
| Lattice query (100K symbols) | 200ms | <100ms | 1 week |
| Code indexing (10K LOC) | 2s | <1s | 1 week |
| LLM inference (average) | 8s | <5s (batching) | 2 weeks |
| Permission check | 5ms | <2ms (cache) | 1 week |

**Timeline:** Weeks 14, 20

---

## Part 5: Deployment & Rollout

### Staging Environment

**Setup:**
- Separate AWS account/VPC
- PostgreSQL (production scale)
- Load testing capability
- Monitoring stack (Datadog)

**Validation:**
- All tests passing
- Security scanning clean
- Performance benchmarks met
- Load testing 2x expected peak

**Timeline:** Weeks 4, 24

---

### Blue-Green Deployment

**Strategy:**
```
Current (Blue):  v2.9.9 (security baseline)
Staging (Green): v3.0.0 (with all enhancements)

Deploy to Green, validate, switch traffic
Rollback to Blue if issues
```

**Phases:**
1. Internal team: 100% (1 week)
2. Early adopters: 10% (1 week)
3. Gradual: 25% → 50% → 100% (2 weeks)

**Timeline:** Week 24+

---

### Monitoring & Alerting

**Key Metrics:**
- API latency (p50, p95, p99)
- Error rate (4xx, 5xx, timeouts)
- Token usage (by user, model, phase)
- Security events (denied permissions, suspicious inputs)
- Memory/CPU usage

**Alerts:**
- Latency >5s (p95)
- Error rate >1%
- Token budget exceeded
- Denial rate >5%

---

## Consolidated Timeline

```
WEEK 1-4:   SECURITY HARDENING (Blocking)
├─ Critical & high fixes
├─ Testing & validation
└─ Production readiness

WEEK 5-8:   MENTRIX FOUNDATION
├─ Conversation memory
├─ Project context store
├─ Unified prompts
└─ Phase 1 integration testing

WEEK 9-14:  CODE UNDERSTANDING
├─ Tree-Sitter integration
├─ Call graph analysis
├─ Type inference
├─ Pattern detection
└─ Lattice integration

WEEK 15-20: ORCHESTRATION LAYER
├─ Active run awareness
├─ Phase-aware tool gating
├─ Error context enrichment
├─ Feedback loops
└─ Event streaming

WEEK 21-24: LEARNING SYSTEM
├─ Conversation clustering
├─ Pattern extraction
├─ Lesson staging
├─ Self-improvement integration
└─ Final validation

PARALLEL:
├─ LangGraph migration (optional)
├─ Observability (logging, tracing, dashboards)
├─ Performance optimization
└─ Testing & security validation

WEEK 24+:   DEPLOYMENT
├─ Staging validation
├─ Blue-green deployment
├─ Monitoring & alerting
└─ Rollout (phased)
```

---

## Resource Requirements

### Team Composition

**Full-Time Engineers:** 6-8
- 2 Backend engineers (Mentrix + security)
- 2 Frontend engineers (UI + orchestration)
- 1 Infrastructure engineer (deployment, monitoring)
- 1 Security engineer (security hardening, testing)
- 1 ML/AI engineer (prompt engineering, LangGraph)
- 1 QA engineer (testing, validation)

### Budget Estimate

**Infrastructure:**
- AWS (dev/staging/prod): $5K/month
- Datadog monitoring: $2K/month
- External AI services (Tree-Sitter, LangGraph): $1K/month

**Human Capital:**
- 6-8 FTE × 24 weeks × $200/hour = $1.2M - $1.6M

**Total:** ~$1.3M - $1.8M

---

## Success Metrics

### Security
- ✅ 0 critical issues
- ✅ <2 high issues
- ✅ CVSS average <4.0
- ✅ No security test failures

### Performance
- ✅ API latency p95 <2s
- ✅ Token cost -30% via optimization
- ✅ Code indexing <1s per 10K LOC

### Functionality
- ✅ Conversation memory working
- ✅ Deep code understanding (call graphs accurate)
- ✅ Phase-aware orchestration active
- ✅ Self-improvement via Dream Engine

### Adoption
- ✅ 100% of new projects using Mentrix
- ✅ 80%+ user satisfaction
- ✅ 50%+ reduction in manual work

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Security fixes introduce regressions | Medium | High | Comprehensive testing, phased rollout |
| Tree-Sitter parsing incomplete | Low | Medium | Start with top 3 languages, expand |
| LLM cost overruns | Medium | Medium | Token budgets, monitoring, caching |
| Team turnover | Low | High | Documentation, knowledge sharing, mentorship |
| Scope creep | High | High | Strict roadmap, feature gates, prioritization |

---

## Conclusion

This **24-week roadmap** transforms ZECT from a production-grade **feature-complete platform** to an **enterprise-grade AI-driven system** with:

1. **Security hardening** (production-ready)
2. **Smart orchestration** (Mentrix as intelligent hub)
3. **Deep code understanding** (semantic analysis)
4. **Self-improving capabilities** (Dream Engine integration)
5. **Enterprise monitoring** (complete visibility)

The result: A platform that not only delivers features but **learns and improves** over time, with Mentrix as the intelligent orchestrator coordinating all workflows.

**Ready to transform ZECT into an enterprise AI platform.**

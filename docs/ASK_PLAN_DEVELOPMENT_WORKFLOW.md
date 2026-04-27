# Ask / Plan / Development Workflow Guide

> Step-by-step guide for using ZECT's 5-stage engineering delivery workflow.

## Overview

ZECT implements a structured 5-stage workflow for engineering delivery. Each stage has defined activities, deliverables, and gates that must be satisfied before proceeding to the next stage.

```
Ask → Plan → Build → Review → Deploy
```

## The 5 Stages

### Stage 1: Ask Mode

**Purpose:** Gather requirements, define scope, and validate assumptions.

**Navigate:** Sidebar > Workflow Stages > Ask Mode (or `/stages/ask`)

#### Key Activities

1. Stakeholder interviews and workshops
2. Requirements elicitation and documentation
3. Competitive analysis and market research
4. Technical feasibility assessment
5. Risk identification and scoring

#### Deliverables

- Requirements document with acceptance criteria
- Stakeholder sign-off on scope
- Risk assessment and mitigation plan
- Technology constraints and preferences
- Success metrics and KPIs

#### Stage Gates (must pass before moving to Plan)

- [ ] All stakeholders reviewed requirements
- [ ] Scope is bounded and achievable
- [ ] Dependencies identified and documented
- [ ] Budget and timeline approved

---

### Stage 2: Plan Mode

**Purpose:** Design architecture, plan sprints, and create implementation roadmap.

**Navigate:** Sidebar > Workflow Stages > Plan Mode (or `/stages/plan`)

#### Key Activities

1. System design and architecture review
2. API and data model design
3. Sprint planning and estimation
4. Dependency mapping and sequencing
5. Security and compliance review

#### Deliverables

- Architecture decision records (ADRs)
- API design and data model specifications
- Sprint plan with story points
- Infrastructure provisioning plan
- Testing strategy document

#### Stage Gates (must pass before moving to Build)

- [ ] Architecture approved by tech lead
- [ ] API contracts finalized
- [ ] Sprint capacity confirmed
- [ ] Infrastructure costs estimated

---

### Stage 3: Build Phase

**Purpose:** Implement features, write code, and create automated tests.

**Navigate:** Sidebar > Workflow Stages > Build Phase (or `/stages/build`)

#### Key Activities

1. Feature implementation in sprints
2. Test-driven development (TDD)
3. Code reviews and pair programming
4. CI/CD pipeline maintenance
5. Technical debt tracking and resolution

#### Deliverables

- Working feature code with unit tests
- CI pipeline green on all commits
- Integration tests passing
- Code documentation and inline comments
- Performance benchmarks baseline

#### Stage Gates (must pass before moving to Review)

- [ ] All unit tests passing (>80% coverage)
- [ ] CI pipeline green
- [ ] No critical security vulnerabilities
- [ ] Code follows established patterns

---

### Stage 4: Review

**Purpose:** Quality assurance, security audit, and performance review.

**Navigate:** Sidebar > Workflow Stages > Review (or `/stages/review`)

#### Key Activities

1. Security vulnerability scanning
2. Performance and load testing
3. Accessibility testing
4. Code quality analysis
5. User acceptance testing (UAT)

#### Deliverables

- Security audit report with findings
- Performance test results
- Accessibility compliance report
- Code quality metrics and trends
- Bug fix verification results

#### Stage Gates (must pass before moving to Deploy)

- [ ] No critical or high severity bugs
- [ ] Security audit passed
- [ ] Performance within SLA targets
- [ ] Accessibility standards met (WCAG 2.1)

---

### Stage 5: Deployment

**Purpose:** Release to production, monitor health, and validate deployment.

**Navigate:** Sidebar > Workflow Stages > Deployment (or `/stages/deploy`)

#### Key Activities

1. Blue/green or canary deployment
2. Health check verification
3. Monitoring dashboard review
4. Stakeholder communication
5. Post-deployment retrospective

#### Deliverables

- Production deployment runbook
- Monitoring dashboards and alerts
- Rollback procedure documentation
- Post-deployment verification checklist
- Release notes for stakeholders

#### Stage Gates (must pass for release sign-off)

- [ ] Staging environment verified
- [ ] Rollback procedure tested
- [ ] Monitoring and alerting configured
- [ ] Stakeholders notified of release

---

## Using the Workflow with AI Tools

### With ZECT Blueprint Generator

1. Run a Blueprint analysis on your repo
2. Copy the generated prompt
3. Paste into your AI tool with stage-specific instructions:
   - **Ask:** "Analyze these requirements and identify gaps"
   - **Plan:** "Design the architecture for this system"
   - **Build:** "Implement the feature following existing patterns"
   - **Review:** "Review this code for security and performance issues"
   - **Deploy:** "Generate a deployment runbook for this service"

### With ZEF Templates

Use ZEF prompt templates for each stage:
- `templates/prompts/analyze-legacy-repo.md` — Ask stage
- `templates/prompts/analyze-for-enhancement.md` — Plan stage
- `templates/prompts/analyze-new-project.md` — Build stage

## Best Practices

1. **Do not skip stages** — Each stage builds on the previous one
2. **Document gate decisions** — Record why each gate was passed or waived
3. **Use ZECT's repo analysis** — Feed real data into each stage's decisions
4. **Iterate within stages** — It's normal to loop within a stage before moving forward
5. **Track progress in ZECT** — Use project status to reflect current stage

# ZECT — AI Usage Rules

## Overview

These rules govern how AI tools are used within ZECT and across Zinnia engineering teams. They ensure safety, auditability, cost control, and quality.

---

## Core Principles

1. **AI assists, humans decide** — AI generates, recommends, and analyzes. Humans approve, merge, and deploy.
2. **Transparency** — Every AI interaction is logged with token counts and costs.
3. **AI-agnostic** — No vendor lock-in. Any LLM provider can be used.
4. **Security first** — No secrets in prompts. No sensitive data sent to AI without encryption.
5. **Cost-conscious** — Use the cheapest model that produces acceptable quality.

---

## What AI CAN Do

| Action | Category | Example |
|--------|----------|---------|
| Generate code | Creation | Write a new API endpoint |
| Review code | Analysis | Identify bugs in a PR |
| Generate documentation | Creation | Write API reference from code |
| Answer questions | Analysis | Explain architecture decisions |
| Generate plans | Planning | Create phased migration plan |
| Analyze repos | Analysis | Map dependencies and structure |
| Generate prompts | Creation | Create fix prompts from review findings |
| Estimate effort | Planning | Estimate story points for features |
| Suggest refactoring | Analysis | Identify code smells and suggest fixes |
| Generate tests | Creation | Write unit tests for a function |

---

## What AI CANNOT Do

| Action | Why | Who Can |
|--------|-----|---------|
| Merge PRs | Requires human judgment | Tech Lead |
| Deploy to production | Risk too high for automation | DevOps + PM approval |
| Delete data | Irreversible action | Admin only |
| Access production databases | Security risk | DBA only |
| Send external emails/notifications | Could affect customers | Marketing/PM approval |
| Modify CI/CD pipelines | Could break builds for everyone | DevOps |
| Change access permissions | Security risk | Admin only |
| Commit secrets | Security violation | Nobody (blocked by tooling) |

---

## Model Selection Guidelines

| Task | Recommended Model | Why |
|------|-------------------|-----|
| Simple Q&A | gpt-4o-mini / haiku | Low cost, fast |
| Code generation | gpt-4o / sonnet | Higher quality needed |
| Code review | gpt-4o / sonnet | Needs deep understanding |
| Documentation | gpt-4o-mini / haiku | Mostly formatting |
| Blueprint generation | gpt-4o / sonnet | Complex synthesis |
| Plan generation | gpt-4o / sonnet | Strategic thinking |
| Token estimation | Local calculation | No API call needed |

---

## Prompt Quality Standards

Every prompt sent to AI must:

1. **Have clear context** — What repo, what files, what problem
2. **Have specific instructions** — What to do, what format to use
3. **Have constraints** — What NOT to do, what patterns to follow
4. **Be minimal** — No unnecessary context that wastes tokens
5. **Be safe** — No secrets, credentials, or PII in prompts

---

## Token Usage Limits

| Role | Daily Limit | Monthly Limit |
|------|-------------|---------------|
| Developer | 100,000 tokens | 2,000,000 tokens |
| Tech Lead | 200,000 tokens | 5,000,000 tokens |
| Admin | Unlimited | Unlimited |

### Escalation

When limits are reached:
1. Alert user that they're at 80% of budget
2. Block non-critical requests at 100%
3. Allow override with manager approval
4. Log all overrides for audit

---

## Audit Requirements

Every AI interaction MUST log:

| Field | Purpose |
|-------|---------|
| User ID | Who made the request |
| Timestamp | When it happened |
| Model used | Which AI model |
| Token count | Input + output tokens |
| Cost | Estimated cost in USD |
| Feature | Which ZECT feature triggered it |
| Success/failure | Whether the call succeeded |

---

## Data Classification

| Classification | Can Send to AI | Examples |
|----------------|----------------|----------|
| **Public** | Yes | Open-source code, public docs |
| **Internal** | Yes (with logging) | Internal code, architecture docs |
| **Confidential** | No | Customer data, PII, credentials |
| **Restricted** | Never | Encryption keys, production secrets |

---

## Compliance

- All AI usage must comply with Zinnia's data governance policy
- No customer PII in AI prompts
- No production data in development AI calls
- Retain audit logs for 90 days minimum
- Regular review of AI usage patterns by security team

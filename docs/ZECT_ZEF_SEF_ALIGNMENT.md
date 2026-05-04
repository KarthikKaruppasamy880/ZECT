# ZECT / ZEF / SEF — Alignment & Comparison

## Overview

This document compares ZECT (Zinnia Engineering Control Tower) with ZEF (Zinnia Engineering Framework) and recommends alignment strategies. The goal is to ensure complementary capabilities without duplication.

---

## Tool Comparison

| Aspect | ZECT | ZEF |
|--------|------|-----|
| **Full Name** | Zinnia Engineering Control Tower | Zinnia Engineering Framework |
| **Purpose** | AI-governed engineering productivity platform | Engineering standards & component framework |
| **Focus** | AI-assisted workflows, code review, blueprints | UI components, design system, standards |
| **Tech Stack** | React + FastAPI + AI APIs | React + TypeScript |
| **AI Integration** | Core feature (multi-provider) | None (pure framework) |
| **Target User** | Engineers using AI tools daily | Engineers building Zinnia products |
| **Scope** | Cross-project orchestration | Per-project implementation |

---

## Capability Matrix

| Capability | ZECT | ZEF | Overlap? |
|-----------|------|-----|----------|
| AI Code Review | Yes | No | None |
| Blueprint Generation | Yes | No | None |
| Repo Analysis | Yes | No | None |
| Token Tracking | Yes | No | None |
| Plan Generation | Yes | No | None |
| Ask Mode (Q&A) | Yes | No | None |
| UI Component Library | No | Yes | None |
| Design System | No | Yes | None |
| Project Templates | Partial | Yes | **Overlap** |
| Documentation | Yes (auto-generated) | Yes (manual) | **Overlap** |
| Engineering Standards | Yes (via governance) | Yes (via conventions) | **Overlap** |

---

## Alignment Recommendations

### 1. ZECT as the Orchestration Layer

**Recommendation:** ZECT should orchestrate and enhance ZEF projects, not replace them.

```
ZEF defines HOW to build (standards, components, patterns)
ZECT defines HOW TO USE AI to build faster (workflows, reviews, blueprints)
```

### 2. ZEF Components in ZECT UI

**Recommendation:** ZECT's frontend should eventually adopt ZEF's design system components for visual consistency across Zinnia tools.

| Current ZECT UI | Aligned with ZEF |
|----------------|------------------|
| Custom Tailwind cards | ZEF Card component |
| Custom sidebar | ZEF Navigation component |
| Custom buttons | ZEF Button component |
| Custom forms | ZEF Form components |

### 3. ZECT Generates ZEF-Compliant Code

**Recommendation:** When ZECT generates blueprints or plans, it should follow ZEF's engineering standards.

| ZECT Feature | ZEF Alignment |
|-------------|---------------|
| Blueprint Generator | Output follows ZEF project structure |
| Plan Mode | Recommends ZEF-approved tech stack |
| Code Review | Checks against ZEF coding standards |
| Doc Generator | Uses ZEF documentation templates |

### 4. Shared Skills

**Recommendation:** Create Skills that bridge both tools.

| Skill | ZECT Role | ZEF Role |
|-------|-----------|----------|
| New Project Setup | Generate plan + blueprint | Provide template + standards |
| Code Review | AI analysis | Standards checklist |
| Documentation | Auto-generate from code | Manual refinement + design |
| Component Creation | Blueprint for component | Component library standard |

---

## What NOT to Duplicate

| Capability | Keep In | Do NOT Duplicate In |
|-----------|---------|---------------------|
| UI Component Library | ZEF | ZECT |
| Design Tokens | ZEF | ZECT |
| AI Workflows | ZECT | ZEF |
| Token Tracking | ZECT | ZEF |
| Code Review | ZECT | ZEF |
| Project Templates (code) | ZEF | ZECT |
| Project Templates (AI-generated) | ZECT | — |
| Engineering Standards | Both (different aspects) | — |

---

## Integration Points

### How ZECT Uses ZEF

1. **Blueprint Generation** → References ZEF project templates
2. **Code Review** → Validates against ZEF coding standards
3. **Plan Mode** → Recommends ZEF-approved patterns
4. **New Project** → Scaffolds from ZEF templates
5. **Documentation** → Follows ZEF documentation structure

### How ZEF Benefits from ZECT

1. **Automated reviews** → ZECT reviews ZEF PRs for quality
2. **Documentation** → ZECT auto-generates ZEF component docs
3. **Migration** → ZECT plans migrations to latest ZEF version
4. **Analytics** → ZECT tracks ZEF adoption across projects

---

## Migration Strategy

### For Teams Currently Using ZEF

```
1. Keep ZEF for component library and design system
2. Add ZECT for AI-assisted workflows
3. Configure ZECT to use ZEF standards as review criteria
4. Use ZECT Blueprint to onboard new projects to ZEF
```

### For Teams Not Using Either

```
1. Start with ZECT for immediate productivity gains (AI review, blueprints)
2. Adopt ZEF components gradually as project matures
3. Use ZECT's analysis to identify where ZEF patterns apply
```

---

## Key Principle

> **Do NOT blindly copy ZEF into ZECT or vice versa. Each tool has its own purpose. Adapt correctly — use ZECT for AI orchestration and ZEF for engineering standards.**

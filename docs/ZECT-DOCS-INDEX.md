# ZECT Documentation Index

## Complete Guide to All Repository Documentation

**Version:** 3.2 | **Date:** May 2026 | **Total Docs:** 90+ markdown files | **Screenshots:** 49

---

## Quick Reference

| If You Need... | Read This |
|----------------|-----------|
| Full tech details (one-page) | `ZECT-TECH-DETAILS-ONE-PAGE.md` |
| Executive overview for management | `ZECT-ONE-SHEET.md` |
| Full technical white paper | `ZECT-WHITE-PAPER.md` |
| Demo/presentation content | `ZECT-DEMO-PPT-CONTENT.md` |
| How to use every screen | `ZECT_USER_MANUAL.md` |
| Gap analysis (all gaps closed) | `ZECT-GAP-ANALYSIS.md` |
| How to deploy to AWS | `AWS_DEPLOYMENT_GUIDE.md` |
| Management-level feature overview | `ZECT_MANAGEMENT_GUIDE_v2.md` |
| AI-agnostic architecture | `architecture/AI_AGNOSTIC_ARCHITECTURE.md` |
| All screenshots | `screenshots/` (42 images, all sidebar screens) |

---

## 1. Core Documents (Top-Level `docs/`)

### Strategy & Overview

| File | Path | Purpose |
|------|------|---------|
| **White Paper** | `docs/ZECT-WHITE-PAPER.md` | Technical white paper for stakeholders — architecture, capabilities, competitive positioning, ROI |
| **Tech Details** | `docs/ZECT-TECH-DETAILS-ONE-PAGE.md` | Complete tech stack, all gaps fixed, data integrity, deployment, usefulness to Zinnia |
| **One-Sheet** | `docs/ZECT-ONE-SHEET.md` | Single-page executive summary — at-a-glance metrics, differentiators, roadmap |
| **Demo PPT Content** | `docs/ZECT-DEMO-PPT-CONTENT.md` | Slide-by-slide content for live demo presentations with speaker notes |
| **Gap Analysis v3.0** | `docs/ZECT-GAP-ANALYSIS.md` | Feature-by-feature comparison with industry tools — all gaps CLOSED (except 2.7 Integrations) |
| **Feature Roadmap** | `docs/ZECT_FEATURE_ROADMAP_AND_GAP_ANALYSIS.md` | Earlier roadmap with phase-by-phase feature plan |
| **Vision & Integrations** | `docs/ZECT_VISION_AND_INTEGRATIONS.md` | Long-term vision and integration strategy |
| **ZEF/SEF Alignment** | `docs/ZECT_ZEF_SEF_ALIGNMENT.md` | How ZECT aligns with ZEF and SEF platforms |

### User Documentation

| File | Path | Purpose |
|------|------|---------|
| **User Manual v3.0** | `docs/ZECT_USER_MANUAL.md` | Complete user guide — every sidebar section, every screen, every button including v3.0 gap fixes |
| **User Manual (Earlier)** | `docs/USER_MANUAL.md` | Earlier version of user manual |
| **Management Guide v2** | `docs/ZECT_MANAGEMENT_GUIDE_v2.md` | Management-oriented guide — all 33 screens explained for leadership |
| **Management Guide v1** | `docs/ZECT_MANAGEMENT_GUIDE.md` | Earlier management guide version |
| **Tool Guide** | `docs/ZECT_TOOL_GUIDE.md` | How to use ZECT as a development tool |
| **Usage Guide** | `docs/ZECT_USAGE_GUIDE.md` | General usage patterns and workflows |
| **Features Reference** | `docs/FEATURES_REFERENCE.md` | Feature-by-feature reference with API details |
| **Screen Modes & Buttons** | `docs/SCREEN_MODES_AND_BUTTONS.md` | Detailed UI element reference for all screens |
| **Zinnia Intelligence Manual** | `docs/ZINNIA_INTELLIGENCE_USER_MANUAL.md` | Memory System, Dream Engine, Data Layer, Flywheel, Permissions |

### Setup & Configuration

| File | Path | Purpose |
|------|------|---------|
| **Local Setup** | `docs/LOCAL_SETUP_GUIDE.md` | Step-by-step local development setup |
| **Environment Setup** | `docs/ENV_SETUP_GUIDE.md` | Environment variable configuration |
| **Configuration Guide** | `docs/CONFIGURATION_GUIDE.md` | Full configuration reference |
| **Local Configuration** | `docs/LOCAL_CONFIGURATION_GUIDE.md` | Local-specific configuration details |
| **PostgreSQL Setup** | `docs/POSTGRESQL_SETUP_GUIDE.md` | PostgreSQL database setup and migration |
| **Docker Setup** | `docs/DOCKER_SETUP_GUIDE.md` | Docker Compose configuration |
| **Database Schema** | `docs/DATABASE_SCHEMA.md` | All SQLAlchemy models and table definitions |

### Deployment

| File | Path | Purpose |
|------|------|---------|
| **AWS Deployment** | `docs/AWS_DEPLOYMENT_GUIDE.md` | Full AWS deployment (EC2 + ECS + RDS + S3) |
| **EC2 Deployment** | `docs/EC2_DEPLOYMENT_GUIDE.md` | EC2-specific deployment steps |
| **ECS Deployment** | `docs/ECS_DEPLOYMENT_GUIDE.md` | ECS Fargate deployment with auto-scaling |
| **Deployment Prompts** | `docs/DEPLOYMENT_PROMPTS.md` | AI prompts for deployment assistance |

### Workflow & Process

| File | Path | Purpose |
|------|------|---------|
| **Project Workflow** | `docs/PROJECT_WORKFLOW_GUIDE.md` | Project lifecycle from creation to deployment |
| **Ask/Plan Development** | `docs/ASK_PLAN_DEVELOPMENT_WORKFLOW.md` | Ask → Plan → Build workflow details |
| **Code Review Workflow** | `docs/CODE_REVIEW_WORKFLOW.md` | All 5 code review modes explained |
| **Repo Integration Guide** | `docs/DEEP-REPO-INTEGRATION-USAGE-GUIDE.md` | Deep repo integration — clone, browse, index, write-back (744 lines) |
| **Repo Analysis Integration** | `docs/ZECT-repo-analysis-integration.md` | Repo analysis feature integration details |
| **Blueprint Generation** | `docs/BLUEPRINT_GENERATION_GUIDE.md` | Blueprint Generator usage |
| **Prompt Generation** | `docs/PROMPT_GENERATION_GUIDE.md` | How AI prompts are generated |
| **Multi-Repo Analysis** | `docs/MULTI_REPO_ANALYSIS_GUIDE.md` | Multi-repo analysis feature |
| **Repo Analysis** | `docs/REPO_ANALYSIS_GUIDE.md` | Single repo analysis guide |

### AI & Governance

| File | Path | Purpose |
|------|------|---------|
| **AI Agnostic Usage** | `docs/AI_AGNOSTIC_USAGE.md` | Provider-neutral AI usage guidelines |
| **Auto Skills** | `docs/AUTO_SKILLS_GUIDE.md` | Auto-skill discovery and execution |
| **ZEF for ZECT** | `docs/ZEF_FOR_ZECT_GUIDE.md` | ZEF integration capabilities |

### Testing & QA

| File | Path | Purpose |
|------|------|---------|
| **Sample Test Cases** | `docs/SAMPLE_TEST_CASES.md` | Test scenarios for all features |
| **UI/UX Requirements** | `docs/UI_UX_REQUIREMENTS.md` | UI/UX specifications |
| **UI Validation** | `docs/UI_VALIDATION_GUIDE.md` | UI validation checklist |
| **E2E Test Report** | `docs/ZECT-E2E-Test-Report.md` | End-to-end test results |
| **Project Status** | `docs/PROJECT_STATUS_REPORT.md` | Current project status |
| **Session Repo Details** | `docs/session-repo-details.md` | Session and repository information |

---

## 2. Architecture (`docs/architecture/`)

| File | Purpose |
|------|---------|
| `AI_AGNOSTIC_ARCHITECTURE.md` | Provider-neutral architecture design — works with any AI tool |
| `BACKEND_ARCHITECTURE.md` | FastAPI backend structure — routers, services, models |
| `FRONTEND_ARCHITECTURE.md` | React frontend structure — components, pages, routing |
| `TOOL_ARCHITECTURE.md` | Tool integration architecture |

---

## 3. Configuration (`docs/configuration/`)

| File | Purpose |
|------|---------|
| `MODEL_CONFIGURATION.md` | LLM model configuration — OpenAI, Anthropic, Ollama |

---

## 4. Governance (`docs/governance/`)

| File | Purpose |
|------|---------|
| `AI_USAGE_RULES.md` | Rules for AI feature usage and access |
| `MODEL_PROVIDER_RULES.md` | Model provider selection and security rules |
| `SECURITY_AND_APPROVALS.md` | Security protocols and approval workflows |

---

## 5. Guides (`docs/guides/`)

| File | Purpose |
|------|---------|
| `OLLAMA_LOCAL_LLM_GUIDE.md` | How to use Ollama for local LLM inference (no API key needed) |
| `ZECT_CONFIGURATION_GUIDE.md` | Detailed configuration guide |
| `ZECT_TOOL_GUIDE_FULL.md` | Full tool reference guide |

---

## 6. Repo Analysis (`docs/repo-analysis/`)

| File | Purpose |
|------|---------|
| `SINGLE_REPO_ANALYSIS.md` | Single repository analysis workflow |
| `MULTI_REPO_ANALYSIS.md` | Multi-repository comparison analysis |
| `BLUEPRINT_GENERATION.md` | Blueprint generation from repo analysis |
| `GRANULAR_DOCUMENTATION.md` | Granular doc generation from repos |

---

## 7. Reports (`docs/reports/`)

| File | Purpose |
|------|---------|
| `App-Runner-Test-Report.md` | App Runner feature test results |
| `ZECT-500-Error-Fix-Report.md` | 500 error fix documentation |
| `ZECT-Docker-Test-Report.md` | Docker deployment test results |
| `ZECT-Enterprise-Upgrade-Summary.md` | Enterprise feature upgrade summary |
| `ZECT-Full-E2E-Test-Report-v2.md` | Full E2E test report v2 |
| `ZECT-Legal-Compliance-Report.md` | Legal compliance review (branding cleanup) |
| `ZECT-Light-Theme-Test-Report.md` | Light theme test results |
| `ZECT-REPO-ANALYSIS-REPORT.md` | Repository analysis test report |
| `ZECT-comprehensive-test-report.md` | Comprehensive test results |
| `ZECT-failure-test-report.md` | Failure scenario test results |
| `ZECT-file-attachment-test-report.md` | File attachment feature test |
| `ZECT-final-test-report.md` | Final test summary |
| `ZECT-project-review.md` | Project review document |

---

## 8. Skills (`docs/skills/`)

| File | Purpose |
|------|---------|
| `AGENTS_OVERVIEW.md` | Agent system overview |
| `AGENT_TEMPLATE.md` | Template for creating new agents |
| `SKILLS_OVERVIEW.md` | Skills system overview |
| `SKILLS_REGISTRY.md` | Registry of all available skills |
| `SKILL_TEMPLATE.md` | Template for creating new skills |

---

## 9. Test Recordings (`docs/test-recordings/`)

| File | Purpose |
|------|---------|
| `APP-RUNNER-TEST-REPORT.md` | App Runner test with recording |
| `ZECT-DEEP-REPO-INTEGRATION-E2E-TEST-REPORT.md` | Deep repo integration E2E test with recording |
| `ZECT-GAP-FIX-E2E-TEST-REPORT.md` | v3.0 gap fix E2E test — Agent Mode, Sessions, Sandbox, CI Remediation, Collaboration, Diff Viewer, File Watcher |

---

## 10. Workflows (`docs/workflows/`)

| File | Purpose |
|------|---------|
| `ADD_COMMIT_PROMPT_WORKFLOW.md` | Git add/commit workflow |
| `ASK_PLAN_DEVELOP_WORKFLOW.md` | Ask → Plan → Develop workflow |
| `CONTEXT_MANAGEMENT.md` | Project context management |
| `PR_HUMAN_APPROVAL_WORKFLOW.md` | PR review and approval workflow |
| `SESSION_MANAGEMENT.md` | Session lifecycle management |
| `TOKEN_MANAGEMENT.md` | Token usage and budget management |

---

## 11. Screenshots (`docs/screenshots/`)

42 screenshots covering every ZECT screen:

| File | Screen |
|------|--------|
| `00-login.png` | Login page |
| `01-dashboard.png` | Dashboard |
| `02-projects.png` | Projects |
| `03-orchestration.png` | Orchestration |
| `04-repo-analysis.png` | Repo Analysis |
| `05-blueprint.png` | Blueprint Generator |
| `06-doc-generator.png` | Doc Generator |
| `07-code-review.png` | Code Review Engine |
| `08-analytics.png` | Analytics |
| `09-docs-center.png` | Docs Center |
| `10-settings.png` | Settings |
| `11-ask-mode.png` | Ask Mode |
| `12-plan-mode.png` | Plan Mode |
| `13-build-phase.png` | Build Phase |
| `14-review-phase.png` | Review Phase |
| `15-deployment.png` | Deployment |
| `16-skill-library.png` | Skill Library |
| `17-token-controls.png` | Token Controls |
| `18-app-runner.png` | App Runner |
| `19-file-explorer.png` | File Explorer |
| `20-git-operations.png` | Git Operations |
| `21-ci-monitor.png` | CI Monitor |
| `22-repo-workspace.png` | Repo Workspace |
| `23-memory-system.png` | Memory System |
| `24-dream-engine.png` | Dream Engine |
| `25-data-layer.png` | Data Layer |
| `26-data-flywheel.png` | Data Flywheel |
| `27-permissions.png` | Permissions |
| `28-transfer-onboard.png` | Transfer & Onboarding |
| `29-skills-engine.png` | Skills Engine |
| `30-knowledge-base.png` | Knowledge Base |
| `31-playbooks.png` | Playbooks |
| `32-scheduled-tasks.png` | Scheduled Tasks |
| `33-secrets-manager.png` | Secrets Manager |
| `34-code-index.png` | Code Index |
| `35-session-insights.png` | Session Insights |
| `36-conversations.png` | Conversations |
| `37-audit-trail.png` | Audit Trail |
| `38-rules-engine.png` | Rules Engine |
| `39-integrations.png` | Integrations |
| `40-export-share.png` | Export/Share |
| `41-output-history.png` | Output History |

---

## Document Statistics

| Category | Count | Total Lines |
|----------|-------|------------|
| Top-level docs | 35 | ~12,000 |
| Architecture | 4 | ~950 |
| Configuration | 1 | ~160 |
| Governance | 3 | ~470 |
| Guides | 3 | ~900 |
| Repo Analysis | 4 | ~550 |
| Reports | 13 | ~1,500 |
| Skills | 5 | ~880 |
| Test Recordings | 2 | ~340 |
| Workflows | 6 | ~1,060 |
| Screenshots | 42 | (images) |
| **Total** | **118 files** | **~19,000+ lines** |

---

*Document Location: `docs/ZECT-DOCS-INDEX.md`*
*Zinnia Technology — May 2026*

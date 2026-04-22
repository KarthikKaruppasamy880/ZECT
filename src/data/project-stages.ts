import {
  RequirementItem,
  PlanSection,
  BuildTask,
  ReviewFinding,
  DeployCheckItem,
} from "@/types";

// ============================================================
// Project-specific stage data for all 6 projects
// Each project has unique requirements, plans, tasks, findings,
// and deploy checklists appropriate to its domain.
// ============================================================

export interface ProjectStageData {
  requirements: RequirementItem[];
  planSections: PlanSection[];
  buildTasks: BuildTask[];
  reviewFindings: ReviewFinding[];
  deployChecklist: DeployCheckItem[];
}

// --- proj-001: Policy Admin Modernization ---

const policyAdminStages: ProjectStageData = {
  requirements: [
    { id: "pa-req-001", title: "Policy CRUD Operations", description: "Users must be able to create, read, update, and archive insurance policies through the admin interface.", priority: "must", status: "approved" },
    { id: "pa-req-002", title: "Role-Based Access Control", description: "System must support admin, underwriter, agent, and read-only roles with granular permissions.", priority: "must", status: "approved" },
    { id: "pa-req-003", title: "Real-Time Premium Calculator", description: "Premium calculations must update in real time as users modify coverage parameters.", priority: "must", status: "in-progress" },
    { id: "pa-req-004", title: "Audit Trail", description: "All policy modifications must be logged with user, timestamp, and before/after values.", priority: "must", status: "defined" },
    { id: "pa-req-005", title: "Bulk Import from Legacy System", description: "Support CSV and XML import of existing policies from the legacy mainframe system.", priority: "should", status: "defined" },
    { id: "pa-req-006", title: "Document Attachment Support", description: "Users should be able to attach supporting documents (PDF, images) to policy records.", priority: "should", status: "approved" },
    { id: "pa-req-007", title: "Mobile-Responsive Dashboard", description: "The agent dashboard should be usable on tablet devices in the field.", priority: "could", status: "defined" },
    { id: "pa-req-008", title: "Multi-Language Support", description: "Interface should support English and Spanish initially.", priority: "could", status: "defined" },
  ],
  planSections: [
    { id: "pa-plan-001", title: "Architecture Overview", content: "**Pattern:** Microservices with API Gateway\n**Frontend:** Next.js 15 with TypeScript, deployed on Vercel\n**Backend:** Node.js + Express microservices, deployed on AWS ECS\n**Database:** PostgreSQL (RDS) for transactional data, Redis for caching\n**Message Queue:** Amazon SQS for async operations\n**Auth:** AWS Cognito with SAML federation for enterprise SSO", status: "approved" },
    { id: "pa-plan-002", title: "API Design", content: "**Style:** RESTful with OpenAPI 3.0 specification\n**Versioning:** URL-based (v1, v2)\n**Key Endpoints:**\n- POST /api/v1/policies — Create policy\n- GET /api/v1/policies/:id — Get policy details\n- PUT /api/v1/policies/:id — Update policy\n- GET /api/v1/policies — List with pagination\n- POST /api/v1/policies/:id/calculate — Premium calculation\n- GET /api/v1/audit/:policyId — Audit trail", status: "approved" },
    { id: "pa-plan-003", title: "Database Schema", content: "**Core Tables:** policies, policy_versions, users, roles, permissions, audit_log, documents\n**Migrations:** Managed via Prisma with version-controlled migration files\n**Indexes:** Composite index on (tenant_id, policy_number), index on audit_log(created_at)\n**Estimated Size:** ~500K policies in year one, growing 20% annually", status: "approved" },
    { id: "pa-plan-004", title: "Deployment Strategy", content: "**Environment:** AWS us-east-1 (primary), us-west-2 (DR)\n**CI/CD:** GitHub Actions with staging and production pipelines\n**Containers:** Docker images built per service, stored in ECR\n**Infrastructure:** Terraform for IaC, managed in separate infra repo\n**Rollback:** Blue-green deployment with automatic rollback on health check failure", status: "draft" },
    { id: "pa-plan-005", title: "Impact Analysis", content: "**Systems Affected:**\n- Legacy mainframe (data migration source)\n- Agent Portal (will consume new APIs)\n- Billing System (premium calculation integration)\n- Reporting Data Warehouse (new event streams)\n\n**Risk Areas:**\n- Data migration accuracy from legacy format\n- Premium calculation parity with existing system\n- SSO integration with corporate Active Directory\n\n**Estimated Timeline:** 14 weeks (3 sprints build + 1 sprint testing + 1 sprint deployment)", status: "approved" },
  ],
  buildTasks: [
    { id: "pa-task-001", title: "Set up monorepo with Turborepo", assignee: "Sarah Chen", status: "done", progress: 100 },
    { id: "pa-task-002", title: "Implement authentication service", assignee: "Marcus Johnson", status: "done", progress: 100 },
    { id: "pa-task-003", title: "Build policy CRUD API endpoints", assignee: "Sarah Chen", status: "done", progress: 100 },
    { id: "pa-task-004", title: "Create React component library", assignee: "Priya Patel", status: "in-progress", progress: 72 },
    { id: "pa-task-005", title: "Build premium calculation engine", assignee: "Marcus Johnson", status: "in-progress", progress: 45 },
    { id: "pa-task-006", title: "Implement audit trail service", assignee: "David Kim", status: "in-progress", progress: 30 },
    { id: "pa-task-007", title: "Build agent dashboard pages", assignee: "Priya Patel", status: "todo", progress: 0 },
    { id: "pa-task-008", title: "Set up data migration scripts", assignee: "David Kim", status: "todo", progress: 0 },
    { id: "pa-task-009", title: "Integration testing suite", assignee: "Sarah Chen", status: "blocked", progress: 10 },
  ],
  reviewFindings: [
    { id: "pa-find-001", severity: "critical", title: "SQL Injection Vulnerability in Policy Search", description: "The policy search endpoint concatenates user input directly into SQL queries without parameterization.", file: "src/routes/policies.ts", line: 142, status: "open" },
    { id: "pa-find-002", severity: "high", title: "Missing Rate Limiting on Auth Endpoints", description: "Login and token refresh endpoints have no rate limiting, making them vulnerable to brute force attacks.", file: "src/middleware/auth.ts", line: 28, status: "open" },
    { id: "pa-find-003", severity: "high", title: "Sensitive Data in Error Responses", description: "Stack traces and internal paths are exposed in production error responses.", file: "src/middleware/errorHandler.ts", line: 15, status: "resolved" },
    { id: "pa-find-004", severity: "medium", title: "Missing Test Coverage for Premium Calculator", description: "Premium calculation module has only 34% coverage. Critical multi-policy discount paths are untested.", file: "src/services/premiumCalculator.ts", line: 1, status: "open" },
    { id: "pa-find-005", severity: "medium", title: "N+1 Query in Policy List Endpoint", description: "The policy list endpoint makes a separate query for each policy's documents. Use eager loading.", file: "src/routes/policies.ts", line: 67, status: "resolved" },
    { id: "pa-find-006", severity: "low", title: "Inconsistent Error Message Formats", description: "Some endpoints return { error: string } while others use { message: string, code: number }.", file: "src/utils/responses.ts", line: 1, status: "open" },
  ],
  deployChecklist: [
    { id: "pa-dep-001", category: "Infrastructure", item: "Docker images built and pushed to ECR", checked: true, notes: "All 4 service images tagged v1.2.0" },
    { id: "pa-dep-002", category: "Infrastructure", item: "Terraform plan reviewed and approved", checked: true, notes: "No destructive changes detected" },
    { id: "pa-dep-003", category: "Infrastructure", item: "Database migrations tested on staging", checked: true, notes: "3 migrations applied successfully" },
    { id: "pa-dep-004", category: "CI/CD", item: "All CI checks passing on release branch", checked: true, notes: "152 tests passing, 0 failures" },
    { id: "pa-dep-005", category: "CI/CD", item: "Staging deployment successful", checked: true, notes: "Deployed 2026-04-10, smoke tests passed" },
    { id: "pa-dep-006", category: "CI/CD", item: "Performance benchmarks within thresholds", checked: false, notes: "P95 latency on policy search is 450ms (threshold: 300ms)" },
    { id: "pa-dep-007", category: "Security", item: "No critical or high severity findings open", checked: false, notes: "2 high severity findings still open" },
    { id: "pa-dep-008", category: "Security", item: "Secrets rotated and stored in AWS Secrets Manager", checked: true, notes: "All 12 secrets rotated" },
    { id: "pa-dep-009", category: "Monitoring", item: "CloudWatch alarms configured", checked: true, notes: "CPU, memory, error rate, latency alarms set" },
    { id: "pa-dep-010", category: "Monitoring", item: "Health check endpoints responding", checked: true, notes: "/health returns 200 on all services" },
    { id: "pa-dep-011", category: "Communication", item: "Release notes drafted", checked: true, notes: "Shared in #engineering-releases" },
    { id: "pa-dep-012", category: "Communication", item: "Stakeholders notified of deployment window", checked: false, notes: "Pending approval from VP Engineering" },
  ],
};

// --- proj-002: Claims Processing API ---

const claimsProcessingStages: ProjectStageData = {
  requirements: [
    { id: "cp-req-001", title: "Claims Intake Endpoint", description: "Accept new insurance claims via REST API with real-time field validation and document upload.", priority: "must", status: "approved" },
    { id: "cp-req-002", title: "Automated Adjudication Rules", description: "Engine must evaluate claims against configurable rules and flag auto-approve, manual review, or deny.", priority: "must", status: "approved" },
    { id: "cp-req-003", title: "Fraud Detection Hooks", description: "Integrate with third-party fraud scoring API. Flag claims scoring above 0.7 for manual review.", priority: "must", status: "approved" },
    { id: "cp-req-004", title: "Real-Time Status Tracking", description: "Claimants and agents must see claim status updates in real time via WebSocket events.", priority: "must", status: "done" },
    { id: "cp-req-005", title: "SLA Dashboard", description: "Show claims processing time vs SLA targets with drill-down by claim type and adjuster.", priority: "should", status: "approved" },
    { id: "cp-req-006", title: "Batch Processing for Legacy Claims", description: "Accept bulk CSV uploads of legacy claims with validation and error reporting.", priority: "should", status: "in-progress" },
    { id: "cp-req-007", title: "Multi-Currency Support", description: "Support USD, CAD, and GBP for international claim submissions.", priority: "could", status: "defined" },
  ],
  planSections: [
    { id: "cp-plan-001", title: "Architecture Overview", content: "**Pattern:** Event-driven microservices\n**Intake API:** Python FastAPI with Pydantic validation\n**Adjudication Engine:** Python with configurable rule DSL\n**Event Bus:** AWS EventBridge for claim lifecycle events\n**Database:** PostgreSQL for claims data, DynamoDB for audit events\n**Queue:** SQS for async fraud scoring", status: "approved" },
    { id: "cp-plan-002", title: "API Design", content: "**Style:** RESTful with OpenAPI 3.1\n**Key Endpoints:**\n- POST /api/v1/claims — Submit new claim\n- GET /api/v1/claims/:id — Claim details with timeline\n- PUT /api/v1/claims/:id/adjudicate — Manual adjudication\n- GET /api/v1/claims/queue — Adjuster work queue\n- WebSocket /ws/claims/:id — Real-time status", status: "approved" },
    { id: "cp-plan-003", title: "Fraud Detection Integration", content: "**Provider:** Third-party fraud scoring API\n**Flow:** Claim submitted → async fraud score request → score returned via webhook → stored on claim record\n**Threshold:** Score ≥ 0.7 → manual review, Score ≥ 0.9 → auto-flag for investigation\n**Fallback:** If scoring service unavailable, route to manual review", status: "approved" },
    { id: "cp-plan-004", title: "Data Migration", content: "**Source:** Legacy claims database (Oracle)\n**Volume:** ~2.1M historical claims\n**Strategy:** Batch ETL with validation — migrate in 100K batches over 3 weekends\n**Mapping:** 47 legacy fields mapped to 32 new schema fields\n**Rollback:** Keep legacy system read-only for 90 days post-migration", status: "revised" },
  ],
  buildTasks: [
    { id: "cp-task-001", title: "Scaffold FastAPI project with Pydantic models", assignee: "Maria Garcia", status: "done", progress: 100 },
    { id: "cp-task-002", title: "Implement claims intake endpoint with validation", assignee: "Maria Garcia", status: "done", progress: 100 },
    { id: "cp-task-003", title: "Build adjudication rule engine", assignee: "David Park", status: "done", progress: 100 },
    { id: "cp-task-004", title: "Integrate fraud detection webhook", assignee: "Maria Garcia", status: "done", progress: 100 },
    { id: "cp-task-005", title: "Build real-time WebSocket status updates", assignee: "Lisa Wong", status: "done", progress: 100 },
    { id: "cp-task-006", title: "Build claims portal frontend", assignee: "Lisa Wong", status: "done", progress: 100 },
    { id: "cp-task-007", title: "Implement SLA dashboard metrics", assignee: "David Park", status: "in-progress", progress: 60 },
    { id: "cp-task-008", title: "Build batch CSV import processor", assignee: "Maria Garcia", status: "in-progress", progress: 35 },
    { id: "cp-task-009", title: "End-to-end integration tests", assignee: "David Park", status: "todo", progress: 0 },
  ],
  reviewFindings: [
    { id: "cp-find-001", severity: "critical", title: "Claim Amount Overflow Not Handled", description: "Claim amounts exceeding DECIMAL(12,2) max cause silent truncation. No validation on input range.", file: "src/models/claim.py", line: 45, status: "open" },
    { id: "cp-find-002", severity: "high", title: "Fraud Score Webhook Lacks Signature Verification", description: "Incoming fraud score webhooks are accepted without HMAC signature verification.", file: "src/webhooks/fraud_score.py", line: 12, status: "open" },
    { id: "cp-find-003", severity: "high", title: "Missing Idempotency on Claim Submission", description: "Duplicate claim submissions create separate records. Need idempotency key support.", file: "src/routes/claims.py", line: 88, status: "resolved" },
    { id: "cp-find-004", severity: "medium", title: "WebSocket Connection Leak", description: "WebSocket connections not properly cleaned up on client disconnect in status tracker.", file: "src/ws/status_tracker.py", line: 34, status: "open" },
    { id: "cp-find-005", severity: "medium", title: "Adjudication Rules Not Versioned", description: "Rule changes take effect immediately with no versioning or rollback capability.", file: "src/engine/rules.py", line: 1, status: "open" },
    { id: "cp-find-006", severity: "low", title: "Claim Status Enum Not Consistent", description: "Backend uses snake_case but frontend expects camelCase for status values.", file: "src/models/claim.py", line: 18, status: "resolved" },
    { id: "cp-find-007", severity: "info", title: "Add Claim Processing Time Metrics", description: "Add Prometheus metrics for claim processing latency by type and outcome.", file: "src/metrics.py", line: 1, status: "dismissed" },
  ],
  deployChecklist: [
    { id: "cp-dep-001", category: "Infrastructure", item: "EventBridge rules configured for claim events", checked: true, notes: "6 event rules deployed" },
    { id: "cp-dep-002", category: "Infrastructure", item: "DynamoDB tables provisioned with auto-scaling", checked: true, notes: "Read/write capacity: 100/50 units" },
    { id: "cp-dep-003", category: "Infrastructure", item: "SQS dead-letter queue configured", checked: true, notes: "Max receive count: 3, retention: 14 days" },
    { id: "cp-dep-004", category: "CI/CD", item: "All CI checks passing", checked: true, notes: "287 tests passing, 0 failures" },
    { id: "cp-dep-005", category: "CI/CD", item: "Staging smoke tests passed", checked: false, notes: "Fraud webhook test failing intermittently" },
    { id: "cp-dep-006", category: "Security", item: "No critical findings open", checked: false, notes: "1 critical finding (amount overflow)" },
    { id: "cp-dep-007", category: "Security", item: "API rate limiting configured", checked: true, notes: "100 req/min per client" },
    { id: "cp-dep-008", category: "Monitoring", item: "Claim processing latency alarms set", checked: true, notes: "P95 < 2s threshold" },
    { id: "cp-dep-009", category: "Monitoring", item: "Dead-letter queue depth alarm", checked: true, notes: "Alert if > 10 messages" },
    { id: "cp-dep-010", category: "Communication", item: "Runbook documented for on-call team", checked: false, notes: "Draft in progress" },
  ],
};

// --- proj-003: Agent Portal Redesign ---

const agentPortalStages: ProjectStageData = {
  requirements: [
    { id: "ap-req-001", title: "Mobile-First Responsive Layout", description: "All pages must work seamlessly on tablets (768px+) and phones (375px+) used by field agents.", priority: "must", status: "approved" },
    { id: "ap-req-002", title: "Quick Quote Generation", description: "Agents must generate an insurance quote in under 3 clicks from the dashboard.", priority: "must", status: "approved" },
    { id: "ap-req-003", title: "Offline Capability", description: "Core quote generation must work offline using service workers and sync when connectivity returns.", priority: "must", status: "in-progress" },
    { id: "ap-req-004", title: "Client Portfolio View", description: "Agents need a unified view of all policies for a given client with renewal status and alerts.", priority: "should", status: "approved" },
    { id: "ap-req-005", title: "Commission Tracker", description: "Show agents their commission earnings by policy type, month, and client.", priority: "should", status: "defined" },
    { id: "ap-req-006", title: "Accessibility (WCAG 2.1 AA)", description: "All interactive elements must meet WCAG 2.1 AA compliance.", priority: "must", status: "defined" },
  ],
  planSections: [
    { id: "ap-plan-001", title: "Architecture Overview", content: "**Pattern:** BFF (Backend for Frontend) with GraphQL\n**Frontend:** Next.js 15 with TypeScript, PWA-enabled\n**BFF:** Express + Apollo GraphQL server\n**Design System:** Custom Zinnia agent design system (shared-lib repo)\n**State:** React Query for server state, Zustand for client state\n**Offline:** Service Worker + IndexedDB for offline quote cache", status: "approved" },
    { id: "ap-plan-002", title: "Design System Strategy", content: "**Base:** Zinnia Agent Design System v2.1\n**Components:** DataTable, FormWizard, QuoteCard, PolicyTimeline, CommissionChart\n**Theme:** Light mode primary with dark mode support\n**Tokens:** Design tokens shared via CSS custom properties\n**Testing:** Storybook for visual regression testing", status: "approved" },
    { id: "ap-plan-003", title: "Quote Generation Flow", content: "**Steps:** 1) Select product type → 2) Enter client info → 3) Configure coverage → 4) View premium → 5) Generate quote PDF\n**Performance:** Target < 500ms for premium calculation on each step change\n**Caching:** Cache product configs locally, refresh every 24h\n**Fallback:** Offline mode uses last-synced product configs", status: "draft" },
  ],
  buildTasks: [
    { id: "ap-task-001", title: "Scaffold Next.js PWA with service worker", assignee: "Lisa Wong", status: "done", progress: 100 },
    { id: "ap-task-002", title: "Build BFF with GraphQL schema", assignee: "James Wilson", status: "done", progress: 100 },
    { id: "ap-task-003", title: "Implement design system components", assignee: "Lisa Wong", status: "in-progress", progress: 65 },
    { id: "ap-task-004", title: "Build mobile-first quote wizard", assignee: "Lisa Wong", status: "in-progress", progress: 40 },
    { id: "ap-task-005", title: "Implement offline quote caching", assignee: "James Wilson", status: "todo", progress: 0 },
    { id: "ap-task-006", title: "Build client portfolio dashboard", assignee: "Lisa Wong", status: "todo", progress: 0 },
    { id: "ap-task-007", title: "WCAG 2.1 AA accessibility audit", assignee: "James Wilson", status: "todo", progress: 0 },
  ],
  reviewFindings: [],
  deployChecklist: [
    { id: "ap-dep-001", category: "Infrastructure", item: "CDN configured for static assets", checked: false, notes: "CloudFront distribution pending" },
    { id: "ap-dep-002", category: "CI/CD", item: "Lighthouse CI thresholds set", checked: false, notes: "Performance > 90, Accessibility > 95" },
    { id: "ap-dep-003", category: "Security", item: "Content Security Policy headers configured", checked: false, notes: "Not started" },
    { id: "ap-dep-004", category: "Monitoring", item: "Real User Monitoring (RUM) configured", checked: false, notes: "Datadog RUM pending setup" },
  ],
};

// --- proj-004: Underwriting Rules Engine ---

const underwritingStages: ProjectStageData = {
  requirements: [
    { id: "uw-req-001", title: "Configurable Rule Sets", description: "Business users must configure underwriting rules via a web UI without code deployments.", priority: "must", status: "done" },
    { id: "uw-req-002", title: "Rule Versioning & Rollback", description: "All rule changes must be versioned with ability to rollback to any previous version.", priority: "must", status: "done" },
    { id: "uw-req-003", title: "Decision Audit Trail", description: "Every underwriting decision must log the rule version, input data, and decision outcome.", priority: "must", status: "done" },
    { id: "uw-req-004", title: "Override Workflow", description: "Underwriters must be able to override automated decisions with justification and manager approval.", priority: "must", status: "done" },
    { id: "uw-req-005", title: "Rule Simulation Mode", description: "Test new rules against historical data before activation to predict impact.", priority: "should", status: "done" },
    { id: "uw-req-006", title: "Performance SLA", description: "Rule evaluation must complete within 200ms for 99th percentile of requests.", priority: "must", status: "done" },
    { id: "uw-req-007", title: "External Data Integration", description: "Integrate with credit score, MVR, and CLUE report providers for data-enriched decisions.", priority: "should", status: "done" },
  ],
  planSections: [
    { id: "uw-plan-001", title: "Architecture Overview", content: "**Pattern:** Domain-driven design with CQRS\n**Rule Engine:** Custom DSL parsed at runtime, compiled to evaluation tree\n**API:** Go gRPC service for low-latency rule evaluation\n**UI:** React admin dashboard for rule management\n**Database:** PostgreSQL for rules/versions, ClickHouse for decision analytics\n**Cache:** Redis for hot rule sets", status: "approved" },
    { id: "uw-plan-002", title: "Rule DSL Design", content: "**Syntax:** Declarative JSON-based rule definitions\n**Operators:** eq, gt, lt, between, in, contains, regex\n**Combinators:** AND, OR, NOT with nesting\n**Actions:** approve, deny, refer, escalate\n**Variables:** Policy type, coverage amount, applicant age, credit score, loss history\n**Functions:** calculate_risk_score, lookup_territory_rate, check_moratorium", status: "approved" },
    { id: "uw-plan-003", title: "Performance Strategy", content: "**Caching:** Hot rule sets cached in Redis (TTL: 5min)\n**Compilation:** Rules compiled to evaluation tree on publish, not on each request\n**Batching:** Support batch evaluation for portfolio-level analysis\n**Monitoring:** P99 latency tracked per rule set with alerting on degradation", status: "approved" },
    { id: "uw-plan-004", title: "Simulation Framework", content: "**Input:** Historical decisions dataset (last 12 months)\n**Process:** Run new rules against historical inputs, compare outcomes\n**Output:** Impact report showing changed decisions, revenue impact, risk exposure delta\n**Guard:** Must run simulation before any rule can be promoted to production", status: "approved" },
  ],
  buildTasks: [
    { id: "uw-task-001", title: "Implement rule DSL parser and evaluator", assignee: "Alex Kumar", status: "done", progress: 100 },
    { id: "uw-task-002", title: "Build gRPC rule evaluation service", assignee: "Alex Kumar", status: "done", progress: 100 },
    { id: "uw-task-003", title: "Create rule management admin UI", assignee: "Priya Patel", status: "done", progress: 100 },
    { id: "uw-task-004", title: "Implement rule versioning system", assignee: "Alex Kumar", status: "done", progress: 100 },
    { id: "uw-task-005", title: "Build override workflow with approval chain", assignee: "Priya Patel", status: "done", progress: 100 },
    { id: "uw-task-006", title: "Build simulation framework", assignee: "Alex Kumar", status: "done", progress: 100 },
    { id: "uw-task-007", title: "Integrate external data providers", assignee: "Marcus Johnson", status: "done", progress: 100 },
    { id: "uw-task-008", title: "Performance optimization and load testing", assignee: "Alex Kumar", status: "done", progress: 100 },
    { id: "uw-task-009", title: "Decision analytics dashboard", assignee: "Priya Patel", status: "done", progress: 100 },
  ],
  reviewFindings: [
    { id: "uw-find-001", severity: "medium", title: "Rule Compilation Memory Spike", description: "Complex nested rules (>10 levels) cause temporary memory spikes during compilation. Add depth limit.", file: "pkg/compiler/tree.go", line: 89, status: "resolved" },
    { id: "uw-find-002", severity: "low", title: "Missing Pagination on Decision History", description: "Decision history endpoint returns all records without pagination for high-volume rule sets.", file: "pkg/api/decisions.go", line: 42, status: "resolved" },
    { id: "uw-find-003", severity: "info", title: "Add Circuit Breaker for External Data Providers", description: "External provider calls should use circuit breaker pattern to gracefully degrade.", file: "pkg/integrations/providers.go", line: 1, status: "resolved" },
  ],
  deployChecklist: [
    { id: "uw-dep-001", category: "Infrastructure", item: "gRPC service deployed to ECS with auto-scaling", checked: true, notes: "Min 3, max 12 instances" },
    { id: "uw-dep-002", category: "Infrastructure", item: "Redis cluster provisioned for rule caching", checked: true, notes: "3-node cluster, 6.8GB" },
    { id: "uw-dep-003", category: "Infrastructure", item: "ClickHouse cluster for decision analytics", checked: true, notes: "2-node cluster provisioned" },
    { id: "uw-dep-004", category: "CI/CD", item: "All CI checks passing", checked: true, notes: "412 tests, 0 failures" },
    { id: "uw-dep-005", category: "CI/CD", item: "Load test passed — P99 < 200ms", checked: true, notes: "P99: 142ms under 500 RPS" },
    { id: "uw-dep-006", category: "CI/CD", item: "Staging deployment verified", checked: true, notes: "All rule sets evaluated correctly" },
    { id: "uw-dep-007", category: "Security", item: "No open security findings", checked: true, notes: "All findings resolved" },
    { id: "uw-dep-008", category: "Security", item: "mTLS between services configured", checked: true, notes: "Certificates rotated" },
    { id: "uw-dep-009", category: "Monitoring", item: "Rule evaluation latency dashboards", checked: true, notes: "Grafana dashboards deployed" },
    { id: "uw-dep-010", category: "Monitoring", item: "Decision outcome anomaly detection", checked: true, notes: "Alert if approval rate deviates >5% from baseline" },
    { id: "uw-dep-011", category: "Communication", item: "Release notes and migration guide", checked: true, notes: "Shared with all underwriting teams" },
    { id: "uw-dep-012", category: "Communication", item: "Training sessions scheduled", checked: false, notes: "3 sessions planned for next week" },
  ],
};

// --- proj-005: Customer Notifications Service ---

const notificationsStages: ProjectStageData = {
  requirements: [
    { id: "cn-req-001", title: "Multi-Channel Delivery", description: "Send notifications via email, SMS, and push notifications from a single API.", priority: "must", status: "done" },
    { id: "cn-req-002", title: "Template Engine", description: "Support Handlebars templates with dynamic data binding for all notification types.", priority: "must", status: "done" },
    { id: "cn-req-003", title: "Delivery Tracking", description: "Track delivery status (sent, delivered, bounced, failed) for every notification.", priority: "must", status: "done" },
    { id: "cn-req-004", title: "User Preferences", description: "Users control which channels they receive notifications on and can opt out per category.", priority: "must", status: "done" },
    { id: "cn-req-005", title: "Rate Limiting per User", description: "Prevent notification fatigue by limiting to max 5 notifications per user per hour.", priority: "should", status: "done" },
    { id: "cn-req-006", title: "Scheduled Notifications", description: "Support scheduling notifications for future delivery with timezone awareness.", priority: "should", status: "done" },
  ],
  planSections: [
    { id: "cn-plan-001", title: "Architecture Overview", content: "**Pattern:** Event-driven with fan-out\n**API:** Node.js Express for notification submission\n**Channels:** SES (email), SNS (SMS), Firebase (push)\n**Queue:** SQS with per-channel queues\n**Database:** DynamoDB for delivery tracking, S3 for templates\n**Scheduler:** EventBridge Scheduler for future delivery", status: "approved" },
    { id: "cn-plan-002", title: "Template System", content: "**Engine:** Handlebars with custom helpers\n**Storage:** S3 with versioning\n**Languages:** en-US, es-MX (initial)\n**Preview:** Admin UI for template preview with sample data\n**Validation:** Templates validated on upload — missing variables flagged", status: "approved" },
  ],
  buildTasks: [
    { id: "cn-task-001", title: "Build notification API with channel routing", assignee: "Elena Rodriguez", status: "done", progress: 100 },
    { id: "cn-task-002", title: "Implement email channel (SES)", assignee: "Elena Rodriguez", status: "done", progress: 100 },
    { id: "cn-task-003", title: "Implement SMS channel (SNS)", assignee: "Marcus Johnson", status: "done", progress: 100 },
    { id: "cn-task-004", title: "Implement push notification channel (Firebase)", assignee: "Marcus Johnson", status: "done", progress: 100 },
    { id: "cn-task-005", title: "Build template engine with Handlebars", assignee: "Elena Rodriguez", status: "done", progress: 100 },
    { id: "cn-task-006", title: "Build delivery tracking and analytics", assignee: "Elena Rodriguez", status: "done", progress: 100 },
    { id: "cn-task-007", title: "Implement user preference management", assignee: "Marcus Johnson", status: "done", progress: 100 },
    { id: "cn-task-008", title: "Build scheduling system", assignee: "Elena Rodriguez", status: "done", progress: 100 },
  ],
  reviewFindings: [
    { id: "cn-find-001", severity: "medium", title: "Template Injection Risk", description: "Handlebars triple-stash ({{{}}}) used in some templates allows HTML injection. Audit all templates.", file: "src/templates/renderer.ts", line: 23, status: "resolved" },
    { id: "cn-find-002", severity: "low", title: "Missing Retry Backoff on Channel Failures", description: "Channel delivery retries use fixed interval. Should use exponential backoff.", file: "src/channels/base.ts", line: 45, status: "resolved" },
  ],
  deployChecklist: [
    { id: "cn-dep-001", category: "Infrastructure", item: "SQS queues provisioned per channel", checked: true, notes: "3 queues + 3 DLQs" },
    { id: "cn-dep-002", category: "Infrastructure", item: "SES domain verification complete", checked: true, notes: "DKIM and SPF configured" },
    { id: "cn-dep-003", category: "CI/CD", item: "All tests passing", checked: true, notes: "198 tests, 0 failures" },
    { id: "cn-dep-004", category: "CI/CD", item: "Staging validation complete", checked: true, notes: "All 3 channels tested" },
    { id: "cn-dep-005", category: "Security", item: "PII handling reviewed", checked: true, notes: "No PII stored in logs" },
    { id: "cn-dep-006", category: "Monitoring", item: "Delivery rate dashboards live", checked: true, notes: "Per-channel delivery rates tracked" },
    { id: "cn-dep-007", category: "Communication", item: "Integration guide published", checked: true, notes: "Available in internal docs" },
  ],
};

// --- proj-006: Document Intelligence Pipeline ---

const docIntelligenceStages: ProjectStageData = {
  requirements: [
    { id: "di-req-001", title: "Document Classification", description: "Automatically classify uploaded documents into categories: policy application, claim form, medical record, ID document.", priority: "must", status: "in-progress" },
    { id: "di-req-002", title: "Data Extraction", description: "Extract key-value pairs from classified documents (e.g., name, DOB, policy number, claim amount).", priority: "must", status: "in-progress" },
    { id: "di-req-003", title: "Multi-Format Support", description: "Support PDF, JPEG, PNG, TIFF, and HEIC formats. Handle scanned and digital documents.", priority: "must", status: "defined" },
    { id: "di-req-004", title: "Confidence Scoring", description: "Each extracted field must include a confidence score. Fields below 0.85 routed to human review.", priority: "must", status: "defined" },
    { id: "di-req-005", title: "Processing SLA", description: "Document classification within 5 seconds, full extraction within 30 seconds for standard documents.", priority: "should", status: "defined" },
    { id: "di-req-006", title: "Human-in-the-Loop Review", description: "Low-confidence extractions presented to human reviewers for correction, feeding back into model training.", priority: "should", status: "defined" },
    { id: "di-req-007", title: "Batch Processing API", description: "Support batch upload of up to 1000 documents per request for bulk processing scenarios.", priority: "could", status: "defined" },
  ],
  planSections: [
    { id: "di-plan-001", title: "Architecture Overview", content: "**Pattern:** ML pipeline with human-in-the-loop\n**Ingestion:** S3 + Lambda for document intake\n**Classification:** Custom CNN model served via SageMaker\n**Extraction:** Combination of AWS Textract and custom NER model\n**Review:** React web app for human review queue\n**Storage:** S3 for documents, PostgreSQL for metadata and extractions", status: "draft" },
  ],
  buildTasks: [
    { id: "di-task-001", title: "Set up ML pipeline infrastructure (SageMaker, S3)", assignee: "Raj Patel", status: "in-progress", progress: 25 },
    { id: "di-task-002", title: "Train document classification model", assignee: "Raj Patel", status: "todo", progress: 0 },
    { id: "di-task-003", title: "Implement document ingestion Lambda", assignee: "Elena Rodriguez", status: "todo", progress: 0 },
    { id: "di-task-004", title: "Build extraction pipeline with Textract", assignee: "Raj Patel", status: "todo", progress: 0 },
    { id: "di-task-005", title: "Build human review web interface", assignee: "Elena Rodriguez", status: "todo", progress: 0 },
  ],
  reviewFindings: [],
  deployChecklist: [
    { id: "di-dep-001", category: "Infrastructure", item: "SageMaker endpoint configured", checked: false, notes: "Pending model training completion" },
    { id: "di-dep-002", category: "Infrastructure", item: "S3 buckets with lifecycle policies", checked: false, notes: "Not started" },
    { id: "di-dep-003", category: "Security", item: "Document encryption at rest and in transit", checked: false, notes: "Required for medical records (HIPAA)" },
  ],
};

// --- Lookup map ---

const projectStageDataMap: Record<string, ProjectStageData> = {
  "proj-001": policyAdminStages,
  "proj-002": claimsProcessingStages,
  "proj-003": agentPortalStages,
  "proj-004": underwritingStages,
  "proj-005": notificationsStages,
  "proj-006": docIntelligenceStages,
};

export function getProjectStageData(projectId: string): ProjectStageData | undefined {
  const data = projectStageDataMap[projectId];
  if (!data) {
    console.warn(
      `[ZECT] No stage data found for project "${projectId}". ` +
      `Add an entry to projectStageDataMap in project-stages.ts.`
    );
  }
  return data;
}

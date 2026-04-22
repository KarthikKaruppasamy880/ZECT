import {
  RequirementItem,
  PlanSection,
  BuildTask,
  ReviewFinding,
  DeployCheckItem,
} from "@/types";

export const sampleRequirements: RequirementItem[] = [
  {
    id: "req-001",
    title: "Policy CRUD Operations",
    description:
      "Users must be able to create, read, update, and archive insurance policies through the admin interface.",
    priority: "must",
    status: "approved",
  },
  {
    id: "req-002",
    title: "Role-Based Access Control",
    description:
      "System must support admin, underwriter, agent, and read-only roles with granular permissions.",
    priority: "must",
    status: "approved",
  },
  {
    id: "req-003",
    title: "Real-Time Premium Calculator",
    description:
      "Premium calculations must update in real time as users modify coverage parameters.",
    priority: "must",
    status: "in-progress",
  },
  {
    id: "req-004",
    title: "Audit Trail",
    description:
      "All policy modifications must be logged with user, timestamp, and before/after values.",
    priority: "must",
    status: "defined",
  },
  {
    id: "req-005",
    title: "Bulk Import from Legacy System",
    description:
      "Support CSV and XML import of existing policies from the legacy mainframe system.",
    priority: "should",
    status: "defined",
  },
  {
    id: "req-006",
    title: "Document Attachment Support",
    description:
      "Users should be able to attach supporting documents (PDF, images) to policy records.",
    priority: "should",
    status: "approved",
  },
  {
    id: "req-007",
    title: "Mobile-Responsive Dashboard",
    description:
      "The agent dashboard should be usable on tablet devices in the field.",
    priority: "could",
    status: "defined",
  },
  {
    id: "req-008",
    title: "Multi-Language Support",
    description: "Interface should support English and Spanish initially.",
    priority: "could",
    status: "defined",
  },
];

export const samplePlanSections: PlanSection[] = [
  {
    id: "plan-001",
    title: "Architecture Overview",
    content: `**Pattern:** Microservices with API Gateway
**Frontend:** Next.js 15 with TypeScript, deployed on Vercel
**Backend:** Node.js + Express microservices, deployed on AWS ECS
**Database:** PostgreSQL (RDS) for transactional data, Redis for caching
**Message Queue:** Amazon SQS for async operations
**Auth:** AWS Cognito with SAML federation for enterprise SSO`,
    status: "approved",
  },
  {
    id: "plan-002",
    title: "API Design",
    content: `**Style:** RESTful with OpenAPI 3.0 specification
**Versioning:** URL-based (v1, v2)
**Key Endpoints:**
- POST /api/v1/policies — Create policy
- GET /api/v1/policies/:id — Get policy details
- PUT /api/v1/policies/:id — Update policy
- GET /api/v1/policies — List policies with pagination
- POST /api/v1/policies/:id/calculate — Run premium calculation
- GET /api/v1/audit/:policyId — Get audit trail`,
    status: "approved",
  },
  {
    id: "plan-003",
    title: "Database Schema",
    content: `**Core Tables:** policies, policy_versions, users, roles, permissions, audit_log, documents
**Migrations:** Managed via Prisma with version-controlled migration files
**Indexes:** Composite index on (tenant_id, policy_number), index on audit_log(created_at)
**Estimated Size:** ~500K policies in year one, growing 20% annually`,
    status: "approved",
  },
  {
    id: "plan-004",
    title: "Deployment Strategy",
    content: `**Environment:** AWS us-east-1 (primary), us-west-2 (DR)
**CI/CD:** GitHub Actions with staging and production pipelines
**Containers:** Docker images built per service, stored in ECR
**Infrastructure:** Terraform for IaC, managed in separate infra repo
**Rollback:** Blue-green deployment with automatic rollback on health check failure`,
    status: "draft",
  },
  {
    id: "plan-005",
    title: "Impact Analysis",
    content: `**Systems Affected:**
- Legacy mainframe (data migration source)
- Agent Portal (will consume new APIs)
- Billing System (premium calculation integration)
- Reporting Data Warehouse (new event streams)

**Risk Areas:**
- Data migration accuracy from legacy format
- Premium calculation parity with existing system
- SSO integration with corporate Active Directory

**Estimated Timeline:** 14 weeks (3 sprints build + 1 sprint testing + 1 sprint deployment)`,
    status: "approved",
  },
];

export const sampleBuildTasks: BuildTask[] = [
  {
    id: "task-001",
    title: "Set up monorepo with Turborepo",
    assignee: "Sarah Chen",
    status: "done",
    progress: 100,
  },
  {
    id: "task-002",
    title: "Implement authentication service",
    assignee: "Marcus Johnson",
    status: "done",
    progress: 100,
  },
  {
    id: "task-003",
    title: "Build policy CRUD API endpoints",
    assignee: "Sarah Chen",
    status: "done",
    progress: 100,
  },
  {
    id: "task-004",
    title: "Create React component library",
    assignee: "Priya Patel",
    status: "in-progress",
    progress: 72,
  },
  {
    id: "task-005",
    title: "Build premium calculation engine",
    assignee: "Marcus Johnson",
    status: "in-progress",
    progress: 45,
  },
  {
    id: "task-006",
    title: "Implement audit trail service",
    assignee: "David Kim",
    status: "in-progress",
    progress: 30,
  },
  {
    id: "task-007",
    title: "Build agent dashboard pages",
    assignee: "Priya Patel",
    status: "todo",
    progress: 0,
  },
  {
    id: "task-008",
    title: "Set up data migration scripts",
    assignee: "David Kim",
    status: "todo",
    progress: 0,
  },
  {
    id: "task-009",
    title: "Integration testing suite",
    assignee: "Sarah Chen",
    status: "blocked",
    progress: 10,
  },
];

export const sampleReviewFindings: ReviewFinding[] = [
  {
    id: "finding-001",
    severity: "critical",
    title: "SQL Injection Vulnerability in Policy Search",
    description:
      "The policy search endpoint concatenates user input directly into SQL queries without parameterization. This allows arbitrary SQL execution.",
    file: "src/routes/policies.ts",
    line: 142,
    status: "open",
  },
  {
    id: "finding-002",
    severity: "high",
    title: "Missing Rate Limiting on Auth Endpoints",
    description:
      "Login and token refresh endpoints have no rate limiting, making them vulnerable to brute force attacks.",
    file: "src/middleware/auth.ts",
    line: 28,
    status: "open",
  },
  {
    id: "finding-003",
    severity: "high",
    title: "Sensitive Data in Error Responses",
    description:
      "Stack traces and internal paths are exposed in production error responses. This leaks implementation details.",
    file: "src/middleware/errorHandler.ts",
    line: 15,
    status: "resolved",
  },
  {
    id: "finding-004",
    severity: "medium",
    title: "Missing Test Coverage for Premium Calculator",
    description:
      "The premium calculation module has only 34% test coverage. Critical business logic paths for multi-policy discounts are untested.",
    file: "src/services/premiumCalculator.ts",
    line: 1,
    status: "open",
  },
  {
    id: "finding-005",
    severity: "medium",
    title: "N+1 Query in Policy List Endpoint",
    description:
      "The policy list endpoint makes a separate database query for each policy's associated documents. Use eager loading instead.",
    file: "src/routes/policies.ts",
    line: 67,
    status: "resolved",
  },
  {
    id: "finding-006",
    severity: "low",
    title: "Inconsistent Error Message Formats",
    description:
      "Some endpoints return errors as { error: string } while others use { message: string, code: number }. Standardize the format.",
    file: "src/utils/responses.ts",
    line: 1,
    status: "open",
  },
  {
    id: "finding-007",
    severity: "info",
    title: "Consider Adding Request ID Headers",
    description:
      "Adding X-Request-ID headers would improve debugging and log correlation across microservices.",
    file: "src/middleware/requestId.ts",
    line: 1,
    status: "dismissed",
  },
];

export const sampleDeployChecklist: DeployCheckItem[] = [
  {
    id: "deploy-001",
    category: "Infrastructure",
    item: "Docker images built and pushed to ECR",
    checked: true,
    notes: "All 4 service images tagged v1.2.0",
  },
  {
    id: "deploy-002",
    category: "Infrastructure",
    item: "Terraform plan reviewed and approved",
    checked: true,
    notes: "No destructive changes detected",
  },
  {
    id: "deploy-003",
    category: "Infrastructure",
    item: "Database migrations tested on staging",
    checked: true,
    notes: "3 migrations applied successfully",
  },
  {
    id: "deploy-004",
    category: "Infrastructure",
    item: "SSL certificates valid and not expiring soon",
    checked: true,
    notes: "Expires 2027-03-15",
  },
  {
    id: "deploy-005",
    category: "CI/CD",
    item: "All CI checks passing on release branch",
    checked: true,
    notes: "152 tests passing, 0 failures",
  },
  {
    id: "deploy-006",
    category: "CI/CD",
    item: "Staging deployment successful",
    checked: true,
    notes: "Deployed 2026-04-10, smoke tests passed",
  },
  {
    id: "deploy-007",
    category: "CI/CD",
    item: "Performance benchmarks within thresholds",
    checked: false,
    notes: "P95 latency on policy search is 450ms (threshold: 300ms)",
  },
  {
    id: "deploy-008",
    category: "Security",
    item: "No critical or high severity findings open",
    checked: false,
    notes: "2 high severity findings still open",
  },
  {
    id: "deploy-009",
    category: "Security",
    item: "Secrets rotated and stored in AWS Secrets Manager",
    checked: true,
    notes: "All 12 secrets rotated on 2026-04-08",
  },
  {
    id: "deploy-010",
    category: "Monitoring",
    item: "CloudWatch alarms configured",
    checked: true,
    notes: "CPU, memory, error rate, latency alarms set",
  },
  {
    id: "deploy-011",
    category: "Monitoring",
    item: "Health check endpoints responding",
    checked: true,
    notes: "/health returns 200 on all services",
  },
  {
    id: "deploy-012",
    category: "Monitoring",
    item: "Rollback procedure documented and tested",
    checked: false,
    notes: "Documented but not tested in staging",
  },
  {
    id: "deploy-013",
    category: "Communication",
    item: "Release notes drafted",
    checked: true,
    notes: "Shared in #engineering-releases channel",
  },
  {
    id: "deploy-014",
    category: "Communication",
    item: "Stakeholders notified of deployment window",
    checked: false,
    notes: "Pending approval from VP Engineering",
  },
];

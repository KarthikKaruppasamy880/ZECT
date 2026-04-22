import {
  ProjectOrchestration,
  Repository,
  RepoDependency,
  OrchestrationEvent,
} from "@/types";

// --- Policy Admin Modernization (proj-001) ---

const policyAdminRepos: Repository[] = [
  {
    id: "repo-001a",
    name: "policy-admin-web",
    fullName: "zinnia/policy-admin-web",
    role: "frontend",
    language: "TypeScript",
    branch: "main",
    lastCommit: "2026-04-10T14:22:00Z",
    lastCommitMessage: "feat: add policy renewal wizard step 3",
    lastCommitAuthor: "sarah.chen",
    syncStatus: "synced",
    ciStatus: "passing",
    openPRs: 3,
    openIssues: 7,
    coverage: 82,
  },
  {
    id: "repo-001b",
    name: "policy-admin-api",
    fullName: "zinnia/policy-admin-api",
    role: "backend",
    language: "Java",
    branch: "main",
    lastCommit: "2026-04-10T11:45:00Z",
    lastCommitMessage: "fix: correct premium calculation for multi-policy discount",
    lastCommitAuthor: "james.wilson",
    syncStatus: "ahead",
    ciStatus: "passing",
    openPRs: 2,
    openIssues: 4,
    coverage: 76,
  },
  {
    id: "repo-001c",
    name: "policy-shared-types",
    fullName: "zinnia/policy-shared-types",
    role: "shared-lib",
    language: "TypeScript",
    branch: "main",
    lastCommit: "2026-04-09T16:00:00Z",
    lastCommitMessage: "chore: add PolicyRenewal interface and validation schemas",
    lastCommitAuthor: "sarah.chen",
    syncStatus: "synced",
    ciStatus: "passing",
    openPRs: 1,
    openIssues: 0,
    coverage: 95,
  },
  {
    id: "repo-001d",
    name: "policy-admin-infra",
    fullName: "zinnia/policy-admin-infra",
    role: "infra",
    language: "HCL",
    branch: "main",
    lastCommit: "2026-04-08T09:30:00Z",
    lastCommitMessage: "feat: add RDS read replica for reporting queries",
    lastCommitAuthor: "alex.kumar",
    syncStatus: "synced",
    ciStatus: "passing",
    openPRs: 0,
    openIssues: 2,
    coverage: 0,
  },
];

const policyAdminDeps: RepoDependency[] = [
  {
    id: "dep-001a",
    sourceRepoId: "repo-001a",
    targetRepoId: "repo-001b",
    type: "api-consumer",
    description: "Frontend consumes REST API endpoints for policy CRUD operations",
    status: "healthy",
  },
  {
    id: "dep-001b",
    sourceRepoId: "repo-001a",
    targetRepoId: "repo-001c",
    type: "imports",
    description: "Frontend imports shared TypeScript types and validation schemas",
    status: "healthy",
  },
  {
    id: "dep-001c",
    sourceRepoId: "repo-001b",
    targetRepoId: "repo-001c",
    type: "shared-schema",
    description: "API uses shared types for request/response serialization",
    status: "healthy",
  },
  {
    id: "dep-001d",
    sourceRepoId: "repo-001b",
    targetRepoId: "repo-001d",
    type: "deploy-depends",
    description: "API deployment requires infrastructure (RDS, ECS, ALB) to be provisioned",
    status: "healthy",
  },
];

const policyAdminEvents: OrchestrationEvent[] = [
  {
    id: "evt-001a",
    timestamp: "2026-04-10T14:30:00Z",
    type: "pr-merged",
    repoId: "repo-001a",
    message: "PR #47 merged: Policy renewal wizard — step 3 implementation",
    impactedRepoIds: [],
    severity: "info",
  },
  {
    id: "evt-001b",
    timestamp: "2026-04-10T11:50:00Z",
    type: "schema-change",
    repoId: "repo-001c",
    message: "PolicyRenewal interface updated — consumers may need regeneration",
    impactedRepoIds: ["repo-001a", "repo-001b"],
    severity: "warning",
  },
  {
    id: "evt-001c",
    timestamp: "2026-04-09T16:15:00Z",
    type: "deploy",
    repoId: "repo-001d",
    message: "Infrastructure updated: RDS read replica provisioned in us-east-1",
    impactedRepoIds: ["repo-001b"],
    severity: "info",
  },
];

// --- Claims Processing API (proj-002) ---

const claimsRepos: Repository[] = [
  {
    id: "repo-002a",
    name: "claims-intake-api",
    fullName: "zinnia/claims-intake-api",
    role: "backend",
    language: "Python",
    branch: "main",
    lastCommit: "2026-04-08T10:00:00Z",
    lastCommitMessage: "feat: add fraud detection webhook integration",
    lastCommitAuthor: "maria.garcia",
    syncStatus: "synced",
    ciStatus: "failing",
    openPRs: 4,
    openIssues: 12,
    coverage: 68,
  },
  {
    id: "repo-002b",
    name: "claims-adjudication-engine",
    fullName: "zinnia/claims-adjudication-engine",
    role: "backend",
    language: "Python",
    branch: "main",
    lastCommit: "2026-04-07T15:30:00Z",
    lastCommitMessage: "refactor: extract rule evaluation into separate module",
    lastCommitAuthor: "david.park",
    syncStatus: "behind",
    ciStatus: "passing",
    openPRs: 1,
    openIssues: 5,
    coverage: 74,
  },
  {
    id: "repo-002c",
    name: "claims-shared-models",
    fullName: "zinnia/claims-shared-models",
    role: "shared-lib",
    language: "Python",
    branch: "main",
    lastCommit: "2026-04-06T12:00:00Z",
    lastCommitMessage: "feat: add ClaimAdjudicationResult model with status enum",
    lastCommitAuthor: "maria.garcia",
    syncStatus: "synced",
    ciStatus: "passing",
    openPRs: 0,
    openIssues: 1,
    coverage: 91,
  },
  {
    id: "repo-002d",
    name: "claims-event-bus",
    fullName: "zinnia/claims-event-bus",
    role: "infra",
    language: "TypeScript",
    branch: "main",
    lastCommit: "2026-04-05T09:00:00Z",
    lastCommitMessage: "feat: add dead-letter queue for failed claim events",
    lastCommitAuthor: "alex.kumar",
    syncStatus: "synced",
    ciStatus: "passing",
    openPRs: 0,
    openIssues: 3,
    coverage: 0,
  },
  {
    id: "repo-002e",
    name: "claims-portal",
    fullName: "zinnia/claims-portal",
    role: "frontend",
    language: "TypeScript",
    branch: "main",
    lastCommit: "2026-04-08T13:20:00Z",
    lastCommitMessage: "fix: claim status badge not updating on real-time events",
    lastCommitAuthor: "lisa.wong",
    syncStatus: "diverged",
    ciStatus: "pending",
    openPRs: 5,
    openIssues: 9,
    coverage: 71,
  },
];

const claimsDeps: RepoDependency[] = [
  {
    id: "dep-002a",
    sourceRepoId: "repo-002e",
    targetRepoId: "repo-002a",
    type: "api-consumer",
    description: "Portal consumes claims intake API for submission and status tracking",
    status: "warning",
  },
  {
    id: "dep-002b",
    sourceRepoId: "repo-002a",
    targetRepoId: "repo-002b",
    type: "event-subscriber",
    description: "Intake API publishes events consumed by adjudication engine",
    status: "healthy",
  },
  {
    id: "dep-002c",
    sourceRepoId: "repo-002a",
    targetRepoId: "repo-002c",
    type: "shared-schema",
    description: "Both APIs share claim models and validation schemas",
    status: "healthy",
  },
  {
    id: "dep-002d",
    sourceRepoId: "repo-002b",
    targetRepoId: "repo-002c",
    type: "shared-schema",
    description: "Adjudication engine uses shared claim result models",
    status: "healthy",
  },
  {
    id: "dep-002e",
    sourceRepoId: "repo-002a",
    targetRepoId: "repo-002d",
    type: "deploy-depends",
    description: "Intake API requires event bus infrastructure for claim event publishing",
    status: "broken",
  },
  {
    id: "dep-002f",
    sourceRepoId: "repo-002e",
    targetRepoId: "repo-002d",
    type: "event-subscriber",
    description: "Portal subscribes to real-time claim status events via WebSocket",
    status: "warning",
  },
];

const claimsEvents: OrchestrationEvent[] = [
  {
    id: "evt-002a",
    timestamp: "2026-04-08T13:25:00Z",
    type: "ci-fail",
    repoId: "repo-002a",
    message: "CI failed: fraud detection webhook tests timing out on integration suite",
    impactedRepoIds: ["repo-002e"],
    severity: "critical",
  },
  {
    id: "evt-002b",
    timestamp: "2026-04-08T10:15:00Z",
    type: "breaking-change",
    repoId: "repo-002c",
    message: "Breaking: ClaimStatus enum values renamed — all consumers must update",
    impactedRepoIds: ["repo-002a", "repo-002b", "repo-002e"],
    severity: "critical",
  },
  {
    id: "evt-002c",
    timestamp: "2026-04-07T16:00:00Z",
    type: "pr-merged",
    repoId: "repo-002b",
    message: "PR #23 merged: Extract rule evaluation module for reuse",
    impactedRepoIds: [],
    severity: "info",
  },
  {
    id: "evt-002d",
    timestamp: "2026-04-06T12:30:00Z",
    type: "schema-change",
    repoId: "repo-002c",
    message: "New model ClaimAdjudicationResult added to shared models",
    impactedRepoIds: ["repo-002a", "repo-002b"],
    severity: "warning",
  },
  {
    id: "evt-002e",
    timestamp: "2026-04-05T09:30:00Z",
    type: "deploy",
    repoId: "repo-002d",
    message: "Dead-letter queue deployed for failed claim events in us-east-1",
    impactedRepoIds: ["repo-002a"],
    severity: "info",
  },
];

// --- Agent Portal Redesign (proj-003) ---

const agentPortalRepos: Repository[] = [
  {
    id: "repo-003a",
    name: "agent-portal-web",
    fullName: "zinnia/agent-portal-web",
    role: "frontend",
    language: "TypeScript",
    branch: "develop",
    lastCommit: "2026-04-12T15:30:00Z",
    lastCommitMessage: "feat: mobile-first quote generation form prototype",
    lastCommitAuthor: "lisa.wong",
    syncStatus: "ahead",
    ciStatus: "passing",
    openPRs: 2,
    openIssues: 4,
    coverage: 65,
  },
  {
    id: "repo-003b",
    name: "agent-portal-bff",
    fullName: "zinnia/agent-portal-bff",
    role: "backend",
    language: "TypeScript",
    branch: "develop",
    lastCommit: "2026-04-11T10:00:00Z",
    lastCommitMessage: "chore: scaffold BFF with Express and GraphQL",
    lastCommitAuthor: "james.wilson",
    syncStatus: "synced",
    ciStatus: "passing",
    openPRs: 1,
    openIssues: 2,
    coverage: 45,
  },
  {
    id: "repo-003c",
    name: "agent-design-system",
    fullName: "zinnia/agent-design-system",
    role: "shared-lib",
    language: "TypeScript",
    branch: "main",
    lastCommit: "2026-04-10T09:00:00Z",
    lastCommitMessage: "feat: add responsive DataTable and FormWizard components",
    lastCommitAuthor: "lisa.wong",
    syncStatus: "synced",
    ciStatus: "passing",
    openPRs: 1,
    openIssues: 0,
    coverage: 88,
  },
];

const agentPortalDeps: RepoDependency[] = [
  {
    id: "dep-003a",
    sourceRepoId: "repo-003a",
    targetRepoId: "repo-003b",
    type: "api-consumer",
    description: "Portal frontend queries BFF via GraphQL for agent data",
    status: "healthy",
  },
  {
    id: "dep-003b",
    sourceRepoId: "repo-003a",
    targetRepoId: "repo-003c",
    type: "imports",
    description: "Portal imports design system components (DataTable, FormWizard)",
    status: "healthy",
  },
];

const agentPortalEvents: OrchestrationEvent[] = [
  {
    id: "evt-003a",
    timestamp: "2026-04-12T15:35:00Z",
    type: "pr-merged",
    repoId: "repo-003a",
    message: "PR #12 merged: Mobile-first quote generation form prototype",
    impactedRepoIds: [],
    severity: "info",
  },
  {
    id: "evt-003b",
    timestamp: "2026-04-10T09:15:00Z",
    type: "sync",
    repoId: "repo-003c",
    message: "Design system v2.1 published — portal should update dependency",
    impactedRepoIds: ["repo-003a"],
    severity: "warning",
  },
];

// --- Combined orchestration data ---

export const projectOrchestrations: ProjectOrchestration[] = [
  {
    projectId: "proj-001",
    repositories: policyAdminRepos,
    dependencies: policyAdminDeps,
    events: policyAdminEvents,
  },
  {
    projectId: "proj-002",
    repositories: claimsRepos,
    dependencies: claimsDeps,
    events: claimsEvents,
  },
  {
    projectId: "proj-003",
    repositories: agentPortalRepos,
    dependencies: agentPortalDeps,
    events: agentPortalEvents,
  },
];

export function getOrchestration(projectId: string): ProjectOrchestration | undefined {
  return projectOrchestrations.find((o) => o.projectId === projectId);
}

// Global repo count for dashboard metrics
export function getGlobalRepoStats() {
  const allRepos = projectOrchestrations.flatMap((o) => o.repositories);
  const allDeps = projectOrchestrations.flatMap((o) => o.dependencies);
  const allEvents = projectOrchestrations.flatMap((o) => o.events);

  return {
    totalRepos: allRepos.length,
    reposByCiStatus: {
      passing: allRepos.filter((r) => r.ciStatus === "passing").length,
      failing: allRepos.filter((r) => r.ciStatus === "failing").length,
      pending: allRepos.filter((r) => r.ciStatus === "pending").length,
    },
    totalDependencies: allDeps.length,
    healthyDeps: allDeps.filter((d) => d.status === "healthy").length,
    warningDeps: allDeps.filter((d) => d.status === "warning").length,
    brokenDeps: allDeps.filter((d) => d.status === "broken").length,
    criticalEvents: allEvents.filter((e) => e.severity === "critical").length,
    recentEvents: allEvents
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 10),
  };
}

import { Metric, ActivityItem, DocItem } from "@/types";

export const dashboardMetrics: Metric[] = [
  {
    label: "Active Projects",
    value: 5,
    trend: "+2 this sprint",
    trendDirection: "up",
  },
  {
    label: "Token Savings",
    value: "34%",
    trend: "using context memory",
    trendDirection: "up",
  },
  {
    label: "Risk Alerts",
    value: 11,
    trend: "3 high priority",
    trendDirection: "down",
  },
  {
    label: "Deploy Ready",
    value: "2 of 5",
    trend: "active projects",
    trendDirection: "neutral",
  },
];

export const recentActivity: ActivityItem[] = [
  {
    id: "act-001",
    projectName: "Policy Admin Modernization",
    action: "Build Phase: Component library reached 72% completion",
    user: "Priya Patel",
    timestamp: "2026-04-13T14:30:00Z",
  },
  {
    id: "act-002",
    projectName: "Claims Processing API",
    action: "Review: Resolved SQL injection finding in policy search",
    user: "Sarah Chen",
    timestamp: "2026-04-13T11:15:00Z",
  },
  {
    id: "act-003",
    projectName: "Agent Portal Redesign",
    action: "Plan Mode: Architecture overview approved by tech lead",
    user: "Marcus Johnson",
    timestamp: "2026-04-12T16:45:00Z",
  },
  {
    id: "act-004",
    projectName: "Underwriting Rules Engine",
    action: "Deploy: Staging deployment successful, smoke tests passed",
    user: "David Kim",
    timestamp: "2026-04-12T10:00:00Z",
  },
  {
    id: "act-005",
    projectName: "Document Intelligence Pipeline",
    action: "Ask Mode: Initial requirements gathering started",
    user: "Elena Rodriguez",
    timestamp: "2026-04-11T09:00:00Z",
  },
  {
    id: "act-006",
    projectName: "Claims Processing API",
    action: "Review: 2 new medium-severity findings reported",
    user: "Automated Review",
    timestamp: "2026-04-10T15:30:00Z",
  },
];

export const docsItems: DocItem[] = [
  {
    id: "doc-001",
    title: "ZEF Getting Started Guide",
    category: "Onboarding",
    description:
      "How to set up the Zinnia Engineering Foundation in your project for context management and workflow guidance.",
    lastUpdated: "2026-04-10",
  },
  {
    id: "doc-002",
    title: "AI-Assisted Development Standards",
    category: "Standards",
    description:
      "Company-wide standards for using AI tools (Devin, Cursor, Windsurf, Claude Code, Codex) in engineering workflows.",
    lastUpdated: "2026-04-08",
  },
  {
    id: "doc-003",
    title: "Context Management Deep Dive",
    category: "Architecture",
    description:
      "How the pointer-based context system works, why it saves tokens, and how to maintain context files across sessions.",
    lastUpdated: "2026-04-05",
  },
  {
    id: "doc-004",
    title: "Deployment Readiness Checklist",
    category: "Operations",
    description:
      "Standard checklist for all Zinnia projects before production deployment: infrastructure, security, monitoring, communication.",
    lastUpdated: "2026-04-01",
  },
  {
    id: "doc-005",
    title: "Review Standards",
    category: "Quality",
    description:
      "How automated review integrates with human code review, severity classifications, and resolution SLAs.",
    lastUpdated: "2026-03-28",
  },
  {
    id: "doc-006",
    title: "Token Optimization Strategies",
    category: "Efficiency",
    description:
      "Techniques for reducing AI token usage: context pruning, domain-scoped loading, session handoff patterns.",
    lastUpdated: "2026-03-25",
  },
  {
    id: "doc-007",
    title: "Project Setup Playbook",
    category: "Playbooks",
    description:
      "Step-by-step playbook for initializing a new project with ZEF context structure, CI/CD, and deployment configuration.",
    lastUpdated: "2026-03-20",
  },
  {
    id: "doc-008",
    title: "Incident Response Playbook",
    category: "Playbooks",
    description:
      "How to respond to production incidents: triage, mitigation, root cause analysis, and post-mortem process.",
    lastUpdated: "2026-03-15",
  },
];

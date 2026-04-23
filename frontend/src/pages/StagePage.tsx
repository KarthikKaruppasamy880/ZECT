import { useParams, Link } from "react-router-dom";
import type { Stage } from "@/types";
import {
  MessageSquare,
  ClipboardList,
  Hammer,
  Search,
  Rocket,
  ArrowLeft,
  CheckCircle2,
  Circle,
} from "lucide-react";

interface StageInfo {
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
  deliverables: string[];
  gates: string[];
  activities: string[];
}

const stageMap: Record<Stage, StageInfo> = {
  ask: {
    title: "Ask Mode",
    description: "Gather requirements, define scope, and validate assumptions. This is where business needs become engineering requirements through structured discovery.",
    icon: MessageSquare,
    color: "bg-purple-500",
    deliverables: [
      "Requirements document with acceptance criteria",
      "Stakeholder sign-off on scope",
      "Risk assessment and mitigation plan",
      "Technology constraints and preferences",
      "Success metrics and KPIs",
    ],
    gates: [
      "All stakeholders reviewed requirements",
      "Scope is bounded and achievable",
      "Dependencies identified and documented",
      "Budget and timeline approved",
    ],
    activities: [
      "Stakeholder interviews and workshops",
      "Requirements elicitation and documentation",
      "Competitive analysis and market research",
      "Technical feasibility assessment",
      "Risk identification and scoring",
    ],
  },
  plan: {
    title: "Plan Mode",
    description: "Design architecture, plan sprints, and create implementation roadmap. Convert validated requirements into actionable engineering plans.",
    icon: ClipboardList,
    color: "bg-blue-500",
    deliverables: [
      "Architecture decision records (ADRs)",
      "API design and data model specifications",
      "Sprint plan with story points",
      "Infrastructure provisioning plan",
      "Testing strategy document",
    ],
    gates: [
      "Architecture approved by tech lead",
      "API contracts finalized",
      "Sprint capacity confirmed",
      "Infrastructure costs estimated",
    ],
    activities: [
      "System design and architecture review",
      "API and data model design",
      "Sprint planning and estimation",
      "Dependency mapping and sequencing",
      "Security and compliance review",
    ],
  },
  build: {
    title: "Build Phase",
    description: "Implement features, write code, and create automated tests. Execute the plan with continuous integration and incremental delivery.",
    icon: Hammer,
    color: "bg-amber-500",
    deliverables: [
      "Working feature code with unit tests",
      "CI pipeline green on all commits",
      "Integration tests passing",
      "Code documentation and inline comments",
      "Performance benchmarks baseline",
    ],
    gates: [
      "All unit tests passing (>80% coverage)",
      "CI pipeline green",
      "No critical security vulnerabilities",
      "Code follows established patterns",
    ],
    activities: [
      "Feature implementation in sprints",
      "Test-driven development (TDD)",
      "Code reviews and pair programming",
      "CI/CD pipeline maintenance",
      "Technical debt tracking and resolution",
    ],
  },
  review: {
    title: "Review",
    description: "Quality assurance, security audit, and performance review. Validate that the built solution meets all requirements and quality standards.",
    icon: Search,
    color: "bg-cyan-500",
    deliverables: [
      "Security audit report with findings",
      "Performance test results",
      "Accessibility compliance report",
      "Code quality metrics and trends",
      "Bug fix verification results",
    ],
    gates: [
      "No critical or high severity bugs",
      "Security audit passed",
      "Performance within SLA targets",
      "Accessibility standards met (WCAG 2.1)",
    ],
    activities: [
      "Security vulnerability scanning",
      "Performance and load testing",
      "Accessibility testing",
      "Code quality analysis (SonarQube/similar)",
      "User acceptance testing (UAT)",
    ],
  },
  deploy: {
    title: "Deployment",
    description: "Release to production, monitor health, and validate deployment. Safely roll out changes with observability and rollback capability.",
    icon: Rocket,
    color: "bg-green-500",
    deliverables: [
      "Production deployment runbook",
      "Monitoring dashboards and alerts",
      "Rollback procedure documentation",
      "Post-deployment verification checklist",
      "Release notes for stakeholders",
    ],
    gates: [
      "Staging environment verified",
      "Rollback procedure tested",
      "Monitoring and alerting configured",
      "Stakeholders notified of release",
    ],
    activities: [
      "Blue/green or canary deployment",
      "Health check verification",
      "Monitoring dashboard review",
      "Stakeholder communication",
      "Post-deployment retrospective",
    ],
  },
};

export default function StagePage() {
  const { stage } = useParams<{ stage: string }>();
  const info = stageMap[stage as Stage];

  if (!info) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Stage not found</p>
        <Link to="/" className="text-indigo-600 text-sm mt-2 inline-block">Back to Dashboard</Link>
      </div>
    );
  }

  const Icon = info.icon;

  return (
    <div>
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4">
        <ArrowLeft className="h-4 w-4" /> Back to Dashboard
      </Link>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center gap-4 mb-4">
          <div className={`rounded-xl p-3 ${info.color}`}>
            <Icon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">{info.title}</h1>
            <p className="text-sm text-slate-500 mt-0.5">{info.description}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Key Activities</h2>
          <ul className="space-y-2.5">
            {info.activities.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <Circle className="h-4 w-4 shrink-0 mt-0.5 text-slate-300" />
                {a}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Deliverables</h2>
          <ul className="space-y-2.5">
            {info.deliverables.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5 text-green-500" />
                {d}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Stage Gates</h2>
          <ul className="space-y-2.5">
            {info.gates.map((g, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <div className="w-4 h-4 shrink-0 mt-0.5 rounded border-2 border-slate-300" />
                {g}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

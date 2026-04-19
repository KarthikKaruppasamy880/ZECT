import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";

const architectureSections = [
  { title: "System Architecture", description: "High-level component diagram showing frontend, backend, APIs, databases, and external integrations", status: "Approved" },
  { title: "Data Model", description: "Entity-relationship design for policy, user, claim, and audit entities with versioning strategy", status: "Approved" },
  { title: "API Design", description: "RESTful API contract with OpenAPI spec, authentication flow, rate limiting, and error handling patterns", status: "In Review" },
  { title: "Infrastructure", description: "AWS deployment topology — ECS Fargate, RDS PostgreSQL, ElastiCache Redis, CloudFront CDN", status: "Draft" },
  { title: "Security Model", description: "Authentication (Azure AD SSO), authorization (RBAC), encryption (AES-256), and audit logging approach", status: "Approved" },
];

const impactAnalysis = [
  { system: "Legacy Policy Admin", impact: "Full replacement — data migration required", risk: "high", effort: "3 sprints" },
  { system: "Claims Processing API", impact: "API contract change — v2 endpoints needed", risk: "medium", effort: "1 sprint" },
  { system: "Rating Engine", impact: "No change — existing REST API compatible", risk: "low", effort: "0.5 sprint" },
  { system: "Salesforce CRM", impact: "New integration — webhook listeners needed", risk: "medium", effort: "2 sprints" },
  { system: "DocuSign", impact: "Upgrade SDK from v2 to v3 — breaking changes", risk: "high", effort: "1 sprint" },
];

const milestones = [
  { phase: "Phase 1: Foundation", duration: "Weeks 1-3", items: ["Project scaffolding", "Auth integration", "Core data models", "CI/CD pipeline"], status: "complete" },
  { phase: "Phase 2: Core Features", duration: "Weeks 4-8", items: ["Policy CRUD", "Search & filters", "Document management", "Audit trail"], status: "in-progress" },
  { phase: "Phase 3: Integrations", duration: "Weeks 9-11", items: ["Salesforce sync", "DocuSign workflow", "Rating engine connector", "Email notifications"], status: "planned" },
  { phase: "Phase 4: Polish & Launch", duration: "Weeks 12-14", items: ["Performance optimization", "Accessibility audit", "UAT", "Production deployment"], status: "planned" },
];

export default function PlanModePage() {
  return (
    <>
      <Header
        title="Plan Mode"
        subtitle="Transform requirements into a concrete engineering plan. Architecture decisions, impact analysis, implementation roadmap, and risk assessment — all before a single line of code."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Plan Mode" },
        ]}
      />

      {/* What is Plan Mode */}
      <Card className="mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-100 flex items-center justify-center shrink-0">
            <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">What Happens in Plan Mode</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Plan Mode takes approved requirements and produces a comprehensive engineering plan. The AI generates 
              architecture proposals, impact analysis reports, implementation roadmaps, and risk assessments. Every 
              technical decision is documented as an Architecture Decision Record (ADR). Human architects review and 
              approve all plans before implementation begins.
            </p>
          </div>
        </div>
      </Card>

      {/* How It Works */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[
          { step: "1", title: "Architecture Design", description: "AI proposes system architecture based on requirements, existing patterns, and Zinnia's tech standards. Includes component diagrams and data models.", color: "bg-indigo-50 border-indigo-200" },
          { step: "2", title: "Impact Analysis", description: "Automated analysis of how changes affect existing systems, APIs, databases, and downstream consumers. Risk-scored by severity.", color: "bg-violet-50 border-violet-200" },
          { step: "3", title: "Implementation Roadmap", description: "Phased delivery plan with milestones, sprint estimates, team assignments, and dependency ordering for parallel workstreams.", color: "bg-purple-50 border-purple-200" },
          { step: "4", title: "Architect Review", description: "Senior architects review proposals, challenge assumptions, approve or request changes. ADRs are finalized and stored for future reference.", color: "bg-fuchsia-50 border-fuchsia-200" },
        ].map((item) => (
          <Card key={item.step} className={`${item.color} border`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-full bg-white flex items-center justify-center text-sm font-bold text-slate-700 shadow-sm">
                {item.step}
              </span>
              <h4 className="text-sm font-semibold text-slate-800">{item.title}</h4>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>
          </Card>
        ))}
      </div>

      {/* Key Outputs */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Key Outputs</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {[
            { title: "Architecture Proposal", icon: "🏗️", description: "System design with component diagram, data model, API contracts, and infrastructure topology" },
            { title: "Impact Analysis Report", icon: "📊", description: "Risk-scored analysis of affected systems, breaking changes, migration needs, and effort estimates" },
            { title: "Implementation Roadmap", icon: "🗺️", description: "Phased delivery plan with milestones, sprint estimates, team assignments, and critical path" },
            { title: "ADR Documents", icon: "📝", description: "Architecture Decision Records documenting every major technical decision with rationale and trade-offs" },
          ].map((output) => (
            <div key={output.title} className="border border-slate-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{output.icon}</span>
                <h4 className="text-sm font-semibold text-slate-800">{output.title}</h4>
              </div>
              <p className="text-xs text-slate-600">{output.description}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Sample: Architecture Sections */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Sample: Architecture Sections</h3>
        <p className="text-xs text-slate-500 mb-4">Architecture proposal sections for Policy Admin Modernization</p>
        <div className="space-y-3">
          {architectureSections.map((section) => {
            const statusColor = section.status === "Approved" ? "bg-emerald-100 text-emerald-700" : section.status === "In Review" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600";
            return (
              <div key={section.title} className="border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 mb-1">{section.title}</h4>
                    <p className="text-sm text-slate-600">{section.description}</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${statusColor}`}>
                    {section.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Sample: Impact Analysis */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Sample: Impact Analysis Report</h3>
        <p className="text-xs text-slate-500 mb-4">Cross-system impact assessment with risk scoring and effort estimates</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase">Affected System</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase">Impact</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase">Risk</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase">Effort</th>
              </tr>
            </thead>
            <tbody>
              {impactAnalysis.map((item) => {
                const riskColor = item.risk === "high" ? "bg-red-100 text-red-700" : item.risk === "medium" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700";
                return (
                  <tr key={item.system} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4 font-medium text-slate-900">{item.system}</td>
                    <td className="py-3 px-4 text-slate-600">{item.impact}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${riskColor}`}>{item.risk}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-600">{item.effort}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Sample: Implementation Roadmap */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Sample: Implementation Roadmap</h3>
        <p className="text-xs text-slate-500 mb-4">Phased delivery plan with milestones and status tracking</p>
        <div className="space-y-4">
          {milestones.map((milestone) => {
            const statusColor = milestone.status === "complete" ? "border-l-emerald-500 bg-emerald-50" : milestone.status === "in-progress" ? "border-l-blue-500 bg-blue-50" : "border-l-slate-300 bg-slate-50";
            const statusLabel = milestone.status === "complete" ? "Complete" : milestone.status === "in-progress" ? "In Progress" : "Planned";
            const statusBadge = milestone.status === "complete" ? "bg-emerald-100 text-emerald-700" : milestone.status === "in-progress" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-500";
            return (
              <div key={milestone.phase} className={`border-l-4 ${statusColor} rounded-r-xl p-4`}>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900">{milestone.phase}</h4>
                    <span className="text-xs text-slate-500">{milestone.duration}</span>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusBadge}`}>{statusLabel}</span>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {milestone.items.map((item) => (
                    <span key={item} className="px-2.5 py-1 bg-white rounded-lg text-xs text-slate-600 border border-slate-200">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Gate Criteria */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-3">Gate Criteria to Proceed to Build Phase</h3>
        <p className="text-xs text-slate-500 mb-4">All criteria must be met before implementation can begin</p>
        <div className="space-y-2">
          {[
            "Architecture proposal reviewed and approved by senior architect",
            "All architecture sections have 'Approved' status",
            "Impact analysis completed for all affected systems",
            "No high-risk items without a documented mitigation plan",
            "Implementation roadmap agreed upon by engineering leads",
            "ADR documents finalized and stored in project repository",
            "Resource allocation confirmed by engineering management",
          ].map((criteria, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
              <div className="w-5 h-5 rounded-full border-2 border-emerald-400 bg-emerald-50 flex items-center justify-center shrink-0">
                <svg className="w-3 h-3 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <span className="text-sm text-slate-700">{criteria}</span>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

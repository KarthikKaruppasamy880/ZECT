import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";

const sampleFindings = [
  { id: "BUG-001", title: "SQL injection vulnerability in policy search endpoint", severity: "critical", category: "Security", repo: "policy-admin-api", file: "src/routes/policies.ts:142", status: "Fixed" },
  { id: "BUG-002", title: "Missing input validation on renewal date field", severity: "high", category: "Validation", repo: "policy-admin-web", file: "src/components/PolicyForm.tsx:88", status: "Fixed" },
  { id: "BUG-003", title: "Race condition in concurrent policy update handler", severity: "high", category: "Concurrency", repo: "policy-admin-api", file: "src/services/policyService.ts:205", status: "In Progress" },
  { id: "BUG-004", title: "Inconsistent error response format across API endpoints", severity: "medium", category: "Standards", repo: "policy-admin-api", file: "src/middleware/errorHandler.ts:15", status: "Open" },
  { id: "BUG-005", title: "Missing aria-label on policy status filter dropdown", severity: "low", category: "Accessibility", repo: "policy-admin-web", file: "src/components/PolicyFilters.tsx:34", status: "Open" },
  { id: "BUG-006", title: "Unused import of deprecated utility function", severity: "info", category: "Code Quality", repo: "policy-shared-types", file: "src/utils/legacy.ts:3", status: "Fixed" },
];

const reviewCategories = [
  { name: "Security", count: 3, critical: 1, high: 1, medium: 1, description: "SQL injection, XSS, CSRF, authentication bypass, secrets in code" },
  { name: "Code Quality", count: 8, critical: 0, high: 2, medium: 4, description: "Dead code, complexity, naming, duplication, missing error handling" },
  { name: "Performance", count: 2, critical: 0, high: 0, medium: 2, description: "N+1 queries, missing indexes, unbounded lists, memory leaks" },
  { name: "Accessibility", count: 4, critical: 0, high: 0, medium: 1, description: "Missing labels, color contrast, keyboard navigation, screen reader" },
  { name: "Standards", count: 5, critical: 0, high: 1, medium: 3, description: "Zinnia coding standards, API contract violations, naming conventions" },
  { name: "Testing", count: 3, critical: 0, high: 1, medium: 1, description: "Missing test coverage, brittle tests, untested edge cases" },
];

export default function ReviewPage() {
  return (
    <>
      <Header
        title="Review"
        subtitle="Automated code review powered by AI. Security scanning, code quality analysis, performance checks, accessibility audits, and standards compliance — all before human reviewers see the code."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Review" },
        ]}
      />

      {/* What is Review */}
      <Card className="mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center shrink-0">
            <svg className="w-6 h-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">What Happens in Review</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              The Review stage runs automated quality checks across all project repositories. The AI scans for security 
              vulnerabilities, code quality issues, performance problems, accessibility violations, and standards compliance 
              deviations. Findings are severity-classified and presented to the team. Critical and high findings must be 
              resolved before deployment. This stage ensures no code reaches production without thorough automated review.
            </p>
          </div>
        </div>
      </Card>

      {/* How It Works */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[
          { step: "1", title: "Automated Scanning", description: "AI scans all repositories for security vulnerabilities, code smells, performance anti-patterns, and accessibility issues.", color: "bg-amber-50 border-amber-200" },
          { step: "2", title: "Severity Classification", description: "Each finding is classified as Critical, High, Medium, Low, or Info — with specific file locations and suggested fixes.", color: "bg-orange-50 border-orange-200" },
          { step: "3", title: "Cross-Repo Analysis", description: "Reviews span all project repos — checking API contract compatibility, shared type usage, and dependency health.", color: "bg-red-50 border-red-200" },
          { step: "4", title: "Resolution Tracking", description: "Team resolves findings, marks them as fixed, and the AI re-validates. All Critical/High must be resolved before deployment.", color: "bg-rose-50 border-rose-200" },
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

      {/* Review Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
        <Card className="text-center">
          <div className="text-2xl font-bold text-slate-900">25</div>
          <div className="text-xs text-slate-500 mt-1">Total Findings</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-red-600">1</div>
          <div className="text-xs text-slate-500 mt-1">Critical</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-orange-600">4</div>
          <div className="text-xs text-slate-500 mt-1">High</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-amber-600">11</div>
          <div className="text-xs text-slate-500 mt-1">Medium</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-emerald-600">18</div>
          <div className="text-xs text-slate-500 mt-1">Resolved</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-bold text-blue-600">72%</div>
          <div className="text-xs text-slate-500 mt-1">Resolution Rate</div>
        </Card>
      </div>

      {/* Review Categories */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Review Categories</h3>
        <p className="text-xs text-slate-500 mb-4">Findings grouped by review category with severity breakdown</p>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {reviewCategories.map((cat) => (
            <div key={cat.name} className="border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-slate-900">{cat.name}</h4>
                <span className="text-lg font-bold text-slate-700">{cat.count}</span>
              </div>
              <p className="text-xs text-slate-500 mb-3">{cat.description}</p>
              <div className="flex items-center gap-2">
                {cat.critical > 0 && <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">{cat.critical} critical</span>}
                {cat.high > 0 && <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700">{cat.high} high</span>}
                {cat.medium > 0 && <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">{cat.medium} medium</span>}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Sample: Findings */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Sample: Review Findings</h3>
        <p className="text-xs text-slate-500 mb-4">Individual findings with severity, file location, and resolution status</p>
        <div className="space-y-3">
          {sampleFindings.map((finding) => {
            const severityColor = finding.severity === "critical" ? "bg-red-100 text-red-700 border-l-red-500" : finding.severity === "high" ? "bg-orange-50 text-orange-700 border-l-orange-400" : finding.severity === "medium" ? "bg-amber-50 text-amber-700 border-l-amber-400" : finding.severity === "low" ? "bg-blue-50 text-blue-700 border-l-blue-400" : "bg-slate-50 text-slate-600 border-l-slate-300";
            const sevBadge = finding.severity === "critical" ? "bg-red-100 text-red-700" : finding.severity === "high" ? "bg-orange-100 text-orange-700" : finding.severity === "medium" ? "bg-amber-100 text-amber-700" : finding.severity === "low" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-500";
            const statusColor = finding.status === "Fixed" ? "bg-emerald-100 text-emerald-700" : finding.status === "In Progress" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600";
            return (
              <div key={finding.id} className={`border-l-4 ${severityColor} border border-slate-200 rounded-r-xl p-4`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-mono text-slate-400">{finding.id}</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${sevBadge}`}>{finding.severity.toUpperCase()}</span>
                      <span className="px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-600">{finding.category}</span>
                    </div>
                    <p className="text-sm font-medium text-slate-900 mb-1">{finding.title}</p>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span className="font-mono">{finding.repo}</span>
                      <span className="font-mono text-slate-400">{finding.file}</span>
                    </div>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${statusColor}`}>
                    {finding.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Gate Criteria */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-3">Gate Criteria to Proceed to Deployment</h3>
        <p className="text-xs text-slate-500 mb-4">All criteria must be met before the project can advance to deployment readiness</p>
        <div className="space-y-2">
          {[
            "All Critical severity findings resolved and verified",
            "All High severity findings resolved or have approved mitigation plan",
            "Security scan passes with no known vulnerabilities",
            "Cross-repo API contract validation passes",
            "Code review approved by at least 2 senior engineers",
            "Test coverage maintains or exceeds minimum threshold",
            "Performance regression tests pass within acceptable limits",
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

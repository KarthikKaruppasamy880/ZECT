import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";

const sampleTasks = [
  { id: "TASK-001", title: "Set up Next.js project with TypeScript", assignee: "AI + Sarah Chen", status: "done", pr: "PR #12", tests: "14/14 passing" },
  { id: "TASK-002", title: "Implement Azure AD SSO authentication", assignee: "AI + James Wilson", status: "done", pr: "PR #15", tests: "8/8 passing" },
  { id: "TASK-003", title: "Build policy CRUD API endpoints", assignee: "AI + Maria Garcia", status: "in-progress", pr: "PR #23 (draft)", tests: "11/15 passing" },
  { id: "TASK-004", title: "Create policy search with Elasticsearch", assignee: "AI + David Park", status: "in-progress", pr: "—", tests: "Not started" },
  { id: "TASK-005", title: "Build document upload & versioning", assignee: "AI + Alex Kumar", status: "blocked", pr: "—", tests: "Not started" },
  { id: "TASK-006", title: "Implement audit trail logging", assignee: "AI + Sarah Chen", status: "pending", pr: "—", tests: "Not started" },
];

const codeMetrics = [
  { label: "Lines Generated", value: "12,450", change: "+1,230 today", color: "text-slate-900" },
  { label: "Test Coverage", value: "82%", change: "+3% this week", color: "text-emerald-600" },
  { label: "PRs Created", value: "23", change: "4 open, 19 merged", color: "text-blue-600" },
  { label: "Token Savings", value: "38%", change: "vs. manual coding", color: "text-violet-600" },
  { label: "Build Status", value: "Passing", change: "Last: 2 min ago", color: "text-emerald-600" },
  { label: "Linting Issues", value: "3", change: "0 errors, 3 warnings", color: "text-amber-600" },
];

export default function BuildPhasePage() {
  return (
    <>
      <Header
        title="Build Phase"
        subtitle="AI-assisted code generation with human oversight. Every PR is reviewed, every test is tracked, and every build is monitored. Code is generated in manageable chunks with continuous integration."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Build Phase" },
        ]}
      />

      {/* What is Build Phase */}
      <Card className="mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-100 flex items-center justify-center shrink-0">
            <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">What Happens in Build Phase</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              The Build Phase is where the approved plan becomes code. AI generates implementation in small, reviewable chunks — 
              each tied to a specific task from the roadmap. Every piece of generated code includes tests, follows Zinnia&apos;s 
              coding standards, and goes through CI/CD before human review. The AI tracks progress against the plan, flags 
              deviations, and surfaces blockers early.
            </p>
          </div>
        </div>
      </Card>

      {/* How It Works */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[
          { step: "1", title: "Task Decomposition", description: "Roadmap milestones are broken into small, implementable tasks. Each task maps to a single PR with clear scope and acceptance criteria.", color: "bg-emerald-50 border-emerald-200" },
          { step: "2", title: "AI Code Generation", description: "The AI generates code following Zinnia standards — TypeScript, proper error handling, test coverage, accessibility, and documentation.", color: "bg-teal-50 border-teal-200" },
          { step: "3", title: "Automated Validation", description: "Every generated PR runs through CI: linting, type checking, unit tests, integration tests, build verification, and security scanning.", color: "bg-cyan-50 border-cyan-200" },
          { step: "4", title: "Human Code Review", description: "Engineers review AI-generated PRs just like any other code. Comments, change requests, and approvals follow the standard workflow.", color: "bg-sky-50 border-sky-200" },
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

      {/* Code Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
        {codeMetrics.map((metric) => (
          <Card key={metric.label} className="text-center">
            <div className={`text-2xl font-bold ${metric.color}`}>{metric.value}</div>
            <div className="text-xs text-slate-500 mt-1">{metric.label}</div>
            <div className="text-xs text-slate-400 mt-0.5">{metric.change}</div>
          </Card>
        ))}
      </div>

      {/* Sample: Task Tracker */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Sample: Task Tracker</h3>
        <p className="text-xs text-slate-500 mb-4">Real-time progress tracking for implementation tasks with PR and test status</p>
        <div className="space-y-3">
          {sampleTasks.map((task) => {
            const statusColor = task.status === "done" ? "bg-emerald-100 text-emerald-700" : task.status === "in-progress" ? "bg-blue-100 text-blue-700" : task.status === "blocked" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-500";
            const statusLabel = task.status === "done" ? "Done" : task.status === "in-progress" ? "In Progress" : task.status === "blocked" ? "Blocked" : "Pending";
            const borderColor = task.status === "done" ? "border-l-emerald-400" : task.status === "in-progress" ? "border-l-blue-400" : task.status === "blocked" ? "border-l-red-400" : "border-l-slate-300";
            return (
              <div key={task.id} className={`border-l-4 ${borderColor} bg-white border border-slate-200 rounded-r-xl p-4`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-slate-400">{task.id}</span>
                      <span className="font-medium text-slate-900 text-sm">{task.title}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
                      <span>Assignee: <span className="text-slate-700">{task.assignee}</span></span>
                      <span>PR: <span className="text-slate-700">{task.pr}</span></span>
                      <span>Tests: <span className="text-slate-700">{task.tests}</span></span>
                    </div>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${statusColor}`}>
                    {statusLabel}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Multi-Repo Build Status */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Multi-Repo Build Status</h3>
        <p className="text-xs text-slate-500 mb-4">Cross-repository CI/CD health for the project</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { repo: "policy-admin-web", branch: "main", ci: "passing", lastBuild: "2 min ago", coverage: "82%" },
            { repo: "policy-admin-api", branch: "main", ci: "passing", lastBuild: "5 min ago", coverage: "76%" },
            { repo: "policy-shared-types", branch: "main", ci: "passing", lastBuild: "1 hr ago", coverage: "95%" },
            { repo: "policy-admin-infra", branch: "main", ci: "passing", lastBuild: "3 hr ago", coverage: "N/A" },
          ].map((repo) => (
            <div key={repo.repo} className="border border-slate-200 rounded-xl p-3 flex items-center justify-between">
              <div>
                <span className="font-mono text-sm font-medium text-slate-900">{repo.repo}</span>
                <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                  <span>{repo.branch}</span>
                  <span>|</span>
                  <span>Coverage: {repo.coverage}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">{repo.lastBuild}</span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Gate Criteria */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-3">Gate Criteria to Proceed to Review</h3>
        <p className="text-xs text-slate-500 mb-4">All criteria must be met before the project advances to automated review</p>
        <div className="space-y-2">
          {[
            "All Must-Have tasks completed and merged to main branch",
            "Test coverage meets minimum threshold (80% for new code)",
            "CI/CD pipeline passing on all project repositories",
            "No critical or high-severity linting/type errors",
            "All open PRs either merged or explicitly deferred to next phase",
            "Cross-repo dependency contracts validated and passing",
            "Performance benchmarks within acceptable range",
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

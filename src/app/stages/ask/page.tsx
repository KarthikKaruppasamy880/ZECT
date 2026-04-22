import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";

const sampleRequirements = [
  { id: "REQ-001", title: "User Authentication", priority: "must", status: "Approved", description: "SSO integration with Azure AD for all internal users" },
  { id: "REQ-002", title: "Policy Search", priority: "must", status: "In Progress", description: "Full-text search across policy documents with filters" },
  { id: "REQ-003", title: "Audit Trail", priority: "should", status: "Defined", description: "Track all user actions for compliance reporting" },
  { id: "REQ-004", title: "Dark Mode", priority: "could", status: "Defined", description: "Theme toggle for user preference" },
];

const sampleQuestions = [
  { question: "What systems does this replace?", answer: "Legacy Policy Admin (Java/Struts) and the internal spreadsheet tracker", source: "Product Owner" },
  { question: "What are the compliance requirements?", answer: "SOC 2 Type II, data encryption at rest and in transit, 90-day audit log retention", source: "Security Team" },
  { question: "Expected user volume?", answer: "~200 internal users, peak usage during renewal season (Q4)", source: "Business Analyst" },
  { question: "Integration points?", answer: "Salesforce CRM, DocuSign, internal rating engine API, claims system", source: "Architect" },
];

export default function AskModePage() {
  return (
    <>
      <Header
        title="Ask Mode"
        subtitle="The foundation of every project. Gather requirements, ask clarifying questions, identify constraints, and build shared understanding before any code is written."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Ask Mode" },
        ]}
      />

      {/* What is Ask Mode */}
      <Card className="mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center shrink-0">
            <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">What Happens in Ask Mode</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Ask Mode is where every project begins. The AI assistant works with the team to understand business goals, 
              gather functional requirements, identify technical constraints, and surface dependencies. No code is written
              at this stage — the focus is entirely on building shared understanding between stakeholders and the engineering team.
            </p>
          </div>
        </div>
      </Card>

      {/* How It Works */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[
          { step: "1", title: "Input Context", description: "Product briefs, user stories, Jira tickets, Slack threads, and stakeholder conversations are provided as input.", color: "bg-blue-50 border-blue-200" },
          { step: "2", title: "AI Clarification", description: "The AI identifies gaps, asks clarifying questions, and flags ambiguous requirements that need human input.", color: "bg-indigo-50 border-indigo-200" },
          { step: "3", title: "Requirement Extraction", description: "Structured requirements are extracted with MoSCoW priority (Must/Should/Could/Won't) and status tracking.", color: "bg-violet-50 border-violet-200" },
          { step: "4", title: "Human Approval", description: "All requirements are reviewed and approved by the team before moving to Plan Mode. Nothing proceeds without human sign-off.", color: "bg-purple-50 border-purple-200" },
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { title: "Requirement Summary", icon: "📋", description: "Structured list of all requirements with priority, status, and acceptance criteria", count: "15-40 items typical" },
            { title: "Clarification Q&A Log", icon: "💬", description: "Questions asked by AI, answers from stakeholders, and decisions made during discovery", count: "10-25 questions typical" },
            { title: "Constraint & Dependency Map", icon: "🔗", description: "Technical constraints, compliance requirements, integration points, and external dependencies", count: "5-15 constraints typical" },
          ].map((output) => (
            <div key={output.title} className="border border-slate-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{output.icon}</span>
                <h4 className="text-sm font-semibold text-slate-800">{output.title}</h4>
              </div>
              <p className="text-xs text-slate-600 mb-2">{output.description}</p>
              <span className="text-xs text-slate-400">{output.count}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Sample: Requirement Summary */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Sample: Requirement Summary</h3>
        <p className="text-xs text-slate-500 mb-4">Example output from Ask Mode for the Policy Admin Modernization project</p>
        <div className="space-y-3">
          {sampleRequirements.map((req) => {
            const priorityColor = req.priority === "must" ? "bg-red-100 text-red-700" : req.priority === "should" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700";
            const statusColor = req.status === "Approved" ? "bg-emerald-100 text-emerald-700" : req.status === "In Progress" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600";
            return (
              <div key={req.id} className="border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-slate-400">{req.id}</span>
                      <span className="font-medium text-slate-900 text-sm">{req.title}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${priorityColor}`}>
                        {req.priority.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600">{req.description}</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${statusColor}`}>
                    {req.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Sample: Clarification Q&A */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Sample: Clarification Q&A Log</h3>
        <p className="text-xs text-slate-500 mb-4">AI-generated questions with stakeholder answers captured during discovery</p>
        <div className="space-y-3">
          {sampleQuestions.map((q, i) => (
            <div key={i} className="border border-slate-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-blue-700">Q</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-900 mb-1">{q.question}</p>
                  <p className="text-sm text-slate-600 mb-1">{q.answer}</p>
                  <span className="text-xs text-slate-400">Source: {q.source}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Gate Criteria */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-3">Gate Criteria to Proceed to Plan Mode</h3>
        <p className="text-xs text-slate-500 mb-4">All criteria must be met before the project can advance to the next stage</p>
        <div className="space-y-2">
          {[
            "All Must-Have requirements are defined and approved by product owner",
            "No open clarification questions remain unanswered",
            "Technical constraints and compliance requirements are documented",
            "Integration points and external dependencies are identified",
            "Stakeholder sign-off recorded with timestamp",
            "Risk assessment completed for high-priority requirements",
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

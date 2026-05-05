import { useState } from "react";
import {
  FileText,
  BookOpen,
  GitBranch,
  Shield,
  Zap,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Terminal,
  Database,
  Layers,
  Users,
} from "lucide-react";

interface DocSection {
  title: string;
  description: string;
  icon: typeof BookOpen;
  color: string;
  url?: string;
  content: { heading: string; body: string }[];
}

const resources: DocSection[] = [
  {
    title: "Getting Started",
    description: "Quick start guide for new team members — project setup, tool configuration, and workflow walkthrough.",
    icon: Zap,
    color: "bg-amber-100 text-amber-600",
    content: [
      { heading: "Prerequisites", body: "Node.js 18+, Python 3.11+, PostgreSQL 16, and Git installed on your machine. Docker Desktop is optional but recommended for one-command deployment." },
      { heading: "Clone & Install", body: "git clone https://github.com/KarthikKaruppasamy880/ZECT.git\ncd ZECT\n\n# Frontend\ncd frontend && npm install && cd ..\n\n# Backend\ncd backend && pip install -r requirements.txt && cd .." },
      { heading: "Configure Environment", body: "Copy backend/.env.example to backend/.env and set:\n\u2022 DATABASE_URL \u2014 your PostgreSQL connection string\n\u2022 OPENAI_API_KEY \u2014 for AI features (Ask, Plan, Build, Review)\n\u2022 GITHUB_TOKEN \u2014 for repo analysis and code review\n\nThe frontend reads VITE_API_URL from frontend/.env (defaults to http://localhost:8000)." },
      { heading: "Run the Application", body: "# Start backend\ncd backend && uvicorn app.main:app --reload --port 8000\n\n# Start frontend (new terminal)\ncd frontend && npm run dev\n\nOpen http://localhost:5173 in your browser." },
      { heading: "Docker Deployment", body: "docker compose up --build\n\nThis starts the frontend, backend, and PostgreSQL database. Access the app at http://localhost:5173. The Docker setup works for all users \u2014 just configure your .env file with your own API keys." },
    ],
  },
  {
    title: "ZEF \u2014 Zinnia Engineering Foundation",
    description: "Tool-neutral engineering foundation for AI-assisted development. Includes playbooks, skills, templates, and adapter guides.",
    icon: BookOpen,
    color: "bg-indigo-100 text-indigo-600",
    url: "https://github.com/KarthikKaruppasamy880/ZEF",
    content: [
      { heading: "What is ZEF?", body: "ZEF (Zinnia Engineering Foundation) is the tool-neutral layer that powers ZECT's AI capabilities. It defines playbooks, skills, and adapter interfaces that work with any LLM provider \u2014 OpenAI, Anthropic, local models via Ollama, or OpenRouter." },
      { heading: "Playbooks", body: "Pre-built workflow templates for common engineering tasks: code review, migration planning, test generation, documentation, and deployment checklists. Each playbook is a structured prompt chain that guides the AI through multi-step processes." },
      { heading: "Skills & Templates", body: "Reusable AI skill templates stored in the Skill Library. Skills can be global (available to all projects) or scoped to specific repositories. Use Auto-Detect to analyze your code and discover patterns worth saving as skills." },
      { heading: "Adapter Architecture", body: "ZEF uses an adapter pattern so you can swap LLM providers without changing application code. Supported providers: OpenAI, Anthropic Claude, Google Gemini, OpenRouter (100+ models), and local Ollama models." },
    ],
  },
  {
    title: "ZECT Architecture Guide",
    description: "Technical architecture documentation for the Engineering Delivery Control Tower, including API specs and data models.",
    icon: FileText,
    color: "bg-blue-100 text-blue-600",
    content: [
      { heading: "System Overview", body: "ZECT is a full-stack application with a React/TypeScript frontend (Vite, TailwindCSS) and a Python FastAPI backend with PostgreSQL. The system follows a modular router architecture where each feature has its own API router and frontend page." },
      { heading: "API Endpoints", body: "All endpoints are prefixed with /api:\n\u2022 /api/projects \u2014 Project CRUD and management\n\u2022 /api/llm \u2014 AI features (ask, plan, build, review)\n\u2022 /api/skills \u2014 Skill library CRUD + AI pattern detection\n\u2022 /api/tokens \u2014 Token usage tracking, budgets, and limits\n\u2022 /api/audit \u2014 Audit trail for all system operations\n\u2022 /api/rules \u2014 Rules engine for code quality gates\n\u2022 /api/export \u2014 Export/share generated content\n\u2022 /api/outputs \u2014 Generated output history\n\u2022 /api/jira, /api/slack \u2014 Integration endpoints" },
      { heading: "Database Schema", body: "Core tables: users, projects, repos, skills, token_logs, token_budgets, user_sessions, context_files, generated_outputs, audit_logs, review_sessions, review_findings, rules, jira_configs, slack_configs, export_jobs. All tables auto-migrate on startup \u2014 missing columns are added automatically." },
      { heading: "Authentication", body: "ZECT supports SSO via Azure AD, Okta, or Google. For local development, use the built-in username/password auth. Token-based session management with configurable expiry. Role-based access: admin, lead, developer, viewer." },
    ],
  },
  {
    title: "Multi-Repo Orchestration",
    description: "Guide to managing cross-repository dependencies, CI/CD pipelines, and synchronized deployments.",
    icon: GitBranch,
    color: "bg-purple-100 text-purple-600",
    content: [
      { heading: "Cross-Repo Analysis", body: "ZECT can analyze multiple repositories at once via the Repo Analysis page. It detects shared dependencies, identifies breaking changes across repos, and generates unified blueprints that consider the entire system architecture." },
      { heading: "Dependency Mapping", body: "The orchestration engine maps dependencies between repos: shared packages, API contracts, database schemas, and CI/CD triggers. This helps prevent breaking changes when updating one repo that affects others." },
      { heading: "Synchronized Deployments", body: "Use the Deployment page to generate coordinated runbooks when multiple repos need to be deployed together. The system automatically orders deployments based on dependency graphs and includes rollback procedures." },
      { heading: "CI/CD Integration", body: "ZECT reads GitHub Actions workflow status for all connected repos. View build status, test coverage, and deployment history from the Projects dashboard. Set up Rules Engine quality gates to enforce standards across all repos." },
    ],
  },
  {
    title: "Security & Compliance",
    description: "Security standards, credential management, audit procedures, and compliance checklists for engineering projects.",
    icon: Shield,
    color: "bg-green-100 text-green-600",
    content: [
      { heading: "Credential Management", body: "API keys and tokens are stored in environment variables, never in code or database. The .env file is gitignored by default. For production, use your cloud provider's secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)." },
      { heading: "Audit Trail", body: "Every CRUD operation, login, export, and review is logged in the audit trail with timestamp, user, action, resource type, and IP address. Use the Audit Trail page to filter and search through the complete history." },
      { heading: "Code Review Security", body: "The Code Review engine includes security-focused analysis: CWE identification, OWASP category mapping, and automated detection of secrets, SQL injection, XSS, and other vulnerabilities. Findings are rated by severity (critical, high, medium, low, info)." },
      { heading: "Role-Based Access Control", body: "Four roles control access: Admin (full access, user management, budget control), Lead (project management, review approval), Developer (use AI features, create skills), Viewer (read-only access to dashboards and reports)." },
    ],
  },
  {
    title: "Workflow Stages Guide",
    description: "How to use each ZECT workflow stage: Ask, Plan, Build, Review, and Deploy.",
    icon: Layers,
    color: "bg-cyan-100 text-cyan-600",
    content: [
      { heading: "Ask Mode", body: "Ask questions about your codebase, architecture, or engineering best practices. Attach files or repo context for more specific answers. Supports model selection \u2014 choose between free (OpenRouter) and paid (OpenAI) models." },
      { heading: "Plan Mode", body: "Generate structured development plans with task breakdowns, dependencies, and effort estimates. Provide project description and constraints to get a step-by-step implementation plan with risk assessments." },
      { heading: "Build Phase", body: "Generate production-ready code from your plan steps. Attach context files, select the target language and framework, then generate code with a single click. Review the output and iterate." },
      { heading: "Review Phase", body: "Paste code or point to a GitHub PR for AI-powered code review. Get findings categorized by severity, with specific line references, fix suggestions, and auto-generated corrected code." },
      { heading: "Deployment", body: "Generate deployment checklists and runbooks tailored to your tech stack and infrastructure. Includes pre-deploy checks, deployment steps, verification procedures, and rollback plans." },
    ],
  },
  {
    title: "Token Controls & Budget",
    description: "How to configure token limits, budgets, model selection, and per-user tracking.",
    icon: Database,
    color: "bg-rose-100 text-rose-600",
    content: [
      { heading: "Token Dashboard", body: "The Token Controls page shows real-time usage: total calls, tokens consumed, estimated cost, and today's activity. Breakdowns by model and by feature help you understand where tokens are being spent." },
      { heading: "Budget Configuration", body: "Set daily and monthly token limits, cost limits, and alert thresholds. Budgets can be global (apply to everyone) or per-user. Enable 'Enforce Limits' to automatically block requests when the budget is exceeded." },
      { heading: "Model Selection", body: "Choose which models are allowed for your organization. Configure preferred models and restrict access to expensive models. Each AI page (Ask, Plan, Build, Review) shows a model selector dropdown." },
      { heading: "Per-User Tracking", body: "When SSO is configured, token usage is tracked per-user. View individual user activity, top models used, session history, and cost breakdown on the User Activity tab of Token Controls." },
    ],
  },
  {
    title: "Integrations Setup",
    description: "Configure Jira and Slack integrations for ticket creation and team notifications.",
    icon: Users,
    color: "bg-orange-100 text-orange-600",
    content: [
      { heading: "Jira Integration", body: "Connect ZECT to Jira to automatically create tickets from code review findings. Go to Integrations \u2192 Jira \u2192 Configure. Enter your Jira URL, email, API token, and default project key. After setup, review findings can be exported as Jira tickets." },
      { heading: "Slack Integration", body: "Connect Slack to receive notifications for code reviews, deployments, and budget alerts. Go to Integrations \u2192 Slack \u2192 Configure. Enter your Slack bot token, workspace name, and default channel. Enable/disable notification types as needed." },
      { heading: "GitHub Integration", body: "ZECT connects to GitHub for repo analysis, PR review, and CI/CD monitoring. Set GITHUB_TOKEN in your backend/.env file. The token needs read access to repos, pull requests, and actions workflows." },
      { heading: "MCP (Model Context Protocol)", body: "ZECT includes 6 MCP servers with 48 tools for advanced AI agent capabilities: filesystem, GitHub, PostgreSQL, Docker, Slack, and web search. Configure MCP servers in Settings for enhanced AI context." },
    ],
  },
];

export default function Docs() {
  const [expanded, setExpanded] = useState<string | null>("Getting Started");
  const toggle = (title: string) => setExpanded(expanded === title ? null : title);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Docs Center</h1>
        <p className="text-slate-500 text-sm">Engineering documentation and reference guides</p>
      </div>

      <div className="space-y-3">
        {resources.map((r) => {
          const Icon = r.icon;
          const isOpen = expanded === r.title;
          return (
            <div key={r.title} className="bg-white rounded-xl border border-slate-200 overflow-hidden transition-shadow hover:shadow-sm">
              <button onClick={() => toggle(r.title)} className="w-full flex items-center gap-4 p-5 text-left">
                <div className={`rounded-lg p-2.5 h-fit ${r.color}`}><Icon className="h-5 w-5" /></div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h3 className="text-sm font-semibold text-slate-900">{r.title}</h3>
                    {r.url && (
                      <a href={r.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="text-indigo-500 hover:text-indigo-700">
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">{r.description}</p>
                </div>
                {isOpen ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />}
              </button>
              {isOpen && (
                <div className="border-t border-slate-100 bg-slate-50/50 px-5 py-4 space-y-4">
                  {r.content.map((s) => (
                    <div key={s.heading}>
                      <h4 className="text-sm font-semibold text-slate-800 mb-1.5 flex items-center gap-1.5">
                        <Terminal className="h-3.5 w-3.5 text-slate-400" />{s.heading}
                      </h4>
                      <pre className="text-xs text-slate-600 whitespace-pre-wrap font-sans leading-relaxed bg-white rounded-lg border border-slate-100 p-3">{s.body}</pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

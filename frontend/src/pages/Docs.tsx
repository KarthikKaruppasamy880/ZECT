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
  Map,
  Key,
  Clock,
  BarChart3,
  MessageSquare,
  Play,
  Search,
  Settings,
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
    title: "ZECT Management Guide",
    description: "Complete workflow reference for every ZECT feature — how each page works, what it does, and how to use it step by step.",
    icon: Map,
    color: "bg-teal-100 text-teal-600",
    content: [
      { heading: "Dashboard (/)", body: "Overview of all engineering projects, token usage, and stage distribution.\n\n• Stats Cards — Total Projects, Active Projects, Avg Token Savings, Risk Alerts\n• Token Usage Control — Total API Calls, Total Tokens, Estimated Cost\n• Stage Distribution — Visual breakdown across Ask/Plan/Build/Review/Deploy\n• Projects Grid — All projects with completion % and stage badges\n\nClick a project card to open its detail view. Click 'View all' for the full Projects page." },
      { heading: "Ask Mode (/ask)", body: "Ask any engineering question — architecture, debugging, code review, best practices.\n\nWorkflow:\n1. Select an AI Model — GPT-4o Mini (default), GPT-4o, GPT-3.5 Turbo, Claude 3.5 Sonnet, Claude 3 Haiku\n2. Attach Context (optional) — Click '+ Add files, repos, snippets' to add code context\n3. Type your question — Or click a quick prompt\n4. Press Enter — AI responds with a detailed answer\n5. Conversation History — Previous sessions in left sidebar, click to resume\n\nAll conversations are saved to the database and accessible from the sidebar." },
      { heading: "Plan Mode (/plan)", body: "Generate detailed, phased engineering plans for any project or feature.\n\nWorkflow:\n1. Select Model — Choose AI model (pricing shown per 1K tokens)\n2. Describe Your Project — Enter detailed description in the textarea\n3. Attach Context (optional) — Add files/repos/snippets\n4. Show Advanced Options (optional) — Configure plan output format\n5. Click 'Generate Engineering Plan' — AI creates phased plan\n\nOutput includes: phased timeline, tech stack recommendations, risk assessment, resource allocation, dependency mapping." },
      { heading: "Build Phase (/build)", body: "Generate production-ready code from plan steps using AI.\n\nWorkflow:\n1. Describe the Plan Step — What code to generate\n2. Set Tech Stack — e.g. 'TypeScript, React, FastAPI'\n3. Set Target File Path — e.g. 'src/api/auth.ts'\n4. Select Model — With pricing info\n5. Add Context Files — Click '+' to add existing code\n6. Click 'Generate Code' — AI produces code\n7. Auto-Fix Loop — Run lint/test/fix cycles automatically\n8. Create PR — Create a GitHub PR directly from generated code\n\n6 Quick Templates: REST API, React component, Unit tests, DB migration, CI/CD pipeline, Auth middleware." },
      { heading: "Code Review (/code-review)", body: "AI-powered code analysis — bugs, vulnerabilities, performance issues.\n\n5 Tabs:\n• PR Review — Enter owner/repo/PR#, click 'Run ZECT Review', optionally post comments to GitHub\n• Snippet Review — Paste code, select language, get instant analysis\n• Full Repo Scan — Comprehensive codebase security + quality analysis\n• Auto-Fix Loop — AI identifies issues and generates fixes automatically\n• Webhook — Configure automatic PR reviews on push events" },
      { heading: "Knowledge Base (/knowledge-base)", body: "Persistent tips, instructions, project notes — your team's engineering knowledge.\n\nCRUD Operations:\n• Create — Click '+ New Entry', fill title/category/content/tags, click Save\n• Search — Type in search bar to filter by keyword\n• Filter — Use category dropdown (General, Coding, Review, Deploy, Architecture, Testing, Debug)\n• Edit/Delete — Click entry to expand, then Edit or Delete\n\nAll entries stored in SQLite/PostgreSQL database with timestamps." },
      { heading: "Playbooks (/playbooks)", body: "Reusable prompt templates and multi-step automated workflows.\n\nCategory Tabs: All, General, Onboarding, Review, Deploy, Debug, Migration, Testing\n\nCreate a Playbook:\n1. Click '+ New Playbook'\n2. Fill name, description, category\n3. Add ordered steps with prompt templates (supports {{variable}} placeholders)\n4. Click Save\n\nRun a Playbook: Click a playbook → Run → executes all steps in sequence. View run history with timestamps and results." },
      { heading: "Scheduled Tasks (/scheduled-tasks)", body: "Cron-based recurring automated tasks.\n\nCreate a Schedule:\n1. Click '+ New Schedule'\n2. Fill name, cron expression (e.g. '0 2 * * *' = daily at 2 AM), task type, config\n3. Click Save\n\nManage: Toggle enable/disable, Manual Trigger (run immediately), View Runs (execution history), Edit/Delete." },
      { heading: "Secrets Manager (/secrets)", body: "Encrypted storage for API keys, tokens, and credentials.\n\nSecurity: Fernet symmetric encryption at rest. Set ZECT_ENCRYPT_KEY in .env for production.\n\nAdd a Secret:\n1. Click '+ Add Secret'\n2. Fill name (e.g. OPENAI_API_KEY), value (encrypted before storage), scope (org/user/repo)\n3. Click Save\n\nValues always masked (••••••••). Rotate to set new value. Delete is irreversible." },
      { heading: "Code Index (/code-index)", body: "Search functions, classes, variables across your codebase.\n\nIndex a Repo: Click 'Index Repo' → enter repo path → Start Indexing (parses all source files)\n\nSearch: Type symbol name, filter by Type (Function/Class/Variable/Import/Interface/Type/Method) and Language (Python/TypeScript/JavaScript/Java/Go/Rust/Ruby/C/C++). Results show file path, line number, and code preview.\n\nView Stats: Click 'Stats' for total symbols breakdown by type and language." },
      { heading: "Session Insights (/session-insights)", body: "Usage analytics, cost tracking, and quality metrics.\n\n4 Metric Cards: Total Sessions, Total Tokens, Total Cost, Quality Score\nTime Range: Last 7/14/30/90 days\nModel Usage: Which AI models consumed the most tokens\nFeature Usage: Which ZECT features your team uses most\n\nAll data from real database — updates as you use the tool." },
      { heading: "Conversations (/conversations)", body: "Session history across all modes (Ask, Plan, Build, Review, Deploy).\n\nMode Tabs: All, Ask, Plan, Build, Review, Deploy\nSplit-pane layout: conversation list (left) + message thread (right)\n\nCreate: Click '+ New Conversation' → select mode → start messaging\nArchive: Hide conversations (restorable via 'Show Archived')\nDelete: Permanently remove conversations" },
      { heading: "Settings (/settings)", body: "Configure ZECT behavior and integrations.\n\nAPI Keys: GitHub API Key, OpenAI API Key, Token Usage log\nSecrets Manager: Quick link to /secrets page\n\n6 Feature Toggles:\n• Automated Code Review, Token Usage Tracking, Deployment Gate Enforcement\n• Risk Alert Notifications, Auto-Generate Plan, Session Context Memory\n\n4 Config Options:\n• Default Starting Stage, Minimum Review Severity, Deployment Approval Mode, Monthly Token Budget Alert" },
      { heading: "Token Controls (/token-controls)", body: "Per-user monitoring, budgets, and model spending analytics.\n\n5 Tabs:\n• Overview — 4 metric cards + model breakdown + active users\n• User Activity — Per-user token consumption and request history\n• Teams — Team-level aggregated usage and budget allocation\n• Budget — Monthly limits, alert thresholds, budget vs actual\n• Trends — Usage trends over time, cost forecasting" },
      { heading: "App Runner (/app-runner)", body: "Configure, run, and test applications directly inside ZECT.\n\n3 Tabs:\n• Terminal — Full command-line interface in browser. 'Run' for one-shot commands, 'Start Process' for servers\n• Configure — Set environment variables, startup commands, working directory\n• Processes — View/stop/restart running background processes\n\nLive Preview panel shows your app at any localhost URL." },
    ],
  },
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
      { heading: "What is ZEF?", body: "ZEF (Zinnia Engineering Foundation) is the tool-neutral layer that powers ZECT's AI capabilities. It defines playbooks, skills, and adapter interfaces that work with any LLM provider \u2014 OpenAI, Anthropic, local models via Ollama, or custom endpoints." },
      { heading: "Playbooks", body: "Pre-built workflow templates for common engineering tasks: code review, migration planning, test generation, documentation, and deployment checklists. Each playbook is a structured prompt chain that guides the AI through multi-step processes." },
      { heading: "Skills & Templates", body: "Reusable AI skill templates stored in the Skill Library. Skills can be global (available to all projects) or scoped to specific repositories. Use Auto-Detect to analyze your code and discover patterns worth saving as skills." },
      { heading: "Adapter Architecture", body: "ZEF uses an adapter pattern so you can swap LLM providers without changing application code. Supported providers: OpenAI, Anthropic Claude, Google Gemini, and local Ollama models." },
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
      { heading: "Ask Mode", body: "Ask questions about your codebase, architecture, or engineering best practices. Attach files or repo context for more specific answers. Supports model selection \u2014 choose between OpenAI and Anthropic models." },
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

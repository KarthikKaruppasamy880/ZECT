import {
  FileText,
  BookOpen,
  GitBranch,
  Shield,
  Zap,
  ExternalLink,
} from "lucide-react";

const resources = [
  {
    title: "ZEF — Zinnia Engineering Foundation",
    description: "Tool-neutral engineering foundation for AI-assisted development. Includes playbooks, skills, templates, and adapter guides.",
    icon: BookOpen,
    color: "bg-indigo-100 text-indigo-600",
    url: "https://github.com/KarthikKaruppasamy880/ZEF",
  },
  {
    title: "ZECT Architecture Guide",
    description: "Technical architecture documentation for the Engineering Delivery Control Tower, including API specs and data models.",
    icon: FileText,
    color: "bg-blue-100 text-blue-600",
    url: "#",
  },
  {
    title: "Multi-Repo Orchestration",
    description: "Guide to managing cross-repository dependencies, CI/CD pipelines, and synchronized deployments.",
    icon: GitBranch,
    color: "bg-purple-100 text-purple-600",
    url: "#",
  },
  {
    title: "Security & Compliance",
    description: "Security standards, credential management, audit procedures, and compliance checklists for engineering projects.",
    icon: Shield,
    color: "bg-green-100 text-green-600",
    url: "#",
  },
  {
    title: "Getting Started",
    description: "Quick start guide for new team members — project setup, tool configuration, and workflow walkthrough.",
    icon: Zap,
    color: "bg-amber-100 text-amber-600",
    url: "#",
  },
];

export default function Docs() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Docs Center</h1>
        <p className="text-slate-500 text-sm">Engineering documentation and reference guides</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {resources.map((r) => {
          const Icon = r.icon;
          return (
            <a
              key={r.title}
              href={r.url}
              target={r.url.startsWith("http") ? "_blank" : undefined}
              rel="noopener noreferrer"
              className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow flex gap-4"
            >
              <div className={`rounded-lg p-2.5 h-fit ${r.color}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold text-slate-900">{r.title}</h3>
                  {r.url.startsWith("http") && (
                    <ExternalLink className="h-3 w-3 text-slate-400" />
                  )}
                </div>
                <p className="text-xs text-slate-500">{r.description}</p>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}

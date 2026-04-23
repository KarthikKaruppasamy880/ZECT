import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProjects } from "@/lib/api";
import type { Project } from "@/types";
import { STAGES } from "@/types";
import {
  Plus,
  Layers,
  GitBranch,
} from "lucide-react";

function stageBadge(stage: string) {
  const colors: Record<string, string> = {
    ask: "bg-purple-100 text-purple-700",
    plan: "bg-blue-100 text-blue-700",
    build: "bg-amber-100 text-amber-700",
    review: "bg-cyan-100 text-cyan-700",
    deploy: "bg-green-100 text-green-700",
  };
  const label = STAGES.find((s) => s.key === stage)?.label ?? stage;
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded ${colors[stage] ?? "bg-slate-100 text-slate-600"}`}>
      {label}
    </span>
  );
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    active: "bg-emerald-100 text-emerald-700",
    completed: "bg-slate-100 text-slate-600",
    "on-hold": "bg-orange-100 text-orange-700",
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${colors[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    getProjects()
      .then(setProjects)
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter
    ? projects.filter((p) => p.status === filter)
    : projects;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
          <p className="text-slate-500 text-sm">Manage your engineering projects</p>
        </div>
        <Link
          to="/projects/new"
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus className="h-4 w-4" /> New Project
        </Link>
      </div>

      <div className="flex gap-2 mb-6">
        {["", "active", "completed", "on-hold"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === f
                ? "bg-indigo-600 text-white"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {f || "All"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((p) => (
          <Link
            key={p.id}
            to={`/projects/${p.id}`}
            className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-slate-900 text-sm leading-tight">{p.name}</h3>
              <div className="flex gap-1.5 shrink-0 ml-2">
                {statusBadge(p.status)}
                {stageBadge(p.current_stage)}
              </div>
            </div>
            <p className="text-xs text-slate-500 mb-4 line-clamp-2">{p.description}</p>

            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="text-center">
                <p className="text-lg font-bold text-slate-900">{p.completion_percent}%</p>
                <p className="text-xs text-slate-500">Complete</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-blue-600">{p.token_savings}%</p>
                <p className="text-xs text-slate-500">Savings</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-red-600">{p.risk_alerts}</p>
                <p className="text-xs text-slate-500">Alerts</p>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-3">
              <span className="flex items-center gap-1">
                <Layers className="h-3 w-3" /> {p.team}
              </span>
              <span className="flex items-center gap-1">
                <GitBranch className="h-3 w-3" /> {p.repos.length} repo{p.repos.length !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="mt-3">
              <div className="h-1.5 rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all"
                  style={{ width: `${p.completion_percent}%` }}
                />
              </div>
            </div>
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          <FolderIcon className="h-12 w-12 mx-auto mb-3 text-slate-300" />
          <p className="font-medium">No projects found</p>
          <p className="text-sm">Create a new project to get started</p>
        </div>
      )}
    </div>
  );
}

function FolderIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 20h16a2 2 0 002-2V8a2 2 0 00-2-2h-7.93a2 2 0 01-1.66-.9l-.82-1.2A2 2 0 007.93 3H4a2 2 0 00-2 2v13c0 1.1.9 2 2 2z" />
    </svg>
  );
}

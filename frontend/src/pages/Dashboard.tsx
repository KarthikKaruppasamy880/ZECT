import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProjects, getAnalytics } from "@/lib/api";
import type { Project, AnalyticsOverview } from "@/types";
import { STAGES } from "@/types";
import {
  FolderKanban,
  Activity,
  AlertTriangle,
  TrendingUp,
  ArrowRight,
  Layers,
  GitBranch,
} from "lucide-react";

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-start gap-4">
      <div className={`rounded-lg p-2.5 ${color}`}>
        <Icon className="h-5 w-5 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900">{value}</p>
        <p className="text-sm text-slate-500">{label}</p>
      </div>
    </div>
  );
}

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

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getProjects(), getAnalytics()])
      .then(([p, a]) => {
        setProjects(p);
        setAnalytics(a);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 text-sm">Engineering Delivery Control Tower — Overview</p>
      </div>

      {analytics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard label="Total Projects" value={analytics.total_projects} icon={FolderKanban} color="bg-indigo-500" />
          <MetricCard label="Active Projects" value={analytics.active_projects} icon={Activity} color="bg-green-500" />
          <MetricCard label="Avg Token Savings" value={`${analytics.avg_token_savings}%`} icon={TrendingUp} color="bg-blue-500" />
          <MetricCard label="Risk Alerts" value={analytics.total_risk_alerts} icon={AlertTriangle} color="bg-red-500" />
        </div>
      )}

      {analytics && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-8">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Stage Distribution</h2>
          <div className="flex items-end gap-4 h-32">
            {Object.entries(analytics.stage_distribution).map(([stage, count]) => {
              const maxCount = Math.max(...Object.values(analytics.stage_distribution), 1);
              const height = Math.max((count / maxCount) * 100, 4);
              const colors: Record<string, string> = {
                ask: "bg-purple-400",
                plan: "bg-blue-400",
                build: "bg-amber-400",
                review: "bg-cyan-400",
                deploy: "bg-green-400",
              };
              return (
                <div key={stage} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-xs font-bold text-slate-700">{count}</span>
                  <div
                    className={`w-full rounded-t ${colors[stage] ?? "bg-slate-300"}`}
                    style={{ height: `${height}%` }}
                  />
                  <span className="text-xs text-slate-500 capitalize">{stage}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Projects</h2>
        <Link to="/projects" className="text-sm text-indigo-600 hover:text-indigo-700 flex items-center gap-1">
          View all <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {projects.slice(0, 6).map((p) => (
          <Link
            key={p.id}
            to={`/projects/${p.id}`}
            className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-slate-900 text-sm">{p.name}</h3>
              {stageBadge(p.current_stage)}
            </div>
            <p className="text-xs text-slate-500 mb-3 line-clamp-2">{p.description}</p>
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Layers className="h-3 w-3" /> {p.team}
              </span>
              <span className="flex items-center gap-1">
                <GitBranch className="h-3 w-3" /> {p.repos.length} repo{p.repos.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="mt-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">Completion</span>
                <span className="text-xs font-medium text-slate-700">{p.completion_percent}%</span>
              </div>
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
    </div>
  );
}

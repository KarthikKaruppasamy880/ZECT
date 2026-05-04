import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProjects, getAnalytics, getTokenDashboard } from "@/lib/api";
import type { Project, AnalyticsOverview, TokenDashboard } from "@/types";
import { STAGES } from "@/types";
import {
  FolderKanban,
  Activity,
  AlertTriangle,
  TrendingUp,
  ArrowRight,
  Layers,
  GitBranch,
  Zap,
  DollarSign,
  Hash,
  ChevronDown,
  ChevronUp,
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
  const [tokenData, setTokenData] = useState<TokenDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTokenDetails, setShowTokenDetails] = useState(false);

  useEffect(() => {
    Promise.all([getProjects(), getAnalytics(), getTokenDashboard().catch(() => null)])
      .then(([p, a, t]) => {
        setProjects(p);
        setAnalytics(a);
        setTokenData(t);
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

      {/* Token Control Panel */}
      {tokenData && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="rounded-lg p-2 bg-amber-100">
                <Zap className="h-4 w-4 text-amber-600" />
              </div>
              <h2 className="text-sm font-semibold text-slate-700">Token Usage Control</h2>
            </div>
            <button
              onClick={() => setShowTokenDetails(!showTokenDetails)}
              className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
            >
              {showTokenDetails ? "Hide" : "Details"}
              {showTokenDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <div className="bg-amber-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <Hash className="h-4 w-4 text-amber-600" />
                <span className="text-xs text-amber-700 font-medium">Total API Calls</span>
              </div>
              <p className="text-2xl font-bold text-amber-900">{tokenData.total_calls}</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-4 w-4 text-blue-600" />
                <span className="text-xs text-blue-700 font-medium">Total Tokens</span>
              </div>
              <p className="text-2xl font-bold text-blue-900">{tokenData.total_tokens.toLocaleString()}</p>
              <p className="text-xs text-blue-500 mt-0.5">
                {tokenData.total_prompt_tokens.toLocaleString()} prompt / {tokenData.total_completion_tokens.toLocaleString()} completion
              </p>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign className="h-4 w-4 text-green-600" />
                <span className="text-xs text-green-700 font-medium">Estimated Cost</span>
              </div>
              <p className="text-2xl font-bold text-green-900">${tokenData.total_cost_usd.toFixed(4)}</p>
            </div>
          </div>

          {/* Feature Breakdown */}
          {showTokenDetails && (
            <div className="space-y-4">
              {/* By Feature */}
              {Object.keys(tokenData.by_feature).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Usage by Feature</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(tokenData.by_feature).map(([feature, data]) => (
                      <div key={feature} className="bg-slate-50 rounded-lg p-3">
                        <p className="text-xs font-medium text-slate-700 capitalize">{feature.replace(/_/g, " ")}</p>
                        <p className="text-sm font-bold text-slate-900">{data.calls} calls</p>
                        <p className="text-xs text-slate-500">{data.tokens.toLocaleString()} tokens &middot; ${data.cost.toFixed(4)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* By Model */}
              {Object.keys(tokenData.by_model).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Usage by Model</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(tokenData.by_model).map(([model, data]) => (
                      <div key={model} className="bg-slate-50 rounded-lg p-3">
                        <p className="text-xs font-medium text-slate-700">{model}</p>
                        <p className="text-sm font-bold text-slate-900">{data.calls} calls</p>
                        <p className="text-xs text-slate-500">{data.tokens.toLocaleString()} tokens &middot; ${data.cost.toFixed(4)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Activity */}
              {tokenData.recent.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Recent Activity</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-200">
                          <th className="text-left py-2 px-2 text-slate-500 font-medium">Action</th>
                          <th className="text-left py-2 px-2 text-slate-500 font-medium">Feature</th>
                          <th className="text-left py-2 px-2 text-slate-500 font-medium">Model</th>
                          <th className="text-right py-2 px-2 text-slate-500 font-medium">Tokens</th>
                          <th className="text-right py-2 px-2 text-slate-500 font-medium">Cost</th>
                          <th className="text-right py-2 px-2 text-slate-500 font-medium">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tokenData.recent.slice(0, 10).map((entry) => (
                          <tr key={entry.id} className="border-b border-slate-100">
                            <td className="py-2 px-2 text-slate-700">{entry.action}</td>
                            <td className="py-2 px-2 text-slate-500 capitalize">{entry.feature.replace(/_/g, " ")}</td>
                            <td className="py-2 px-2 text-slate-500">{entry.model}</td>
                            <td className="py-2 px-2 text-right text-slate-700">{entry.total_tokens.toLocaleString()}</td>
                            <td className="py-2 px-2 text-right text-slate-700">${entry.estimated_cost_usd.toFixed(4)}</td>
                            <td className="py-2 px-2 text-right text-slate-400">
                              {entry.created_at ? new Date(entry.created_at).toLocaleString() : "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {tokenData.total_calls === 0 && (
                <p className="text-sm text-slate-400 text-center py-4">
                  No token usage recorded yet. Use Ask Mode, Plan Mode, or Blueprint Generator to see usage here.
                </p>
              )}
            </div>
          )}
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

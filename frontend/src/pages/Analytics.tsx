import { useEffect, useState } from "react";
import { getAnalytics, getProjects } from "@/lib/api";
import type { AnalyticsOverview, Project } from "@/types";
import { STAGES } from "@/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  FolderKanban,
  Activity,
  TrendingUp,
  AlertTriangle,
  GitBranch,
  Layers,
} from "lucide-react";

const COLORS = ["#8b5cf6", "#3b82f6", "#f59e0b", "#06b6d4", "#22c55e"];

export default function Analytics() {
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAnalytics(), getProjects()])
      .then(([a, p]) => {
        setAnalytics(a);
        setProjects(p);
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

  if (!analytics) return null;

  const stageData = Object.entries(analytics.stage_distribution).map(([key, value]) => ({
    name: STAGES.find((s) => s.key === key)?.label ?? key,
    count: value,
  }));

  const pieData = [
    { name: "Active", value: analytics.active_projects },
    { name: "Completed", value: analytics.completed_projects },
    { name: "On Hold", value: analytics.total_projects - analytics.active_projects - analytics.completed_projects },
  ].filter((d) => d.value > 0);

  const pieFills = ["#22c55e", "#6366f1", "#f59e0b"];

  const teamData = projects.reduce<Record<string, { count: number; avgCompletion: number }>>((acc, p) => {
    if (!acc[p.team]) acc[p.team] = { count: 0, avgCompletion: 0 };
    acc[p.team].count += 1;
    acc[p.team].avgCompletion += p.completion_percent;
    return acc;
  }, {});

  const teamChart = Object.entries(teamData).map(([team, d]) => ({
    name: team,
    projects: d.count,
    avgCompletion: Math.round(d.avgCompletion / d.count),
  }));

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
        <p className="text-slate-500 text-sm">Project metrics and performance insights</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard label="Total Projects" value={analytics.total_projects} icon={FolderKanban} color="bg-indigo-500" />
        <MetricCard label="Active Projects" value={analytics.active_projects} icon={Activity} color="bg-green-500" />
        <MetricCard label="Avg Token Savings" value={`${analytics.avg_token_savings}%`} icon={TrendingUp} color="bg-blue-500" />
        <MetricCard label="Risk Alerts" value={analytics.total_risk_alerts} icon={AlertTriangle} color="bg-red-500" />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <MetricCard label="Total Repos" value={analytics.total_repos} icon={GitBranch} color="bg-purple-500" />
        <MetricCard label="Avg Completion" value={`${analytics.avg_completion}%`} icon={Layers} color="bg-cyan-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Stage Distribution</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={stageData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} />
              <YAxis tick={{ fontSize: 12, fill: "#64748b" }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {stageData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Project Status</h2>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
                label={({ name, value }) => `${name} (${value})`}
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={pieFills[i % pieFills.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-8">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Team Performance</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={teamChart}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} />
            <YAxis tick={{ fontSize: 12, fill: "#64748b" }} />
            <Tooltip />
            <Bar dataKey="avgCompletion" name="Avg Completion %" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Project Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Project</th>
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Team</th>
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Stage</th>
                <th className="text-right py-2 px-3 text-slate-500 font-medium">Completion</th>
                <th className="text-right py-2 px-3 text-slate-500 font-medium">Savings</th>
                <th className="text-right py-2 px-3 text-slate-500 font-medium">Alerts</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2 px-3 font-medium text-slate-900">{p.name}</td>
                  <td className="py-2 px-3 text-slate-500">{p.team}</td>
                  <td className="py-2 px-3">
                    <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600 capitalize">
                      {STAGES.find((s) => s.key === p.current_stage)?.label ?? p.current_stage}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right font-mono">{p.completion_percent}%</td>
                  <td className="py-2 px-3 text-right font-mono text-blue-600">{p.token_savings}%</td>
                  <td className="py-2 px-3 text-right font-mono text-red-600">{p.risk_alerts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

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

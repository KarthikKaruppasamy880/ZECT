import { useEffect, useState } from "react";
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
  LineChart,
  Line,
} from "recharts";
import {
  Activity,
  TrendingUp,
  DollarSign,
  Zap,
  Clock,
  CheckCircle,
  Download,
  FileText,
  RefreshCw,
} from "lucide-react";
import { showToast } from "@/components/Toast";
import Pagination from "@/components/Pagination";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const COLORS = ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

interface Dashboard {
  period_days: number;
  kpis: {
    total_events: number;
    total_tokens: number;
    total_cost_usd: number;
    success_rate: number;
    avg_duration_seconds: number;
    throughput_per_day: number;
  };
  harness_breakdown: Record<string, { count: number; tokens: number; cost: number; successes: number }>;
  category_breakdown: Record<string, { count: number; tokens: number; cost: number }>;
  model_breakdown: Record<string, { count: number; tokens: number; cost: number }>;
  daily_trends: { date: string; count: number; tokens: number; cost: number; successes: number }[];
}

export default function DataLayer() {
  const [projectId] = useState<number | undefined>(undefined);
  const [days, setDays] = useState(7);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"dashboard" | "events" | "reports">("dashboard");
  const [reports, setReports] = useState<any[]>([]);
  const [eventsPage, setEventsPage] = useState(1);
  const eventsPerPage = 15;

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${API}/api/data-layer/dashboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, days }),
      });
      if (res.ok) setDashboard(await res.json());
      else showToast("error", `Failed to load dashboard (${res.status})`);
    } catch (err) { showToast("error", "Network error loading dashboard"); }
  };

  const fetchEvents = async () => {
    try {
      const params = new URLSearchParams({ days: String(days), limit: "50" });
      if (projectId) params.set("project_id", String(projectId));
      const res = await fetch(`${API}/api/data-layer/events?${params}`);
      if (res.ok) setEvents(await res.json());
      else showToast("error", `Failed to load events (${res.status})`);
    } catch (err) { showToast("error", "Network error loading events"); }
  };

  const fetchReports = async () => {
    try {
      const params = new URLSearchParams({ limit: "30" });
      if (projectId) params.set("project_id", String(projectId));
      const res = await fetch(`${API}/api/data-layer/daily-reports?${params}`);
      if (res.ok) setReports(await res.json());
      else showToast("error", `Failed to load reports (${res.status})`);
    } catch (err) { showToast("error", "Network error loading reports"); }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchDashboard(), fetchEvents(), fetchReports()])
      .finally(() => setLoading(false));
  }, [projectId, days]);

  const handleExport = async () => {
    try {
      const params = new URLSearchParams({ days: "30" });
      if (projectId) params.set("project_id", String(projectId));
      const res = await fetch(`${API}/api/data-layer/export/csv?${params}`);
      if (res.ok) {
        const data = await res.json();
        const csv = [data.columns.join(","), ...data.rows.map((r: any[]) => r.join(","))].join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "agent-events.csv";
        a.click();
        URL.revokeObjectURL(url);
      } else {
        showToast("error", `Export failed (${res.status})`);
      }
    } catch (err) { showToast("error", "Network error during export"); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-600" />
      </div>
    );
  }

  const tabs = [
    { key: "dashboard" as const, label: "Analytics Dashboard", icon: Activity },
    { key: "events" as const, label: "Event Log", icon: Zap },
    { key: "reports" as const, label: "Daily Reports", icon: FileText },
  ];

  const harnessData = dashboard ? Object.entries(dashboard.harness_breakdown).map(([k, v]) => ({ name: k, ...v })) : [];
  const categoryData = dashboard ? Object.entries(dashboard.category_breakdown).map(([k, v]) => ({ name: k, ...v })) : [];
  const modelData = dashboard ? Object.entries(dashboard.model_breakdown).map(([k, v]) => ({ name: k, ...v })) : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Data Layer</h1>
          <p className="text-slate-500 text-sm">Cross-agent monitoring, KPIs, and analytics</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="px-2 py-1 border rounded text-sm">
            <option value={1}>1 day</option>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
          <button onClick={handleExport} className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 rounded text-sm hover:bg-slate-200">
            <Download className="h-3.5 w-3.5" /> Export CSV
          </button>
          <button onClick={() => { fetchDashboard(); fetchEvents(); fetchReports(); }} className="p-2 rounded hover:bg-slate-100">
            <RefreshCw className="h-4 w-4 text-slate-500" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.key ? "bg-white text-cyan-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Dashboard Tab */}
      {activeTab === "dashboard" && dashboard && (
        <div>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <KPICard label="Total Events" value={dashboard.kpis.total_events} icon={Activity} color="bg-indigo-500" />
            <KPICard label="Total Tokens" value={dashboard.kpis.total_tokens.toLocaleString()} icon={Zap} color="bg-blue-500" />
            <KPICard label="Total Cost" value={`$${dashboard.kpis.total_cost_usd.toFixed(4)}`} icon={DollarSign} color="bg-green-500" />
            <KPICard label="Success Rate" value={`${dashboard.kpis.success_rate}%`} icon={CheckCircle} color="bg-emerald-500" />
            <KPICard label="Avg Duration" value={`${dashboard.kpis.avg_duration_seconds}s`} icon={Clock} color="bg-amber-500" />
            <KPICard label="Throughput/Day" value={dashboard.kpis.throughput_per_day} icon={TrendingUp} color="bg-purple-500" />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Daily Trend */}
            {dashboard.daily_trends.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Daily Event Trend</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={dashboard.daily_trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={{ fill: "#6366f1" }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Harness Breakdown */}
            {harnessData.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">By Harness</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={harnessData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="count" label={({ name, count }) => `${name} (${count})`}>
                      {harnessData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Category Breakdown */}
            {categoryData.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">By Category</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={categoryData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Model Breakdown */}
            {modelData.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">By Model</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={modelData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} />
                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                    <Tooltip />
                    <Bar dataKey="tokens" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Events Tab */}
      {activeTab === "events" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Agent Event Log</h3>
          {events.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No events recorded yet.</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-2 px-2 text-slate-500 font-medium">Harness</th>
                      <th className="text-left py-2 px-2 text-slate-500 font-medium">Type</th>
                      <th className="text-left py-2 px-2 text-slate-500 font-medium">Category</th>
                      <th className="text-left py-2 px-2 text-slate-500 font-medium">Description</th>
                      <th className="text-right py-2 px-2 text-slate-500 font-medium">Tokens</th>
                      <th className="text-right py-2 px-2 text-slate-500 font-medium">Cost</th>
                      <th className="text-center py-2 px-2 text-slate-500 font-medium">Status</th>
                      <th className="text-left py-2 px-2 text-slate-500 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.slice((eventsPage - 1) * eventsPerPage, eventsPage * eventsPerPage).map((e) => (
                      <tr key={e.id} className="border-b border-slate-50 hover:bg-slate-50">
                        <td className="py-2 px-2"><span className="text-xs font-medium px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">{e.harness}</span></td>
                        <td className="py-2 px-2 text-slate-700">{e.event_type}</td>
                        <td className="py-2 px-2 text-slate-500">{e.category}</td>
                        <td className="py-2 px-2 text-slate-600 truncate max-w-[200px]">{e.description}</td>
                        <td className="py-2 px-2 text-right font-mono text-slate-600">{e.tokens_used.toLocaleString()}</td>
                        <td className="py-2 px-2 text-right font-mono text-green-600">${e.cost_usd.toFixed(4)}</td>
                        <td className="py-2 px-2 text-center">{e.success ? <CheckCircle className="h-4 w-4 text-green-500 mx-auto" /> : <span className="text-red-500 text-xs">FAIL</span>}</td>
                        <td className="py-2 px-2 text-xs text-slate-400">{e.created_at?.split("T")[0]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination currentPage={eventsPage} totalItems={events.length} pageSize={eventsPerPage} onPageChange={setEventsPage} />
            </>
          )}
        </div>
      )}

      {/* Reports Tab */}
      {activeTab === "reports" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Daily Reports</h3>
          {reports.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No daily reports generated yet. Log events to auto-generate reports.</p>
          ) : (
            <div className="space-y-3">
              {reports.map((r) => (
                <div key={r.id} className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-slate-800">{r.report_date?.split("T")[0]}</h4>
                    <span className="text-xs text-slate-500">{r.total_events} events</span>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    <div><span className="text-slate-500">Tokens:</span> <span className="font-mono">{r.total_tokens?.toLocaleString()}</span></div>
                    <div><span className="text-slate-500">Cost:</span> <span className="font-mono text-green-600">${r.total_cost_usd?.toFixed(4)}</span></div>
                    <div><span className="text-slate-500">Success:</span> <span className="font-mono">{r.success_rate}%</span></div>
                    <div><span className="text-slate-500">Report:</span> <span className="text-indigo-600 cursor-pointer hover:underline" onClick={() => alert(r.report_markdown)}>View</span></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function KPICard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-start gap-3">
      <div className={`rounded-lg p-2 ${color}`}><Icon className="h-4 w-4 text-white" /></div>
      <div>
        <p className="text-xl font-bold text-slate-900">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}

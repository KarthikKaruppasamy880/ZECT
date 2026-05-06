import { useEffect, useState } from "react";
import {
  Repeat,
  FileText,
  CheckCircle,
  Star,
  RefreshCw,
  Layers,
  FlaskConical,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function DataFlywheel() {
  const [activeTab, setActiveTab] = useState<"overview" | "traces" | "cards" | "evals">("overview");
  const [stats, setStats] = useState<any>(null);
  const [traces, setTraces] = useState<any[]>([]);
  const [cards, setCards] = useState<any[]>([]);
  const [evals, setEvals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectId] = useState<number | undefined>(undefined);

  const fetchStats = async () => {
    try {
      const params = projectId ? `?project_id=${projectId}` : "";
      const res = await fetch(`${API}/api/flywheel/stats${params}`);
      if (res.ok) setStats(await res.json());
    } catch { /* ignore */ }
  };

  const fetchTraces = async () => {
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (projectId) params.set("project_id", String(projectId));
      const res = await fetch(`${API}/api/flywheel/traces?${params}`);
      if (res.ok) setTraces(await res.json());
    } catch { /* ignore */ }
  };

  const fetchCards = async () => {
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (projectId) params.set("project_id", String(projectId));
      const res = await fetch(`${API}/api/flywheel/context-cards?${params}`);
      if (res.ok) setCards(await res.json());
    } catch { /* ignore */ }
  };

  const fetchEvals = async () => {
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (projectId) params.set("project_id", String(projectId));
      const res = await fetch(`${API}/api/flywheel/eval-cases?${params}`);
      if (res.ok) setEvals(await res.json());
    } catch { /* ignore */ }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchStats(), fetchTraces(), fetchCards(), fetchEvals()])
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleApproveTrace = async (traceId: number) => {
    try {
      await fetch(`${API}/api/flywheel/traces/${traceId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_by: "user" }),
      });
      fetchTraces();
      fetchStats();
    } catch { /* ignore */ }
  };

  const handleRateTrace = async (traceId: number, score: number) => {
    try {
      await fetch(`${API}/api/flywheel/traces/${traceId}/rate?score=${score}`, { method: "POST" });
      fetchTraces();
    } catch { /* ignore */ }
  };

  const handleApproveCard = async (cardId: number) => {
    try {
      await fetch(`${API}/api/flywheel/context-cards/${cardId}/approve`, { method: "POST" });
      fetchCards();
      fetchStats();
    } catch { /* ignore */ }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600" />
      </div>
    );
  }

  const tabs = [
    { key: "overview" as const, label: "Flywheel Status", icon: Repeat },
    { key: "traces" as const, label: "Traces", icon: FileText },
    { key: "cards" as const, label: "Context Cards", icon: Layers },
    { key: "evals" as const, label: "Eval Cases", icon: FlaskConical },
  ];

  const readinessColor = (level: string) => {
    switch (level) {
      case "adapter_candidate": return "text-green-700 bg-green-100";
      case "compression_ready": return "text-blue-700 bg-blue-100";
      case "eval_set_ready": return "text-indigo-700 bg-indigo-100";
      case "first_context_card": return "text-amber-700 bg-amber-100";
      default: return "text-slate-700 bg-slate-100";
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Repeat className="h-6 w-6 text-orange-600" /> Data Flywheel
          </h1>
          <p className="text-slate-500 text-sm">Approved runs to traces to context cards to eval cases</p>
        </div>
        <button onClick={() => { fetchStats(); fetchTraces(); fetchCards(); fetchEvals(); }} className="p-2 rounded hover:bg-slate-100">
          <RefreshCw className="h-4 w-4 text-slate-500" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.key ? "bg-white text-orange-700 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && stats && (
        <div>
          {/* Readiness Level */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-700">Flywheel Readiness</h3>
              <span className={`text-xs font-bold px-3 py-1 rounded-full ${readinessColor(stats.readiness_level)}`}>
                {stats.readiness_level.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>

            {/* Progress bar */}
            <div className="space-y-3">
              {Object.entries(stats.readiness_thresholds as Record<string, number>).map(([level, threshold]) => {
                const current = stats.traces.approved;
                const pct = Math.min(100, (current / threshold) * 100);
                return (
                  <div key={level}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600">{level.replace(/_/g, " ")}</span>
                      <span className="text-slate-500">{current}/{threshold}</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${pct >= 100 ? "bg-green-500" : "bg-orange-400"}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500">Total Traces</p>
              <p className="text-2xl font-bold text-slate-900">{stats.traces.total}</p>
              <p className="text-xs text-green-600">{stats.traces.approved} approved</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500">Context Cards</p>
              <p className="text-2xl font-bold text-slate-900">{stats.context_cards.total}</p>
              <p className="text-xs text-green-600">{stats.context_cards.approved} approved</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500">Eval Cases</p>
              <p className="text-2xl font-bold text-slate-900">{stats.eval_cases.total}</p>
              <p className="text-xs text-green-600">{stats.eval_cases.passing} passing</p>
            </div>
          </div>
        </div>
      )}

      {/* Traces Tab */}
      {activeTab === "traces" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Redacted Traces</h3>
          {traces.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No traces captured yet. Traces are created from approved AI interactions.</p>
          ) : (
            <div className="space-y-2">
              {traces.map((t) => (
                <div key={t.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">{t.source_type}</span>
                      {t.model_used && <span className="text-xs text-slate-500">{t.model_used}</span>}
                      {t.is_approved && <CheckCircle className="h-3.5 w-3.5 text-green-500" />}
                    </div>
                    <div className="flex items-center gap-1">
                      {!t.is_approved && (
                        <button onClick={() => handleApproveTrace(t.id)} className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200">Approve</button>
                      )}
                      {[1, 2, 3, 4, 5].map((s) => (
                        <button key={s} onClick={() => handleRateTrace(t.id, s)} className={`${(t.quality_score || 0) >= s ? "text-amber-500" : "text-slate-300"}`}>
                          <Star className="h-3.5 w-3.5" />
                        </button>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 truncate">{t.input_redacted?.substring(0, 100)}</p>
                  <p className="text-xs text-slate-500 truncate">{t.output_redacted?.substring(0, 100)}</p>
                  <div className="flex gap-3 mt-1 text-xs text-slate-400">
                    <span>Tokens: {t.tokens_used}</span>
                    <span>{t.created_at?.split("T")[0]}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Context Cards Tab */}
      {activeTab === "cards" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Context Cards</h3>
          {cards.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No context cards yet. Cards are generated from clustered traces.</p>
          ) : (
            <div className="space-y-2">
              {cards.map((c) => (
                <div key={c.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-sm font-medium text-slate-800">{c.title}</h4>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded ${c.status === "approved" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"}`}>{c.status}</span>
                      {c.status !== "approved" && (
                        <button onClick={() => handleApproveCard(c.id)} className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200">Approve</button>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-slate-600">{c.pattern_description}</p>
                  <div className="flex gap-3 mt-1 text-xs text-slate-400">
                    <span>Frequency: {c.frequency}</span>
                    <span>Quality: {c.avg_quality?.toFixed(1)}/5</span>
                    <span>Traces: {c.trace_ids?.length || 0}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Eval Cases Tab */}
      {activeTab === "evals" && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Evaluation Cases</h3>
          {evals.length === 0 ? (
            <p className="text-slate-400 text-sm py-8 text-center">No eval cases yet. Create eval cases from context cards to test AI quality.</p>
          ) : (
            <div className="space-y-2">
              {evals.map((e) => (
                <div key={e.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-500">Eval #{e.id}</span>
                    {e.pass_fail && (
                      <span className={`text-xs font-medium px-2 py-0.5 rounded ${e.pass_fail === "pass" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {e.pass_fail}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-700"><span className="font-medium">Input:</span> {e.input_text?.substring(0, 100)}</p>
                  <p className="text-xs text-slate-600"><span className="font-medium">Expected:</span> {e.expected_output?.substring(0, 100)}</p>
                  {e.actual_output && <p className="text-xs text-slate-500"><span className="font-medium">Actual:</span> {e.actual_output?.substring(0, 100)}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

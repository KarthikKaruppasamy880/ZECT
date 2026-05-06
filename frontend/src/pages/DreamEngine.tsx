import { useEffect, useState } from "react";
import {
  Sparkles,
  Play,
  CheckCircle,
  XCircle,
  BarChart3,
  Archive,
  RefreshCw,
} from "lucide-react";
import { showToast } from "@/components/Toast";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface DreamRun {
  id: number;
  project_id: number;
  status: string;
  episodes_processed: number;
  clusters_found: number;
  candidates_staged: number;
  candidates_prefiltered: number;
  episodes_decayed: number;
  workspaces_archived: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export default function DreamEngine() {
  const [projectId, setProjectId] = useState(1);
  const [runs, setRuns] = useState<DreamRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [maxAgeDays, setMaxAgeDays] = useState(14);
  const [minOccurrences, setMinOccurrences] = useState(3);
  const [lastResult, setLastResult] = useState<DreamRun | null>(null);

  const fetchRuns = async () => {
    try {
      const res = await fetch(`${API}/api/dream/runs/${projectId}?limit=20`);
      if (res.ok) setRuns(await res.json());
      else showToast("error", `Failed to load dream runs (${res.status})`);
    } catch (err) { showToast("error", "Network error loading dream runs"); }
  };

  useEffect(() => {
    setLoading(true);
    fetchRuns().finally(() => setLoading(false));
  }, [projectId]);

  const handleRun = async () => {
    setRunning(true);
    setLastResult(null);
    try {
      const res = await fetch(`${API}/api/dream/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          max_age_days: maxAgeDays,
          min_occurrences: minOccurrences,
        }),
      });
      if (res.ok) {
        const result = await res.json();
        setLastResult(result);
        showToast("success", "Dream cycle completed");
        fetchRuns();
      } else {
        showToast("error", `Dream cycle failed (${res.status})`);
      }
    } catch (err) { showToast("error", "Network error running dream cycle"); }
    setRunning(false);
  };

  const handleDecay = async () => {
    try {
      const res = await fetch(`${API}/api/dream/decay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, max_age_days: 30 }),
      });
      if (res.ok) {
        const data = await res.json();
        showToast("success", `Decayed ${data.decayed} old episodes`);
      } else {
        showToast("error", `Decay failed (${res.status})`);
      }
    } catch (err) { showToast("error", "Network error during decay"); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-purple-600" /> Dream Engine
          </h1>
          <p className="text-slate-500 text-sm">Automated pattern extraction, candidate staging, and memory decay</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">Project ID:</label>
          <input type="number" value={projectId} onChange={(e) => setProjectId(Number(e.target.value))} className="w-20 px-2 py-1 border rounded text-sm" />
        </div>
      </div>

      {/* Run Controls */}
      <div className="bg-white rounded-xl border border-purple-200 p-5 mb-6">
        <h3 className="text-sm font-semibold text-purple-700 mb-4">Run Dream Cycle</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="text-xs text-slate-600 block mb-1">Max Age (days)</label>
            <input type="number" value={maxAgeDays} onChange={(e) => setMaxAgeDays(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">Min Occurrences for Pattern</label>
            <input type="number" value={minOccurrences} onChange={(e) => setMinOccurrences(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div className="flex items-end gap-2">
            <button onClick={handleRun} disabled={running} className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50">
              {running ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? "Running..." : "Run Dream Cycle"}
            </button>
            <button onClick={handleDecay} className="px-3 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200" title="Manual decay">
              <Archive className="h-4 w-4" />
            </button>
          </div>
        </div>

        <p className="text-xs text-slate-500">
          The Dream Engine clusters episodic memories, extracts common patterns, stages them as candidate lessons,
          prefilters junk, decays old episodes, and archives stale workspaces.
        </p>
      </div>

      {/* Last Run Result */}
      {lastResult && (
        <div className={`rounded-xl border p-5 mb-6 ${lastResult.status === "completed" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            {lastResult.status === "completed" ? <CheckCircle className="h-4 w-4 text-green-600" /> : <XCircle className="h-4 w-4 text-red-600" />}
            Last Run — {lastResult.status.toUpperCase()}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <MiniStat label="Episodes" value={lastResult.episodes_processed} />
            <MiniStat label="Clusters" value={lastResult.clusters_found} />
            <MiniStat label="Candidates" value={lastResult.candidates_staged} />
            <MiniStat label="Prefiltered" value={lastResult.candidates_prefiltered} />
            <MiniStat label="Decayed" value={lastResult.episodes_decayed} />
            <MiniStat label="Archived" value={lastResult.workspaces_archived} />
          </div>
          {lastResult.error_message && (
            <p className="text-xs text-red-600 mt-2">{lastResult.error_message}</p>
          )}
        </div>
      )}

      {/* Run History */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" /> Run History
        </h3>
        {runs.length === 0 ? (
          <p className="text-slate-400 text-sm py-8 text-center">No dream cycles have been run yet. Click "Run Dream Cycle" above to start.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-2 text-slate-500 font-medium">ID</th>
                  <th className="text-left py-2 px-2 text-slate-500 font-medium">Status</th>
                  <th className="text-right py-2 px-2 text-slate-500 font-medium">Episodes</th>
                  <th className="text-right py-2 px-2 text-slate-500 font-medium">Clusters</th>
                  <th className="text-right py-2 px-2 text-slate-500 font-medium">Staged</th>
                  <th className="text-right py-2 px-2 text-slate-500 font-medium">Filtered</th>
                  <th className="text-right py-2 px-2 text-slate-500 font-medium">Decayed</th>
                  <th className="text-left py-2 px-2 text-slate-500 font-medium">Started</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2 px-2 font-mono text-slate-700">#{r.id}</td>
                    <td className="py-2 px-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded ${r.status === "completed" ? "bg-green-100 text-green-700" : r.status === "failed" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right font-mono">{r.episodes_processed}</td>
                    <td className="py-2 px-2 text-right font-mono">{r.clusters_found}</td>
                    <td className="py-2 px-2 text-right font-mono text-green-600">{r.candidates_staged}</td>
                    <td className="py-2 px-2 text-right font-mono text-amber-600">{r.candidates_prefiltered}</td>
                    <td className="py-2 px-2 text-right font-mono text-slate-500">{r.episodes_decayed}</td>
                    <td className="py-2 px-2 text-slate-500">{r.started_at?.split("T")[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center">
      <p className="text-lg font-bold text-slate-800">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}

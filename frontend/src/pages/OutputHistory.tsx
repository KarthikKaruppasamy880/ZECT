import { useState, useEffect } from "react";
import { History, Star, Trash2, BarChart3, Code, FileText, ClipboardList } from "lucide-react";

interface GeneratedOutput {
  id: number;
  user_id: number | null;
  session_id: number | null;
  output_type: string;
  feature: string;
  title: string;
  prompt_used: string;
  output_content: string;
  language: string;
  file_path: string;
  model_used: string;
  tokens_used: number;
  cost_usd: number;
  quality_score: number | null;
  was_accepted: boolean | null;
  created_at: string;
}

interface OutputStats {
  total_outputs: number;
  by_type: Record<string, number>;
  by_feature: Record<string, number>;
  total_tokens: number;
  total_cost_usd: number;
  avg_quality: number | null;
}

const API = import.meta.env.VITE_API_URL ?? "";

const typeIcon: Record<string, typeof Code> = {
  code: Code,
  plan: ClipboardList,
  review: FileText,
  blueprint: FileText,
};

export default function OutputHistory() {
  const [outputs, setOutputs] = useState<GeneratedOutput[]>([]);
  const [stats, setStats] = useState<OutputStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterType) params.set("output_type", filterType);
      const [outRes, statsRes] = await Promise.all([
        fetch(`${API}/api/outputs?${params}`),
        fetch(`${API}/api/outputs/stats`),
      ]);
      if (outRes.ok) setOutputs(await outRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch { /* API not available */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [filterType]);

  const rateOutput = async (id: number, score: number) => {
    try {
      await fetch(`${API}/api/outputs/${id}/rate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quality_score: score, was_accepted: score >= 3 }),
      });
      fetchData();
    } catch { /* error */ }
  };

  const deleteOutput = async (id: number) => {
    try {
      await fetch(`${API}/api/outputs/${id}`, { method: "DELETE" });
      fetchData();
    } catch { /* error */ }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <History className="h-6 w-6 text-purple-400" />
          Output History
        </h1>
        <p className="text-sm text-slate-400 mt-1">Browse all AI-generated code, plans, reviews, and blueprints</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Total</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.total_outputs}</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Tokens Used</p>
            <p className="text-2xl font-bold text-cyan-400 mt-1">{(stats.total_tokens / 1000).toFixed(1)}k</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Total Cost</p>
            <p className="text-2xl font-bold text-green-400 mt-1">${stats.total_cost_usd.toFixed(4)}</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Avg Quality</p>
            <p className="text-2xl font-bold text-yellow-400 mt-1">{stats.avg_quality ? `${stats.avg_quality}/5` : "—"}</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
            <p className="text-xs text-slate-400 uppercase">Types</p>
            <p className="text-2xl font-bold text-white mt-1">{Object.keys(stats.by_type).length}</p>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-3">
        <BarChart3 className="h-4 w-4 text-slate-400" />
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          <option value="code">Code</option>
          <option value="plan">Plan</option>
          <option value="review">Review</option>
          <option value="blueprint">Blueprint</option>
          <option value="checklist">Checklist</option>
          <option value="runbook">Runbook</option>
        </select>
      </div>

      {/* Outputs List */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8 text-center text-slate-400">Loading outputs...</div>
        ) : outputs.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8 text-center text-slate-400">
            <History className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No generated outputs yet</p>
            <p className="text-sm mt-1">Use Ask, Plan, Build, or Review to generate content</p>
          </div>
        ) : (
          outputs.map((o) => {
            const Icon = typeIcon[o.output_type] || FileText;
            return (
              <div key={o.id} className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
                <div
                  className="p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                  onClick={() => setExpanded(expanded === o.id ? null : o.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className="h-5 w-5 text-slate-400" />
                      <div>
                        <h3 className="text-white font-medium">{o.title || o.output_type}</h3>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-slate-400">{o.feature || o.output_type}</span>
                          <span className="text-xs text-slate-500">{o.model_used}</span>
                          <span className="text-xs text-cyan-400">{o.tokens_used} tokens</span>
                          {o.quality_score && (
                            <span className="text-xs text-yellow-400 flex items-center gap-0.5">
                              <Star className="h-3 w-3" /> {o.quality_score}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">
                        {o.created_at ? new Date(o.created_at).toLocaleDateString() : ""}
                      </span>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteOutput(o.id); }}
                        className="p-1.5 text-slate-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>

                {expanded === o.id && (
                  <div className="border-t border-slate-700 p-4 space-y-3">
                    {o.prompt_used && (
                      <div>
                        <p className="text-xs text-slate-400 uppercase mb-1">Prompt</p>
                        <p className="text-sm text-slate-300 bg-slate-900 rounded-lg p-3">{o.prompt_used}</p>
                      </div>
                    )}
                    {o.output_content && (
                      <div>
                        <p className="text-xs text-slate-400 uppercase mb-1">Output</p>
                        <pre className="text-sm text-slate-300 bg-slate-900 rounded-lg p-3 overflow-x-auto max-h-64">{o.output_content}</pre>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">Rate:</span>
                      {[1, 2, 3, 4, 5].map((s) => (
                        <button
                          key={s}
                          onClick={() => rateOutput(o.id, s)}
                          className={`p-1 ${o.quality_score && o.quality_score >= s ? "text-yellow-400" : "text-slate-600"} hover:text-yellow-400 transition-colors`}
                        >
                          <Star className="h-4 w-4" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

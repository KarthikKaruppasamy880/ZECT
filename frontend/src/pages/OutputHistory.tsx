import { useState, useEffect } from "react";
import { History, Star, Trash2, BarChart3, Code, FileText, ClipboardList, Info } from "lucide-react";

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

const typeColor: Record<string, string> = {
  code: "bg-blue-100 text-blue-700",
  plan: "bg-purple-100 text-purple-700",
  review: "bg-amber-100 text-amber-700",
  blueprint: "bg-cyan-100 text-cyan-700",
  checklist: "bg-green-100 text-green-700",
  runbook: "bg-rose-100 text-rose-700",
};

export default function OutputHistory() {
  const [outputs, setOutputs] = useState<GeneratedOutput[]>([]);
  const [stats, setStats] = useState<OutputStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [showGuide, setShowGuide] = useState(false);

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
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-100 rounded-xl">
            <History className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Output History</h1>
            <p className="text-sm text-slate-500">Browse all AI-generated code, plans, reviews, and blueprints</p>
          </div>
        </div>
        <button onClick={() => setShowGuide(!showGuide)} className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 text-sm">
          <Info className="h-4 w-4" /> Guide
        </button>
      </div>

      {/* Usage Guide */}
      {showGuide && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-5 space-y-2">
          <h3 className="font-semibold text-purple-900">How to use Output History</h3>
          <ul className="text-sm text-purple-800 space-y-1 list-disc list-inside">
            <li><strong>Browse outputs</strong> — All AI-generated content (code, plans, reviews, blueprints) is saved here automatically.</li>
            <li><strong>Filter by type</strong> — Use the dropdown to view only specific output types (e.g., just code or just plans).</li>
            <li><strong>Expand to view</strong> — Click any output to see the original prompt and full generated content.</li>
            <li><strong>Rate quality</strong> — Use the star rating (1-5) to track output quality. Ratings above 3 mark the output as "accepted".</li>
            <li><strong>Delete outputs</strong> — Click the trash icon to remove outputs you no longer need.</li>
            <li><strong>Token tracking</strong> — Each output shows the model used, tokens consumed, and cost for budget tracking.</li>
          </ul>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Total</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{stats?.total_outputs ?? 0}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Tokens Used</p>
          <p className="text-2xl font-bold text-cyan-600 mt-1">{stats ? (stats.total_tokens / 1000).toFixed(1) : "0"}k</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Total Cost</p>
          <p className="text-2xl font-bold text-green-600 mt-1">${stats ? stats.total_cost_usd.toFixed(4) : "0.0000"}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Avg Quality</p>
          <p className="text-2xl font-bold text-amber-500 mt-1">{stats?.avg_quality ? `${stats.avg_quality}/5` : "\u2014"}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-slate-500 uppercase font-medium">Types</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{stats ? Object.keys(stats.by_type).length : 0}</p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <BarChart3 className="h-4 w-4 text-slate-400" />
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="border border-slate-300 text-slate-700 rounded-lg px-3 py-2 text-sm bg-white"
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
          <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-400">Loading outputs...</div>
        ) : outputs.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-sm">
            <History className="h-12 w-12 mx-auto mb-3 text-slate-300" />
            <p className="font-medium text-slate-700">No generated outputs yet</p>
            <p className="text-sm text-slate-500 mt-1">Use Ask, Plan, Build, or Review to generate content.</p>
            <p className="text-sm text-slate-500">All AI-generated outputs will be saved here automatically.</p>
          </div>
        ) : (
          outputs.map((o) => {
            const Icon = typeIcon[o.output_type] || FileText;
            return (
              <div key={o.id} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:border-slate-300 transition-colors">
                <div
                  className="p-4 cursor-pointer hover:bg-slate-50 transition-colors"
                  onClick={() => setExpanded(expanded === o.id ? null : o.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className="h-5 w-5 text-slate-400" />
                      <div>
                        <h3 className="text-slate-900 font-medium">{o.title || o.output_type}</h3>
                        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
                          <span className={`text-xs px-2 py-0.5 rounded font-medium ${typeColor[o.output_type] || "bg-slate-100 text-slate-600"}`}>
                            {o.feature || o.output_type}
                          </span>
                          <span className="text-xs text-slate-400">{o.model_used}</span>
                          <span className="text-xs text-cyan-600 font-medium">{o.tokens_used} tokens</span>
                          {o.quality_score && (
                            <span className="text-xs text-amber-500 flex items-center gap-0.5">
                              <Star className="h-3 w-3" /> {o.quality_score}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">
                        {o.created_at ? new Date(o.created_at).toLocaleDateString() : ""}
                      </span>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteOutput(o.id); }}
                        className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>

                {expanded === o.id && (
                  <div className="border-t border-slate-200 p-4 space-y-3 bg-slate-50/50">
                    {o.prompt_used && (
                      <div>
                        <p className="text-xs text-slate-500 uppercase font-medium mb-1">Prompt</p>
                        <p className="text-sm text-slate-700 bg-white rounded-lg p-3 border border-slate-200">{o.prompt_used}</p>
                      </div>
                    )}
                    {o.output_content && (
                      <div>
                        <p className="text-xs text-slate-500 uppercase font-medium mb-1">Output</p>
                        <pre className="text-sm text-slate-700 bg-white rounded-lg p-3 overflow-x-auto max-h-64 border border-slate-200">{o.output_content}</pre>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">Rate:</span>
                      {[1, 2, 3, 4, 5].map((s) => (
                        <button
                          key={s}
                          onClick={() => rateOutput(o.id, s)}
                          className={`p-1 ${o.quality_score && o.quality_score >= s ? "text-amber-400" : "text-slate-300"} hover:text-amber-400 transition-colors`}
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

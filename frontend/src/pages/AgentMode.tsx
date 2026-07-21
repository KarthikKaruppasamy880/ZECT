import { useState, useEffect } from "react";
import { Bot, Play, Pause, Trash2, CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("zect_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

interface AgentStep {
  id: number;
  stage: string;
  step_index: number;
  output: string;
  tokens_used: number;
  duration_ms: number;
  status: string;
  model: string;
  created_at: string | null;
}

interface AgentRun {
  id: number;
  run_id: string;
  task: string;
  stages: string[];
  model: string;
  status: string;
  current_stage_index: number;
  auto_advance: boolean;
  total_tokens: number;
  steps: AgentStep[];
  created_at: string | null;
  completed_at: string | null;
}

const STAGE_COLORS: Record<string, string> = {
  ask: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  plan: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  build: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  review: "bg-green-500/20 text-green-400 border-green-500/30",
  deploy: "bg-red-500/20 text-red-400 border-red-500/30",
};

const STATUS_ICONS: Record<string, JSX.Element> = {
  completed: <CheckCircle className="w-4 h-4 text-green-400" />,
  running: <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />,
  paused: <Pause className="w-4 h-4 text-yellow-400" />,
  failed: <AlertCircle className="w-4 h-4 text-red-400" />,
  cancelled: <Trash2 className="w-4 h-4 text-gray-400" />,
  pending: <Clock className="w-4 h-4 text-gray-400" />,
};

export default function AgentMode() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [activeRun, setActiveRun] = useState<AgentRun | null>(null);
  const [task, setTask] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [autoAdvance, setAutoAdvance] = useState(true);
  const [selectedStages, setSelectedStages] = useState<string[]>(["ask", "plan", "build", "review", "deploy"]);
  const [repoContext, setRepoContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  // Mentrix powers /api/agent/run when MENTRIX_ENABLED=true

  useEffect(() => {
    fetchRuns();
  }, []);

  const fetchRuns = async () => {
    try {
      const res = await fetch(`${API}/api/agent/runs`, { headers: authHeaders() });
      if (res.ok) setRuns(await res.json());
    } catch { /* ignore */ }
  };

  const startRun = async () => {
    if (!task.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/agent/run`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          task: task.trim(),
          stages: selectedStages,
          model,
          repo_context: repoContext,
          auto_advance: autoAdvance,
        }),
      });
      if (res.ok) {
        const run = await res.json();
        setActiveRun(run);
        setTask("");
        fetchRuns();
      }
    } catch { /* ignore */ }
    setLoading(false);
  };

  const resumeRun = async (runId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/agent/run/${runId}/resume`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ model }),
      });
      if (res.ok) {
        const run = await res.json();
        setActiveRun(run);
        fetchRuns();
      }
    } catch { /* ignore */ }
    setLoading(false);
  };

  const cancelRun = async (runId: string) => {
    try {
      await fetch(`${API}/api/agent/run/${runId}`, { method: "DELETE", headers: authHeaders() });
      setActiveRun(null);
      fetchRuns();
    } catch { /* ignore */ }
  };

  const viewRun = async (runId: string) => {
    try {
      const res = await fetch(`${API}/api/agent/run/${runId}`, { headers: authHeaders() });
      if (res.ok) setActiveRun(await res.json());
    } catch { /* ignore */ }
  };

  const toggleStage = (stage: string) => {
    setSelectedStages((prev) =>
      prev.includes(stage) ? prev.filter((s) => s !== stage) : [...prev, stage]
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Bot className="w-8 h-8 text-teal-500" />
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Mode · Mentrix</h1>
          <p className="text-sm text-slate-400">Mentrix-powered delivery — Ask → Plan → Build → Review → Deploy</p>
        </div>
      </div>

      {/* New Run Form */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Start New Agent Run</h2>
        <textarea
          className="w-full bg-slate-900 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Describe the task for the agent to execute..."
          value={task}
          onChange={(e) => setTask(e.target.value)}
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Model</label>
            <select
              className="w-full bg-slate-900 border border-slate-600 rounded-lg p-2 text-white"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="gpt-4o">GPT-4o</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Stages</label>
            <div className="flex flex-wrap gap-2">
              {["ask", "plan", "build", "review", "deploy"].map((stage) => (
                <button
                  key={stage}
                  onClick={() => toggleStage(stage)}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                    selectedStages.includes(stage) ? STAGE_COLORS[stage] : "bg-slate-700 text-slate-500 border-slate-600"
                  }`}
                >
                  {stage}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={autoAdvance}
                onChange={(e) => setAutoAdvance(e.target.checked)}
                className="rounded bg-slate-700 border-slate-500"
              />
              Auto-advance
            </label>
          </div>
        </div>

        <textarea
          className="w-full bg-slate-900 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 min-h-[60px] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Optional: Paste repo context, code snippets, or requirements..."
          value={repoContext}
          onChange={(e) => setRepoContext(e.target.value)}
        />

        <button
          onClick={startRun}
          disabled={loading || !task.trim()}
          className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {loading ? "Running..." : "Start Agent Run"}
        </button>
      </div>

      {/* Active Run Details */}
      {activeRun && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {STATUS_ICONS[activeRun.status] || STATUS_ICONS.pending}
              <h2 className="text-lg font-semibold text-white">Run: {activeRun.run_id}</h2>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                activeRun.status === "completed" ? "bg-green-500/20 text-green-400" :
                activeRun.status === "running" ? "bg-blue-500/20 text-blue-400" :
                activeRun.status === "paused" ? "bg-yellow-500/20 text-yellow-400" :
                "bg-slate-600/20 text-slate-400"
              }`}>
                {activeRun.status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {activeRun.status === "paused" && (
                <button onClick={() => resumeRun(activeRun.run_id)} className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-sm flex items-center gap-1">
                  <Play className="w-3 h-3" /> Resume
                </button>
              )}
              {(activeRun.status === "running" || activeRun.status === "paused") && (
                <button onClick={() => cancelRun(activeRun.run_id)} className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-sm flex items-center gap-1">
                  <Trash2 className="w-3 h-3" /> Cancel
                </button>
              )}
            </div>
          </div>

          <p className="text-sm text-slate-300">{activeRun.task}</p>
          <p className="text-xs text-slate-500">Tokens: {activeRun.total_tokens.toLocaleString()} | Model: {activeRun.model}</p>

          {/* Pipeline Progress */}
          <div className="flex items-center gap-2">
            {activeRun.stages.map((stage, i) => {
              const step = activeRun.steps.find((s) => s.stage === stage);
              const isComplete = step?.status === "completed";
              const isCurrent = i === activeRun.current_stage_index && activeRun.status === "running";
              return (
                <div key={stage} className="flex items-center gap-2">
                  <div className={`px-3 py-1.5 rounded-lg border text-xs font-medium ${
                    isComplete ? "bg-green-500/20 text-green-400 border-green-500/30" :
                    isCurrent ? "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse" :
                    STAGE_COLORS[stage] || "bg-slate-700 text-slate-400 border-slate-600"
                  }`}>
                    {stage}
                  </div>
                  {i < activeRun.stages.length - 1 && <span className="text-slate-600">→</span>}
                </div>
              );
            })}
          </div>

          {/* Steps Output */}
          <div className="space-y-3">
            {activeRun.steps.map((step) => (
              <div key={step.id} className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden">
                <button
                  onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                  className="w-full flex items-center justify-between p-3 hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${STAGE_COLORS[step.stage] || ""}`}>
                      {step.stage}
                    </span>
                    <span className="text-xs text-slate-500">{step.duration_ms}ms | {step.tokens_used} tokens</span>
                  </div>
                  <span className="text-xs text-slate-500">{expandedStep === step.id ? "▼" : "▶"}</span>
                </button>
                {expandedStep === step.id && (
                  <div className="p-4 border-t border-slate-700">
                    <pre className="text-sm text-slate-300 whitespace-pre-wrap max-h-96 overflow-y-auto">
                      {step.output}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Run History */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Run History</h2>
        {runs.length === 0 ? (
          <p className="text-sm text-slate-500">No agent runs yet. Start one above.</p>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <button
                key={run.run_id}
                onClick={() => viewRun(run.run_id)}
                className="w-full flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-700 hover:border-slate-500 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  {STATUS_ICONS[run.status] || STATUS_ICONS.pending}
                  <div>
                    <p className="text-sm text-white">{run.task.length > 80 ? run.task.slice(0, 80) + "..." : run.task}</p>
                    <p className="text-xs text-slate-500">{run.run_id} | {run.stages.join(" → ")} | {run.total_tokens} tokens</p>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  run.status === "completed" ? "bg-green-500/20 text-green-400" :
                  run.status === "paused" ? "bg-yellow-500/20 text-yellow-400" :
                  "bg-slate-600/20 text-slate-400"
                }`}>
                  {run.status}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

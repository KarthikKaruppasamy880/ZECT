import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Bot,
  Play,
  Pause,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
  MonitorPlay,
  FileCode,
} from "lucide-react";
import { readMentrixWorkspace } from "@/lib/workspaceContext";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { isAgentModeEnabled } from "@/lib/featureFlags";
import {
  agentCancelRun,
  agentGetRun,
  agentListRuns,
  agentResumeRun,
  agentStartRun,
  codingAgentApprovePlan,
  type AgentModeRun,
} from "@/lib/api";

const STAGE_COLORS: Record<string, string> = {
  ask: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  plan: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  build: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  review: "bg-green-500/20 text-green-400 border-green-500/30",
  deploy: "bg-red-500/20 text-red-400 border-red-500/30",
};

const STATUS_ICONS: Record<string, JSX.Element> = {
  completed: <CheckCircle className="w-4 h-4 text-green-400" />,
  awaiting_approval: <CheckCircle className="w-4 h-4 text-teal-400" />,
  needs_human: <AlertCircle className="w-4 h-4 text-amber-400" />,
  running: <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />,
  paused: <Pause className="w-4 h-4 text-yellow-400" />,
  failed: <AlertCircle className="w-4 h-4 text-red-400" />,
  cancelled: <Trash2 className="w-4 h-4 text-gray-400" />,
  pending: <Clock className="w-4 h-4 text-gray-400" />,
};

export default function AgentMode() {
  const { activeRepoId, activeLocalPath, activeProjectKey } = useActiveProject();
  const [runs, setRuns] = useState<AgentModeRun[]>([]);
  const [activeRun, setActiveRun] = useState<AgentModeRun | null>(null);
  const [task, setTask] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [autoAdvance, setAutoAdvance] = useState(true);
  const [selectedStages, setSelectedStages] = useState<string[]>([
    "ask",
    "plan",
    "build",
    "review",
    "deploy",
  ]);
  const [repoContext, setRepoContext] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [projectKey, setProjectKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  useEffect(() => {
    const ws = readMentrixWorkspace();
    if (activeLocalPath) setWorkspace(activeLocalPath);
    else if (ws?.path) setWorkspace(ws.path);
    if (activeProjectKey) setProjectKey(activeProjectKey);
    else if (ws?.projectKey) setProjectKey(ws.projectKey);
  }, [activeLocalPath, activeProjectKey]);

  useEffect(() => {
    void fetchRuns();
  }, []);

  const fetchRuns = async () => {
    try {
      setRuns(await agentListRuns());
    } catch {
      /* ignore */
    }
  };

  const startRun = async () => {
    if (!task.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const body = await agentStartRun({
        task: task.trim(),
        stages: selectedStages,
        model,
        repo_context: repoContext,
        auto_advance: autoAdvance,
        workspace: workspace.trim(),
        project_key: projectKey.trim(),
        repo_id: activeRepoId ?? undefined,
      });
      setActiveRun(body);
      if (body.warning) setError(body.warning);
      setTask("");
      void fetchRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent run failed");
    } finally {
      setLoading(false);
    }
  };

  const resumeRun = async (runId: string) => {
    setLoading(true);
    setError(null);
    try {
      setActiveRun(await agentResumeRun(runId, model));
      void fetchRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Resume failed");
    } finally {
      setLoading(false);
    }
  };

  const approvePlan = async (runId: string) => {
    setLoading(true);
    setError(null);
    try {
      // Mission-backed runs only (run_id is "mission-<uuid>") -- this button
      // only ever renders for status === "awaiting_approval", which the
      // backend only sets on a mission-backed run.
      await codingAgentApprovePlan(runId.replace(/^mission-/, ""));
      setActiveRun(await agentGetRun(runId));
      void fetchRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setLoading(false);
    }
  };

  const cancelRun = async (runId: string) => {
    try {
      await agentCancelRun(runId);
      setActiveRun(null);
      void fetchRuns();
    } catch {
      /* ignore */
    }
  };

  const viewRun = async (runId: string) => {
    try {
      setActiveRun(await agentGetRun(runId));
    } catch {
      /* ignore */
    }
  };

  const toggleStage = (stage: string) => {
    setSelectedStages((prev) =>
      prev.includes(stage) ? prev.filter((s) => s !== stage) : [...prev, stage],
    );
  };

  const filesWritten = activeRun?.files_written || [];
  const runWorkspace = activeRun?.workspace || workspace;

  if (!isAgentModeEnabled()) {
    return (
      <div className="space-y-4 rounded-xl border border-amber-200 bg-amber-50 p-6" data-testid="agent-mode-gated">
        <div className="flex items-center gap-3">
          <Bot className="h-7 w-7 text-amber-700" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">Agent Mode is off</h1>
            <p className="text-sm text-slate-600 mt-1">
              Mentrix Delivery is the primary Agent Workspace experience. Enable the legacy Agent Mode
              orchestrator under Settings → Advanced when you need it.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/settings"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Open Settings
          </Link>
          <Link
            to="/mentrix"
            className="rounded-lg border border-teal-300 bg-white px-4 py-2 text-sm font-medium text-teal-800 hover:bg-teal-50"
          >
            Go to Mentrix Delivery
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="agent-mode-page">
      <div className="flex items-center gap-3">
        <Bot className="w-8 h-8 text-teal-500" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Agent Mode · Mentrix</h1>
          <p className="text-sm text-slate-500">
            Mentrix upgrade pipeline — Ask → Plan → <strong>Build (writes files)</strong> → Review →
            gates. Set a workspace path so code generation lands on disk, then open App Runner.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">Start New Agent Run</h2>
        <textarea
          data-testid="agent-task"
          className="w-full bg-slate-50 border border-slate-300 rounded-lg p-3 text-slate-900 placeholder-slate-400 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Describe the task for Mentrix to plan and build (e.g. Add health check endpoint and unit test)..."
          value={task}
          onChange={(e) => setTask(e.target.value)}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">Workspace path (required to write files)</label>
            <input
              data-testid="agent-workspace"
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 text-sm"
              placeholder="C:\Users\...\zect-workspaces\zinnia\zoas"
              value={workspace}
              onChange={(e) => setWorkspace(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">Lattice project key</label>
            <input
              data-testid="agent-project-key"
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 text-sm"
              placeholder="zinnia-zoas"
              value={projectKey}
              onChange={(e) => setProjectKey(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">Model</label>
            <select
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              <option value="gpt-4o-mini">GPT-4o Mini</option>
              <option value="gpt-4o">GPT-4o</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">Stages</label>
            <div className="flex flex-wrap gap-2">
              {["ask", "plan", "build", "review", "deploy"].map((stage) => (
                <button
                  key={stage}
                  type="button"
                  onClick={() => toggleStage(stage)}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                    selectedStages.includes(stage)
                      ? STAGE_COLORS[stage]
                      : "bg-slate-100 text-slate-500 border-slate-300"
                  }`}
                >
                  {stage}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Including <code>build</code> runs Mentrix <strong>upgrade</strong> (real codegen).
            </p>
          </div>
          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={autoAdvance}
                onChange={(e) => setAutoAdvance(e.target.checked)}
                className="rounded border-slate-400"
              />
              Auto-advance
            </label>
          </div>
        </div>

        <textarea
          className="w-full bg-slate-50 border border-slate-300 rounded-lg p-3 text-slate-900 placeholder-slate-400 min-h-[60px] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Optional: extra requirements / constraints (not used as disk path)"
          value={repoContext}
          onChange={(e) => setRepoContext(e.target.value)}
        />

        {error && (
          <div
            data-testid="agent-error"
            className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3"
          >
            {error}
          </div>
        )}

        <button
          data-testid="agent-start"
          type="button"
          onClick={() => void startRun()}
          disabled={loading || !task.trim()}
          className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {loading ? "Running Mentrix Build..." : "Start Agent Run"}
        </button>
      </div>

      {activeRun && (
        <div
          className="bg-white rounded-xl border border-slate-200 p-6 space-y-4"
          data-testid="agent-active-run"
        >
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              {STATUS_ICONS[activeRun.status] || STATUS_ICONS.pending}
              <h2 className="text-lg font-semibold text-slate-900">Run: {activeRun.run_id}</h2>
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                {activeRun.status}
              </span>
              {activeRun.mode && (
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-teal-50 text-teal-700 border border-teal-200">
                  mode={activeRun.mode}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {activeRun.status === "awaiting_approval" && (
                <button
                  type="button"
                  onClick={() => void approvePlan(activeRun.run_id)}
                  className="px-3 py-1 bg-teal-600 hover:bg-teal-500 text-white rounded text-sm flex items-center gap-1"
                  data-testid="agent-approve-plan"
                >
                  <CheckCircle className="w-3 h-3" /> Approve Plan &amp; Build
                </button>
              )}
              {activeRun.status === "paused" && (
                <button
                  type="button"
                  onClick={() => void resumeRun(activeRun.run_id)}
                  className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-sm flex items-center gap-1"
                >
                  <Play className="w-3 h-3" /> Resume
                </button>
              )}
              {(activeRun.status === "running" ||
                activeRun.status === "paused" ||
                activeRun.status === "awaiting_approval") && (
                <button
                  type="button"
                  onClick={() => void cancelRun(activeRun.run_id)}
                  className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-sm flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" /> Cancel
                </button>
              )}
              {runWorkspace && (
                <Link
                  data-testid="agent-open-app-runner"
                  to={`/app-runner?cwd=${encodeURIComponent(runWorkspace)}`}
                  className="px-3 py-1 bg-teal-600 hover:bg-teal-500 text-white rounded text-sm flex items-center gap-1"
                >
                  <MonitorPlay className="w-3 h-3" /> Open App Runner
                </Link>
              )}
            </div>
          </div>

          <p className="text-sm text-slate-700">{activeRun.task}</p>

          {activeRun.status === "awaiting_approval" && (
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-3 space-y-2" data-testid="agent-plan-review">
              <p className="text-xs font-semibold text-teal-800">
                Review the PLAN below before any worktree is created or file is written:
              </p>
              <pre className="text-xs text-slate-800 whitespace-pre-wrap font-mono bg-white border border-teal-100 rounded p-2 max-h-56 overflow-auto">
                {String(
                  (activeRun.result?.mission as { plan?: string } | undefined)?.plan || "(no plan text)",
                )}
              </pre>
            </div>
          )}

          <p className="text-xs text-slate-500">
            Tokens: {(activeRun.total_tokens ?? 0).toLocaleString()} | Model: {activeRun.model || "—"}
            {runWorkspace ? ` | Workspace: ${runWorkspace}` : ""}
          </p>

          {filesWritten.length > 0 && (
            <div
              className="rounded-lg border border-teal-200 bg-teal-50 p-3 space-y-1"
              data-testid="agent-files-written"
            >
              <p className="text-xs font-semibold text-teal-800 flex items-center gap-1">
                <FileCode className="w-3.5 h-3.5" /> Files written ({filesWritten.length})
              </p>
              <ul className="text-xs text-teal-900 font-mono space-y-0.5 max-h-40 overflow-auto">
                {filesWritten.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {filesWritten.length === 0 && activeRun.status !== "running" && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
              No files written. Ensure Workspace path points at a cloned repo and that{" "}
              <code>build</code> is in Stages (uses Mentrix upgrade mode).
            </p>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            {(activeRun.stages || []).map((stage, i) => {
              const step = (activeRun.steps || []).find((s) => s.stage === stage);
              const isComplete = step?.status === "completed";
              const isCurrent =
                i === (activeRun.current_stage_index ?? 0) && activeRun.status === "running";
              return (
                <div key={`${stage}-${i}`} className="flex items-center gap-2">
                  <div
                    className={`px-3 py-1.5 rounded-lg border text-xs font-medium ${
                      isComplete
                        ? "bg-green-500/20 text-green-700 border-green-500/30"
                        : isCurrent
                          ? "bg-blue-500/20 text-blue-700 border-blue-500/30 animate-pulse"
                          : STAGE_COLORS[stage] || "bg-slate-100 text-slate-600 border-slate-300"
                    }`}
                  >
                    {stage}
                  </div>
                  {i < (activeRun.stages?.length || 0) - 1 && (
                    <span className="text-slate-400">→</span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="space-y-3">
            {(activeRun.steps || []).map((step) => (
              <div
                key={step.id}
                className="bg-slate-50 rounded-lg border border-slate-200 overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                  className="w-full flex items-center justify-between p-3 hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium border ${STAGE_COLORS[step.stage] || "bg-slate-100 text-slate-600 border-slate-300"}`}
                    >
                      {step.stage}
                    </span>
                    <span className="text-xs text-slate-500">
                      {step.duration_ms}ms | {step.tokens_used} tokens
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">
                    {expandedStep === step.id ? "▼" : "▶"}
                  </span>
                </button>
                {expandedStep === step.id && (
                  <div className="p-4 border-t border-slate-200">
                    <pre className="text-sm text-slate-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
                      {step.output}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Run History</h2>
        {runs.length === 0 ? (
          <p className="text-sm text-slate-500">No agent runs yet. Start one above.</p>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => (
              <button
                key={run.run_id}
                type="button"
                onClick={() => void viewRun(run.run_id)}
                className="w-full flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 hover:border-slate-400 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  {STATUS_ICONS[run.status] || STATUS_ICONS.pending}
                  <div>
                    <p className="text-sm text-slate-900">
                      {run.task.length > 80 ? run.task.slice(0, 80) + "..." : run.task}
                    </p>
                    <p className="text-xs text-slate-500">
                      {run.run_id} | {(run.stages || []).join(" → ") || run.mode || "—"} |{" "}
                      {run.total_tokens ?? 0} tokens
                    </p>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
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

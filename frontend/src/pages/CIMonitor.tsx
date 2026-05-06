import { useState } from "react";
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Info,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  Zap,
  GitBranch,
  ChevronDown,
  ChevronUp,
  Wrench,
} from "lucide-react";
import { ciRuns, ciJobs, ciLogs, ciAnalyzeFailure, ciStatusBadge } from "@/lib/api";

interface CIRun {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  branch: string;
  commit_sha: string;
  commit_message: string;
  html_url: string;
  created_at: string;
  updated_at: string;
  run_number: number;
}

export default function CIMonitor() {
  const [showGuide, setShowGuide] = useState(false);
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [branch, setBranch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [runs, setRuns] = useState<CIRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<CIRun | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [failureLogs, setFailureLogs] = useState<any>(null);
  const [fixSuggestions, setFixSuggestions] = useState<any[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [expandedJob, setExpandedJob] = useState<number | null>(null);
  const [statusBadge, setStatusBadge] = useState<any>(null);

  // Load CI runs
  const loadRuns = async () => {
    if (!owner.trim() || !repo.trim()) { setError("Enter owner and repo"); return; }
    setLoading(true); setError("");
    try {
      const data = await ciRuns(owner, repo, branch || undefined, 15);
      setRuns(data);
      // Also load status badge
      const badge = await ciStatusBadge(owner, repo, branch || "main");
      setStatusBadge(badge);
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Load jobs for a run
  const loadJobs = async (run: CIRun) => {
    setSelectedRun(run);
    setJobs([]);
    setFailureLogs(null);
    setFixSuggestions([]);
    setLoading(true); setError("");
    try {
      const data = await ciJobs(owner, repo, run.id);
      setJobs(data);
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Load failure logs
  const loadFailureLogs = async (runId: number) => {
    setLoading(true); setError("");
    try {
      const data = await ciLogs(owner, repo, runId);
      setFailureLogs(data);
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Analyze failure with AI
  const analyzeFailure = async (runId: number) => {
    setAnalyzing(true); setError("");
    try {
      const suggestions = await ciAnalyzeFailure(owner, repo, runId);
      setFixSuggestions(suggestions);
    } catch (err: any) { setError(err.message); }
    setAnalyzing(false);
  };

  // Status icon
  const statusIcon = (conclusion: string | null, status: string) => {
    if (status === "in_progress" || status === "queued") {
      return <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />;
    }
    switch (conclusion) {
      case "success": return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failure": return <XCircle className="h-4 w-4 text-red-500" />;
      case "cancelled": return <XCircle className="h-4 w-4 text-slate-400" />;
      case "skipped": return <Clock className="h-4 w-4 text-slate-400" />;
      default: return <Clock className="h-4 w-4 text-yellow-500" />;
    }
  };

  const conclusionColor = (conclusion: string | null) => {
    switch (conclusion) {
      case "success": return "text-green-700 bg-green-50 border-green-200";
      case "failure": return "text-red-700 bg-red-50 border-red-200";
      case "cancelled": return "text-slate-500 bg-slate-50 border-slate-200";
      default: return "text-yellow-700 bg-yellow-50 border-yellow-200";
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Activity className="h-6 w-6 text-cyan-600" />
            CI/CD Monitor
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Monitor GitHub Actions, detect failures, and get AI-powered fix suggestions
          </p>
        </div>
        <button
          onClick={() => setShowGuide(!showGuide)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
        >
          <Info className="h-4 w-4" />
          Guide
        </button>
      </div>

      {/* Guide */}
      {showGuide && (
        <div className="bg-cyan-50 border border-cyan-200 rounded-xl p-5 space-y-3">
          <h3 className="font-semibold text-cyan-900">CI/CD Monitor — Intelligent Pipeline Monitoring</h3>
          <div className="text-sm text-cyan-800 space-y-2">
            <p><strong>Monitor</strong> — View all recent CI/CD workflow runs with status, branch, and timing info.</p>
            <p><strong>Inspect</strong> — Click a run to see individual jobs and their steps. Failed steps are highlighted.</p>
            <p><strong>AI Fix</strong> — For failed runs, click &quot;Analyze Failure&quot; to get AI-powered root cause analysis and fix suggestions.</p>
            <p><strong>Status Badge</strong> — See the current CI status at a glance for any branch.</p>
          </div>
        </div>
      )}

      {/* Repo input */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <input
            type="text"
            placeholder="Owner (e.g. KarthikKaruppasamy880)"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none"
          />
          <span className="text-slate-400">/</span>
          <input
            type="text"
            placeholder="Repo (e.g. ZECT)"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none"
          />
          <input
            type="text"
            placeholder="Branch (optional)"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            className="w-40 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-cyan-500 outline-none"
          />
          <button
            onClick={loadRuns}
            disabled={loading || !owner.trim() || !repo.trim()}
            className="px-4 py-2 bg-cyan-600 text-white text-sm rounded-lg hover:bg-cyan-700 disabled:opacity-50 flex items-center gap-1.5"
          >
            {loading && !analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Load
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 flex items-center gap-2">
          <XCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError("")} className="ml-auto text-red-500 hover:text-red-700 text-xs font-medium">Dismiss</button>
        </div>
      )}

      {/* Status badge */}
      {statusBadge && (
        <div className={`border rounded-xl p-4 flex items-center justify-between ${conclusionColor(statusBadge.status)}`}>
          <div className="flex items-center gap-3">
            {statusIcon(statusBadge.status, "")}
            <div>
              <p className="text-sm font-medium">
                CI Status: <span className="uppercase">{statusBadge.status}</span>
              </p>
              <p className="text-xs opacity-75">
                Branch: {statusBadge.branch} &middot; Commit: {statusBadge.commit} &middot; Run #{statusBadge.run_number}
              </p>
            </div>
          </div>
          {statusBadge.url && (
            <a href={statusBadge.url} target="_blank" rel="noopener noreferrer" className="text-sm hover:underline flex items-center gap-1">
              <ExternalLink className="h-3.5 w-3.5" /> View
            </a>
          )}
        </div>
      )}

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: CI Runs list */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-cyan-600" />
              Workflow Runs
              {runs.length > 0 && <span className="text-xs text-slate-400">({runs.length})</span>}
            </h3>
            <button onClick={loadRuns} className="text-slate-400 hover:text-slate-600">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          {runs.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <Activity className="h-10 w-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">No CI runs found</p>
              <p className="text-xs mt-1">Enter owner/repo and click Load</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
              {runs.map((run) => (
                <div
                  key={run.id}
                  className={`px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors ${
                    selectedRun?.id === run.id ? "bg-cyan-50 border-l-2 border-cyan-500" : ""
                  }`}
                  onClick={() => loadJobs(run)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      {statusIcon(run.conclusion, run.status)}
                      <span className="text-sm font-medium text-slate-900 truncate">{run.name}</span>
                    </div>
                    <span className="text-xs text-slate-400 shrink-0">#{run.run_number}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <GitBranch className="h-3 w-3" />
                      {run.branch}
                    </span>
                    <span>{run.commit_sha}</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                      run.conclusion === "success" ? "bg-green-100 text-green-700" :
                      run.conclusion === "failure" ? "bg-red-100 text-red-700" :
                      "bg-yellow-100 text-yellow-700"
                    }`}>
                      {run.conclusion || run.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 truncate">{run.commit_message}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Run details + AI analysis */}
        <div className="space-y-4">
          {/* Jobs */}
          {selectedRun && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                <h3 className="font-semibold text-slate-900 text-sm">
                  Jobs — {selectedRun.name} #{selectedRun.run_number}
                </h3>
                <div className="flex items-center gap-2">
                  {selectedRun.conclusion === "failure" && (
                    <button
                      onClick={() => { loadFailureLogs(selectedRun.id); analyzeFailure(selectedRun.id); }}
                      disabled={analyzing}
                      className="px-3 py-1.5 bg-red-600 text-white text-xs rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
                      Analyze Failure
                    </button>
                  )}
                  <a
                    href={selectedRun.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-400 hover:text-slate-600"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
              </div>

              {jobs.length === 0 ? (
                <div className="p-6 text-center text-slate-400">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                  <p className="text-sm">Loading jobs...</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {jobs.map((job: any) => (
                    <div key={job.id}>
                      <div
                        className="px-4 py-3 cursor-pointer hover:bg-slate-50 flex items-center justify-between"
                        onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                      >
                        <div className="flex items-center gap-2">
                          {statusIcon(job.conclusion, job.status)}
                          <span className="text-sm font-medium text-slate-700">{job.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {job.conclusion && (
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              job.conclusion === "success" ? "bg-green-100 text-green-700" :
                              job.conclusion === "failure" ? "bg-red-100 text-red-700" :
                              "bg-slate-100 text-slate-500"
                            }`}>
                              {job.conclusion}
                            </span>
                          )}
                          {expandedJob === job.id ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                        </div>
                      </div>
                      {expandedJob === job.id && job.steps && (
                        <div className="px-4 pb-3">
                          <div className="bg-slate-50 rounded-lg p-3 space-y-1">
                            {job.steps.map((step: any) => (
                              <div key={step.number} className="flex items-center gap-2 text-xs">
                                {statusIcon(step.conclusion, step.status)}
                                <span className={step.conclusion === "failure" ? "text-red-700 font-medium" : "text-slate-600"}>
                                  {step.name}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Failure logs */}
          {failureLogs && failureLogs.failed_jobs?.length > 0 && (
            <div className="bg-white border border-red-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-red-100 bg-red-50">
                <h3 className="font-semibold text-red-900 text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Failure Details
                </h3>
              </div>
              <div className="p-4 space-y-3">
                {failureLogs.failed_jobs.map((job: any, i: number) => (
                  <div key={i} className="bg-red-50 rounded-lg p-3">
                    <p className="text-sm font-medium text-red-800">{job.job_name}</p>
                    {job.failed_steps?.map((step: any, j: number) => (
                      <p key={j} className="text-xs text-red-600 mt-1 flex items-center gap-1">
                        <XCircle className="h-3 w-3" />
                        Step {step.number}: {step.name}
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Fix Suggestions */}
          {fixSuggestions.length > 0 && (
            <div className="bg-white border border-emerald-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-emerald-100 bg-emerald-50">
                <h3 className="font-semibold text-emerald-900 text-sm flex items-center gap-2">
                  <Wrench className="h-4 w-4" />
                  AI Fix Suggestions ({fixSuggestions.length})
                </h3>
              </div>
              <div className="p-4 space-y-4">
                {fixSuggestions.map((fix: any, i: number) => (
                  <div key={i} className="border border-slate-200 rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-slate-900">{fix.error_summary}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        fix.confidence === "high" ? "bg-green-100 text-green-700" :
                        fix.confidence === "medium" ? "bg-yellow-100 text-yellow-700" :
                        "bg-slate-100 text-slate-600"
                      }`}>
                        {fix.confidence} confidence
                      </span>
                    </div>
                    <p className="text-sm text-slate-600"><strong>Root Cause:</strong> {fix.root_cause}</p>
                    <p className="text-sm text-emerald-700"><strong>Suggested Fix:</strong> {fix.suggested_fix}</p>
                    {fix.fix_code && (
                      <pre className="bg-slate-950 text-green-300 font-mono text-xs p-3 rounded-lg overflow-x-auto">
                        {fix.fix_code}
                      </pre>
                    )}
                    {fix.file_path && (
                      <p className="text-xs text-slate-500">File: <span className="font-mono">{fix.file_path}</span></p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty state when no run selected */}
          {!selectedRun && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-12 text-center">
              <Activity className="h-12 w-12 mx-auto mb-3 text-slate-300" />
              <p className="text-slate-500">Select a workflow run to view details</p>
              <p className="text-xs text-slate-400 mt-1">Click any run in the left panel to inspect jobs and steps</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

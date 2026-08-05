import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { buildGenerate, buildApply, autofixRunAndFix, gitCreatePR, gitCommit, gitAdd, gitPush, loadContext } from "@/lib/api";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";
import { contextPageFor } from "@/lib/workspaceContext";
import CodeOutput from "@/components/CodeOutput";
import DiffViewer from "@/components/DiffViewer";
import ModelSelector from "@/components/ModelSelector";
import PromptHygieneTips from "@/components/PromptHygieneTips";
import ConversationHistory from "@/components/ConversationHistory";
import PhaseErrorBanner from "@/components/PhaseErrorBanner";
import AttachedContextPanel, { type AttachedFile } from "@/components/AttachedContextPanel";
import {
  Hammer,
  Play,
  Loader2,
  FileCode,
  Layers,
  Paperclip,
  Download,
  Copy,
  Check,
  GitPullRequest,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Wrench,
  ArrowUpRight,
} from "lucide-react";

export default function BuildPhase() {
  const location = useLocation();
  const { projectKey } = useWorkspaceRepoContext();
  const [planStep, setPlanStep] = useState("");
  const [techStack, setTechStack] = useState("");
  const [filePath, setFilePath] = useState("");
  const [repoId, setRepoId] = useState("");
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [copied, setCopied] = useState(false);
  const [generatedFiles, setGeneratedFiles] = useState<any[]>([]);

  // Plan → Build handoff: "Open in Build" navigates here with the plan text in
  // location.state, but a page refresh (or arriving fresh via the sidebar)
  // loses that — fall back to what Plan persisted to the context store, same
  // pattern PlanMode.tsx already uses for its own carried inputs.
  useEffect(() => {
    void (async () => {
      const state = location.state as { planStep?: string } | null;
      if (state?.planStep) {
        setPlanStep(state.planStep);
        return;
      }
      const ws = await loadContext(contextPageFor("workspace", projectKey), ["last_plan"]).catch(() => null);
      const savedPlan = ws?.entries.find((e) => e.key === "last_plan")?.value;
      if (savedPlan) setPlanStep(savedPlan.slice(0, 6000));
    })();
  }, [location.state, projectKey]);

  // Auto-fix state
  const [autoFixRunning, setAutoFixRunning] = useState(false);
  const [autoFixResult, setAutoFixResult] = useState<any>(null);
  const [autoFixCommand, setAutoFixCommand] = useState("");
  const [autoFixCwd, setAutoFixCwd] = useState("");
  const [autoFixRetries, setAutoFixRetries] = useState(3);

  // Create PR state
  const [prRepoPath, setPrRepoPath] = useState("");
  const [prTitle, setPrTitle] = useState("");
  const [prBody, setPrBody] = useState("");
  const [prBase, setPrBase] = useState("main");
  const [prCreating, setPrCreating] = useState(false);
  const [prResult, setPrResult] = useState<any>(null);
  const [showPrPanel, setShowPrPanel] = useState(false);
  const [showAutoFix, setShowAutoFix] = useState(false);

  const handleGenerate = async () => {
    if (!planStep.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setApplied(false);
    try {
      const contextParts: string[] = [];
      if (attachedFiles.length > 0) {
        contextParts.push(
          "Referenced files:\n" +
            attachedFiles
              .map((f) => `--- ${f.name} (${f.type}) ---\n${f.content}`)
              .join("\n\n")
        );
      }
      const projectContext = contextParts.length > 0 ? contextParts.join("\n") : undefined;
      const res = await buildGenerate(
        planStep,
        techStack || undefined,
        projectContext,
        filePath || undefined,
        repoId ? Number(repoId) : undefined
      );
      setResult(res);
      if (res.generated_code) {
        setGeneratedFiles((prev) => [
          ...prev,
          {
            file_path: res.file_path || filePath || `generated_${prev.length + 1}.${res.language || "ts"}`,
            code: res.generated_code,
            language: res.language,
            explanation: res.explanation,
            tokens: res.tokens_used,
            model: res.model,
          },
        ]);
      }
    } catch (e: any) {
      setError(e.message || "Failed to generate code");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!result?.generated_code || !repoId || !result.file_path) return;
    setApplying(true);
    setError("");
    try {
      await buildApply(Number(repoId), result.file_path, result.generated_code);
      setApplied(true);
    } catch (e: any) {
      setError(e.message || "Failed to write file");
    } finally {
      setApplying(false);
    }
  };

  const handleCopyAll = async () => {
    const allCode = generatedFiles.map((f) => `// ${f.file_path}\n${f.code}`).join("\n\n");
    await navigator.clipboard.writeText(allCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Auto-fix loop
  const handleAutoFix = async () => {
    if (!autoFixCommand.trim()) return;
    setAutoFixRunning(true);
    setAutoFixResult(null);
    try {
      const result = await autofixRunAndFix(
        autoFixCommand,
        autoFixCwd || undefined,
        undefined,
        undefined,
        autoFixRetries
      );
      setAutoFixResult(result);
    } catch (e: any) {
      setAutoFixResult({ success: false, error: e.message, iterations: [] });
    } finally {
      setAutoFixRunning(false);
    }
  };

  // Create PR
  const handleCreatePR = async () => {
    if (!prRepoPath.trim() || !prTitle.trim()) return;
    setPrCreating(true);
    try {
      // Stage, commit, push, then create PR
      await gitAdd(prRepoPath);
      await gitCommit(prRepoPath, prTitle);
      await gitPush(prRepoPath);
      const result = await gitCreatePR(prRepoPath, prTitle, prBody, prBase);
      setPrResult(result);
    } catch (e: any) {
      setPrResult({ error: e.message });
    } finally {
      setPrCreating(false);
    }
  };

  const handleDownloadAll = () => {
    const allCode = generatedFiles
      .map((f) => `// File: ${f.file_path}\n// Generated by ZECT Build Phase (${f.model})\n\n${f.code}`)
      .join("\n\n" + "=".repeat(80) + "\n\n");
    const blob = new Blob([allCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "zect-generated-code.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex gap-4">
      {/* Conversation History Sidebar */}
      <ConversationHistory mode="build" className="hidden lg:flex shrink-0" />

      <div className="flex-1 max-w-6xl space-y-6 min-w-0">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-100 rounded-xl">
            <Hammer className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Build Phase</h1>
            <p className="text-slate-500">Generate production-ready code from plan steps using AI</p>
          </div>
        </div>
        {generatedFiles.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">{generatedFiles.length} file(s) generated</span>
            <button onClick={handleCopyAll} className="p-2 text-slate-500 hover:text-blue-600 rounded-lg hover:bg-blue-50" title="Copy all code">
              {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
            </button>
            <button onClick={handleDownloadAll} className="p-2 text-slate-500 hover:text-blue-600 rounded-lg hover:bg-blue-50" title="Download all">
              <Download className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* Prompt Hygiene Tips */}
      <PromptHygieneTips mode="build" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel — Input & Output */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Plan Step / Feature Description *
                </label>
                <textarea
                  value={planStep}
                  onChange={(e) => setPlanStep(e.target.value)}
                  placeholder="e.g., Create a REST API endpoint for user authentication with JWT tokens, input validation, and rate limiting"
                  className="w-full h-32 p-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    <Layers className="inline h-4 w-4 mr-1" />
                    Tech Stack (optional)
                  </label>
                  <input
                    type="text"
                    value={techStack}
                    onChange={(e) => setTechStack(e.target.value)}
                    placeholder="e.g., TypeScript, React, FastAPI, PostgreSQL"
                    className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    <FileCode className="inline h-4 w-4 mr-1" />
                    Target File Path (optional)
                  </label>
                  <input
                    type="text"
                    value={filePath}
                    onChange={(e) => setFilePath(e.target.value)}
                    placeholder="e.g., src/api/auth.ts"
                    className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    <FolderGit2 className="inline h-4 w-4 mr-1" />
                    Repo ID (optional)
                  </label>
                  <input
                    type="text"
                    value={repoId}
                    onChange={(e) => setRepoId(e.target.value)}
                    placeholder="Cloned repo ID — enables retrieval + diff review"
                    className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                  />
                </div>
              </div>

              <ModelSelector value={selectedModel} onChange={setSelectedModel} />

              <button
                onClick={handleGenerate}
                disabled={loading || !planStep.trim()}
                className="flex items-center gap-2 px-5 py-2.5 bg-amber-600 hover:bg-amber-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {loading ? "Generating..." : "Generate Code"}
              </button>
            </div>
          </div>

          {/* Error */}
          <PhaseErrorBanner error={error} density="plain" />

          {/* Generated Code Result */}
          {result && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-slate-900">Generated Code</h2>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span className="px-2 py-1 bg-slate-100 rounded">{result.language}</span>
                  <span>{result.tokens_used} tokens</span>
                  <span className="text-slate-400">via {result.model}</span>
                </div>
              </div>
              {result.file_path && (
                <p className="text-sm text-slate-600 mb-2">
                  <FileCode className="inline h-4 w-4 mr-1" />
                  {result.file_path}
                </p>
              )}
              {result.explanation && (
                <p className="text-sm text-slate-600 mb-3 bg-blue-50 p-3 rounded-lg">{result.explanation}</p>
              )}
              <CodeOutput
                code={result.generated_code}
                language={result.language}
                title={result.file_path || result.language}
                maxHeight="500px"
              />

              {repoId && result.file_path && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  {result.file_existed && result.diff ? (
                    <>
                      <h3 className="text-sm font-semibold text-slate-700 mb-2">
                        Review changes to {result.file_path}
                      </h3>
                      <DiffViewer
                        sideBySide={result.diff.side_by_side}
                        unified={result.diff.unified}
                        stats={result.diff.stats}
                        leftLabel="Current"
                        rightLabel="Generated"
                      />
                    </>
                  ) : (
                    <p className="text-sm text-slate-500 mb-2">
                      {result.file_path} doesn't exist yet in this repo — nothing to diff against.
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-3">
                    <button
                      onClick={handleApply}
                      disabled={applying || applied}
                      className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white text-sm rounded-lg font-medium transition"
                    >
                      {applying ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Writing...</>
                      ) : applied ? (
                        <><Check className="h-4 w-4" /> Applied</>
                      ) : (
                        <><CheckCircle2 className="h-4 w-4" /> Apply to Repo</>
                      )}
                    </button>
                    {!applied && (
                      <button
                        onClick={() => setResult(null)}
                        className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm rounded-lg font-medium transition"
                      >
                        Reject
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Panel — Files & Context */}
        <div className="space-y-4">
          {/* Attached Files Panel */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Paperclip className="h-4 w-4" />
              Context Files ({attachedFiles.length})
            </h3>
            <AttachedContextPanel
              files={attachedFiles}
              onChange={setAttachedFiles}
              accent="amber"
            />
            {attachedFiles.length === 0 && (
              <p className="text-[10px] text-slate-400">
                Add files, repos, or code snippets for generation context
              </p>
            )}
          </div>

          {/* Generated Files List */}
          {generatedFiles.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="p-4 border-b border-slate-100">
                <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                  <FileCode className="h-4 w-4 text-green-500" />
                  Generated Files ({generatedFiles.length})
                </h3>
              </div>
              <div className="p-3 space-y-2 max-h-48 overflow-y-auto">
                {generatedFiles.map((file, idx) => (
                  <div key={idx} className="p-2 bg-green-50 rounded-lg border border-green-100">
                    <p className="text-xs font-medium text-slate-700 truncate">{file.file_path}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      {file.language} &bull; {file.tokens} tokens &bull; {file.model}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Auto-Fix Panel */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <button
              onClick={() => setShowAutoFix(!showAutoFix)}
              className="w-full p-4 border-b border-slate-100 flex items-center justify-between text-left"
            >
              <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Wrench className="h-4 w-4 text-orange-500" />
                Auto-Fix Loop
              </h3>
              <span className="text-xs text-slate-400">{showAutoFix ? "Hide" : "Show"}</span>
            </button>
            {showAutoFix && (
              <div className="p-4 space-y-3">
                <p className="text-xs text-slate-500">Run a command, detect errors, fix them automatically, and retry.</p>
                <input
                  type="text"
                  placeholder="Command to run (e.g., npm run build)"
                  value={autoFixCommand}
                  onChange={(e) => setAutoFixCommand(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-orange-500"
                />
                <input
                  type="text"
                  placeholder="Working directory (optional)"
                  value={autoFixCwd}
                  onChange={(e) => setAutoFixCwd(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-orange-500"
                />
                <div className="flex items-center gap-2">
                  <label className="text-xs text-slate-600">Max retries:</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={autoFixRetries}
                    onChange={(e) => setAutoFixRetries(Number(e.target.value))}
                    className="w-16 p-1.5 border border-slate-300 rounded text-xs"
                  />
                </div>
                <button
                  onClick={handleAutoFix}
                  disabled={autoFixRunning || !autoFixCommand.trim()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 text-white text-xs rounded-lg font-medium hover:bg-orange-700 disabled:bg-slate-300 transition"
                >
                  {autoFixRunning ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Running...</> : <><RefreshCw className="h-3.5 w-3.5" /> Run & Auto-Fix</>}
                </button>
                {autoFixResult && (
                  <div className={`p-3 rounded-lg text-xs ${autoFixResult.success ? "bg-green-50 border border-green-200 text-green-700" : "bg-red-50 border border-red-200 text-red-700"}`}>
                    <div className="flex items-center gap-1.5 mb-1">
                      {autoFixResult.success ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                      <span className="font-medium">{autoFixResult.success ? "Fixed!" : "Failed"}</span>
                    </div>
                    {autoFixResult.iterations?.map((iter: any, i: number) => (
                      <div key={i} className="mt-1 pl-4 border-l-2 border-slate-200">
                        <p className="font-mono">Attempt {i + 1}: {iter.success ? "Success" : "Error detected"}</p>
                        {iter.error_summary && <p className="text-slate-500 mt-0.5">{iter.error_summary}</p>}
                        {iter.fix_applied && <p className="text-green-600 mt-0.5">Fix: {iter.fix_applied}</p>}
                      </div>
                    ))}
                    {autoFixResult.error && <p>{autoFixResult.error}</p>}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Create PR Panel */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <button
              onClick={() => setShowPrPanel(!showPrPanel)}
              className="w-full p-4 border-b border-slate-100 flex items-center justify-between text-left"
            >
              <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <GitPullRequest className="h-4 w-4 text-violet-500" />
                Create PR
              </h3>
              <span className="text-xs text-slate-400">{showPrPanel ? "Hide" : "Show"}</span>
            </button>
            {showPrPanel && (
              <div className="p-4 space-y-3">
                <p className="text-xs text-slate-500">Commit generated code, push, and create a GitHub PR — all from here.</p>
                <input
                  type="text"
                  placeholder="Repo path (e.g., /home/user/project)"
                  value={prRepoPath}
                  onChange={(e) => setPrRepoPath(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-violet-500"
                />
                <input
                  type="text"
                  placeholder="PR title"
                  value={prTitle}
                  onChange={(e) => setPrTitle(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-violet-500"
                />
                <textarea
                  placeholder="PR description (optional)"
                  value={prBody}
                  onChange={(e) => setPrBody(e.target.value)}
                  rows={3}
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-violet-500 resize-none"
                />
                <input
                  type="text"
                  placeholder="Base branch (default: main)"
                  value={prBase}
                  onChange={(e) => setPrBase(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-violet-500"
                />
                <button
                  onClick={handleCreatePR}
                  disabled={prCreating || !prRepoPath.trim() || !prTitle.trim()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-violet-600 text-white text-xs rounded-lg font-medium hover:bg-violet-700 disabled:bg-slate-300 transition"
                >
                  {prCreating ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Creating PR...</> : <><GitPullRequest className="h-3.5 w-3.5" /> Commit, Push & Create PR</>}
                </button>
                {prResult && (
                  <div className={`p-3 rounded-lg text-xs ${prResult.error ? "bg-red-50 border border-red-200 text-red-700" : "bg-green-50 border border-green-200 text-green-700"}`}>
                    {prResult.error ? (
                      <p>{prResult.error}</p>
                    ) : (
                      <div>
                        <p className="font-medium">PR #{prResult.pr_number} created!</p>
                        {prResult.pr_url && (
                          <a href={prResult.pr_url} target="_blank" rel="noopener noreferrer" className="text-green-600 hover:text-green-700 underline flex items-center gap-1 mt-1">
                            <ArrowUpRight className="h-3 w-3" /> View on GitHub
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Quick Build Templates */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="p-4 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-slate-700">Quick Templates</h3>
            </div>
            <div className="p-3 space-y-1.5">
              {[
                "Create a REST API endpoint with CRUD operations",
                "Build a React component with state management",
                "Write unit tests with mocking",
                "Create a database migration script",
                "Build a CI/CD pipeline (GitHub Actions)",
                "Create auth middleware with JWT",
              ].map((template) => (
                <button
                  key={template}
                  onClick={() => setPlanStep(template)}
                  className="w-full text-left text-xs p-2 bg-slate-50 border border-slate-100 rounded-lg hover:border-amber-300 hover:bg-amber-50 transition text-slate-600 hover:text-amber-700"
                >
                  {template}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  RefreshCw,
  Loader2,
  Info,
  Plus,
  Upload,
  CheckCircle2,
  XCircle,
  FileText,
  ArrowUpRight,
  FolderOpen,
  AlertTriangle,
} from "lucide-react";
import {
  gitStatus,
  gitAdd,
  gitCommit,
  gitPush,
  gitBranch,
  gitCheckout,
  gitDiff,
  gitLog,
  gitBranches,
  gitPull,
  gitCreatePR,
} from "@/lib/api";

export default function GitOps() {
  const [showGuide, setShowGuide] = useState(false);
  const [repoPath, setRepoPath] = useState("");
  const [activeTab, setActiveTab] = useState<"status" | "commit" | "branches" | "log" | "pr">("status");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Status state
  const [statusData, setStatusData] = useState<any>(null);

  // Commit state
  const [commitMsg, setCommitMsg] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [diffContent, setDiffContent] = useState("");

  // Branch state
  const [branchList, setBranchList] = useState<any>(null);
  const [newBranchName, setNewBranchName] = useState("");

  // Log state
  const [logEntries, setLogEntries] = useState<any[]>([]);

  // PR state
  const [prTitle, setPrTitle] = useState("");
  const [prBody, setPrBody] = useState("");
  const [prBase, setPrBase] = useState("main");
  const [prHead, setPrHead] = useState("");
  const [prResult, setPrResult] = useState<any>(null);

  const clearMessages = () => { setError(""); setSuccess(""); };

  // Load git status
  const loadStatus = async () => {
    if (!repoPath.trim()) { setError("Enter a repo path first"); return; }
    setLoading(true); clearMessages();
    try {
      const data = await gitStatus(repoPath);
      setStatusData(data);
      setPrHead(data.branch || "");
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Stage files
  const stageFiles = async (files?: string[]) => {
    setLoading(true); clearMessages();
    try {
      await gitAdd(repoPath, files);
      setSuccess(files ? `Staged ${files.length} file(s)` : "Staged all changes");
      loadStatus();
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Commit
  const handleCommit = async () => {
    if (!commitMsg.trim()) { setError("Enter a commit message"); return; }
    setLoading(true); clearMessages();
    try {
      const result = await gitCommit(repoPath, commitMsg, selectedFiles.length > 0 ? selectedFiles : undefined);
      setSuccess(result.message || "Committed successfully");
      setCommitMsg("");
      setSelectedFiles([]);
      loadStatus();
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Push
  const handlePush = async () => {
    setLoading(true); clearMessages();
    try {
      const result = await gitPush(repoPath);
      setSuccess(result.message || "Pushed successfully");
      loadStatus();
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Pull
  const handlePull = async () => {
    setLoading(true); clearMessages();
    try {
      const result = await gitPull(repoPath);
      setSuccess(result.stdout || "Pulled successfully");
      loadStatus();
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Load diff
  const loadDiff = async (staged = false) => {
    setLoading(true); clearMessages();
    try {
      const result = await gitDiff(repoPath, staged);
      setDiffContent(result.diff || "No changes");
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Load branches
  const loadBranches = async () => {
    if (!repoPath.trim()) { setError("Enter a repo path first"); return; }
    setLoading(true); clearMessages();
    try {
      const data = await gitBranches(repoPath);
      setBranchList(data);
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Create branch
  const createBranch = async () => {
    if (!newBranchName.trim()) return;
    setLoading(true); clearMessages();
    try {
      const result = await gitBranch(repoPath, newBranchName, true);
      setSuccess(result.message || `Branch '${newBranchName}' created`);
      setNewBranchName("");
      loadBranches();
      loadStatus();
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Checkout branch
  const switchBranch = async (branch: string) => {
    setLoading(true); clearMessages();
    try {
      await gitCheckout(repoPath, branch);
      setSuccess(`Switched to branch '${branch}'`);
      loadBranches();
      loadStatus();
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Load log
  const loadLog = async () => {
    if (!repoPath.trim()) { setError("Enter a repo path first"); return; }
    setLoading(true); clearMessages();
    try {
      const entries = await gitLog(repoPath, 20);
      setLogEntries(entries);
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Create PR
  const handleCreatePR = async () => {
    if (!prTitle.trim()) { setError("Enter a PR title"); return; }
    setLoading(true); clearMessages();
    try {
      const result = await gitCreatePR(repoPath, prTitle, prBody, prBase, prHead || undefined);
      setPrResult(result);
      setSuccess(`PR #${result.pr_number} created!`);
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  // Tab change handler
  const onTabChange = (tab: typeof activeTab) => {
    setActiveTab(tab);
    clearMessages();
    if (tab === "status") loadStatus();
    if (tab === "branches") loadBranches();
    if (tab === "log") loadLog();
  };

  const tabs = [
    { key: "status" as const, label: "Status", icon: RefreshCw },
    { key: "commit" as const, label: "Commit", icon: GitCommit },
    { key: "branches" as const, label: "Branches", icon: GitBranch },
    { key: "log" as const, label: "Log", icon: FileText },
    { key: "pr" as const, label: "Create PR", icon: GitPullRequest },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-violet-600" />
            Git Operations
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Autonomous git add, commit, push, branch, and PR creation
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
        <div className="bg-violet-50 border border-violet-200 rounded-xl p-5 space-y-3">
          <h3 className="font-semibold text-violet-900">Git Operations — Autonomous Git Workflow</h3>
          <div className="text-sm text-violet-800 space-y-2">
            <p><strong>Status</strong> — View current branch, staged/modified/untracked files, and ahead/behind status.</p>
            <p><strong>Commit</strong> — Stage files, write a commit message, and commit changes. Then push to remote.</p>
            <p><strong>Branches</strong> — List, create, and switch between branches.</p>
            <p><strong>Log</strong> — View commit history with author, date, and message.</p>
            <p><strong>Create PR</strong> — Create a GitHub Pull Request directly from ZECT without leaving the tool.</p>
          </div>
        </div>
      )}

      {/* Repo path input */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
        <div className="flex items-center gap-3">
          <FolderOpen className="h-5 w-5 text-violet-500" />
          <input
            type="text"
            placeholder="/path/to/your/repo"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadStatus()}
            className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none"
          />
          <button
            onClick={loadStatus}
            disabled={loading || !repoPath.trim()}
            className="px-4 py-2 bg-violet-600 text-white text-sm rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-1.5"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Load
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 flex items-center gap-2">
          <XCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError("")} className="ml-auto text-red-500 hover:text-red-700 text-xs font-medium">Dismiss</button>
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {success}
          <button onClick={() => setSuccess("")} className="ml-auto text-green-500 hover:text-green-700 text-xs font-medium">Dismiss</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors flex items-center justify-center gap-1.5 ${
              activeTab === tab.key
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="space-y-4">
        {/* STATUS TAB */}
        {activeTab === "status" && (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-4">
            {!statusData ? (
              <div className="text-center text-slate-400 py-8">
                <GitBranch className="h-10 w-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Enter a repo path and click Load</p>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-4 flex-wrap">
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-violet-50 rounded-lg">
                    <GitBranch className="h-4 w-4 text-violet-600" />
                    <span className="text-sm font-medium text-violet-900">{statusData.branch}</span>
                  </div>
                  {statusData.ahead > 0 && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                      {statusData.ahead} ahead
                    </span>
                  )}
                  {statusData.behind > 0 && (
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded-full">
                      {statusData.behind} behind
                    </span>
                  )}
                  <div className="ml-auto flex gap-2">
                    <button onClick={handlePull} disabled={loading} className="px-3 py-1.5 bg-slate-100 text-slate-600 text-sm rounded-lg hover:bg-slate-200 disabled:opacity-50 flex items-center gap-1.5">
                      <ArrowUpRight className="h-3.5 w-3.5 rotate-180" /> Pull
                    </button>
                    <button onClick={handlePush} disabled={loading} className="px-3 py-1.5 bg-violet-600 text-white text-sm rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-1.5">
                      <Upload className="h-3.5 w-3.5" /> Push
                    </button>
                  </div>
                </div>

                {/* File lists */}
                {statusData.staged?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-green-700 mb-2">Staged ({statusData.staged.length})</h4>
                    <div className="space-y-1">
                      {statusData.staged.map((f: string) => (
                        <div key={f} className="flex items-center gap-2 text-sm text-green-600 bg-green-50 px-3 py-1.5 rounded">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span className="font-mono text-xs">{f}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {statusData.modified?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-amber-700 mb-2 flex items-center justify-between">
                      Modified ({statusData.modified.length})
                      <button onClick={() => stageFiles(statusData.modified)} className="text-xs text-violet-600 hover:text-violet-700 font-normal">Stage All</button>
                    </h4>
                    <div className="space-y-1">
                      {statusData.modified.map((f: string) => (
                        <div key={f} className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 px-3 py-1.5 rounded group">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          <span className="font-mono text-xs flex-1">{f}</span>
                          <button
                            onClick={() => stageFiles([f])}
                            className="text-xs text-violet-600 hover:text-violet-700 opacity-0 group-hover:opacity-100"
                          >
                            Stage
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {statusData.untracked?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-600 mb-2 flex items-center justify-between">
                      Untracked ({statusData.untracked.length})
                      <button onClick={() => stageFiles(statusData.untracked)} className="text-xs text-violet-600 hover:text-violet-700 font-normal">Stage All</button>
                    </h4>
                    <div className="space-y-1">
                      {statusData.untracked.map((f: string) => (
                        <div key={f} className="flex items-center gap-2 text-sm text-slate-500 bg-slate-50 px-3 py-1.5 rounded group">
                          <Plus className="h-3.5 w-3.5" />
                          <span className="font-mono text-xs flex-1">{f}</span>
                          <button
                            onClick={() => stageFiles([f])}
                            className="text-xs text-violet-600 hover:text-violet-700 opacity-0 group-hover:opacity-100"
                          >
                            Stage
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {!statusData.staged?.length && !statusData.modified?.length && !statusData.untracked?.length && (
                  <div className="text-center text-slate-400 py-4">
                    <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-400" />
                    <p className="text-sm">Working tree clean</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* COMMIT TAB */}
        {activeTab === "commit" && (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-4">
            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
              <GitCommit className="h-5 w-5 text-violet-600" />
              Commit Changes
            </h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Commit Message</label>
              <input
                type="text"
                placeholder="feat: add new feature..."
                value={commitMsg}
                onChange={(e) => setCommitMsg(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => stageFiles()}
                disabled={loading}
                className="px-4 py-2 bg-slate-100 text-slate-600 text-sm rounded-lg hover:bg-slate-200 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Plus className="h-4 w-4" /> Stage All
              </button>
              <button
                onClick={handleCommit}
                disabled={loading || !commitMsg.trim()}
                className="px-4 py-2 bg-violet-600 text-white text-sm rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-1.5"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitCommit className="h-4 w-4" />}
                Commit
              </button>
              <button
                onClick={handlePush}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Upload className="h-4 w-4" /> Push
              </button>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-slate-700">Diff Preview</label>
                <div className="flex gap-2">
                  <button onClick={() => loadDiff(false)} className="text-xs text-violet-600 hover:text-violet-700">Unstaged</button>
                  <button onClick={() => loadDiff(true)} className="text-xs text-violet-600 hover:text-violet-700">Staged</button>
                </div>
              </div>
              <pre className="bg-slate-950 text-green-300 font-mono text-xs p-4 rounded-lg max-h-64 overflow-auto whitespace-pre-wrap">
                {diffContent || "Click 'Unstaged' or 'Staged' to view diff"}
              </pre>
            </div>
          </div>
        )}

        {/* BRANCHES TAB */}
        {activeTab === "branches" && (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-4">
            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-violet-600" />
              Branches
            </h3>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="New branch name..."
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createBranch()}
                className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-violet-500 outline-none"
              />
              <button
                onClick={createBranch}
                disabled={loading || !newBranchName.trim()}
                className="px-4 py-2 bg-violet-600 text-white text-sm rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Plus className="h-4 w-4" /> Create & Checkout
              </button>
            </div>
            {branchList ? (
              <div className="space-y-1">
                {branchList.branches?.map((b: string) => (
                  <div
                    key={b}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg ${
                      b === branchList.current ? "bg-violet-50 border border-violet-200" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <GitBranch className={`h-4 w-4 ${b === branchList.current ? "text-violet-600" : "text-slate-400"}`} />
                      <span className={`text-sm ${b === branchList.current ? "font-medium text-violet-900" : "text-slate-700"}`}>
                        {b}
                      </span>
                      {b === branchList.current && (
                        <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full">current</span>
                      )}
                    </div>
                    {b !== branchList.current && (
                      <button
                        onClick={() => switchBranch(b)}
                        className="text-xs text-violet-600 hover:text-violet-700"
                      >
                        Checkout
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-slate-400 py-4">
                <p className="text-sm">Load a repo to see branches</p>
              </div>
            )}
          </div>
        )}

        {/* LOG TAB */}
        {activeTab === "log" && (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <FileText className="h-4 w-4 text-violet-600" />
                Commit History
              </h3>
              <button onClick={loadLog} className="text-slate-400 hover:text-slate-600">
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
            {logEntries.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">Load a repo to see commit history</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
                {logEntries.map((entry: any, i: number) => (
                  <div key={i} className="px-4 py-3 hover:bg-slate-50">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3 min-w-0">
                        <div className="mt-1">
                          <GitCommit className="h-4 w-4 text-violet-500" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-900 truncate">{entry.message}</p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {entry.author} &middot; {entry.date}
                          </p>
                        </div>
                      </div>
                      <span className="text-xs font-mono text-slate-400 shrink-0 ml-3">{entry.sha?.slice(0, 7)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* CREATE PR TAB */}
        {activeTab === "pr" && (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-4">
            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
              <GitPullRequest className="h-5 w-5 text-violet-600" />
              Create Pull Request
            </h3>
            <p className="text-sm text-slate-500">
              Create a GitHub PR directly from ZECT — no need to switch to a browser.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">PR Title</label>
                <input
                  type="text"
                  placeholder="feat: add new feature"
                  value={prTitle}
                  onChange={(e) => setPrTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-violet-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  placeholder="Describe your changes..."
                  value={prBody}
                  onChange={(e) => setPrBody(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-violet-500 outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Base Branch</label>
                  <input
                    type="text"
                    placeholder="main"
                    value={prBase}
                    onChange={(e) => setPrBase(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-violet-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Head Branch (current)</label>
                  <input
                    type="text"
                    placeholder="feature-branch"
                    value={prHead}
                    onChange={(e) => setPrHead(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-violet-500 outline-none"
                  />
                </div>
              </div>
              <button
                onClick={handleCreatePR}
                disabled={loading || !prTitle.trim()}
                className="w-full px-4 py-2.5 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitPullRequest className="h-4 w-4" />}
                Create Pull Request
              </button>
            </div>

            {prResult && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
                <p className="text-sm font-medium text-green-700">
                  PR #{prResult.pr_number} created successfully!
                </p>
                {prResult.pr_url && (
                  <a
                    href={prResult.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-green-600 hover:text-green-700 underline flex items-center gap-1"
                  >
                    <ArrowUpRight className="h-3.5 w-3.5" />
                    View on GitHub
                  </a>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

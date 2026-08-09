import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  GitBranch,
  GitCompare,
  Loader2,
  RefreshCw,
  Save,
  AlertCircle,
  Sparkles,
  Code2,
} from "lucide-react";
import MonacoCodeEditor, { type EditorSelection } from "@/components/MonacoCodeEditor";
import PhaseErrorBanner from "@/components/PhaseErrorBanner";
import WorkspaceDiffPanel from "@/components/WorkspaceDiffPanel";
import WorkspaceInlinePanel, { replaceSelectionInContent } from "@/components/WorkspaceInlinePanel";
import WorkspaceMentrixTimeline from "@/components/WorkspaceMentrixTimeline";
import WorkspaceSymbolsPanel, { type SymbolJumpTarget } from "@/components/WorkspaceSymbolsPanel";
import WorkspaceTerminal from "@/components/WorkspaceTerminal";
import MentrixCodingAgentPanel from "@/components/MentrixCodingAgentPanel";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import {
  fileList,
  fileRead,
  fileTree,
  fileWrite,
  gitBranches,
  gitRestore,
  gitStatus,
  gitWorktrees,
  mentrixGetRun,
  mentrixListRuns,
} from "@/lib/api";
import { readMentrixWorkspace } from "@/lib/workspaceContext";
import { isPathInsideRoot, languageFromPath, normalizePath, pathMatchesMarker, relativeToRoot } from "@/lib/workspacePaths";

type TreeNode = {
  name: string;
  path: string;
  is_dir: boolean;
  children?: TreeNode[];
  /** True after we attempted a list fetch (even if empty). */
  childrenLoaded?: boolean;
};

function normalizeTreeNodes(nodes: unknown[]): TreeNode[] {
  if (!Array.isArray(nodes)) return [];
  return nodes.map((raw) => {
    const n = raw as Record<string, unknown>;
    const path = normalizePath(String(n.path || ""));
    const isDir = Boolean(n.is_dir);
    const childrenRaw = n.children;
    const children = Array.isArray(childrenRaw) ? normalizeTreeNodes(childrenRaw) : undefined;
    return {
      name: String(n.name || path.split("/").pop() || path),
      path,
      is_dir: isDir,
      children,
      childrenLoaded: isDir ? Array.isArray(childrenRaw) : undefined,
    };
  });
}

function upsertChildren(nodes: TreeNode[], dirPath: string, children: TreeNode[]): TreeNode[] {
  const target = normalizePath(dirPath);
  return nodes.map((node) => {
    if (normalizePath(node.path) === target) {
      return { ...node, children, childrenLoaded: true };
    }
    if (node.children?.length) {
      return { ...node, children: upsertChildren(node.children, target, children) };
    }
    return node;
  });
}

function findNode(nodes: TreeNode[], path: string): TreeNode | null {
  const target = normalizePath(path);
  for (const node of nodes) {
    if (normalizePath(node.path) === target) return node;
    if (node.children?.length) {
      const hit = findNode(node.children, target);
      if (hit) return hit;
    }
  }
  return null;
}

function countGitChanges(st: Record<string, unknown> | null | undefined): number {
  if (!st) return 0;
  const staged = Array.isArray(st.staged) ? st.staged.length : 0;
  const modified = Array.isArray(st.modified) ? st.modified.length : 0;
  const untracked = Array.isArray(st.untracked) ? st.untracked.length : 0;
  if (staged || modified || untracked) return staged + modified + untracked;
  if (Array.isArray(st.files)) return st.files.length;
  return 0;
}

function collectGitPaths(st: Record<string, unknown> | null | undefined): string[] {
  if (!st) return [];
  const out: string[] = [];
  for (const key of ["staged", "modified", "untracked"] as const) {
    const arr = st[key];
    if (Array.isArray(arr)) out.push(...arr.map(String));
  }
  return out;
}

/**
 * Phase 3 — unified developer workspace (Stages A–E).
 */
export default function DeveloperWorkspace() {
  const [searchParams] = useSearchParams();
  const deepRunId = searchParams.get("run");
  const deepPath = searchParams.get("path") || "";
  const deepSession = searchParams.get("session") || "";
  const deepGoal = searchParams.get("goal") || "";
  const { activeLocalPath, activeRepo, activeRepoId } = useActiveProject();
  const mentrix = readMentrixWorkspace();
  const rootPath = (activeLocalPath || mentrix?.path || "").trim();

  const [tree, setTree] = useState<TreeNode[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState("");
  const [browsingDir, setBrowsingDir] = useState<string>("");
  const [loadingDir, setLoadingDir] = useState(false);
  const [content, setContent] = useState("");
  const [baseline, setBaseline] = useState("");
  const [loadingTree, setLoadingTree] = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [branch, setBranch] = useState("");
  const [gitSummary, setGitSummary] = useState("");
  const [dirtyCount, setDirtyCount] = useState(0);
  const [gitChanged, setGitChanged] = useState<string[]>([]);
  const [agentFiles, setAgentFiles] = useState<string[]>([]);
  const [showDiff, setShowDiff] = useState(false);
  const [showInline, setShowInline] = useState(false);
  const [showSymbols, setShowSymbols] = useState(false);
  const [selection, setSelection] = useState<EditorSelection | null>(null);
  const [revealLine, setRevealLine] = useState<number | null>(null);
  const [worktrees, setWorktrees] = useState<{ path?: string; branch?: string; is_current?: boolean }[]>([]);
  const [agentModel, setAgentModel] = useState("gpt-4o-mini");

  const dirty = content !== baseline && Boolean(selectedPath);
  const sideOpen = showDiff || showInline;
  const currentWorktree = worktrees.find((w) => w.is_current) || worktrees[0];
  const isLinkedWorktree = worktrees.length > 1;
  const rootNorm = rootPath ? normalizePath(rootPath) : "";
  const browsingNode = browsingDir ? findNode(tree, browsingDir) : null;
  const browsingChildren = browsingNode?.children || [];

  const refreshGit = useCallback(async (root: string) => {
    if (!root) return;
    try {
      const [st, br, wt] = await Promise.all([gitStatus(root), gitBranches(root), gitWorktrees(root).catch(() => null)]);
      setBranch(br?.current || st?.branch || "");
      const count = countGitChanges(st);
      setDirtyCount(count);
      setGitSummary(st?.clean || count === 0 ? "clean" : `${count} change${count === 1 ? "" : "s"}`);
      setGitChanged(collectGitPaths(st));
      setWorktrees(Array.isArray(wt?.worktrees) ? wt.worktrees : []);
    } catch {
      setBranch("");
      setGitSummary("git unavailable");
      setDirtyCount(0);
      setGitChanged([]);
      setWorktrees([]);
    }
  }, []);

  const refreshAgentMarkers = useCallback(async () => {
    try {
      if (deepRunId && /^\d+$/.test(deepRunId)) {
        const run = await mentrixGetRun(Number(deepRunId));
        const files = [
          ...(Array.isArray(run?.batch_files) ? run.batch_files : []),
          ...(Array.isArray(run?.files_written) ? run.files_written : []),
        ].map(String);
        setAgentFiles([...new Set(files)]);
        return;
      }
      const runs = await mentrixListRuns(5);
      const arr = Array.isArray(runs) ? runs : [];
      const withFiles = arr.find((r) => Array.isArray(r?.files_written) && r.files_written.length > 0);
      setAgentFiles(withFiles?.files_written?.map(String) || []);
    } catch {
      setAgentFiles([]);
    }
  }, [deepRunId]);

  const loadTree = useCallback(async () => {
    if (!rootPath) {
      setTree([]);
      return;
    }
    setLoadingTree(true);
    setError("");
    try {
      const nodes = await fileTree(rootPath, 5);
      const normalized = normalizeTreeNodes(Array.isArray(nodes) ? nodes : []);
      setTree(normalized);
      setExpanded(new Set([normalizePath(rootPath)]));
      setBrowsingDir("");
      setSelectedPath("");
      setContent("");
      setBaseline("");
      await Promise.all([refreshGit(rootPath), refreshAgentMarkers()]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tree");
      setTree([]);
    } finally {
      setLoadingTree(false);
    }
  }, [rootPath, refreshGit, refreshAgentMarkers]);

  useEffect(() => {
    void loadTree();
  }, [loadTree]);

  const loadDirChildren = useCallback(async (dirPath: string): Promise<TreeNode[]> => {
    const norm = normalizePath(dirPath);
    setLoadingDir(true);
    setError("");
    try {
      const listed = await fileList(dirPath);
      const children = normalizeTreeNodes(Array.isArray(listed) ? listed : []).map((c) =>
        c.is_dir ? { ...c, children: [], childrenLoaded: false } : { ...c, childrenLoaded: undefined },
      );
      setTree((prev) => upsertChildren(prev, norm, children));
      return children;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to list directory");
      setTree((prev) => upsertChildren(prev, norm, []));
      return [];
    } finally {
      setLoadingDir(false);
    }
  }, []);

  const openFile = async (path: string, line?: number) => {
    const norm = normalizePath(path);
    if (!rootPath || !isPathInsideRoot(norm, rootPath)) {
      setError("File is outside the active workspace root");
      return;
    }
    setBrowsingDir("");
    setLoadingFile(true);
    setError("");
    try {
      const file = await fileRead(path);
      const text = typeof file?.content === "string" ? file.content : "";
      setSelectedPath(norm);
      setContent(text);
      setBaseline(text);
      setSelection(null);
      setRevealLine(line && line > 0 ? line : null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to read file");
    } finally {
      setLoadingFile(false);
    }
  };

  const openAgentPath = (relOrAbs: string) => {
    if (!rootPath) return;
    const abs =
      isPathInsideRoot(normalizePath(relOrAbs), rootPath) &&
      (normalizePath(relOrAbs).startsWith(normalizePath(rootPath)) ||
        /^[a-zA-Z]:[\\/]/.test(relOrAbs) ||
        relOrAbs.startsWith("/"))
        ? normalizePath(relOrAbs)
        : normalizePath(`${rootPath.replace(/[/\\]+$/, "")}/${relOrAbs.replace(/^[/\\]+/, "")}`);
    void openFile(abs);
    setAgentFiles((prev) => (prev.includes(relOrAbs) ? prev : [...prev, relOrAbs]));
  };

  useEffect(() => {
    if (!deepPath || !rootPath) return;
    const abs =
      deepPath.includes("/") || deepPath.includes("\\")
        ? deepPath
        : `${rootPath.replace(/[/\\]+$/, "")}/${deepPath}`;
    const t = window.setTimeout(() => {
      void openFile(abs);
      setShowDiff(true);
    }, 400);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deep-link one-shot
  }, [deepPath, rootPath, deepRunId]);

  const openDirectory = async (path: string) => {
    const norm = normalizePath(path);
    setSelectedPath("");
    setContent("");
    setBaseline("");
    setRevealLine(null);
    setBrowsingDir(norm);
    setExpanded((prev) => new Set(prev).add(norm));
    await loadDirChildren(path);
  };

  const jumpToSymbol = (target: SymbolJumpTarget) => {
    void openFile(target.filePath, target.line);
  };

  const saveFile = async () => {
    if (!selectedPath || !rootPath) return;
    if (!isPathInsideRoot(selectedPath, rootPath)) {
      setError("Refusing to save outside the active workspace root");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await fileWrite(selectedPath, content, true);
      setBaseline(content);
      await refreshGit(rootPath);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const revertFile = async () => {
    if (!selectedPath || !rootPath) return;
    setSaving(true);
    setError("");
    try {
      const rel = relativeToRoot(selectedPath, rootPath);
      if (rel) {
        try {
          await gitRestore(rootPath, [rel]);
        } catch {
          /* disk may already match HEAD; still re-read */
        }
      }
      const file = await fileRead(selectedPath);
      const text = typeof file?.content === "string" ? file.content : "";
      setContent(text);
      setBaseline(text);
      setSelection(null);
      await refreshGit(rootPath);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Revert failed");
    } finally {
      setSaving(false);
    }
  };

  const applyInlineCode = (code: string, mode: "replace-selection" | "replace-file") => {
    if (mode === "replace-selection" && selection) {
      setContent(replaceSelectionInContent(content, selection, code));
    } else {
      setContent(code);
    }
  };

  const toggleDir = (path: string) => {
    const norm = normalizePath(path);
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(norm)) {
        next.delete(norm);
        return next;
      }
      next.add(norm);
      return next;
    });
    // Always refresh children when expanding — depth-limited tree often has empty children.
    void loadDirChildren(path);
  };

  const onDirClick = (path: string) => {
    void openDirectory(path);
  };

  const renderTree = (nodes: TreeNode[], depth = 0): ReactNode =>
    nodes.map((node) => {
      const path = normalizePath(node.path);
      const isOpen = expanded.has(path);
      if (node.is_dir) {
        const childCount = node.children?.length;
        return (
          <div key={path}>
            <button
              type="button"
              className={`w-full flex items-center gap-1 px-2 py-1 text-left text-xs hover:bg-slate-100 ${
                browsingDir === path ? "bg-sky-50 text-sky-900 font-medium" : "text-slate-700"
              }`}
              style={{ paddingLeft: 8 + depth * 12 }}
              onClick={() => onDirClick(node.path)}
              onDoubleClick={() => toggleDir(node.path)}
              data-testid={`workspace-dir-${node.name}`}
              title="Click to browse · double-click to expand/collapse"
            >
              <span
                className="shrink-0 p-0.5"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleDir(node.path);
                }}
              >
                {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              </span>
              <Folder className="h-3.5 w-3.5 text-amber-600 shrink-0" />
              <span className="truncate">{node.name}</span>
              {typeof childCount === "number" && node.childrenLoaded ? (
                <span className="ml-auto text-[10px] text-slate-400">{childCount}</span>
              ) : null}
            </button>
            {isOpen ? (
              node.children && node.children.length > 0 ? (
                renderTree(node.children, depth + 1)
              ) : node.childrenLoaded ? (
                <p className="px-2 py-1 text-[10px] text-slate-400" style={{ paddingLeft: 20 + depth * 12 }}>
                  Empty folder
                </p>
              ) : loadingDir && browsingDir === path ? (
                <p className="px-2 py-1 text-[10px] text-slate-400" style={{ paddingLeft: 20 + depth * 12 }}>
                  Loading…
                </p>
              ) : null
            ) : null}
          </div>
        );
      }
      const isGit = pathMatchesMarker(path, rootNorm || rootPath, gitChanged);
      const isAgent = pathMatchesMarker(path, rootNorm || rootPath, agentFiles);
      return (
        <button
          key={path}
          type="button"
          className={`w-full flex items-center gap-1 px-2 py-1 text-left text-xs hover:bg-slate-100 ${
            selectedPath === path ? "bg-teal-50 text-teal-900 font-medium" : "text-slate-700"
          }`}
          style={{ paddingLeft: 8 + depth * 12 }}
          onClick={() => void openFile(node.path)}
          data-testid={`workspace-file-${node.name}`}
          title={[isAgent ? "agent-written" : "", isGit ? "git-changed" : ""].filter(Boolean).join(" · ") || undefined}
        >
          <span className="w-3 flex justify-center">
            {isAgent ? (
              <span className="h-1.5 w-1.5 rounded-full bg-teal-500" data-testid="workspace-marker-agent" />
            ) : isGit ? (
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" data-testid="workspace-marker-git" />
            ) : null}
          </span>
          <File className={`h-3.5 w-3.5 ${isAgent ? "text-teal-600" : isGit ? "text-amber-600" : "text-slate-500"}`} />
          <span className="truncate">{node.name}</span>
        </button>
      );
    });

  return (
    <div className="flex flex-col gap-3 h-[calc(100vh-7rem)]" data-testid="developer-workspace">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Developer Workspace</h1>
          <p className="text-xs text-slate-500" data-testid="workspace-spine-hint">
            Mentrix Coding Agent edits here — Delivery owns ship (plan → batches → Approve → PR).
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadTree()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700"
          data-testid="workspace-refresh"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loadingTree ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div
        className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
        data-testid="workspace-git-strip"
      >
        <span className="inline-flex items-center gap-1 font-medium">
          <GitBranch className="h-3.5 w-3.5 text-teal-700" />
          {branch || "—"}
        </span>
        <span className="text-slate-400">|</span>
        <span data-testid="workspace-git-summary">
          {gitSummary || "—"}
          {dirtyCount > 0 ? ` (${dirtyCount})` : ""}
        </span>
        {isLinkedWorktree && (
          <>
            <span className="text-slate-400">|</span>
            <span
              className="text-violet-700"
              data-testid="workspace-worktree-badge"
              title={worktrees.map((w) => `${w.branch || "detached"} → ${w.path}`).join("\n")}
            >
              worktrees {worktrees.length}
              {currentWorktree?.branch ? ` · ${currentWorktree.branch}` : ""}
            </span>
          </>
        )}
        {agentFiles.length > 0 && (
          <>
            <span className="text-slate-400">|</span>
            <span className="text-teal-700" data-testid="workspace-agent-files-count">
              agent {agentFiles.length} file{agentFiles.length === 1 ? "" : "s"}
            </span>
          </>
        )}
        <span className="text-slate-400">|</span>
        <span className="truncate font-mono text-[11px] text-slate-500" title={rootPath}>
          {rootPath || "No workspace root — set Active Project or Mentrix workspace"}
        </span>
        {activeRepo && (
          <span className="text-slate-500">
            {activeRepo.owner}/{activeRepo.repo_name}
          </span>
        )}
        <span className="ml-auto inline-flex items-center gap-2 text-[10px] text-slate-500">
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-500" /> agent
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> git
          </span>
        </span>
      </div>

      <PhaseErrorBanner error={error} testId="workspace-error" density="compact" />

      {!rootPath ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          Select an Active Project with a local clone, or set Mentrix workspace, then refresh.
        </div>
      ) : (
        <div className="flex flex-1 min-h-0 flex-col gap-3">
          <div className="flex flex-1 min-h-0 gap-3">
            <aside className="w-64 shrink-0 flex flex-col gap-2 min-h-0">
              <div
                className="flex-1 overflow-auto rounded-lg border border-slate-200 bg-white"
                data-testid="workspace-file-tree"
              >
                <div className="px-2 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500 border-b border-slate-100">
                  Files
                </div>
                {loadingTree ? (
                  <div className="p-4 flex items-center gap-2 text-xs text-slate-500">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
                  </div>
                ) : tree.length === 0 ? (
                  <p className="p-3 text-xs text-slate-500">Empty or inaccessible tree.</p>
                ) : (
                  <div className="py-1">{renderTree(tree)}</div>
                )}
              </div>
              {showSymbols ? (
                <div className="h-56 shrink-0">
                  <WorkspaceSymbolsPanel
                    workspaceRoot={rootPath}
                    openFilePath={selectedPath}
                    repoId={activeRepoId}
                    onJump={jumpToSymbol}
                  />
                </div>
              ) : null}
            </aside>

            <section className="flex-1 min-w-0 flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <div className="truncate font-mono text-xs text-slate-600" data-testid="workspace-open-path">
                  {selectedPath || "Select a file"}
                  {revealLine ? `:${revealLine}` : ""}
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setShowSymbols((v) => !v)}
                    className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs ${
                      showSymbols ? "border-teal-300 bg-teal-50 text-teal-900" : "border-slate-200 bg-white text-slate-700"
                    }`}
                    data-testid="workspace-toggle-symbols"
                  >
                    <Code2 className="h-3.5 w-3.5" />
                    Symbols
                  </button>
                  <button
                    type="button"
                    disabled={!selectedPath}
                    onClick={() => setShowInline((v) => !v)}
                    className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs disabled:opacity-40 ${
                      showInline ? "border-teal-300 bg-teal-50 text-teal-900" : "border-slate-200 bg-white text-slate-700"
                    }`}
                    data-testid="workspace-toggle-inline"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Ask
                  </button>
                  <button
                    type="button"
                    disabled={!selectedPath}
                    onClick={() => setShowDiff((v) => !v)}
                    className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs disabled:opacity-40 ${
                      showDiff ? "border-teal-300 bg-teal-50 text-teal-900" : "border-slate-200 bg-white text-slate-700"
                    }`}
                    data-testid="workspace-toggle-diff"
                  >
                    <GitCompare className="h-3.5 w-3.5" />
                    Diff
                  </button>
                  <button
                    type="button"
                    disabled={!dirty || saving || !selectedPath}
                    onClick={() => void saveFile()}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-40"
                    data-testid="workspace-save"
                  >
                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                    Save
                  </button>
                </div>
              </div>
              <div className={`flex-1 min-h-0 ${sideOpen ? "grid grid-cols-1 xl:grid-cols-2 gap-2" : ""}`}>
                <div className="min-h-[200px] h-full">
                  {loadingFile || (loadingDir && browsingDir && !selectedPath) ? (
                    <div className="h-full flex items-center justify-center text-sm text-slate-500 gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" /> {loadingFile ? "Opening…" : "Listing folder…"}
                    </div>
                  ) : selectedPath ? (
                    <MonacoCodeEditor
                      path={selectedPath}
                      value={content}
                      language={languageFromPath(selectedPath)}
                      revealLine={revealLine}
                      onChange={setContent}
                      onSelectionChange={setSelection}
                    />
                  ) : browsingDir ? (
                    <div
                      className="h-full rounded-lg border border-slate-200 bg-white overflow-auto p-4"
                      data-testid="workspace-dir-pane"
                    >
                      <p className="text-sm font-semibold text-slate-900 mb-1">Folder</p>
                      <p className="font-mono text-xs text-slate-500 mb-3 break-all">{browsingDir}</p>
                      <p className="text-xs text-slate-600 mb-3">
                        {browsingChildren.length} item{browsingChildren.length === 1 ? "" : "s"} — click a file to
                        open in the editor.
                      </p>
                      <ul className="space-y-1">
                        {browsingChildren.map((child) => (
                          <li key={normalizePath(child.path)}>
                            <button
                              type="button"
                              className="w-full flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-slate-800 hover:bg-slate-50"
                              onClick={() =>
                                child.is_dir ? void openDirectory(child.path) : void openFile(child.path)
                              }
                              data-testid={
                                child.is_dir
                                  ? `workspace-dir-pane-dir-${child.name}`
                                  : `workspace-dir-pane-file-${child.name}`
                              }
                            >
                              {child.is_dir ? (
                                <Folder className="h-4 w-4 text-amber-600" />
                              ) : (
                                <File className="h-4 w-4 text-slate-500" />
                              )}
                              <span className="truncate">{child.name}</span>
                            </button>
                          </li>
                        ))}
                        {!browsingChildren.length && !loadingDir ? (
                          <li className="text-xs text-slate-500">Empty folder</li>
                        ) : null}
                      </ul>
                    </div>
                  ) : (
                    <div className="h-full rounded-lg border border-dashed border-slate-200 bg-slate-50 flex items-center justify-center text-sm text-slate-500">
                      Open a folder or file from the tree to browse or edit.
                    </div>
                  )}
                </div>
                {sideOpen && selectedPath ? (
                  <div className="min-h-[200px] h-full flex flex-col gap-2 overflow-auto">
                    {showInline ? (
                      <WorkspaceInlinePanel
                        filePath={selectedPath}
                        content={content}
                        selection={selection}
                        repoId={activeRepoId}
                        onApplyCode={applyInlineCode}
                      />
                    ) : null}
                    {showDiff ? (
                      <WorkspaceDiffPanel
                        baseline={baseline}
                        content={content}
                        fileLabel={normalizePath(selectedPath).split("/").pop()}
                        onContentChange={setContent}
                        onApplySave={saveFile}
                        onRevertFile={revertFile}
                        saving={saving}
                      />
                    ) : null}
                  </div>
                ) : null}
              </div>
            </section>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-64 shrink-0" data-testid="workspace-stage-b-panels">
            <div className="lg:col-span-1 min-h-0">
              <MentrixCodingAgentPanel
                workspaceRoot={rootPath}
                model={agentModel}
                onModelChange={setAgentModel}
                onOpenPath={openAgentPath}
                onFilesChanged={(paths) => {
                  setAgentFiles((prev) => Array.from(new Set([...prev, ...paths])));
                  void loadTree();
                  void refreshGit(rootPath);
                }}
                initialGoal={deepGoal}
                initialSessionId={deepSession || null}
              />
            </div>
            <WorkspaceTerminal workspaceRoot={rootPath} />
            <WorkspaceMentrixTimeline workspaceRoot={rootPath} />
          </div>
        </div>
      )}
    </div>
  );
}

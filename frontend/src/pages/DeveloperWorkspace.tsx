import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  GitBranch,
  Loader2,
  RefreshCw,
  Save,
  AlertCircle,
} from "lucide-react";
import MonacoCodeEditor from "@/components/MonacoCodeEditor";
import PhaseErrorBanner from "@/components/PhaseErrorBanner";
import WorkspaceMentrixTimeline from "@/components/WorkspaceMentrixTimeline";
import WorkspaceTerminal from "@/components/WorkspaceTerminal";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { fileRead, fileTree, fileWrite, gitBranches, gitStatus } from "@/lib/api";
import { readMentrixWorkspace } from "@/lib/workspaceContext";
import { isPathInsideRoot, languageFromPath } from "@/lib/workspacePaths";

type TreeNode = {
  name: string;
  path: string;
  is_dir: boolean;
  children?: TreeNode[];
};

function countGitChanges(st: Record<string, unknown> | null | undefined): number {
  if (!st) return 0;
  const staged = Array.isArray(st.staged) ? st.staged.length : 0;
  const modified = Array.isArray(st.modified) ? st.modified.length : 0;
  const untracked = Array.isArray(st.untracked) ? st.untracked.length : 0;
  if (staged || modified || untracked) return staged + modified + untracked;
  if (Array.isArray(st.files)) return st.files.length;
  return 0;
}

/**
 * Phase 3 — unified developer workspace:
 * file tree + Monaco + git strip (Stage A); terminal + Mentrix timeline (Stage B).
 * Writes and terminal cwd stay under the active workspace root.
 */
export default function DeveloperWorkspace() {
  const { activeLocalPath, activeRepo } = useActiveProject();
  const mentrix = readMentrixWorkspace();
  const rootPath = (activeLocalPath || mentrix?.path || "").trim();

  const [tree, setTree] = useState<TreeNode[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState("");
  const [content, setContent] = useState("");
  const [baseline, setBaseline] = useState("");
  const [loadingTree, setLoadingTree] = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [branch, setBranch] = useState("");
  const [gitSummary, setGitSummary] = useState("");
  const [dirtyCount, setDirtyCount] = useState(0);

  const dirty = content !== baseline && Boolean(selectedPath);

  const refreshGit = useCallback(async (root: string) => {
    if (!root) return;
    try {
      const [st, br] = await Promise.all([gitStatus(root), gitBranches(root)]);
      setBranch(br?.current || st?.branch || "");
      const count = countGitChanges(st);
      setDirtyCount(count);
      setGitSummary(st?.clean || count === 0 ? "clean" : `${count} change${count === 1 ? "" : "s"}`);
    } catch {
      setBranch("");
      setGitSummary("git unavailable");
      setDirtyCount(0);
    }
  }, []);

  const loadTree = useCallback(async () => {
    if (!rootPath) {
      setTree([]);
      return;
    }
    setLoadingTree(true);
    setError("");
    try {
      const nodes = await fileTree(rootPath, 4);
      setTree(Array.isArray(nodes) ? nodes : []);
      setExpanded(new Set([rootPath.replace(/\\/g, "/")]));
      await refreshGit(rootPath);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tree");
      setTree([]);
    } finally {
      setLoadingTree(false);
    }
  }, [rootPath, refreshGit]);

  useEffect(() => {
    void loadTree();
  }, [loadTree]);

  const openFile = async (path: string) => {
    if (!rootPath || !isPathInsideRoot(path, rootPath)) {
      setError("File is outside the active workspace root");
      return;
    }
    setLoadingFile(true);
    setError("");
    try {
      const file = await fileRead(path);
      const text = typeof file?.content === "string" ? file.content : "";
      setSelectedPath(path);
      setContent(text);
      setBaseline(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to read file");
    } finally {
      setLoadingFile(false);
    }
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

  const toggleDir = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const renderTree = (nodes: TreeNode[], depth = 0): ReactNode =>
    nodes.map((node) => {
      const path = node.path;
      const isOpen = expanded.has(path);
      if (node.is_dir) {
        return (
          <div key={path}>
            <button
              type="button"
              className="w-full flex items-center gap-1 px-2 py-1 text-left text-xs text-slate-700 hover:bg-slate-100"
              style={{ paddingLeft: 8 + depth * 12 }}
              onClick={() => toggleDir(path)}
              data-testid={`workspace-dir-${node.name}`}
            >
              {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              <Folder className="h-3.5 w-3.5 text-amber-600" />
              <span className="truncate">{node.name}</span>
            </button>
            {isOpen && node.children?.length ? renderTree(node.children, depth + 1) : null}
          </div>
        );
      }
      return (
        <button
          key={path}
          type="button"
          className={`w-full flex items-center gap-1 px-2 py-1 text-left text-xs hover:bg-slate-100 ${
            selectedPath === path ? "bg-teal-50 text-teal-900 font-medium" : "text-slate-700"
          }`}
          style={{ paddingLeft: 8 + depth * 12 }}
          onClick={() => void openFile(path)}
          data-testid={`workspace-file-${node.name}`}
        >
          <span className="w-3" />
          <File className="h-3.5 w-3.5 text-slate-500" />
          <span className="truncate">{node.name}</span>
        </button>
      );
    });

  return (
    <div className="flex flex-col gap-3 h-[calc(100vh-7rem)]" data-testid="developer-workspace">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Developer Workspace</h1>
          <p className="text-xs text-slate-500">
            Tree + Monaco + git strip + workspace terminal + Mentrix timeline. Saves and shell cwd stay inside the active workspace.
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
        <span className="text-slate-400">|</span>
        <span className="truncate font-mono text-[11px] text-slate-500" title={rootPath}>
          {rootPath || "No workspace root — set Active Project or Mentrix workspace"}
        </span>
        {activeRepo && (
          <span className="text-slate-500">
            {activeRepo.owner}/{activeRepo.repo_name}
          </span>
        )}
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
            <aside
              className="w-64 shrink-0 overflow-auto rounded-lg border border-slate-200 bg-white"
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
            </aside>

            <section className="flex-1 min-w-0 flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <div className="truncate font-mono text-xs text-slate-600" data-testid="workspace-open-path">
                  {selectedPath || "Select a file"}
                </div>
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
              <div className="flex-1 min-h-0">
                {loadingFile ? (
                  <div className="h-full flex items-center justify-center text-sm text-slate-500 gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> Opening…
                  </div>
                ) : selectedPath ? (
                  <MonacoCodeEditor
                    path={selectedPath}
                    value={content}
                    language={languageFromPath(selectedPath)}
                    onChange={setContent}
                  />
                ) : (
                  <div className="h-full rounded-lg border border-dashed border-slate-200 bg-slate-50 flex items-center justify-center text-sm text-slate-500">
                    Open a file from the tree to edit in Monaco.
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 h-52 shrink-0" data-testid="workspace-stage-b-panels">
            <WorkspaceTerminal workspaceRoot={rootPath} />
            <WorkspaceMentrixTimeline workspaceRoot={rootPath} />
          </div>
        </div>
      )}
    </div>
  );
}

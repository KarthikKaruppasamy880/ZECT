import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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
  FolderOpen,
  Maximize2,
  Minimize2,
} from "lucide-react";
import MonacoCodeEditor, { type EditorSelection } from "@/components/MonacoCodeEditor";
import PhaseErrorBanner from "@/components/PhaseErrorBanner";
import WorkspaceDiffPanel from "@/components/WorkspaceDiffPanel";
import WorkspaceInlinePanel, { replaceSelectionInContent } from "@/components/WorkspaceInlinePanel";
import WorkspaceMentrixTimeline from "@/components/WorkspaceMentrixTimeline";
import WorkspaceSymbolsPanel, { type SymbolJumpTarget } from "@/components/WorkspaceSymbolsPanel";
import WorkspaceTerminal from "@/components/WorkspaceTerminal";
import MentrixCodingAgentPanel from "@/components/MentrixCodingAgentPanel";
import WorkspaceContextUsedPanel from "@/components/WorkspaceContextUsedPanel";
import WorkspaceSearchPanel from "@/components/WorkspaceSearchPanel";
import SplitPane, { resetSplitLayout } from "@/components/SplitPane";
import {
  DEFAULT_WORKSPACE_CHROME,
  WORKSPACE_SPLIT_KEYS,
  effectivePanes,
  loadWorkspaceChrome,
  saveWorkspaceChrome,
  type WorkspaceBottomTab,
  type WorkspaceMaximized,
} from "@/lib/workspaceChrome";
import RepoOnboardingPanel from "@/components/RepoOnboardingPanel";
import DeveloperMultiRepoStatus from "@/components/DeveloperMultiRepoStatus";
import WorkspaceRootsRail from "@/components/WorkspaceRootsRail";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";
import { canonicalLatticeState, latticeHeaderLabel } from "@/lib/contextUsed";
import {
  excludeWorkspaceRoot,
  excludedRootIds,
  includeWorkspaceRoot,
  visibleProjectRepos,
} from "@/lib/workspaceRoots";
import {
  loadWorkspaceSession,
  newTerminalSession,
  saveWorkspaceSession,
} from "@/lib/workspaceSession";
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
import { deriveProjectKey, readMentrixWorkspace, writeMentrixWorkspace } from "@/lib/workspaceContext";
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
  const deepWorkItem = searchParams.get("work_item_id");
  const urlWorkItem = deepWorkItem && /^\d+$/.test(deepWorkItem) ? Number(deepWorkItem) : null;
  const { activeLocalPath, activeRepo, activeRepoId, activeProjectId, activeProjectKey, repos, setActiveRepo, setActiveProject } =
    useActiveProject();
  const { latticeStatus: latticeIdx, loadingStatus: latticeLoading } = useWorkspaceRepoContext();
  const [excludedRoots, setExcludedRoots] = useState(() => excludedRootIds(activeProjectId));
  useEffect(() => {
    setExcludedRoots(excludedRootIds(activeProjectId));
  }, [activeProjectId]);
  const projectRepoIds = useMemo(
    () =>
      repos
        .filter((r) => activeProjectId != null && r.project_id === activeProjectId)
        .map((r) => r.repo_id),
    [repos, activeProjectId],
  );
  const visibleRoots = useMemo(
    () => visibleProjectRepos(activeProjectId, repos, excludedRoots),
    [activeProjectId, repos, excludedRoots],
  );
  const termRoots = useMemo(
    () =>
      visibleRoots
        .filter((r) => r.local_path)
        .map((r) => ({
          repoId: r.repo_id,
          rootPath: r.local_path as string,
          label: `${r.owner}/${r.repo_name}`,
        })),
    [visibleRoots],
  );
  const mentrix = readMentrixWorkspace();
  const rootPath = (activeLocalPath || mentrix?.path || "").trim();

  const [showImport, setShowImport] = useState(false);
  const userToggledImport = useRef(false);
  useEffect(() => {
    if (userToggledImport.current) return;
    if (!rootPath && visibleRoots.length === 0) {
      setShowImport(true);
      return;
    }
    if (rootPath) setShowImport(false);
  }, [rootPath, visibleRoots.length]);
  const [chrome, setChrome] = useState(() => loadWorkspaceChrome());
  const showExplorer = chrome.explorer;
  const showAgent = chrome.agent;
  const showBottom = chrome.bottom;
  const showContext = chrome.context;
  const maximized = chrome.maximized;
  const bottomTab = chrome.bottomTab;
  const panes = effectivePanes(chrome);

  const setShowExplorer = (updater: boolean | ((prev: boolean) => boolean)) => {
    setChrome((prev) => ({
      ...prev,
      explorer: typeof updater === "function" ? updater(prev.explorer) : updater,
      maximized: null,
    }));
  };
  const setShowAgent = (updater: boolean | ((prev: boolean) => boolean)) => {
    setChrome((prev) => ({
      ...prev,
      agent: typeof updater === "function" ? updater(prev.agent) : updater,
      maximized: null,
    }));
  };
  const setShowBottom = (updater: boolean | ((prev: boolean) => boolean)) => {
    setChrome((prev) => ({
      ...prev,
      bottom: typeof updater === "function" ? updater(prev.bottom) : updater,
      maximized: null,
    }));
  };
  const setShowContext = (updater: boolean | ((prev: boolean) => boolean)) => {
    setChrome((prev) => {
      const next = typeof updater === "function" ? updater(prev.context) : updater;
      return {
        ...prev,
        context: next,
        bottom: next ? true : prev.bottom,
        bottomTab: next ? "context" : prev.bottomTab === "context" ? "terminal" : prev.bottomTab,
        maximized: null,
      };
    });
  };
  const setMaximized = (pane: WorkspaceMaximized) => {
    setChrome((prev) => ({ ...prev, maximized: prev.maximized === pane ? null : pane }));
  };
  const setBottomTab = (tab: WorkspaceBottomTab) => {
    setChrome((prev) => ({
      ...prev,
      bottomTab: tab,
      context: tab === "context" ? true : prev.context,
      bottom: true,
      maximized: prev.maximized === "bottom" ? "bottom" : null,
    }));
  };

  useEffect(() => {
    saveWorkspaceChrome(chrome);
  }, [chrome]);
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [treesByRepo, setTreesByRepo] = useState<Record<number, TreeNode[]>>({});
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
  const [wsSession, setWsSession] = useState(() => loadWorkspaceSession());
  const workItemId = urlWorkItem || wsSession.workItemId;
  useEffect(() => {
    saveWorkspaceSession(wsSession);
  }, [wsSession]);
  useEffect(() => {
    if (urlWorkItem && wsSession.workItemId !== urlWorkItem) {
      setWsSession((prev) => ({ ...prev, workItemId: urlWorkItem }));
    }
  }, [urlWorkItem, wsSession.workItemId]);
  useEffect(() => {
    if (!activeProjectId) return;
    setWsSession((prev) =>
      prev.projectId === activeProjectId && prev.activeRepoId === (activeRepoId || null)
        ? prev
        : { ...prev, projectId: activeProjectId, activeRepoId: activeRepoId || null },
    );
  }, [activeProjectId, activeRepoId]);
  useEffect(() => {
    if (activeProjectId || !wsSession.projectId) return;
    setActiveProject(wsSession.projectId);
    if (wsSession.activeRepoId) setActiveRepo(wsSession.activeRepoId);
  }, [activeProjectId, wsSession.projectId, wsSession.activeRepoId, setActiveProject, setActiveRepo]);

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

  const treeGen = useRef(0);
  const rootCatalog = useMemo(
    () => visibleRoots.map((r) => `${r.repo_id}:${r.local_path || ""}`).join("|"),
    [visibleRoots],
  );

  const loadAllTrees = useCallback(async () => {
    const gen = ++treeGen.current;
    if (typeof localStorage !== "undefined" && !localStorage.getItem("zect_token")) {
      setTreesByRepo({});
      setTree([]);
      return;
    }
    setLoadingTree(true);
    setError("");
    try {
      const pairs = await Promise.all(
        visibleRoots.map(async (repo) => {
          if (!repo.local_path) return [repo.repo_id, [] as TreeNode[]] as const;
          try {
            const nodes = await fileTree(repo.local_path, 4);
            return [repo.repo_id, normalizeTreeNodes(Array.isArray(nodes) ? nodes : [])] as const;
          } catch {
            return [repo.repo_id, [] as TreeNode[]] as const;
          }
        }),
      );
      if (gen !== treeGen.current) return;
      const next = Object.fromEntries(pairs);
      setTreesByRepo(next);
      setTree(activeRepoId != null ? next[activeRepoId] || [] : []);
      setExpanded((prev) => {
        const copy = new Set(prev);
        for (const repo of visibleRoots) {
          if (repo.local_path) copy.add(normalizePath(repo.local_path));
        }
        return copy;
      });
      if (rootPath) await Promise.all([refreshGit(rootPath), refreshAgentMarkers()]);
    } catch (e) {
      if (gen !== treeGen.current) return;
      setError(e instanceof Error ? e.message : "Failed to load tree");
    } finally {
      if (gen === treeGen.current) setLoadingTree(false);
    }
  }, [visibleRoots, activeRepoId, rootPath, refreshGit, refreshAgentMarkers]);

  const loadTree = loadAllTrees;

  useEffect(() => {
    void loadAllTrees();
  }, [loadAllTrees]);

  useEffect(() => {
    if (!visibleRoots.length) return;
    setWsSession((prev) => {
      if (prev.terminals.length) return prev;
      const repo =
        visibleRoots.find((r) => r.repo_id === activeRepoId && r.local_path) ||
        visibleRoots.find((r) => r.local_path);
      if (!repo?.local_path) return prev;
      const term = newTerminalSession(repo.repo_id, repo.local_path, `${repo.owner}/${repo.repo_name}`);
      return { ...prev, terminals: [term], activeTerminalId: term.id };
    });
  }, [rootCatalog, visibleRoots, activeRepoId]);

  const handleSelectRoot = (repoId: number) => {
    const nextId = Number(repoId);
    if (!Number.isFinite(nextId) || nextId <= 0) return;
    if (nextId === Number(activeRepoId)) return;
    if (dirty && !window.confirm("Switch workspace root and discard unsaved editor changes?")) return;
    const repo = visibleRoots.find((row) => Number(row.repo_id) === nextId);
    if (repo?.local_path) {
      writeMentrixWorkspace(repo.local_path, deriveProjectKey(repo.owner, repo.repo_name));
    }
    setActiveRepo(nextId);
  };

  const handleRemoveRoot = (repoId: number) => {
    if (activeProjectId == null) return;
    if (!window.confirm("Remove this folder from the workspace? Disk files are not deleted.")) return;
    const next = excludeWorkspaceRoot(activeProjectId, repoId);
    setExcludedRoots(next);
    if (activeRepoId === repoId) {
      const remain = visibleProjectRepos(activeProjectId, repos, next);
      setActiveRepo(remain[0]?.repo_id ?? null);
    }
  };

  const handleAddRoot = () => {
    userToggledImport.current = true;
    setShowImport(true);
  };

  const handleRepairRoot = (repoId: number) => {
    userToggledImport.current = true;
    setActiveRepo(repoId);
    setShowImport(true);
  };

  const handleRootActivated = (info: { projectId: number; repoId: number; localPath?: string }) => {
    includeWorkspaceRoot(info.projectId, info.repoId);
    setExcludedRoots(excludedRootIds(info.projectId));
    setShowImport(false);
    void loadTree();
  };

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
      setTreesByRepo((prev) => {
        const next: Record<number, TreeNode[]> = {};
        for (const [key, nodes] of Object.entries(prev)) {
          next[Number(key)] = upsertChildren(nodes, norm, children);
        }
        return next;
      });
      return children;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to list directory");
      setTree((prev) => upsertChildren(prev, norm, []));
      return [];
    } finally {
      setLoadingDir(false);
    }
  }, []);

  const openFile = async (path: string, line?: number, repoId?: number) => {
    const norm = normalizePath(path);
    const owner =
      (repoId != null ? visibleRoots.find((r) => r.repo_id === repoId) : undefined) ||
      visibleRoots.find((r) => r.local_path && isPathInsideRoot(norm, r.local_path));
    if (!owner?.local_path || !isPathInsideRoot(norm, owner.local_path)) {
      setError("File is outside authorized workspace roots");
      return;
    }
    if (Number(owner.repo_id) !== Number(activeRepoId)) setActiveRepo(owner.repo_id);
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
      setWsSession((prev) => ({
        ...prev,
        openEditors: [{ repoId: owner.repo_id, path: norm }, ...prev.openEditors.filter((e) => e.path !== norm)].slice(
          0,
          12,
        ),
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to read file");
    } finally {
      setLoadingFile(false);
    }
  };

  const restoredEditors = useRef(false);
  useEffect(() => {
    if (restoredEditors.current || !visibleRoots.length) return;
    const first = wsSession.openEditors[0];
    if (!first?.path) {
      restoredEditors.current = true;
      return;
    }
    const owner = visibleRoots.find((r) => r.repo_id === first.repoId && r.local_path);
    if (!owner) return;
    restoredEditors.current = true;
    void openFile(first.path, undefined, first.repoId);
  }, [visibleRoots, wsSession.openEditors]);

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

  const renderTree = (nodes: TreeNode[], depth = 0, repoId?: number): ReactNode =>
    nodes.map((node) => {
      const path = normalizePath(node.path);
      const isOpen = expanded.has(path);
      if (node.is_dir) {
        const childCount = node.children?.length;
        return (
          <div key={`${repoId || 0}:${path}`}>
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
                renderTree(node.children, depth + 1, repoId)
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
          key={`${repoId || 0}:${path}`}
          type="button"
          className={`w-full flex items-center gap-1 px-2 py-1 text-left text-xs hover:bg-slate-100 ${
            selectedPath === path ? "bg-teal-50 text-teal-900 font-medium" : "text-slate-700"
          }`}
          style={{ paddingLeft: 8 + depth * 12 }}
          onClick={() => void openFile(node.path, undefined, repoId)}
          data-testid={repoId != null ? `workspace-file-${repoId}-${node.name}` : `workspace-file-${node.name}`}
          data-file={node.name}
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
        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="workspace-import-local"
            onClick={() => {
              userToggledImport.current = true;
              setShowImport((v) => !v);
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-xs font-medium text-indigo-800 hover:bg-indigo-100"
          >
            <FolderOpen className="h-3.5 w-3.5" />
            {showImport ? "Hide import" : "Import local clone"}
          </button>
          <button
            type="button"
            data-testid="workspace-toggle-explorer"
            onClick={() => setShowExplorer((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700"
          >
            {showExplorer ? "Hide explorer" : "Show explorer"}
          </button>
          <button
            type="button"
            data-testid="workspace-toggle-agent"
            onClick={() => setShowAgent((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700"
          >
            {showAgent ? "Hide agent" : "Show agent"}
          </button>
          <button
            type="button"
            data-testid="workspace-toggle-bottom"
            onClick={() => setShowBottom((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700"
          >
            {showBottom ? "Hide tools" : "Show tools"}
          </button>
          <button
            type="button"
            data-testid="workspace-toggle-context"
            onClick={() => {
              setShowContext((v) => !v);
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700"
          >
            {showContext ? "Hide context" : "Context used"}
          </button>
          <button
            type="button"
            data-testid="workspace-reset-layout"
            onClick={() => {
              resetSplitLayout([...WORKSPACE_SPLIT_KEYS]);
              saveWorkspaceChrome(DEFAULT_WORKSPACE_CHROME);
              window.location.reload();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700"
          >
            Reset layout
          </button>
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
      </div>

      {(showImport || !rootPath) && (
        <div data-testid="workspace-import-panel">
          <RepoOnboardingPanel
            projectId={activeProjectId}
            compact
            preferOpenLocal
            navigateTo={null}
            onActivated={handleRootActivated}
          />
        </div>
      )}

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
        <span
          className="truncate font-mono text-[11px] text-slate-500"
          title={rootPath}
          data-testid="workspace-active-root-path"
        >
          {rootPath || "No workspace root — set Active Project or Mentrix workspace"}
        </span>
        {activeRepo && (
          <span className="text-slate-500">
            {activeRepo.owner}/{activeRepo.repo_name}
          </span>
        )}
        <span
          data-testid="workspace-git-lattice"
          data-lattice-state={latticeLoading ? "" : canonicalLatticeState(latticeIdx?.state)}
          className="rounded bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-600"
          title={[
            latticeIdx?.project_key,
            latticeIdx?.live_commit_sha && `head=${String(latticeIdx.live_commit_sha).slice(0, 12)}`,
            latticeIdx?.indexed_commit_sha && `indexed=${String(latticeIdx.indexed_commit_sha).slice(0, 12)}`,
          ]
            .filter(Boolean)
            .join(" · ")}
        >
          {latticeLoading ? "Lattice …" : latticeHeaderLabel(canonicalLatticeState(latticeIdx?.state))}
        </span>
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

      <div className="flex flex-1 min-h-0 gap-3">
        <div className="flex flex-1 min-h-0 flex-col min-w-0">
      {!rootPath && visibleRoots.length === 0 ? (
        <div className="flex flex-1 min-h-0 flex-col gap-3">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 space-y-2">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">No workspace root yet</p>
              <p className="text-xs mt-1">
                If you already cloned a repo on your Desktop, use{" "}
                <strong>Import Already-Cloned Local Repo</strong> above — paste the folder path and activate it here.
                You can also pick an Active Project from the top bar, then refresh.
              </p>
            </div>
          </div>
        </div>
        {showContext ? (
          <WorkspaceContextUsedPanel
            projectId={activeProjectId}
            projectKey={activeProjectKey || ""}
            repositoryId={activeRepoId}
            repositoryIds={projectRepoIds}
            activeRepoLabel={
              activeRepo ? `${activeRepo.owner}/${activeRepo.repo_name}` : ""
            }
            workItemId={workItemId}
          />
        ) : null}
        </div>
      ) : (
        (() => {
          const explorerPane = (
            <aside className="h-full flex flex-col gap-2 min-h-0 min-w-0 relative z-10">
              <div className="flex-1 overflow-auto rounded-lg border border-slate-200 bg-white flex flex-col min-h-0">
                <WorkspaceRootsRail
                  projectId={activeProjectId}
                  repos={visibleRoots}
                  activeRepoId={activeRepoId}
                  onSelectRoot={handleSelectRoot}
                  onRemoveRoot={handleRemoveRoot}
                  onAddRoot={handleAddRoot}
                  onRepairRoot={handleRepairRoot}
                  fileTree={(repoId) => renderTree(treesByRepo[repoId] || [], 1, repoId)}
                />
                <div
                  className="flex items-center justify-between border-t border-slate-100 px-2 py-1"
                  data-testid="workspace-file-tree"
                >
                  <span className="text-[10px] uppercase tracking-wide text-slate-400">Merged explorer</span>
                  <button
                    type="button"
                    className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-600"
                    data-testid="workspace-maximize-explorer"
                    onClick={() => setMaximized("explorer")}
                  >
                    {maximized === "explorer" ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
                  </button>
                </div>
              </div>
              {showSymbols ? (
                <div className="h-56 shrink-0">
                  <WorkspaceSymbolsPanel
                    workspaceRoot={rootPath}
                    openFilePath={selectedPath}
                    repoId={activeRepoId}
                    repositoryIds={projectRepoIds}
                    onJump={jumpToSymbol}
                  />
                </div>
              ) : null}
            </aside>
          );

          const editorPane = (
            <section className="h-full min-w-0 flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <div className="truncate font-mono text-xs text-slate-600" data-testid="workspace-open-path">
                  {selectedPath || "Select a file"}
                  {revealLine ? `:${revealLine}` : ""}
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-600"
                    data-testid="workspace-maximize-editor"
                    onClick={() => setMaximized("editor")}
                  >
                    {maximized === "editor" ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
                  </button>
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
          );

          const agentPane = (
            <div className="h-full min-w-0 overflow-hidden flex flex-col" data-testid="workspace-agent-pane">
              <div className="flex items-center justify-between border-b border-slate-100 px-2 py-1">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Agent</span>
                <button
                  type="button"
                  className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-600"
                  data-testid="workspace-maximize-agent"
                  onClick={() => setMaximized("agent")}
                >
                  {maximized === "agent" ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
                </button>
              </div>
              <div className="min-h-0 flex-1 overflow-hidden">
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
                projectId={activeProjectId}
                workItemId={workItemId}
                roots={visibleRoots
                  .filter((r) => r.local_path)
                  .map((r) => ({
                    id: r.repo_id,
                    label: r.repo_name || `repo-${r.repo_id}`,
                    path: r.local_path as string,
                  }))}
              />
              </div>
            </div>
          );

          const contextPanel = (
            <WorkspaceContextUsedPanel
              projectId={activeProjectId}
              projectKey={activeProjectKey || ""}
              repositoryId={activeRepoId}
              repositoryIds={projectRepoIds}
              activeRepoLabel={
                activeRepo ? `${activeRepo.owner}/${activeRepo.repo_name}` : ""
              }
              workItemId={workItemId}
            />
          );

          const bottomPane = (
            <div className="flex h-full min-h-0 flex-col" data-testid="workspace-stage-b-panels">
              <div className="flex items-center gap-1 border-b border-slate-100 px-2 py-1">
                {(
                  [
                    ["terminal", "Terminal"],
                    ["problems", "Problems"],
                    ["tests", "Tests"],
                    ["timeline", "Timeline"],
                    ["evidence", "Evidence"],
                    ["context", "Context"],
                    ["search", "Search"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    data-testid={`workspace-bottom-tab-${id}`}
                    onClick={() => setBottomTab(id)}
                    className={`rounded px-2 py-1 text-[11px] ${
                      bottomTab === id ? "bg-teal-50 text-teal-900" : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {label}
                  </button>
                ))}
                <button
                  type="button"
                  className="ml-auto rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-600"
                  data-testid="workspace-maximize-bottom"
                  onClick={() => setMaximized("bottom")}
                >
                  {maximized === "bottom" ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
                </button>
              </div>
              <div className="min-h-0 flex-1 overflow-auto p-2">
                {bottomTab === "terminal" ? (
                  <WorkspaceTerminal
                    workspaceRoot={
                      wsSession.terminals.find((t) => t.id === wsSession.activeTerminalId)?.rootPath || rootPath
                    }
                    sessions={wsSession.terminals}
                    activeSessionId={wsSession.activeTerminalId}
                    roots={termRoots}
                    onSelectSession={(id) => setWsSession((prev) => ({ ...prev, activeTerminalId: id }))}
                    onCreateSession={(root) => {
                      const term = newTerminalSession(root.repoId, root.rootPath, root.label);
                      setWsSession((prev) => ({
                        ...prev,
                        terminals: [...prev.terminals, term],
                        activeTerminalId: term.id,
                      }));
                    }}
                  />
                ) : null}
                {bottomTab === "timeline" ? <WorkspaceMentrixTimeline workspaceRoot={rootPath} /> : null}
                {bottomTab === "context" ? contextPanel : null}
                {bottomTab === "search" ? (
                  <WorkspaceSearchPanel
                    repoIds={visibleRoots.map((r) => r.repo_id)}
                    activeRepoId={activeRepoId}
                    currentFile={selectedPath}
                    onOpen={(abs, repoId) => void openFile(abs, undefined, repoId)}
                  />
                ) : null}
                {bottomTab === "problems" ? (
                  <div data-testid="workspace-problems-panel" className="text-[11px] text-slate-600 space-y-1">
                    {error ? <p className="text-rose-700">{error}</p> : null}
                    <p>Active git: {gitSummary || "—"}</p>
                    {gitChanged.slice(0, 20).map((p) => (
                      <p key={p} className="font-mono text-[10px]">
                        {p}
                      </p>
                    ))}
                    {!error && !gitChanged.length ? <p className="text-slate-400">No problems</p> : null}
                  </div>
                ) : null}
                {bottomTab === "tests" || bottomTab === "evidence" ? (
                  <div data-testid={bottomTab === "tests" ? "workspace-tests-panel" : "workspace-evidence-panel"}>
                    <DeveloperMultiRepoStatus workItemId={workItemId} projectId={activeProjectId} />
                  </div>
                ) : null}
              </div>
            </div>
          );

          let mainRow: ReactNode = editorPane;
          if (panes.agent) {
            mainRow = (
              <SplitPane
                axis="horizontal"
                storageKey="zect_ws_agent"
                initial={76}
                min={55}
                max={90}
                testId="workspace-split-agent"
              >
                {editorPane}
                {agentPane}
              </SplitPane>
            );
          }
          if (panes.explorer) {
            mainRow = (
              <SplitPane
                axis="horizontal"
                storageKey="zect_ws_h"
                initial={22}
                min={14}
                max={40}
                testId="workspace-split-h"
              >
                {explorerPane}
                {mainRow}
              </SplitPane>
            );
          }
          if (panes.bottom) {
            return (
              <SplitPane
                axis="vertical"
                storageKey="zect_ws_v"
                initial={74}
                min={50}
                max={90}
                testId="workspace-split-v"
              >
                {mainRow}
                {bottomPane}
              </SplitPane>
            );
          }
          return mainRow;
        })()
      )}
        </div>
      </div>
    </div>
  );
}

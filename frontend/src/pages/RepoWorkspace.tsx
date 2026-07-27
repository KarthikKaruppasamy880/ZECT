import { useState, useEffect, useCallback } from "react";
import {
  GitBranch, Download, RefreshCw, Trash2, Search, FileCode, FolderOpen,
  ChevronRight, ChevronDown, File, Folder, Loader2, AlertCircle,
  HardDrive, Clock, Code2, Eye, Copy, Check,
} from "lucide-react";
import {
  cloneRepo, pullRepo, deleteRepoClone,
  getRepoBranches, checkoutRepoBranch, getClonedRepos,
  getRepoTree, getRepoFile, searchRepoFiles,
  getProjects, getProject, addProjectRepo, latticeIngest,
} from "@/lib/api";
import { showToast } from "@/components/Toast";
import { deriveProjectKey } from "@/lib/workspaceContext";
import { latticeStatus } from "@/lib/api";
import { Link } from "react-router-dom";

interface TreeNode {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
  extension?: string;
  language?: string;
  children?: TreeNode[];
}

interface FileContent {
  path: string;
  content: string;
  size: number;
  lines: number;
  language: string;
  is_binary: boolean;
}

interface SearchResult {
  file: string;
  line: number;
  content: string;
  language: string;
}

interface ClonedRepo {
  repo_id: number;
  owner: string;
  repo_name: string;
  project_id: number;
  clone_branch: string;
  local_path: string;
  disk_usage_mb: number;
  last_pulled_at: string | null;
  total_files: number;
  total_lines: number;
}

function repoProjectKey(r: { owner: string; repo_name: string }) {
  return deriveProjectKey(r.owner, r.repo_name);
}

export default function RepoWorkspace() {
  // --- Tab state ---
  const [activeTab, setActiveTab] = useState<"clone" | "browse" | "search">("clone");

  // --- Clone tab ---
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [clonedRepos, setClonedRepos] = useState<ClonedRepo[]>([]);
  const [cloneOwner, setCloneOwner] = useState("");
  const [cloneRepoName, setCloneRepoName] = useState("");
  const [cloneBranch, setCloneBranch] = useState("");
  const [cloneShallow, setCloneShallow] = useState(true);
  const [cloning, setCloning] = useState(false);
  const [pulling, setPulling] = useState<number | null>(null);
  const [loadingCloned, setLoadingCloned] = useState(true);

  // --- Browse tab ---
  const [browseRepoId, setBrowseRepoId] = useState<number | null>(null);
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);
  const [copied, setCopied] = useState(false);
  const [branches, setBranches] = useState<{ current: string; local: string[]; remote: string[] }>({ current: "", local: [], remote: [] });
  const [checkingOut, setCheckingOut] = useState(false);

  // --- Search tab ---
  const [searchRepoId, setSearchRepoId] = useState<number | null>(null);
  const [searchPattern, setSearchPattern] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [indexStatus, setIndexStatus] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (clonedRepos.length === 0) return;
    void (async () => {
      const next: Record<number, boolean> = {};
      await Promise.all(
        clonedRepos.map(async (r) => {
          try {
            const st = await latticeStatus(repoProjectKey(r));
            next[r.repo_id] = st.indexed;
          } catch {
            next[r.repo_id] = false;
          }
        }),
      );
      setIndexStatus(next);
    })();
  }, [clonedRepos]);

  // --- Load projects + cloned repos ---
  const loadData = useCallback(async () => {
    setLoadingCloned(true);
    try {
      const [projs, repos] = await Promise.all([
        getProjects().catch(() => []),
        getClonedRepos().catch(() => []),
      ]);
      setProjects(projs);
      setClonedRepos(repos);
    } finally {
      setLoadingCloned(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // --- Clone handler ---
  const handleClone = async () => {
    if (!cloneOwner.trim() || !cloneRepoName.trim()) {
      showToast("error", "Enter owner and repo name");
      return;
    }
    if (!selectedProjectId) {
      showToast("error", "Select a project first");
      return;
    }
    setCloning(true);
    const owner = cloneOwner.trim();
    const name = cloneRepoName.trim();
    const projectKey = repoProjectKey({ owner, repo_name: name });
    try {
      let proj = await getProject(selectedProjectId);
      let repo = proj.repos?.find(
        (r: any) => r.owner === owner && r.repo_name === name,
      );
      if (!repo) {
        proj = await addProjectRepo(selectedProjectId, {
          owner,
          repo_name: name,
          default_branch: cloneBranch || "main",
        });
        repo = proj.repos?.find(
          (r: any) => r.owner === owner && r.repo_name === name,
        );
      }
      if (!repo?.id) {
        showToast("error", "Could not create/find repo");
        return;
      }

      const result = await cloneRepo(repo.id, cloneBranch || undefined, cloneShallow);
      const localPath = result.local_path || result.path || "";
      showToast(
        "success",
        `Cloned ${owner}/${name}: ${result.stats?.total_files || 0} files`,
      );

      if (localPath) {
        try {
          await latticeIngest(localPath, projectKey, true);
          localStorage.setItem(
            "zect_mentrix_workspace",
            JSON.stringify({
              path: localPath,
              workspace: localPath,
              project_key: projectKey,
              projectKey,
            }),
          );
          localStorage.setItem("zect_lattice_key", projectKey);
          showToast("success", `Lattice indexed as project key "${projectKey}"`);
        } catch (ingestErr: any) {
          showToast(
            "error",
            `Clone OK; Lattice ingest failed: ${ingestErr?.message || "unknown"}`,
          );
        }
      }

      setCloneOwner("");
      setCloneRepoName("");
      setCloneBranch("");
      await loadData();
    } catch (e: any) {
      showToast("error", e.message || "Clone failed");
    } finally {
      setCloning(false);
    }
  };

  // --- Pull handler ---
  const handlePull = async (repoId: number) => {
    setPulling(repoId);
    try {
      const result = await pullRepo(repoId);
      showToast("success", `Pulled latest: ${result.stats?.total_files || 0} files`);
      const repo = clonedRepos.find((r) => r.repo_id === repoId);
      const localPath = result.local_path || repo?.local_path || "";
      if (localPath) {
        const owner = repo?.owner || "";
        const name = repo?.repo_name || "";
        const projectKey = repoProjectKey({ owner, repo_name: name });
        try {
          await latticeIngest(localPath, projectKey, true);
          localStorage.setItem(
            "zect_mentrix_workspace",
            JSON.stringify({
              path: localPath,
              workspace: localPath,
              project_key: projectKey,
              projectKey,
            }),
          );
          localStorage.setItem("zect_lattice_key", projectKey);
          showToast("success", `Lattice re-indexed as "${projectKey}"`);
        } catch (ingestErr: any) {
          showToast(
            "error",
            `Pull OK; Lattice re-ingest failed: ${ingestErr?.message || "unknown"}`,
          );
        }
      }
      await loadData();
    } catch (e: any) {
      showToast("error", e.message || "Pull failed");
    } finally {
      setPulling(null);
    }
  };

  // --- Delete clone ---
  const handleDelete = async (repoId: number) => {
    if (!confirm("Delete this local clone? The remote repo is not affected.")) return;
    try {
      await deleteRepoClone(repoId);
      showToast("success", "Clone deleted");
      await loadData();
      if (browseRepoId === repoId) {
        setBrowseRepoId(null);
        setTree([]);
        setSelectedFile(null);
      }
    } catch (e: any) {
      showToast("error", e.message || "Delete failed");
    }
  };

  // --- Browse: load tree ---
  const loadTree = useCallback(async (repoId: number) => {
    setBrowseRepoId(repoId);
    setLoadingTree(true);
    setSelectedFile(null);
    setExpandedPaths(new Set());
    try {
      const [treeData, branchData] = await Promise.all([
        getRepoTree(repoId, "", 2),
        getRepoBranches(repoId).catch(() => ({ current: "", local: [], remote: [] })),
      ]);
      setTree(treeData);
      setBranches(branchData);
    } catch (e: any) {
      showToast("error", e.message || "Failed to load tree");
    } finally {
      setLoadingTree(false);
    }
  }, []);

  // --- Browse: expand directory ---
  const toggleDir = async (node: TreeNode) => {
    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(node.path)) {
      newExpanded.delete(node.path);
    } else {
      newExpanded.add(node.path);
      if (!node.children || node.children.length === 0) {
        try {
          const children = await getRepoTree(browseRepoId!, node.path, 1);
          const updateTree = (nodes: TreeNode[]): TreeNode[] =>
            nodes.map((n) => {
              if (n.path === node.path) return { ...n, children: children };
              if (n.children) return { ...n, children: updateTree(n.children) };
              return n;
            });
          setTree(updateTree(tree));
        } catch {
          // ignore
        }
      }
    }
    setExpandedPaths(newExpanded);
  };

  // --- Browse: open file ---
  const openFile = async (path: string) => {
    if (!browseRepoId) return;
    setLoadingFile(true);
    try {
      const file = await getRepoFile(browseRepoId, path);
      setSelectedFile(file);
    } catch (e: any) {
      showToast("error", e.message || "Failed to read file");
    } finally {
      setLoadingFile(false);
    }
  };

  // --- Browse: checkout branch ---
  const handleCheckout = async (branch: string) => {
    if (!browseRepoId) return;
    setCheckingOut(true);
    try {
      await checkoutRepoBranch(browseRepoId, branch);
      showToast("success", `Checked out ${branch}`);
      await loadTree(browseRepoId);
      await loadData();
    } catch (e: any) {
      showToast("error", e.message || "Checkout failed");
    } finally {
      setCheckingOut(false);
    }
  };

  // --- Search ---
  const handleSearch = async () => {
    if (!searchRepoId || !searchPattern.trim()) {
      showToast("error", "Select a repo and enter a search pattern");
      return;
    }
    setSearching(true);
    try {
      const results = await searchRepoFiles(searchRepoId, searchPattern);
      setSearchResults(results);
      if (results.length === 0) showToast("info", "No matches found");
    } catch (e: any) {
      showToast("error", e.message || "Search failed");
    } finally {
      setSearching(false);
    }
  };

  // --- Copy to clipboard ---
  const copyCode = () => {
    if (selectedFile?.content) {
      navigator.clipboard.writeText(selectedFile.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // --- Tree renderer ---
  const renderTree = (nodes: TreeNode[], depth = 0) => (
    <div style={{ paddingLeft: depth * 16 }}>
      {nodes.map((node) => (
        <div key={node.path}>
          <button
            onClick={() => node.is_dir ? toggleDir(node) : openFile(node.path)}
            className={`w-full flex items-center gap-2 px-2 py-1 text-sm hover:bg-slate-100 rounded text-left ${
              selectedFile?.path === node.path ? "bg-blue-50 text-blue-700" : "text-slate-700"
            }`}
          >
            {node.is_dir ? (
              expandedPaths.has(node.path) ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />
            ) : (
              <span className="w-3.5" />
            )}
            {node.is_dir ? (
              <Folder size={14} className="text-yellow-500" />
            ) : (
              <File size={14} className="text-slate-400" />
            )}
            <span className="truncate">{node.name}</span>
            {!node.is_dir && node.size !== undefined && (
              <span className="ml-auto text-xs text-slate-400">
                {node.size > 1024 ? `${(node.size / 1024).toFixed(1)}KB` : `${node.size}B`}
              </span>
            )}
          </button>
          {node.is_dir && expandedPaths.has(node.path) && node.children && (
            renderTree(node.children, depth + 1)
          )}
        </div>
      ))}
    </div>
  );

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Repo Workspace</h1>
        <p className="text-slate-500 text-sm">Clone, browse, and search project repositories locally</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {[
          { key: "clone", label: "Clone & Manage", icon: Download },
          { key: "browse", label: "File Browser", icon: FolderOpen },
          { key: "search", label: "Code Search", icon: Search },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as any)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === key
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* ================================================================ */}
      {/* CLONE TAB */}
      {/* ================================================================ */}
      {activeTab === "clone" && (
        <div className="space-y-6">
          {/* Clone form */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Clone a Repository</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Project</label>
                <select
                  value={selectedProjectId || ""}
                  onChange={(e) => setSelectedProjectId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm"
                >
                  <option value="">Select project...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Owner</label>
                <input
                  value={cloneOwner}
                  onChange={(e) => setCloneOwner(e.target.value)}
                  placeholder="e.g. facebook"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Repository</label>
                <input
                  value={cloneRepoName}
                  onChange={(e) => setCloneRepoName(e.target.value)}
                  placeholder="e.g. react"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Branch (optional)</label>
                <input
                  value={cloneBranch}
                  onChange={(e) => setCloneBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm"
                />
              </div>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={cloneShallow}
                  onChange={(e) => setCloneShallow(e.target.checked)}
                  className="rounded border-slate-300"
                />
                Shallow clone (faster, less disk)
              </label>
              <button
                onClick={handleClone}
                disabled={cloning}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {cloning ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                {cloning ? "Cloning..." : "Clone Repository"}
              </button>
            </div>
          </div>

          {/* Cloned repos list */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-900">Cloned Repositories</h2>
              <button onClick={loadData} className="text-slate-400 hover:text-slate-600">
                <RefreshCw size={16} className={loadingCloned ? "animate-spin" : ""} />
              </button>
            </div>
            {clonedRepos.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <HardDrive size={32} className="mx-auto mb-2 opacity-50" />
                <p>No repositories cloned yet. Clone one above to get started.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {clonedRepos.map((r) => (
                  <div key={r.repo_id} className="flex items-center justify-between p-4 rounded-lg border border-slate-100 hover:border-slate-200 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-50 rounded-lg">
                        <GitBranch size={18} className="text-green-600" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900 flex items-center gap-2">
                          {r.owner}/{r.repo_name}
                          <span
                            data-testid={`repo-lattice-chip-${r.repo_id}`}
                            className={`text-[10px] px-1.5 py-0.5 rounded ${
                              indexStatus[r.repo_id]
                                ? "bg-teal-50 text-teal-700 border border-teal-200"
                                : "bg-slate-100 text-slate-500"
                            }`}
                          >
                            {indexStatus[r.repo_id] ? "Lattice indexed" : "Not indexed"}
                          </span>
                        </div>
                        <div className="text-xs text-slate-500 flex items-center gap-3 flex-wrap">
                          <span className="font-mono text-teal-600">{repoProjectKey(r)}</span>
                          <span className="flex items-center gap-1"><GitBranch size={10} />{r.clone_branch}</span>
                          <span className="flex items-center gap-1"><FileCode size={10} />{r.total_files} files</span>
                          <span className="flex items-center gap-1"><HardDrive size={10} />{r.disk_usage_mb} MB</span>
                          {r.last_pulled_at && (
                            <span className="flex items-center gap-1"><Clock size={10} />{new Date(r.last_pulled_at).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Link
                        to="/lattice"
                        className="px-3 py-1.5 text-xs font-medium text-teal-700 border border-teal-200 rounded-lg hover:bg-teal-50"
                      >
                        Lattice
                      </Link>
                      <Link
                        to="/blueprint"
                        className="px-3 py-1.5 text-xs font-medium text-indigo-700 border border-indigo-200 rounded-lg hover:bg-indigo-50"
                      >
                        Blueprint
                      </Link>
                      <button
                        onClick={() => { setBrowseRepoId(r.repo_id); loadTree(r.repo_id); setActiveTab("browse"); }}
                        className="px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50"
                      >
                        <Eye size={12} className="inline mr-1" />Browse
                      </button>
                      <button
                        onClick={() => { setSearchRepoId(r.repo_id); setActiveTab("search"); }}
                        className="px-3 py-1.5 text-xs font-medium text-purple-600 border border-purple-200 rounded-lg hover:bg-purple-50"
                      >
                        <Search size={12} className="inline mr-1" />Search
                      </button>
                      <button
                        onClick={() => handlePull(r.repo_id)}
                        disabled={pulling === r.repo_id}
                        className="px-3 py-1.5 text-xs font-medium text-green-600 border border-green-200 rounded-lg hover:bg-green-50 disabled:opacity-50"
                      >
                        {pulling === r.repo_id ? <Loader2 size={12} className="inline animate-spin mr-1" /> : <RefreshCw size={12} className="inline mr-1" />}
                        Pull
                      </button>
                      <button
                        onClick={() => handleDelete(r.repo_id)}
                        className="px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
                      >
                        <Trash2 size={12} className="inline mr-1" />Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* BROWSE TAB */}
      {/* ================================================================ */}
      {activeTab === "browse" && (
        <div>
          {/* Repo selector + branch */}
          <div className="flex items-center gap-3 mb-4">
            <select
              value={browseRepoId || ""}
              onChange={(e) => {
                const id = e.target.value ? Number(e.target.value) : null;
                if (id) loadTree(id);
                else { setBrowseRepoId(null); setTree([]); setSelectedFile(null); }
              }}
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm"
            >
              <option value="">Select repo to browse...</option>
              {clonedRepos.map((r) => (
                <option key={r.repo_id} value={r.repo_id}>{r.owner}/{r.repo_name}</option>
              ))}
            </select>
            {browseRepoId && branches.local.length > 0 && (
              <select
                value={branches.current}
                onChange={(e) => handleCheckout(e.target.value)}
                disabled={checkingOut}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm"
              >
                {[...branches.local, ...branches.remote].map((b) => (
                  <option key={b} value={b}>{b}{b === branches.current ? " (current)" : ""}</option>
                ))}
              </select>
            )}
            {checkingOut && <Loader2 size={16} className="animate-spin text-slate-400" />}
          </div>

          {!browseRepoId ? (
            <div className="text-center py-16 text-slate-400">
              <FolderOpen size={48} className="mx-auto mb-3 opacity-40" />
              <p>Select a cloned repository to browse its files</p>
            </div>
          ) : loadingTree ? (
            <div className="text-center py-16">
              <Loader2 size={32} className="mx-auto animate-spin text-blue-500" />
              <p className="text-slate-500 mt-2">Loading file tree...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* File tree panel */}
              <div className="bg-white rounded-xl border border-slate-200 p-3 max-h-[70vh] overflow-y-auto">
                <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                  <Folder size={14} className="text-yellow-500" />
                  File Tree
                </h3>
                {tree.length === 0 ? (
                  <p className="text-xs text-slate-400 py-4 text-center">Empty repository</p>
                ) : (
                  renderTree(tree)
                )}
              </div>

              {/* Code viewer panel */}
              <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 max-h-[70vh] overflow-hidden flex flex-col">
                {loadingFile ? (
                  <div className="flex-1 flex items-center justify-center">
                    <Loader2 size={24} className="animate-spin text-blue-500" />
                  </div>
                ) : selectedFile ? (
                  <>
                    <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100 bg-slate-50">
                      <div className="flex items-center gap-2">
                        <FileCode size={14} className="text-blue-500" />
                        <span className="text-sm font-medium text-slate-700">{selectedFile.path}</span>
                        <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">{selectedFile.language}</span>
                        <span className="text-xs text-slate-400">{selectedFile.lines} lines</span>
                      </div>
                      <button onClick={copyCode} className="text-slate-400 hover:text-slate-600">
                        {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                      </button>
                    </div>
                    <div className="flex-1 overflow-auto">
                      {selectedFile.is_binary ? (
                        <div className="flex items-center justify-center h-full text-slate-400">
                          <AlertCircle size={20} className="mr-2" />
                          Binary file — cannot display
                        </div>
                      ) : (
                        <pre className="p-4 text-sm font-mono text-slate-800 leading-relaxed">
                          {selectedFile.content.split("\n").map((line, i) => (
                            <div key={i} className="flex hover:bg-yellow-50">
                              <span className="w-12 text-right pr-4 text-slate-300 select-none text-xs leading-relaxed">{i + 1}</span>
                              <code className="flex-1 whitespace-pre-wrap break-all">{line}</code>
                            </div>
                          ))}
                        </pre>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-400">
                    <div className="text-center">
                      <Eye size={32} className="mx-auto mb-2 opacity-40" />
                      <p>Click a file in the tree to view its content</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ================================================================ */}
      {/* SEARCH TAB */}
      {/* ================================================================ */}
      {activeTab === "search" && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <select
              value={searchRepoId || ""}
              onChange={(e) => setSearchRepoId(e.target.value ? Number(e.target.value) : null)}
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm"
            >
              <option value="">Select repo to search...</option>
              {clonedRepos.map((r) => (
                <option key={r.repo_id} value={r.repo_id}>{r.owner}/{r.repo_name}</option>
              ))}
            </select>
            <div className="flex-1 relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={searchPattern}
                onChange={(e) => setSearchPattern(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search pattern (regex supported)..."
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 text-sm"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={searching}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
            >
              {searching ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
              Search
            </button>
          </div>

          {searchResults.length > 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
              <div className="px-4 py-2 bg-slate-50 text-xs font-medium text-slate-500">
                {searchResults.length} match{searchResults.length !== 1 ? "es" : ""} found
              </div>
              {searchResults.map((r, i) => (
                <button
                  key={i}
                  onClick={() => {
                    if (searchRepoId) {
                      setBrowseRepoId(searchRepoId);
                      openFile(r.file);
                      setActiveTab("browse");
                    }
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-slate-50 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <FileCode size={12} className="text-blue-500 shrink-0" />
                    <span className="font-medium text-slate-700">{r.file}</span>
                    <span className="text-xs text-slate-400">:{r.line}</span>
                    {r.language && <span className="text-xs bg-slate-100 text-slate-500 px-1 rounded">{r.language}</span>}
                  </div>
                  <pre className="mt-1 text-xs text-slate-500 font-mono truncate">{r.content}</pre>
                </button>
              ))}
            </div>
          ) : !searching ? (
            <div className="text-center py-16 text-slate-400">
              <Code2 size={48} className="mx-auto mb-3 opacity-40" />
              <p>Search across cloned repositories using regex patterns</p>
              <p className="text-xs mt-1">Examples: <code className="bg-slate-100 px-1 rounded">useState</code>, <code className="bg-slate-100 px-1 rounded">def\s+\w+</code>, <code className="bg-slate-100 px-1 rounded">TODO|FIXME</code></p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";
import { CheckoutBlockedError, checkoutRepoBranch, getRepoIdentity } from "@/lib/api";
import { deriveProjectKey, writeMentrixWorkspace } from "@/lib/workspaceContext";
import { canonicalLatticeState, latticeHeaderLabel } from "@/lib/contextUsed";
import { GitBranch, FolderOpen, RefreshCw, ChevronDown, Network } from "lucide-react";
import { Link } from "react-router-dom";
import { useState, useRef, useEffect } from "react";

export default function ProjectRepoSelector() {
  const {
    projects,
    repos,
    activeProjectId,
    activeRepoId,
    activeBranch,
    branches,
    loading,
    setActiveProject,
    setActiveRepo,
    setActiveBranch,
    refresh,
    activeRepo,
    activeProject,
  } = useActiveProject();
  const { latticeStatus: latticeIdx, loadingStatus, projectKey, refreshStatus } =
    useWorkspaceRepoContext();

  const [showProjectDD, setShowProjectDD] = useState(false);
  const [showRepoDD, setShowRepoDD] = useState(false);
  const [showBranchDD, setShowBranchDD] = useState(false);
  const [branchBusy, setBranchBusy] = useState(false);
  const [branchError, setBranchError] = useState("");
  const [headSha, setHeadSha] = useState("");
  const [dirty, setDirty] = useState(false);
  const [pendingBranch, setPendingBranch] = useState<string | null>(null);
  const projectRef = useRef<HTMLDivElement>(null);
  const repoRef = useRef<HTMLDivElement>(null);
  const branchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (projectRef.current && !projectRef.current.contains(e.target as Node)) setShowProjectDD(false);
      if (repoRef.current && !repoRef.current.contains(e.target as Node)) setShowRepoDD(false);
      if (branchRef.current && !branchRef.current.contains(e.target as Node)) setShowBranchDD(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      setShowProjectDD(false);
      setShowRepoDD(false);
      setShowBranchDD(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  useEffect(() => {
    setPendingBranch(null);
    setBranchError("");
    setHeadSha("");
    setDirty(false);
    if (!activeRepoId) return;
    if (!repos.some((r) => r.repo_id === activeRepoId)) return;
    getRepoIdentity(activeRepoId)
      .then((id) => {
        setHeadSha(id.head_sha || "");
        setDirty(Boolean(id.dirty));
        // Prefer live git branch for THIS repo only
        if (id.branch) setActiveBranch(id.branch);
        if (id.local_path && id.owner && id.name) {
          // Only rewrite workspace if identity matches the selected catalog entry
          const catalogOk =
            !activeRepo ||
            (activeRepo.owner.toLowerCase() === String(id.owner).toLowerCase() &&
              activeRepo.repo_name.toLowerCase() === String(id.name).toLowerCase());
          if (catalogOk) {
            writeMentrixWorkspace(id.local_path, deriveProjectKey(id.owner, id.name));
          } else if (activeRepo?.local_path) {
            // Keep catalog key; path may be wrong — still show identity for debugging
            writeMentrixWorkspace(
              activeRepo.local_path,
              deriveProjectKey(activeRepo.owner, activeRepo.repo_name),
            );
          }
        } else if (activeRepo?.local_path) {
          writeMentrixWorkspace(
            activeRepo.local_path,
            deriveProjectKey(activeRepo.owner, activeRepo.repo_name),
          );
        }
      })
      .catch(() => {
        setHeadSha("");
        setDirty(false);
      });
  }, [activeRepoId, repos, activeRepo, setActiveBranch]);

  const filteredRepos = repos.filter(
    (r) => !activeProjectId || r.project_id === activeProjectId,
  );

  const doCheckout = async (branch: string, action: "require_clean" | "stash" | "force_discard") => {
    if (!activeRepoId) return;
    setBranchBusy(true);
    setBranchError("");
    try {
      const out = await checkoutRepoBranch(activeRepoId, branch, action);
      setActiveBranch(out.branch || branch);
      setHeadSha(out.head_sha || "");
      setDirty(Boolean(out.dirty));
      setPendingBranch(null);
      setShowBranchDD(false);
      await refresh();
      refreshStatus?.();
    } catch (e) {
      if (e instanceof CheckoutBlockedError && e.detail?.error === "dirty_working_tree") {
        setPendingBranch(branch);
        setBranchError("Working tree is dirty — choose Cancel, Stash, or Force discard.");
      } else {
        setBranchError(e instanceof Error ? e.message : "Checkout failed");
      }
    } finally {
      setBranchBusy(false);
    }
  };

  const latticeState = canonicalLatticeState(
    latticeIdx?.state || (latticeIdx?.indexed ? "READY" : projectKey ? "NOT_INDEXED" : "NOT_APPLICABLE"),
  );
  const latticeTone = loadingStatus
    ? "bg-slate-100 text-slate-500"
    : latticeState === "READY"
      ? "bg-teal-50 text-teal-700 border border-teal-200"
      : latticeState === "ERROR"
        ? "bg-rose-50 text-rose-700 border border-rose-200"
        : "bg-amber-50 text-amber-700 border border-amber-200";

  return (
    <div className="flex items-center gap-2 text-sm flex-wrap">
      <div ref={projectRef} className="relative">
        <button
          type="button"
          aria-haspopup="listbox"
          aria-expanded={showProjectDD}
          data-testid="select-project-button"
          onClick={() => setShowProjectDD(!showProjectDD)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors max-w-[180px]"
        >
          <FolderOpen size={14} className="text-blue-500 shrink-0" />
          <span className="truncate">{activeProject?.name || "All Projects"}</span>
          <ChevronDown size={12} className="shrink-0 text-slate-400" />
        </button>
        {showProjectDD && (
          <div
            data-testid="select-project-dropdown"
            className="zect-dropdown absolute top-full left-0 mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto"
          >
            <button
              onClick={() => {
                setActiveProject(null);
                setShowProjectDD(false);
              }}
              className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${!activeProjectId ? "bg-blue-50 text-blue-700 font-medium" : "text-slate-700"}`}
            >
              All Projects
            </button>
            {projects.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setActiveProject(p.id);
                  setShowProjectDD(false);
                }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${activeProjectId === p.id ? "bg-blue-50 text-blue-700 font-medium" : "text-slate-700"}`}
              >
                {p.name}
              </button>
            ))}
            {projects.length === 0 && (
              <div className="px-3 py-2 text-xs text-slate-400">No projects yet</div>
            )}
            <Link
              to="/projects"
              className="block px-3 py-2 text-xs text-indigo-600 border-t border-slate-100 hover:bg-slate-50"
              onClick={() => setShowProjectDD(false)}
            >
              Open / Clone / Discover…
            </Link>
          </div>
        )}
      </div>

      <div ref={repoRef} className="relative">
        <button
          type="button"
          data-testid="select-repo-button"
          aria-haspopup="listbox"
          aria-expanded={showRepoDD}
          onClick={() => setShowRepoDD(!showRepoDD)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors max-w-[200px]"
        >
          <GitBranch size={14} className="text-green-500 shrink-0" />
          <span className="truncate">
            {activeRepo ? `${activeRepo.owner}/${activeRepo.repo_name}` : "Select Repo"}
          </span>
          <ChevronDown size={12} className="shrink-0 text-slate-400" />
        </button>
        {showRepoDD && (
          <div
            data-testid="select-repo-dropdown"
            className="zect-dropdown absolute top-full left-0 mt-1 w-72 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-72 overflow-y-auto"
          >
            <button
              onClick={() => {
                setActiveRepo(null);
                setShowRepoDD(false);
              }}
              className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${!activeRepoId ? "bg-green-50 text-green-700 font-medium" : "text-slate-700"}`}
            >
              No Repo Selected
            </button>
            {filteredRepos.map((r) => (
              <button
                key={r.repo_id}
                data-testid={`select-repo-${r.repo_id}`}
                onClick={() => {
                  setActiveRepo(r.repo_id);
                  if (r.local_path) {
                    writeMentrixWorkspace(
                      r.local_path,
                      deriveProjectKey(r.owner, r.repo_name),
                    );
                  }
                  setShowRepoDD(false);
                }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${activeRepoId === r.repo_id ? "bg-green-50 text-green-700 font-medium" : "text-slate-700"}`}
              >
                <div className="font-medium">
                  {r.owner}/{r.repo_name}
                </div>
                <div className="text-xs text-slate-400 truncate" title={r.local_path || undefined}>
                  {r.clone_branch || "—"} · {r.local_path || "no local path"}
                </div>
              </button>
            ))}
            {filteredRepos.length === 0 && (
              <div className="px-3 py-2 text-xs text-slate-400">
                No cloned repos yet.
              </div>
            )}
            <Link
              to="/projects"
              data-testid="select-repo-onboard-link"
              className="block px-3 py-2 text-xs text-indigo-600 border-t border-slate-100 hover:bg-slate-50"
              onClick={() => setShowRepoDD(false)}
            >
              Open Local / Clone / Discover / Attach…
            </Link>
          </div>
        )}
      </div>

      {activeRepoId && (
        <div ref={branchRef} className="relative">
          <button
            type="button"
            data-testid="select-branch-button"
            aria-haspopup="listbox"
            aria-expanded={showBranchDD}
            onClick={() => setShowBranchDD(!showBranchDD)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors max-w-[160px]"
          >
            <GitBranch size={14} className="text-purple-500 shrink-0" />
            <span className="truncate">{activeBranch || "Branch"}</span>
            {dirty && (
              <span className="text-[10px] text-amber-600 font-medium" data-testid="repo-dirty-badge">
                dirty
              </span>
            )}
            <ChevronDown size={12} className="shrink-0 text-slate-400" />
          </button>
          {showBranchDD && (
            <div
              data-testid="select-branch-dropdown"
              className="zect-dropdown absolute top-full left-0 mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto"
            >
              {branches.map((b) => (
                <button
                  key={b}
                  data-testid={`select-branch-${b}`}
                  disabled={branchBusy}
                  onClick={() => void doCheckout(b, "require_clean")}
                  className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm disabled:opacity-50 ${activeBranch === b ? "bg-purple-50 text-purple-700 font-medium" : "text-slate-700"}`}
                >
                  {b}
                </button>
              ))}
              {branches.length === 0 && (
                <div className="px-3 py-2 text-xs text-slate-400">No branches</div>
              )}
              {headSha && (
                <div
                  data-testid="repo-head-sha"
                  className="px-3 py-2 text-[10px] font-mono text-slate-500 border-t border-slate-100 truncate"
                >
                  HEAD {headSha.slice(0, 12)}
                </div>
              )}
              {activeRepo?.local_path && (
                <div
                  data-testid="repo-bound-path"
                  className="px-3 py-2 text-[10px] text-slate-500 border-t border-slate-100 truncate"
                  title={activeRepo.local_path}
                >
                  Bound path: {activeRepo.local_path}
                </div>
              )}
              {branchError && (
                <div
                  data-testid="branch-checkout-error"
                  className="px-3 py-2 text-[11px] text-red-600 border-t border-slate-100"
                >
                  {branchError}
                </div>
              )}
              {pendingBranch && (
                <div
                  data-testid="dirty-checkout-modal"
                  className="px-3 py-2 border-t border-amber-100 bg-amber-50 space-y-1"
                >
                  <p className="text-[11px] text-amber-900">
                    Switch to <strong>{pendingBranch}</strong> with dirty changes?
                  </p>
                  <div className="flex flex-wrap gap-1">
                    <button
                      type="button"
                      data-testid="dirty-cancel"
                      className="text-[11px] px-2 py-1 rounded border border-slate-200 bg-white"
                      onClick={() => {
                        setPendingBranch(null);
                        setBranchError("");
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      data-testid="dirty-stash"
                      className="text-[11px] px-2 py-1 rounded border border-indigo-200 bg-indigo-50 text-indigo-800"
                      disabled={branchBusy}
                      onClick={() => void doCheckout(pendingBranch, "stash")}
                    >
                      Stash
                    </button>
                    <button
                      type="button"
                      data-testid="dirty-force"
                      className="text-[11px] px-2 py-1 rounded border border-red-200 bg-red-50 text-red-700"
                      disabled={branchBusy}
                      onClick={() => void doCheckout(pendingBranch, "force_discard")}
                    >
                      Force discard
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeRepo && projectKey && (
        <span
          data-testid="workspace-lattice-status"
          data-lattice-state={loadingStatus ? "" : latticeState}
          className={`hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium ${latticeTone}`}
          title={[projectKey, latticeIdx?.indexed_commit_sha && `indexed=${String(latticeIdx.indexed_commit_sha).slice(0, 12)}`, latticeIdx?.live_commit_sha && `head=${String(latticeIdx.live_commit_sha).slice(0, 12)}`].filter(Boolean).join(" · ")}
        >
          <Network size={10} />
          {loadingStatus ? "…" : latticeHeaderLabel(latticeState)}
        </span>
      )}
      <button
        onClick={() => void refresh()}
        disabled={loading}
        className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
        title="Refresh projects & repos"
      >
        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
      </button>
    </div>
  );
}

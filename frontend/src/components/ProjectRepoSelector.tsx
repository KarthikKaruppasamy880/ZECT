import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { GitBranch, FolderOpen, RefreshCw, ChevronDown } from "lucide-react";
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

  const [showProjectDD, setShowProjectDD] = useState(false);
  const [showRepoDD, setShowRepoDD] = useState(false);
  const [showBranchDD, setShowBranchDD] = useState(false);
  const projectRef = useRef<HTMLDivElement>(null);
  const repoRef = useRef<HTMLDivElement>(null);
  const branchRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (projectRef.current && !projectRef.current.contains(e.target as Node)) setShowProjectDD(false);
      if (repoRef.current && !repoRef.current.contains(e.target as Node)) setShowRepoDD(false);
      if (branchRef.current && !branchRef.current.contains(e.target as Node)) setShowBranchDD(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filteredRepos = repos.filter(
    (r) => !activeProjectId || r.project_id === activeProjectId
  );

  return (
    <div className="flex items-center gap-2 text-sm">
      {/* Project Selector */}
      <div ref={projectRef} className="relative">
        <button
          onClick={() => setShowProjectDD(!showProjectDD)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors max-w-[180px]"
        >
          <FolderOpen size={14} className="text-blue-500 shrink-0" />
          <span className="truncate">{activeProject?.name || "All Projects"}</span>
          <ChevronDown size={12} className="shrink-0 text-slate-400" />
        </button>
        {showProjectDD && (
          <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
            <button
              onClick={() => { setActiveProject(null); setShowProjectDD(false); }}
              className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${!activeProjectId ? "bg-blue-50 text-blue-700 font-medium" : "text-slate-700"}`}
            >
              All Projects
            </button>
            {projects.map((p) => (
              <button
                key={p.id}
                onClick={() => { setActiveProject(p.id); setShowProjectDD(false); }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${activeProjectId === p.id ? "bg-blue-50 text-blue-700 font-medium" : "text-slate-700"}`}
              >
                {p.name}
              </button>
            ))}
            {projects.length === 0 && (
              <div className="px-3 py-2 text-xs text-slate-400">No projects yet</div>
            )}
          </div>
        )}
      </div>

      {/* Repo Selector */}
      <div ref={repoRef} className="relative">
        <button
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
          <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
            <button
              onClick={() => { setActiveRepo(null); setShowRepoDD(false); }}
              className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${!activeRepoId ? "bg-green-50 text-green-700 font-medium" : "text-slate-700"}`}
            >
              No Repo Selected
            </button>
            {filteredRepos.map((r) => (
              <button
                key={r.repo_id}
                onClick={() => { setActiveRepo(r.repo_id); setShowRepoDD(false); }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${activeRepoId === r.repo_id ? "bg-green-50 text-green-700 font-medium" : "text-slate-700"}`}
              >
                <div className="font-medium">{r.owner}/{r.repo_name}</div>
                <div className="text-xs text-slate-400">{r.clone_branch} &middot; {r.total_files} files</div>
              </button>
            ))}
            {filteredRepos.length === 0 && (
              <div className="px-3 py-2 text-xs text-slate-400">No cloned repos. Go to Repo Workspace to clone one.</div>
            )}
          </div>
        )}
      </div>

      {/* Branch Selector */}
      {activeRepoId && (
        <div ref={branchRef} className="relative">
          <button
            onClick={() => setShowBranchDD(!showBranchDD)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors max-w-[160px]"
          >
            <GitBranch size={14} className="text-purple-500 shrink-0" />
            <span className="truncate">{activeBranch || "Branch"}</span>
            <ChevronDown size={12} className="shrink-0 text-slate-400" />
          </button>
          {showBranchDD && (
            <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
              {branches.map((b) => (
                <button
                  key={b}
                  onClick={() => { setActiveBranch(b); setShowBranchDD(false); }}
                  className={`w-full text-left px-3 py-2 hover:bg-slate-50 text-sm ${activeBranch === b ? "bg-purple-50 text-purple-700 font-medium" : "text-slate-700"}`}
                >
                  {b}
                </button>
              ))}
              {branches.length === 0 && (
                <div className="px-3 py-2 text-xs text-slate-400">No branches</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Refresh */}
      <button
        onClick={refresh}
        disabled={loading}
        className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
        title="Refresh projects & repos"
      >
        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
      </button>
    </div>
  );
}

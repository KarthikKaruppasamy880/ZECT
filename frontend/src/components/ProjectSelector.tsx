import { useState, useRef, useEffect } from "react";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import { Link } from "react-router-dom";
import {
  FolderGit2,
  ChevronDown,
  GitBranch,
  Check,
  Plus,
  Loader2,
  X,
} from "lucide-react";

export default function ProjectSelector() {
  const {
    projects,
    activeProject,
    activeRepo,
    loading,
    setActiveProject,
    setActiveRepo,
  } = useActiveProject();

  const [open, setOpen] = useState(false);
  const [repoOpen, setRepoOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const repoDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
      if (repoDropdownRef.current && !repoDropdownRef.current.contains(e.target as Node)) {
        setRepoOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 rounded-lg border border-slate-700">
        <Loader2 className="h-3.5 w-3.5 text-slate-400 animate-spin" />
        <span className="text-xs text-slate-400">Loading...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {/* Project Selector */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setOpen(!open)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
            activeProject
              ? "bg-indigo-900/40 border-indigo-500/50 text-indigo-200 hover:bg-indigo-900/60"
              : "bg-slate-800/50 border-slate-700 text-slate-300 hover:bg-slate-700/50"
          }`}
        >
          <FolderGit2 className="h-3.5 w-3.5" />
          <span className="max-w-[140px] truncate">
            {activeProject ? activeProject.name : "Select Project"}
          </span>
          <ChevronDown className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`} />
        </button>

        {open && (
          <div className="absolute top-full left-0 mt-1 w-64 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
            <div className="p-2 border-b border-slate-700">
              <p className="text-[10px] uppercase text-slate-500 font-semibold px-2">Active Project</p>
            </div>
            <div className="max-h-60 overflow-y-auto">
              {/* No project option */}
              <button
                onClick={() => { setActiveProject(null); setOpen(false); }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-slate-700/50 transition-colors ${
                  !activeProject ? "text-indigo-300 bg-indigo-900/20" : "text-slate-300"
                }`}
              >
                <X className="h-3 w-3 text-slate-500" />
                <span>No project selected</span>
                {!activeProject && <Check className="h-3 w-3 ml-auto text-indigo-400" />}
              </button>

              {projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => { setActiveProject(p); setOpen(false); }}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-slate-700/50 transition-colors ${
                    activeProject?.id === p.id ? "text-indigo-300 bg-indigo-900/20" : "text-slate-300"
                  }`}
                >
                  <FolderGit2 className="h-3 w-3 shrink-0" />
                  <span className="truncate flex-1 text-left">{p.name}</span>
                  <span className="text-[10px] text-slate-500 shrink-0">
                    {p.repos.length} repo{p.repos.length !== 1 ? "s" : ""}
                  </span>
                  {activeProject?.id === p.id && <Check className="h-3 w-3 text-indigo-400 shrink-0" />}
                </button>
              ))}
            </div>
            <div className="p-2 border-t border-slate-700">
              <Link
                to="/projects/new"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-3 py-1.5 text-xs text-indigo-300 hover:bg-indigo-900/20 rounded transition-colors"
              >
                <Plus className="h-3 w-3" /> Create New Project
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Repo Selector (only when project is selected and has repos) */}
      {activeProject && activeProject.repos.length > 0 && (
        <div className="relative" ref={repoDropdownRef}>
          <button
            onClick={() => setRepoOpen(!repoOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-emerald-900/30 border-emerald-500/40 text-emerald-200 text-xs font-medium hover:bg-emerald-900/50 transition-colors"
          >
            <GitBranch className="h-3.5 w-3.5" />
            <span className="max-w-[160px] truncate">
              {activeRepo ? `${activeRepo.owner}/${activeRepo.repo_name}` : "Select Repo"}
            </span>
            {activeProject.repos.length > 1 && (
              <ChevronDown className={`h-3 w-3 transition-transform ${repoOpen ? "rotate-180" : ""}`} />
            )}
          </button>

          {repoOpen && activeProject.repos.length > 1 && (
            <div className="absolute top-full left-0 mt-1 w-64 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
              <div className="p-2 border-b border-slate-700">
                <p className="text-[10px] uppercase text-slate-500 font-semibold px-2">
                  Repos in {activeProject.name}
                </p>
              </div>
              <div className="max-h-48 overflow-y-auto">
                {activeProject.repos.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => { setActiveRepo(r); setRepoOpen(false); }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-slate-700/50 transition-colors ${
                      activeRepo?.id === r.id ? "text-emerald-300 bg-emerald-900/20" : "text-slate-300"
                    }`}
                  >
                    <GitBranch className="h-3 w-3 shrink-0" />
                    <span className="truncate flex-1 text-left">{r.owner}/{r.repo_name}</span>
                    <span className="text-[10px] text-slate-500 shrink-0">{r.default_branch}</span>
                    {activeRepo?.id === r.id && <Check className="h-3 w-3 text-emerald-400 shrink-0" />}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Status indicator */}
      {activeProject && (
        <div className="hidden md:flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${activeRepo ? "bg-emerald-400" : "bg-amber-400"}`} />
          <span className="text-[10px] text-slate-500">
            {activeRepo ? "Connected" : "No repo linked"}
          </span>
        </div>
      )}
    </div>
  );
}

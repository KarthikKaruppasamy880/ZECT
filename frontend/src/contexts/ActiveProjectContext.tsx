import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getProjects, getClonedRepos, getRepoBranches } from "@/lib/api";

interface RepoInfo {
  repo_id: number;
  owner: string;
  repo_name: string;
  project_id: number;
  clone_status: string;
  clone_branch: string | null;
  local_path: string | null;
  disk_usage_mb: number;
  total_files: number;
  total_lines: number;
}

interface ProjectInfo {
  id: number;
  name: string;
  status: string;
}

interface ActiveProjectState {
  projects: ProjectInfo[];
  repos: RepoInfo[];
  activeProjectId: number | null;
  activeRepoId: number | null;
  activeBranch: string | null;
  branches: string[];
  loading: boolean;

  setActiveProject: (id: number | null) => void;
  setActiveRepo: (id: number | null) => void;
  setActiveBranch: (branch: string | null) => void;
  refresh: () => Promise<void>;
  activeRepo: RepoInfo | null;
  activeProject: ProjectInfo | null;
}

const ActiveProjectContext = createContext<ActiveProjectState | null>(null);

const STORAGE_KEY = "zect_active_project";

function loadFromStorage(): { projectId: number | null; repoId: number | null; branch: string | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        projectId: parsed.projectId ?? null,
        repoId: parsed.repoId ?? null,
        branch: parsed.branch ?? null,
      };
    }
  } catch {
    // ignore
  }
  return { projectId: null, repoId: null, branch: null };
}

function saveToStorage(projectId: number | null, repoId: number | null, branch: string | null) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ projectId, repoId, branch }));
  } catch {
    // ignore
  }
}

export function ActiveProjectProvider({ children }: { children: ReactNode }) {
  const stored = loadFromStorage();
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(stored.projectId);
  const [activeRepoId, setActiveRepoId] = useState<number | null>(stored.repoId);
  const [activeBranch, setActiveBranch] = useState<string | null>(stored.branch);
  const [branches, setBranches] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [projs, cloned] = await Promise.all([
        getProjects().catch(() => []),
        getClonedRepos().catch(() => []),
      ]);
      setProjects(projs.map((p: any) => ({ id: p.id, name: p.name, status: p.status })));
      setRepos(cloned.map((r: any) => ({
        repo_id: r.repo_id,
        owner: r.owner,
        repo_name: r.repo_name,
        project_id: r.project_id,
        clone_status: "cloned",
        clone_branch: r.clone_branch,
        local_path: r.local_path,
        disk_usage_mb: r.disk_usage_mb || 0,
        total_files: r.total_files || 0,
        total_lines: r.total_lines || 0,
      })));
    } catch {
      // swallow
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Fetch branches when active repo changes
  useEffect(() => {
    if (activeRepoId) {
      getRepoBranches(activeRepoId)
        .then((data) => {
          const all = [...(data.local || []), ...(data.remote || [])];
          setBranches([...new Set(all)]);
          if (data.current && !activeBranch) {
            setActiveBranch(data.current);
          }
        })
        .catch(() => setBranches([]));
    } else {
      setBranches([]);
    }
  }, [activeRepoId]);

  // Persist to localStorage
  useEffect(() => {
    saveToStorage(activeProjectId, activeRepoId, activeBranch);
  }, [activeProjectId, activeRepoId, activeBranch]);

  const setActiveProject = useCallback((id: number | null) => {
    setActiveProjectId(id);
    // Reset repo when project changes
    setActiveRepoId(null);
    setActiveBranch(null);
  }, []);

  const setActiveRepo = useCallback((id: number | null) => {
    setActiveRepoId(id);
    setActiveBranch(null);
  }, []);

  const activeRepo = repos.find((r) => r.repo_id === activeRepoId) || null;
  const activeProject = projects.find((p) => p.id === activeProjectId) || null;

  return (
    <ActiveProjectContext.Provider
      value={{
        projects,
        repos,
        activeProjectId,
        activeRepoId,
        activeBranch,
        branches,
        loading,
        setActiveProject,
        setActiveRepo,
        setActiveBranch: (b) => setActiveBranch(b),
        refresh,
        activeRepo,
        activeProject,
      }}
    >
      {children}
    </ActiveProjectContext.Provider>
  );
}

export function useActiveProject() {
  const ctx = useContext(ActiveProjectContext);
  if (!ctx) {
    throw new Error("useActiveProject must be used within ActiveProjectProvider");
  }
  return ctx;
}

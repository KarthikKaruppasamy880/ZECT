import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getProjects, getClonedRepos, getRepoBranches } from "@/lib/api";
import { deriveProjectKey, writeMentrixWorkspace } from "@/lib/workspaceContext";

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
  activeProjectKey: string;
  activeLocalPath: string | null;
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

  // Fetch branches when active repo changes — never keep another repo's branch list
  useEffect(() => {
    let cancelled = false;
    if (!activeRepoId) {
      setBranches([]);
      return;
    }
    setBranches([]);
    getRepoBranches(activeRepoId)
      .then((data) => {
        if (cancelled) return;
        const all = [...(data.local || []), ...(data.remote || [])].filter(Boolean);
        const unique = [...new Set(all)];
        setBranches(unique);
        const current = data.current || null;
        // Always align displayed branch to THIS repo's HEAD (drop stale Mentrix/etc branch names)
        setActiveBranch((prev) => {
          if (current && unique.includes(current)) return current;
          if (prev && unique.includes(prev)) return prev;
          return current || unique[0] || null;
        });
      })
      .catch(() => {
        if (!cancelled) {
          setBranches([]);
          setActiveBranch(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeRepoId]);

  // Persist to localStorage
  useEffect(() => {
    saveToStorage(activeProjectId, activeRepoId, activeBranch);
  }, [activeProjectId, activeRepoId, activeBranch]);

  const setActiveProject = useCallback((id: number | null) => {
    setActiveProjectId((prev) => {
      if (prev === id) return prev;
      // Only clear repo when switching to a different project
      setActiveRepoId(null);
      setActiveBranch(null);
      return id;
    });
  }, []);

  const setActiveRepo = useCallback((id: number | null) => {
    setActiveRepoId(id);
    setActiveBranch(null);
    setBranches([]);
  }, []);

  const activeRepo = repos.find((r) => r.repo_id === activeRepoId) || null;
  const activeProject = projects.find((p) => p.id === activeProjectId) || null;
  const activeProjectKey = activeRepo
    ? deriveProjectKey(activeRepo.owner, activeRepo.repo_name)
    : "";
  const activeLocalPath = activeRepo?.local_path ?? null;

  useEffect(() => {
    if (activeRepo?.local_path) {
      writeMentrixWorkspace(
        activeRepo.local_path,
        deriveProjectKey(activeRepo.owner, activeRepo.repo_name),
      );
    }
  }, [activeRepo?.repo_id, activeRepo?.local_path, activeRepo?.owner, activeRepo?.repo_name]);

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
        activeProjectKey,
        activeLocalPath,
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

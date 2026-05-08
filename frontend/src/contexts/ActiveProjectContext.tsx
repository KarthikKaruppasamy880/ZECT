import { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { Project, Repo } from "@/types";
import { getProjects } from "@/lib/api";

interface ActiveProjectState {
  projects: Project[];
  activeProject: Project | null;
  activeRepo: Repo | null;
  loading: boolean;
  setActiveProject: (project: Project | null) => void;
  setActiveRepo: (repo: Repo | null) => void;
  refreshProjects: () => void;
  /** Convenience: returns "owner/repo_name" for the active repo */
  repoFullName: string | null;
  /** Convenience: returns repo context string for AI prompts */
  repoContextString: string | null;
}

const ActiveProjectContext = createContext<ActiveProjectState>({
  projects: [],
  activeProject: null,
  activeRepo: null,
  loading: true,
  setActiveProject: () => {},
  setActiveRepo: () => {},
  refreshProjects: () => {},
  repoFullName: null,
  repoContextString: null,
});

export function ActiveProjectProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProjectState] = useState<Project | null>(null);
  const [activeRepo, setActiveRepoState] = useState<Repo | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProjects = useCallback(() => {
    setLoading(true);
    getProjects()
      .then((data) => {
        setProjects(data);
        // Restore from localStorage
        const savedProjectId = localStorage.getItem("zect_active_project_id");
        const savedRepoId = localStorage.getItem("zect_active_repo_id");
        if (savedProjectId) {
          const proj = data.find((p) => p.id === Number(savedProjectId));
          if (proj) {
            setActiveProjectState(proj);
            if (savedRepoId && proj.repos.length > 0) {
              const repo = proj.repos.find((r) => r.id === Number(savedRepoId));
              setActiveRepoState(repo || proj.repos[0]);
            } else if (proj.repos.length > 0) {
              setActiveRepoState(proj.repos[0]);
            }
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const setActiveProject = useCallback((project: Project | null) => {
    setActiveProjectState(project);
    if (project) {
      localStorage.setItem("zect_active_project_id", String(project.id));
      // Auto-select first repo if available
      if (project.repos.length > 0) {
        const savedRepoId = localStorage.getItem("zect_active_repo_id");
        const repo = savedRepoId
          ? project.repos.find((r) => r.id === Number(savedRepoId)) || project.repos[0]
          : project.repos[0];
        setActiveRepoState(repo);
        localStorage.setItem("zect_active_repo_id", String(repo.id));
      } else {
        setActiveRepoState(null);
        localStorage.removeItem("zect_active_repo_id");
      }
    } else {
      localStorage.removeItem("zect_active_project_id");
      localStorage.removeItem("zect_active_repo_id");
      setActiveRepoState(null);
    }
  }, []);

  const setActiveRepo = useCallback((repo: Repo | null) => {
    setActiveRepoState(repo);
    if (repo) {
      localStorage.setItem("zect_active_repo_id", String(repo.id));
    } else {
      localStorage.removeItem("zect_active_repo_id");
    }
  }, []);

  const repoFullName = activeRepo ? `${activeRepo.owner}/${activeRepo.repo_name}` : null;

  const repoContextString = activeRepo
    ? `Repository: ${activeRepo.owner}/${activeRepo.repo_name} (branch: ${activeRepo.default_branch})`
    : null;

  return (
    <ActiveProjectContext.Provider
      value={{
        projects,
        activeProject,
        activeRepo,
        loading,
        setActiveProject,
        setActiveRepo,
        refreshProjects: fetchProjects,
        repoFullName,
        repoContextString,
      }}
    >
      {children}
    </ActiveProjectContext.Provider>
  );
}

export function useActiveProject() {
  return useContext(ActiveProjectContext);
}

/** Persist Developer Workspace authorized roots (subset of project repos). Never stores secrets. */

export const WORKSPACE_ROOTS_KEY = "zect_ws_roots";

export type WorkspaceRootsStore = {
  excludedByProject: Record<string, number[]>;
};

type ProjectRepo = {
  repo_id: number;
  project_id: number;
};

function emptyStore(): WorkspaceRootsStore {
  return { excludedByProject: {} };
}

export function loadWorkspaceRootsStore(): WorkspaceRootsStore {
  try {
    const raw = JSON.parse(localStorage.getItem(WORKSPACE_ROOTS_KEY) || "{}") as Record<string, unknown>;
    const excluded = raw.excludedByProject;
    if (!excluded || typeof excluded !== "object") return emptyStore();
    const excludedByProject: Record<string, number[]> = {};
    for (const [key, value] of Object.entries(excluded as Record<string, unknown>)) {
      if (!Array.isArray(value)) continue;
      excludedByProject[key] = value.map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0);
    }
    return { excludedByProject };
  } catch {
    return emptyStore();
  }
}

export function saveWorkspaceRootsStore(store: WorkspaceRootsStore): void {
  try {
    localStorage.setItem(WORKSPACE_ROOTS_KEY, JSON.stringify(store));
  } catch {
    /* ignore quota */
  }
}

export function excludedRootIds(projectId: number | null): number[] {
  if (projectId == null) return [];
  return loadWorkspaceRootsStore().excludedByProject[String(projectId)] || [];
}

export function excludeWorkspaceRoot(projectId: number, repoId: number): number[] {
  const store = loadWorkspaceRootsStore();
  const key = String(projectId);
  const next = Array.from(new Set([...(store.excludedByProject[key] || []), repoId]));
  store.excludedByProject[key] = next;
  saveWorkspaceRootsStore(store);
  return next;
}

export function includeWorkspaceRoot(projectId: number, repoId: number): number[] {
  const store = loadWorkspaceRootsStore();
  const key = String(projectId);
  const next = (store.excludedByProject[key] || []).filter((id) => id !== repoId);
  store.excludedByProject[key] = next;
  saveWorkspaceRootsStore(store);
  return next;
}

export function visibleProjectRepos<T extends ProjectRepo>(
  projectId: number | null,
  repos: T[],
  excluded: number[] = excludedRootIds(projectId),
): T[] {
  if (projectId == null) return [];
  const hide = new Set(excluded);
  return repos.filter((repo) => repo.project_id === projectId && !hide.has(repo.repo_id));
}

export type KeepZoasProject = {
  id: number;
  name: string;
  repos?: Array<{ owner?: string; repo_name?: string }>;
};

export function isZoasKeepProject(project: KeepZoasProject): boolean {
  const name = (project.name || "").trim().toLowerCase();
  if (name === "zoas" || name === "zoas eval") return true;
  return (project.repos || []).some((r) => {
    const owner = (r.owner || "").trim().toLowerCase();
    const repo = (r.repo_name || "").trim().toLowerCase();
    return repo === "zoas" || `${owner}/${repo}` === "zinnia/zoas";
  });
}

/** Projects that may be bulk-deleted. Never includes zoas keep-list or the active zoas project. */
export function projectsToDeleteKeepingZoas(
  projects: KeepZoasProject[],
  activeProjectId: number | null,
): KeepZoasProject[] {
  return projects.filter((p) => {
    if (isZoasKeepProject(p)) return false;
    if (activeProjectId != null && p.id === activeProjectId && isZoasKeepProject(p)) return false;
    return true;
  });
}

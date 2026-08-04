/** Shared repo → Lattice project_key and Mentrix workspace localStorage helpers. */

export interface MentrixWorkspace {
  path: string;
  workspace: string;
  project_key: string;
  projectKey: string;
}

export function deriveProjectKey(owner: string, repo: string): string {
  return `${owner}-${repo}`.toLowerCase().replace(/[^a-z0-9._-]+/g, "-");
}

/**
 * Context Store's rows are unique on (user_id, page, key) only — no project
 * scoping. Ask/Plan used a bare page like "workspace", so whichever repo's
 * blueprint was generated/loaded last kept showing up regardless of which
 * project you'd since switched to. Fold projectKey into the page so each
 * project gets its own slot.
 */
export function contextPageFor(base: string, projectKey: string): string {
  return projectKey ? `${base}:${projectKey}` : base;
}

export function readMentrixWorkspace(): MentrixWorkspace | null {
  try {
    const raw = localStorage.getItem("zect_mentrix_workspace");
    if (!raw) return null;
    const ws = JSON.parse(raw) as Partial<MentrixWorkspace>;
    const projectKey = ws.project_key || ws.projectKey;
    const path = ws.path || ws.workspace;
    if (!projectKey || !path) return null;
    return {
      path,
      workspace: path,
      project_key: projectKey,
      projectKey,
    };
  } catch {
    return null;
  }
}

export function writeMentrixWorkspace(path: string, projectKey: string): void {
  try {
    localStorage.setItem(
      "zect_mentrix_workspace",
      JSON.stringify({
        path,
        workspace: path,
        project_key: projectKey,
        projectKey,
      }),
    );
    localStorage.setItem("zect_lattice_key", projectKey);
  } catch {
    /* ignore quota errors */
  }
}

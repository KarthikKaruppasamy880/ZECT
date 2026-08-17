/** Persist safe Developer Workspace session — never stores tokens or secrets. */

export const WORKSPACE_SESSION_KEY = "zect_ws_session";

export type WorkspaceEditorTab = {
  repoId: number;
  path: string;
};

export type WorkspaceTerminalSession = {
  id: string;
  repoId: number;
  rootPath: string;
  label: string;
};

export type WorkspaceSession = {
  openEditors: WorkspaceEditorTab[];
  terminals: WorkspaceTerminalSession[];
  activeTerminalId: string | null;
  workItemId: number | null;
  projectId: number | null;
  activeRepoId: number | null;
};

function emptySession(): WorkspaceSession {
  return {
    openEditors: [],
    terminals: [],
    activeTerminalId: null,
    workItemId: null,
    projectId: null,
    activeRepoId: null,
  };
}

export function loadWorkspaceSession(): WorkspaceSession {
  try {
    const raw = JSON.parse(localStorage.getItem(WORKSPACE_SESSION_KEY) || "{}") as Record<string, unknown>;
    const openEditors = Array.isArray(raw.openEditors)
      ? raw.openEditors
          .map((row) => {
            const r = row as Record<string, unknown>;
            const repoId = Number(r.repoId);
            const path = String(r.path || "");
            if (!Number.isFinite(repoId) || repoId <= 0 || !path) return null;
            return { repoId, path };
          })
          .filter((x): x is WorkspaceEditorTab => Boolean(x))
      : [];
    const terminals = Array.isArray(raw.terminals)
      ? raw.terminals
          .map((row) => {
            const r = row as Record<string, unknown>;
            const id = String(r.id || "");
            const repoId = Number(r.repoId);
            const rootPath = String(r.rootPath || "");
            const label = String(r.label || "");
            if (!id || !Number.isFinite(repoId) || !rootPath) return null;
            return { id, repoId, rootPath, label };
          })
          .filter((x): x is WorkspaceTerminalSession => Boolean(x))
      : [];
    return {
      openEditors,
      terminals,
      activeTerminalId: typeof raw.activeTerminalId === "string" ? raw.activeTerminalId : terminals[0]?.id || null,
      workItemId: typeof raw.workItemId === "number" && raw.workItemId > 0 ? raw.workItemId : null,
      projectId: typeof raw.projectId === "number" && raw.projectId > 0 ? raw.projectId : null,
      activeRepoId: typeof raw.activeRepoId === "number" && raw.activeRepoId > 0 ? raw.activeRepoId : null,
    };
  } catch {
    return emptySession();
  }
}

export function saveWorkspaceSession(session: WorkspaceSession): void {
  try {
    localStorage.setItem(
      WORKSPACE_SESSION_KEY,
      JSON.stringify({
        openEditors: session.openEditors.slice(0, 12),
        terminals: session.terminals.slice(0, 8),
        activeTerminalId: session.activeTerminalId,
        workItemId: session.workItemId,
        projectId: session.projectId,
        activeRepoId: session.activeRepoId,
      }),
    );
  } catch {
    /* ignore quota */
  }
}

export function newTerminalSession(repoId: number, rootPath: string, label: string): WorkspaceTerminalSession {
  const id =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `term-${Date.now()}-${repoId}`;
  return { id, repoId, rootPath, label };
}
